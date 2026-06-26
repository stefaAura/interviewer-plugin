# Refactoring Patterns — aura-core-ai-interviewer

## slim-fat-task

**Síntoma:** Celery task con >30 líneas de lógica de negocio.

**Pasos:**
1. Leer la task completa e identificar qué va dónde:
   - Se queda en la task: `@celery_app.task`, `@track_task_metrics`, `self.retry(exc=exc)`, idempotency lock
   - Va al orchestrator: lógica de negocio, llamadas a services/repos, webhooks/notificaciones

2. Crear el orchestrator ANTES de tocar la task:
```python
# app/domain/orchestrators/<nombre>_orchestrator.py
class <Nombre>Orchestrator:
    def __init__(self, service: <Nombre>Service, repository: <Nombre>Repository) -> None:
        self._service = service
        self._repository = repository

    async def run(self, entity_id: UUID) -> None:
        # Mover aquí toda la lógica extraída de la task
        ...
```

3. Reducir la task a <30 líneas:
```python
@celery_app.task(bind=True, max_retries=3, default_retry_delay=60, name="tasks.<nombre>", acks_late=True)
@track_task_metrics
def process_<nombre>(self, entity_id: str) -> None:
    try:
        orchestrator = container.<nombre>_orchestrator()
        asyncio.run(orchestrator.run(UUID(entity_id)))
    except Exception as exc:
        logger.exception("Error en process_<nombre> entity_id=%s", entity_id)
        raise self.retry(exc=exc)
```

4. Registrar orchestrator en `app/containers.py`.

**Referencia canónica:** `process_mp3_import_v2` + `mp3_import_orchestrator.py`

---

## service-no-persiste

**Síntoma:** Un service hace `db.merge()`, `db.flush()`, o `db.add()`.

**Antes (incorrecto):**
```python
class SomeService:
    async def process(self, entity):
        result = self._calculate(entity)
        self._db.merge(result)   # ❌ VIOLATION
        return result
```

**Después (correcto):**
```python
# Service — solo retorna, no persiste
class SomeService:
    async def process(self, entity) -> ResultType:
        return self._calculate(entity)

# Orchestrator — persiste el resultado
class SomeOrchestrator:
    async def _step_persist(self, entity_id, result) -> None:
        await self._repository.update(entity_id, result)
```

**Pasos:**
1. Elimina el `db` del `__init__` del service
2. Cambia el return type del método para retornar el resultado
3. En el orchestrator (o crealo si no existe), agrega un `_step_persist()` que llame al repository

---

## service-no-webhook

**Síntoma:** Un service llama `webhook_service.send()`, `slack_service.notify()`, o `teams_service.send()`.

**Antes (incorrecto):**
```python
class SomeService:
    async def process(self, entity):
        result = self._calculate(entity)
        await self._webhook_service.send(result)   # ❌ VIOLATION
        return result
```

**Después (correcto):**
```python
# Service — solo retorna
class SomeService:
    async def process(self, entity) -> ResultType:
        return self._calculate(entity)

# Orchestrator — decide si notificar y cómo
class SomeOrchestrator:
    async def run(self, entity_id: UUID) -> None:
        entity = await self._step_load(entity_id)
        result = await self._step_process(entity)
        await self._step_persist(entity_id, result)
        await self._step_notify(result)   # ✅ orquestador notifica

    async def _step_notify(self, result) -> None:
        if result.requires_review:
            await self._slack_service.notify(...)
```

---

## migrate-to-di

**Síntoma:** Un service o provider se instancia manualmente dentro de una Celery task o route.

```python
# ❌ Instanciación manual en la task
def process_interview(self, id):
    service = GenerativeAiService(db=get_db(), openai_key=settings.OPENAI_API_KEY)
    service.process(id)
```

**Pasos:**
1. Verificar que no esté ya en el container:
```bash
rg -n "<NombreServicio>" app/containers.py
```

2. Agregar al container en orden (providers → repositories → services → orchestrators):
```python
# app/containers.py
<nombre>_service = providers.Singleton(
    <Nombre>Service,
    repository=repository.<nombre>_repository,
)
```

3. Agregar wiring donde se consume:
```python
# Si se consume en routes → en app/api/main.py:
container.wire(modules=["app.api.routes.<nombre>"])

# Si se consume en celery tasks → en app/celery_worker.py:
container.wire(modules=["app.domain.services.celery_tasks"])
```

4. Usar `@inject` + `Provide` en el punto de consumo:
```python
from dependency_injector.wiring import inject, Provide

@celery_app.task(...)
@inject
def process_<nombre>(
    self,
    entity_id: str,
    service: <Nombre>Service = Provide[Container.<nombre>_service],
) -> None:
    asyncio.run(service.process(UUID(entity_id)))
```

5. Coexistencia: **NO elimines la instanciación manual** hasta validar en DEV.

6. Test de wiring: `tests/api/dependencies/test_di_wiring.py` — corre en CI.

---

## fix-jsonb

**Síntoma:** Asignación directa a campo JSONB: `obj.meta = {...}` o `obj.analysis = {...}`.

**El bug:** Sobrescribe TODAS las claves existentes en el JSON, destruyendo datos.

**Antes (incorrecto):**
```python
conversation.meta = {"mnpi_score": 5}   # ❌ Destruye todo lo que había en meta
```

**Después (correcto):**
```python
from app.core.utils.metadata_utils import merge_metadata

merge_metadata(conversation, {"mnpi_score": 5})   # ✅ Merge atómico
self._db.merge(conversation)
```

**Buscar todas las ocurrencias:**
```bash
rg -n "\.meta\s*=\s*{" app/ --include="*.py"
rg -n "\.analysis\s*=\s*{" app/ --include="*.py"
rg -n "\.agent_metadata\s*=\s*{" app/ --include="*.py"
```

---

## prompt-template

**Síntoma:** Prompt hardcodeado en un executor, service, o como string literal en el código.

**Regla:** Executors del pipeline → template de archivo. `generative_ai_service` → DB-backed.

**Antes (incorrecto en executor):**
```python
class MyExecutor(Executor):
    PROMPT = "Analyze the following transcript: {text}\n\nProvide..."  # ❌
```

**Después (correcto):**
```python
# app/domain/prompts/templates/my_executor_prompt.txt
Analyze the following transcript: {{text}}
Provide...

# executor
from pathlib import Path

class MyExecutor(Executor):
    def _load_prompt(self) -> str:
        return (
            Path(__file__).parent.parent.parent
            / "prompts/templates/my_executor_prompt.txt"
        ).read_text()
```

**Convención de placeholders:** `{{DOUBLE_BRACES}}` — nunca f-strings en templates.

---

## route-clean

**Síntoma:** Una route valida el estado del dominio (ej. `if entity.status != "completed"`).

**Antes (incorrecto):**
```python
@router.post("/interviews/{id}/edit")
async def edit_interview(id: UUID, db: Session = Depends(get_db)):
    interview = db.get(Interview, id)
    if interview is None:                        # ❌ validación de dominio en route
        raise HTTPException(404)
    if interview.status != "completed":          # ❌
        raise HTTPException(409)
    process_interview.delay(str(id))
    return {"status": "processing"}
```

**Después (correcto):**
```python
# Route — solo delega
@router.post("/interviews/{id}/edit")
async def edit_interview(id: UUID, db: Session = Depends(get_db)):
    handler = InterviewEditHandler(repository=InterviewRepository(db))
    handler.handle(id)
    return {"status": "processing"}

# Request Handler — valida
class InterviewEditHandler:
    def handle(self, interview_id: UUID) -> None:
        interview = self._repository.get_by_id(interview_id)
        if interview is None:
            raise HTTPException(status_code=404)
        if interview.status != "completed":
            raise HTTPException(status_code=409, detail=f"Estado inválido: {interview.status}")
        process_interview.delay(str(interview_id))
```

**Referencia:** `interview_auto_edit_handler.py`

---

## retries-en-vuelo

**Problema:** Si hay Celery tasks con `acks_late=True` corriendo en producción cuando haces deploy de un refactor, pueden ejecutar la versión vieja del código o la nueva, causando inconsistencias.

**Estrategia segura:**
1. Agrega el nuevo orchestrator sin eliminar la lógica vieja de la task
2. Despliega con feature flag o verificando que no haya tasks en cola:
   ```bash
   # Ver tasks en cola
   uv run celery -A app.celery_worker inspect active
   uv run celery -A app.celery_worker inspect reserved
   ```
3. Solo cuando la cola está vacía, elimina la lógica vieja de la task
4. Despliega el cleanup

**Para tasks no-críticas:** puedes hacer el switch directo si el retry es idempotente (la task puede reejecutarse desde cero sin efectos secundarios).
