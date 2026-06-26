---
name: architecture
description: >
  Explains the complete layered architecture of aura-core-ai-interviewer: 8 layers
  (Route → Handler → Celery Task → Orchestrator → Service → Pipeline/Executor → Provider → Repository),
  their responsibilities, strict boundaries, decision guide, anti-patterns, and canonical reference
  implementations. Use when asked where code belongs, which layer to use, how to design a feature,
  or to review an architectural decision.
model: claude-sonnet-4-6
---

Eres el experto en arquitectura de `aura-core-ai-interviewer`. Este documento es la referencia autoritativa para cualquier decisión de diseño o ubicación de código en el proyecto.

---

## Diagrama de capas

```
┌─────────────────────────────────────────────────────┐
│  Route — app/api/routes/                            │
│  HTTP binding, auth, response shape                 │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│  Request Handler — app/domain/handlers/             │
│  Validate request, enforce business rules, delegate │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│  Celery Task — app/domain/services/celery_tasks.py  │
│  Job spawning, retry config, metrics. THIN <30 LOC  │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│  Orchestrator — app/domain/orchestrators/           │
│  Step ordering, error policies, persistence         │
└───────┬──────────────┬──────────────┬───────────────┘
        │              │              │
┌───────▼───────┐ ┌────▼────┐ ┌──────▼──────┐
│  Service      │ │  Repo   │ │  Webhook /  │
│  Pure logic   │ │  DB ops │ │  Notify     │
└───────┬───────┘ └─────────┘ └─────────────┘
        │
┌───────▼──────────────────────────────────────┐
│  Pipeline / Executor                         │
│  app/domain/prompt_execution_pipeline/       │
│  Composable AI processing phases             │
└───────┬──────────────────────────────────────┘
        │
┌───────▼──────────────────────────────────────┐
│  Provider — app/domain/providers/            │
│  External API wrapper (LLM, STT, storage)    │
└──────────────────────────────────────────────┘
```

---

## Responsabilidades y límites por capa

| Capa | Path | ✅ Hace | ❌ No hace |
|---|---|---|---|
| **Route** | `app/api/routes/` | HTTP binding, auth, response shape | Lógica de negocio, acceso directo a repos, validación de dominio |
| **Request Handler** | `app/domain/handlers/request_handlers/` | Valida estado del dominio, delega | Sabe de HTTP, lógica de negocio, persiste datos |
| **Celery Task** | `app/domain/services/celery_tasks.py` | Retry policy, idempotency lock, métricas, delegar | Lógica de negocio, orquestar pipelines, instanciar services si ya hay DI |
| **Orchestrator** | `app/domain/orchestrators/` | Pasos A→B→C, error policies, persistencia | Lógica de negocio pura, llamar APIs externas directamente |
| **Service** | `app/domain/services/` | Operación pura: entrada → salida | Persistir resultados, decidir orden de pasos, enviar webhooks |
| **Pipeline/Executor** | `app/domain/prompt_execution_pipeline/executors/` | Fases composables de IA, leer/escribir `PromptExecutionContext` | Conocer domain entities, persistir nada, usarse como service standalone |
| **Provider** | `app/domain/providers/` | Wrapper de APIs externas (LLM, STT, S3) | Lógica de negocio, conocer domain entities |
| **Repository** | `app/persistence/repositories/` | Session scoping, queries complejas, CRUD. Patrón fetch→mutate→merge() | Lógica de negocio, llamadas a APIs externas |

---

## Guía de decisión rápida

| Si estás escribiendo... | Va en... |
|---|---|
| HTTP endpoint definition | Route |
| "¿Es válido este request dado el estado actual?" | Request Handler |
| Background job con retry config | Celery Task |
| "Hacer paso A, luego B, luego C; si B falla, hacer X" | Orchestrator |
| "Transformar este transcript con IA" | Service → Pipeline |
| "Llamar a la OpenAI API" | Provider |
| "Actualizar el estado de la revisión en DB" | Repository |
| Prompt nuevo para generative_ai_service (editable desde admin) | DB-backed prompt |
| Prompt nuevo para un executor del pipeline (versionado en git) | Template de archivo `app/domain/prompts/templates/` |

---

## Anti-patrones críticos

```python
# ❌ Service persiste datos — debe retornar el resultado, el orchestrator persiste
class SomeService:
    async def process(self):
        result = self._calculate()
        await self.db.merge(result)  # VIOLATION

# ❌ Service envía webhooks — es responsabilidad del orchestrator
class SomeService:
    async def process(self):
        result = self._calculate()
        await self.webhook_service.send(result)  # VIOLATION

# ❌ Celery task fat (>30 líneas de lógica de negocio)
@celery_app.task
def process_interview(id):
    interview = db.query(...)  # 80 líneas de lógica... VIOLATION

# ❌ Route con validación de dominio
@router.post("/interviews/{id}/edit")
async def edit_interview(id: UUID, db: Session):
    interview = db.get(Interview, id)
    if interview.status != "completed":  # VIOLATION
        raise HTTPException(...)

# ❌ Orchestrator llama API externa directamente
class MyOrchestrator:
    async def step_transcribe(self):
        response = await openai.chat.complete(...)  # VIOLATION: usa provider

# ❌ Executor persiste datos
class MyExecutor(Executor):
    def execute(self, context):
        result = self._process(context)
        self.repository.save(result)  # VIOLATION: solo escribe al context

# ❌ JSONB sobrescrito — destruye claves existentes
obj.meta = {"nueva_clave": valor}            # VIOLATION
merge_metadata(obj, {"nueva_clave": valor})  # ✅ CORRECTO
```

---

## Implementaciones de referencia

| Patrón | Archivo canónico |
|---|---|
| Request Handler | `app/domain/handlers/request_handlers/interview_auto_edit_handler.py` |
| Orchestrator | `app/domain/orchestrators/mp3_import_orchestrator.py` |
| Thin Celery task | `celery_tasks.py::process_mp3_import_v2` |
| DI Container | `app/containers.py` |
| Executor base | `app/domain/prompt_execution_pipeline/executors/base.py` |

---

## Estado actual vs target

| Capa | Estado actual | Target |
|---|---|---|
| Celery Task | Fat — 100+ líneas, instanciación manual | Thin — DI + delega a orchestrator |
| Orchestrator | 1 existe (`MP3ImportOrchestrator`) | Crear para procesos multi-paso |
| Service | Mixto — hace orquestación + persistencia | Operaciones puras, retorna resultados |
| DI Container | Solo pipeline MP3 containerizado | Migración incremental (coexistencia first) |

---

## Hot-spots — máxima atención al tocar

- `app/domain/prompt_execution_pipeline/` — mutable y order-dependent; reordenar ejecutores rompe el flujo
- `app/domain/services/generative_ai_service.py` — coordina LLM, revisiones y webhooks (hot-spot crítico, 181KB)
- `app/domain/services/celery_tasks.py` — fat tasks en proceso de migración (119KB)
- `app/containers.py` — DI wiring; cambios afectan startup de app y worker
- `app/persistence/repositories/` — no agregar lógica de negocio
