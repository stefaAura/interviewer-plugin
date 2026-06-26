---
name: new-feature
description: >
  Step-by-step workflow to implement a new feature in aura-core-ai-interviewer following
  the 8-layer architecture. Includes reuse-first search, layer selection, bottom-up file
  creation with validation, DI registration, and test identification. Use when starting
  any new feature, endpoint, background job, or pipeline addition.
argument-hint: "[feature description]"
model: claude-opus-4-8
---

# Nueva Feature: $ARGUMENTS

Sigue estos pasos en orden. Copia la lista y márcalos al avanzar.

```
Progreso:
- [ ] Paso 1: Reuse-first — buscar antes de crear
- [ ] Paso 2: Determinar capas necesarias
- [ ] Paso 3: Crear archivos (bottom-up)
- [ ] Paso 4: Registrar en DI container
- [ ] Paso 5: Validación de capas
- [ ] Paso 6: Identificar tests
```

---

## Paso 1 — Reuse-first (siempre primero)

Antes de crear cualquier archivo, busca código existente:

```bash
# Por concepto/dominio
rg -ti -g '*.py' '$ARGUMENTS' app/core/utils app/domain app/persistence

# Por tipo de operación (ajusta el verbo)
rg -ti -g '*.py' 'def .*(process|handle|create|get|update).*' app/domain/services app/persistence/repositories
```

**Helpers que YA EXISTEN — no recrear:**
- `filename_parser`, `language_utils`, `document_service`, `word_document_service` → `app/core/utils/`
- `celery_task_decorator` → `app/core/utils/celery_task_decorator.py`
- `slack_service`, `teams_service`, `sendgrid_provider` → notificaciones ya cubiertas

**Reporta lo encontrado antes de continuar.** Si existe algo similar, planifica extenderlo.

---

## Paso 2 — Determinar capas necesarias

Responde estas preguntas para saber qué crear:

| Pregunta | Si sí → necesitas |
|---|---|
| ¿Hay un nuevo endpoint HTTP? | Route + Schema Pydantic |
| ¿Hay validación de estado de dominio antes de disparar? | Request Handler |
| ¿El trabajo es asíncrono / larga duración? | Celery Task + Orchestrator |
| ¿El flujo tiene 3+ pasos con error policies distintas? | Orchestrator |
| ¿Hay lógica de negocio pura (transformación, cálculo)? | Service |
| ¿Hay procesamiento IA multi-fase? | Pipeline + Executor(es) |
| ¿Hay una API externa nueva (LLM, STT, storage)? | Provider |
| ¿Hay cambio de schema de DB? | Migration Alembic + Repository |

**Regla:** No crees capas que no se necesitan. Un fix de una línea no necesita orchestrator.

Para más detalle de cada capa → lee [layers-reference.md](layers-reference.md).

---

## Paso 3 — Crear archivos (bottom-up)

Crea en este orden. Solo los que necesitas según el Paso 2.

### 3a. Modelos y DTOs
```
app/domain/models/<nombre>.py      ← Pydantic models / dataclasses del dominio
app/api/schemas/<nombre>.py        ← Request/Response schemas Pydantic para la API
```

### 3b. Migration (si hay cambio de schema)
```bash
uv run alembic revision --autogenerate -m "add_<descripcion>"
```
Revisa el archivo generado en `alembic/versions/`. Verifica:
- ¿Columna NOT NULL sin `server_default`? → Hacer nullable primero, backfill, luego NOT NULL
- ¿Nueva FK? → Agregar `op.create_index` en la misma migración
- ¿El `downgrade()` revierte exactamente el `upgrade()`?

### 3c. Repository (si hay nuevas queries)
```
app/persistence/repositories/<nombre>_repository.py
```
Patrón: `fetch → mutate → db.merge()`. Para JSONB siempre `merge_metadata()`, nunca asignación directa.

### 3d. Provider (si hay nueva API externa)
```
app/domain/providers/<nombre>_provider.py
```
Template en [layers-reference.md](layers-reference.md) → sección Provider.

### 3e. Service
```
app/domain/services/<nombre>_service.py
```
Operación pura: recibe parámetros, retorna resultado. **No persiste. No envía webhooks.**

### 3f. Executor(es) (si hay procesamiento IA multi-fase)
```
app/domain/prompt_execution_pipeline/executors/<nombre>_executor.py
app/domain/prompts/templates/<nombre>_prompt.txt
```
Lee `app/domain/prompt_execution_pipeline/README.md` — el pipeline es order-dependent y mutable.
Registra en `pipelines.py` → factory function del pipeline correspondiente.

### 3g. Orchestrator (si el flujo tiene 3+ pasos)
```
app/domain/orchestrators/<nombre>_orchestrator.py
```
Cada paso = método privado `_step_X()`. Template en [layers-reference.md](layers-reference.md).

### 3h. Celery Task (si el trabajo es async)
Agrega en `app/domain/services/celery_tasks.py`:
```python
@celery_app.task(bind=True, max_retries=3, default_retry_delay=60, name="tasks.<nombre>")
@track_task_metrics
def process_<nombre>(self, entity_id: str) -> None:
    """Thin task — <30 líneas."""
    orchestrator = container.<nombre>_orchestrator()
    asyncio.run(orchestrator.run(UUID(entity_id)))
```

### 3i. Request Handler (si hay validación de estado)
```
app/domain/handlers/request_handlers/<nombre>_handler.py
```
Referencia: `interview_auto_edit_handler.py`.

### 3j. Route
```
app/api/routes/<nombre>.py
```
Solo: binding HTTP, auth con `Depends()`, delegar al handler. Sin lógica de negocio.
Registrar en `app/api/main.py`: `app.include_router(router, prefix="/api/<nombre>")`.

---

## Paso 4 — Registrar en DI container

Si creaste un Provider, Service, u Orchestrator nuevo, agrégalo en `app/containers.py`:

```python
# Orden: providers → repositories → services → orchestrators
<nombre>_provider = providers.Singleton(<NombreProvider>)

<nombre>_service = providers.Singleton(
    <NombreService>,
    provider=<nombre>_provider,
    repository=repository.<nombre>_repository,
)

<nombre>_orchestrator = providers.Factory(
    <NombreOrchestrator>,
    service=<nombre>_service,
    repository=repository.<nombre>_repository,
)
```

Si la route o la celery task usan el container, agrega el wiring en:
- Routes → `app/api/main.py` → `container.wire(modules=[...])`
- Tasks → `app/celery_worker.py`

---

## Paso 5 — Validación de capas

Antes de terminar, revisa cada archivo creado contra esta lista:

```
Checklist de validación:
- [ ] ¿El service hace db.merge() o db.flush()? → ERROR: mueve la persistencia al orchestrator
- [ ] ¿El service llama webhook_service.send()? → ERROR: es responsabilidad del orchestrator
- [ ] ¿La route tiene validación de dominio (if entity.status != ...)? → ERROR: mueve al handler
- [ ] ¿El Celery task tiene >30 líneas de lógica? → ERROR: extrae a orchestrator
- [ ] ¿El orchestrator llama openai / anthropic / boto3 directamente? → ERROR: usa provider
- [ ] ¿El executor llama al repository para persistir? → ERROR: solo escribe al context
- [ ] ¿Hay obj.meta = {...} en algún lugar? → ERROR: usa merge_metadata()
- [ ] ¿Hay secrets hardcodeados? → ERROR: usa get_settings().<API_KEY>
- [ ] ¿El executor tiene el prompt hardcodeado? → ERROR: mueve a app/domain/prompts/templates/
```

Si detectas violaciones, corrígelas antes de continuar.

---

## Paso 6 — Tests necesarios

Identifica qué cubrir:

| Qué creaste | Tests a escribir |
|---|---|
| Service | Unit test: happy path + edge cases + error cases |
| Orchestrator | Unit test con mocks de service y repo |
| Provider | Unit test mockeando el cliente de la API externa |
| Repository | Integration test con DB real |
| Route | Integration test del endpoint completo |
| Executor | Unit test del pipeline context antes/después |

Coverage mínimo: **85%**. Crea los tests o invoca `/aura-dev:add-test <archivo>`.
