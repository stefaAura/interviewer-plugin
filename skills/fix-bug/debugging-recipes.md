# Debugging Recipes — aura-core-ai-interviewer

Recetas por tipo de bug. Cada una indica dónde buscar, cómo reproducir, y las causas raíz más comunes.

---

## Celery — task que falla, se reintenta o queda stuck

### Dónde mirar
```bash
# La task en cuestión
rg -n "name=\"tasks.<nombre>\"\|def process_<nombre>" app/domain/services/celery_tasks.py

# Tasks/revisiones stuck (el worker tiene recovery al arrancar)
rg -n "stuck\|recover\|task_status" app/ --include="*.py"
```

### Cómo reproducir
```bash
# Ver tasks activas y reservadas
uv run celery -A app.celery_worker inspect active
uv run celery -A app.celery_worker inspect reserved

# Correr la task síncronamente para debuggear (sin worker)
uv run python -c "from app.domain.services.celery_tasks import process_x; process_x.apply(args=['<id>'])"
```

### Causas raíz comunes
| Síntoma | Causa raíz probable |
|---|---|
| Task se ejecuta 2+ veces con efectos duplicados | Falta idempotencia — `if entity.status == "completed": return` |
| Task queda en `processing` para siempre | Excepción no capturada antes de actualizar status, o `soft_time_limit` excedido |
| Retry infinito | `max_retries` no definido o `self.retry()` sin contar intentos |
| Revisión stuck tras reinicio del worker | El recovery solo recupera ciertos `task_status` — verificar el estado guardado |
| `acks_late=True` reejecuta tras crash | Esperado — la task DEBE ser idempotente |

---

## Async — coroutine no awaiteada o event loop bloqueado

### Dónde mirar
```bash
# Coroutines no awaiteadas (bug silencioso — Python no lanza error)
rg -n "= \w+\.(process|run|fetch|get|call)\(" app/domain/ --include="*.py" | rg -v "await\|asyncio.run"

# I/O bloqueante dentro de async
rg -n "time\.sleep\|requests\.\|\.read()\b" app/domain/ --include="*.py"
```

### Causas raíz comunes
```python
# ❌ Coroutine no awaiteada — result es una coroutine, no el valor
result = service.process(id)        # falta await
if result.status == "ok":           # AttributeError o comportamiento raro

# ✅
result = await service.process(id)

# ❌ Bloquea el event loop entero (afecta a todas las requests/tasks)
async def handler():
    time.sleep(5)
    requests.get(url)

# ✅
async def handler():
    await asyncio.sleep(5)
    async with httpx.AsyncClient() as client:
        await client.get(url)

# ❌ asyncio.run() dentro de un loop ya corriendo → RuntimeError
async def outer():
    asyncio.run(inner())            # "asyncio.run() cannot be called from a running event loop"

# ✅
async def outer():
    await inner()
```

---

## JSONB — pérdida de datos en meta / analysis / agent_metadata

### Síntoma
Claves que existían en un campo JSONB desaparecen tras una actualización.

### Dónde mirar
```bash
rg -n "\.meta\s*=\s*{\|\.analysis\s*=\s*{\|\.agent_metadata\s*=\s*{\|\.conversation_metadata\s*=\s*{" app/ --include="*.py"
```

### Causa raíz
```python
# ❌ Sobrescribe TODO el JSON — destruye las demás claves
conversation.agent_metadata = {"video_status": "done"}

# ✅ Merge seguro clave por clave
from app.core.utils.metadata_utils import merge_metadata
merge_metadata(conversation, {"video_status": "done"})
db.merge(conversation)
```
Campos afectados: `Conversation.meta/analysis/agent_metadata/conversation_metadata`, `ConversationRevision.meta/analysis`, `Agent.agent_metadata`.

---

## DB / SQLAlchemy — sesión, transacción, N+1

### Dónde mirar
```bash
# N+1: queries dentro de loops
rg -n "for .*:" app/persistence/ app/domain/ --include="*.py" -A6 | rg "\.query\|repository\.\|\.get\("

# Session scoping
rg -n "Session\|sessionmaker\|get_db\|db.commit\|db.rollback" app/ --include="*.py"
```

### Causas raíz comunes
| Síntoma | Causa raíz |
|---|---|
| `DetachedInstanceError` | Se accede a un objeto fuera del scope de su sesión |
| Cambios no persisten | Falta `db.commit()` o el `merge()` no se llamó |
| `StaleDataError` / lost update | Dos procesos escriben el mismo row sin lock → usar advisory lock |
| Query lentísima en producción | N+1 (query en loop) o falta índice en columna filtrada |
| Datos viejos tras update | Objeto cacheado en la sesión — `db.refresh(obj)` |

```python
# ❌ N+1
for conv in repo.get_all():
    print(conv.agent.name)          # 1 query por iteración

# ✅ Eager load
db.query(Conversation).options(joinedload(Conversation.agent)).all()
```

---

## Provider — timeout, rate limit, respuesta inesperada del LLM/API

### Dónde mirar
```bash
rg -n "class.*Provider" app/domain/providers/ --include="*.py"
rg -n "tenacity\|retry\|timeout\|RateLimit" app/domain/providers/ --include="*.py"
```

### Causas raíz comunes
| Síntoma | Causa raíz |
|---|---|
| `Timeout` esporádico | Falta `@retry` con `wait_exponential`, o timeout muy bajo |
| `RateLimitError` | Sin backoff; demasiadas requests concurrentes |
| LLM devuelve JSON inválido | Falta validación/parsing defensivo de la respuesta |
| Respuesta vacía o truncada | `max_tokens` insuficiente, o el prompt excede el context window |
| Falla solo en prod | API key distinta o env var faltante (`get_settings()`) |

```python
# Parsing defensivo de respuesta LLM
import json
try:
    data = json.loads(response_text)
except json.JSONDecodeError:
    logger.error("LLM devolvió JSON inválido: %s", response_text[:500])
    raise ProviderResponseError("Respuesta no parseable")
```

---

## Webhooks — ElevenLabs, race conditions, eventos duplicados

### Dónde mirar
```bash
rg -n "webhook\|elevenlabs\|create_or_update_conversation" app/api/routes/webhooks.py app/domain/services/conversation_service.py
```

### Causas raíz comunes
| Síntoma | Causa raíz |
|---|---|
| Conversación duplicada | Race condition entre eventos concurrentes — usar patrón `create_or_update` (fetch→insert→on-duplicate-update) |
| `expert_id` es None | No viene en el payload directo; está en `conversation_initiation_client_data.dynamic_variables.expert_id` |
| Evento procesado 2 veces | ElevenLabs reenvía webhooks — la lógica debe ser idempotente por `external_id` |
| Webhook 200 pero nada pasa | El router no matchea el `event type`; o ruta duplicada (revisar orden de registro en `api/main.py`) |
| MP3 no se guarda | Evento `post_call_audio` falla silenciosamente al subir a S3 |

```python
# Patrón race-condition safe (ya usado en el proyecto)
existing = repo.get_by_external_id(external_id)
if existing:
    repo.update(existing, data)
else:
    try:
        repo.insert(data)
    except IntegrityError:        # otro proceso insertó primero
        db.rollback()
        existing = repo.get_by_external_id(external_id)
        repo.update(existing, data)
```

---

## Pipeline / Executor — orden incorrecto o context corrupto

### Dónde mirar
```bash
rg -n "create_.*_pipeline\|executors=\[" app/domain/prompt_execution_pipeline/pipelines.py
```

### Causas raíz comunes
| Síntoma | Causa raíz |
|---|---|
| Executor recibe campo vacío del context | Un executor anterior no lo escribió, o el orden está mal en `pipelines.py` |
| Resultado de un executor se pierde | Escribió a una variable local en vez de `context.<campo>` |
| Pipeline modifica transcript cuando no debía | Confundir pipeline de análisis (no modifica) con curing (sí modifica) |
| Cambio de orden rompe todo | El pipeline es order-dependent — verificar dependencias entre executors |

---

## Migrations — Alembic falla en upgrade/downgrade

### Causas raíz comunes
| Síntoma | Causa raíz |
|---|---|
| `NotNullViolation` al migrar | Columna NOT NULL sin `server_default` en tabla con datos → nullable → backfill → NOT NULL |
| `downgrade()` falla | No revierte exactamente el `upgrade()` |
| Migración lenta bloquea la tabla | `ALTER TABLE` con lock sobre tabla grande — usar estrategia online |
| FK sin índice degrada performance | Agregar `op.create_index` en la misma migración |
