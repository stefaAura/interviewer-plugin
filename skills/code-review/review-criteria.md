# Review Criteria — Detalle por categoría

## arquitectura

### Responsabilidades por capa (referencia rápida)

| Capa | ✅ Sí | ❌ No |
|---|---|---|
| Route | HTTP binding, auth (`Depends`), response shape | Lógica de dominio, acceso a repos, validación de estado |
| Request Handler | Valida estado del dominio, dispara task o delega | Sabe de HTTP, persiste datos, contiene lógica de negocio |
| Celery Task | Retry policy, idempotency, métricas, delegar | Lógica de negocio >30 líneas, orquestar pipelines |
| Orchestrator | Pasos A→B→C, error policies, persistencia, webhooks | Lógica pura, llamadas directas a APIs externas |
| Service | Operación pura: entrada → resultado | Persistir, enviar webhooks, decidir orden de pasos |
| Executor | Leer/escribir `PromptExecutionContext` | Persistir, conocer entities de dominio, llamar repos |
| Provider | Wrapper de API externa | Lógica de negocio, conocer domain entities |
| Repository | CRUD, queries, fetch→mutate→merge() | Lógica de negocio, llamadas a APIs |

### Imports que revelan violaciones de capa

```bash
# ¿Un service importa el repository directamente para persistir?
rg -n "from app.persistence" app/domain/services/ --include="*.py"

# ¿Un executor conoce entities del dominio?
rg -n "from app.domain.models\|from app.persistence" app/domain/prompt_execution_pipeline/executors/ --include="*.py"

# ¿Una route importa algo del dominio directamente (sin handler)?
rg -n "from app.domain.services\|from app.domain.orchestrators" app/api/routes/ --include="*.py"
```

---

## escalabilidad

### Async — errores comunes

```python
# ❌ Función async que bloquea el event loop
async def process():
    time.sleep(5)                    # bloquea todo el worker
    requests.get("https://...")      # bloquea todo el worker

# ✅ Correcto
async def process():
    await asyncio.sleep(5)
    async with httpx.AsyncClient() as client:
        await client.get("https://...")
```

```python
# ❌ Awaitable no awaiteado (bug silencioso, Python no lanza error)
async def run():
    result = service.process(id)     # olvidaste await → result es una coroutine, no el resultado

# ✅
async def run():
    result = await service.process(id)
```

### SQLAlchemy — N+1 queries

```python
# ❌ N+1 — una query por each conversation
conversations = repo.get_all()
for conv in conversations:
    print(conv.agent.name)   # lazy load dispara SELECT por cada item

# ✅ Eager loading
conversations = db.query(Conversation).options(joinedload(Conversation.agent)).all()

# ❌ Cargar toda la tabla
entities = db.query(MyModel).all()   # si la tabla tiene 100k rows → OOM

# ✅ Paginar o limitar
entities = db.query(MyModel).filter(...).limit(1000).all()
```

### Celery — diseño para fiabilidad

```python
# ❌ Task no idempotente
@celery_app.task
def process(entity_id):
    entity = repo.get(entity_id)
    entity.count += 1               # si se reintenta 3 veces, count += 3
    repo.save(entity)

# ✅ Idempotente con estado
@celery_app.task
def process(entity_id):
    entity = repo.get(entity_id)
    if entity.status == "completed":
        return                       # ya procesado, salir sin efecto
    # ... procesar
    entity.status = "completed"
    repo.save(entity)
```

### Concurrencia — locks en Celery

Si una task puede correrse en paralelo para el mismo `entity_id`:
```python
# Usar advisory lock de PostgreSQL (ya existe en el proyecto)
from app.core.utils.db_lock import acquire_advisory_lock

@celery_app.task(bind=True, acks_late=True)
def process(self, entity_id: str):
    with acquire_advisory_lock(entity_id):
        orchestrator = container.my_orchestrator()
        asyncio.run(orchestrator.run(UUID(entity_id)))
```

---

## mantenibilidad

### Principio de responsabilidad única (SRP)

Señales de violación:
- Una clase tiene >3 dependencias en `__init__` → probablemente hace demasiado
- Un método hace A, luego B, luego C sin delegación → extraer métodos privados
- El nombre de la clase incluye "And" o "And" conceptualmente → dividir

```python
# ⚠️ Clase que hace demasiado
class ConversationProcessor:
    def process(self, id):
        # 1. Descarga de S3
        # 2. Transcripción
        # 3. Score de calidad
        # 4. MNPI check
        # 5. Envío de email
        # 6. Webhook a frontend
        ...

# ✅ Orquestador + servicios especializados
class ConversationOrchestrator:
    async def run(self, id):
        audio = await self._step_download(id)
        transcript = await self._step_transcribe(audio)
        scores = await self._step_score(transcript)
        await self._step_notify(id, scores)
```

### Nombres — convenciones del proyecto

| Tipo | Convención | Ejemplo |
|---|---|---|
| Orchestrator | `<Nombre>Orchestrator` | `Mp3ImportOrchestrator` |
| Service | `<Nombre>Service` | `GenerativeAiService` |
| Repository | `<Nombre>Repository` | `ConversationRepository` |
| Provider | `<Nombre>Provider` | `OpenAiProvider` |
| Executor | `<Nombre>Executor` | `MNPIAnalysisExecutor` |
| Task | `process_<nombre>` | `process_mp3_import` |
| Handler | `<Nombre>Handler` | `InterviewAutoEditHandler` |

### Dependency Injection — testabilidad

```python
# ❌ Hard dependency — no se puede testear sin OpenAI
class SomeService:
    def __init__(self):
        self._client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)  # directo

# ✅ Inyectado — en tests se pasa un mock
class SomeService:
    def __init__(self, provider: OpenAiProvider) -> None:
        self._provider = provider
```

Corolario: si una clase NO puede testearse sin infraestructura real (DB, APIs) → le falta DI.

---

## patrones-especificos

### JSONB — merge_metadata detallado

```python
from app.core.utils.metadata_utils import merge_metadata

# ❌ NUNCA — sobrescribe todas las claves
conversation.agent_metadata = {"video_status": "triggered"}
db.merge(conversation)

# ✅ SIEMPRE — merge seguro clave por clave
merge_metadata(conversation, {"video_status": "triggered"})
db.merge(conversation)
```

Aplica a TODOS los campos JSONB del proyecto:
- `Conversation.agent_metadata`
- `Conversation.meta`
- `Conversation.analysis`
- `ConversationRevision.meta`
- `ConversationRevision.analysis`
- `Agent.agent_metadata`

### Prompts — cuándo va en DB vs template

| Condición | Usar |
|---|---|
| El prompt se edita desde el admin panel | DB-backed (`generative_ai_service` + tipo "mnpi", "cleanup", etc.) |
| El prompt es parte de un Executor del pipeline | Template file `app/domain/prompts/templates/<nombre>_prompt.txt` |
| Se versiona junto al código | Template file |
| Lo edita un no-developer | DB-backed |

Template file — convenciones:
```
{{DOUBLE_BRACES}} para variables   # nunca {single} ni f-strings
```

### Alembic — checklist de seguridad

```python
# ❌ NOT NULL sin default en tabla con datos
op.add_column("conversations", sa.Column("score", sa.Integer(), nullable=False))

# ✅ Nullable primero → backfill → NOT NULL
def upgrade():
    op.add_column("conversations", sa.Column("score", sa.Integer(), nullable=True))
    op.execute("UPDATE conversations SET score = 0 WHERE score IS NULL")
    op.alter_column("conversations", "score", nullable=False)

# ❌ DROP sin verificar uso
op.drop_column("conversations", "old_field")   # ¿alguien lo usa en producción?

# ✅ Primero deprecar, luego en siguiente release eliminar

# ❌ FK sin índice
op.add_column("revisions", sa.Column("conversation_id", sa.UUID(), sa.ForeignKey("conversations.id")))

# ✅
op.add_column("revisions", sa.Column("conversation_id", sa.UUID(), sa.ForeignKey("conversations.id")))
op.create_index("ix_revisions_conversation_id", "revisions", ["conversation_id"])
```

### Import circulares — cómo detectar

```bash
# Verificar imports de un módulo nuevo
python -c "from app.<modulo> import <Clase>"

# Si falla con ImportError circular → reorganizar
# Solución común: mover el import dentro de la función que lo usa (lazy import)
# O crear un módulo intermedio de tipos/interfaces
```

---

## tests

### Estructura esperada por tipo

```
tests/
  unit/
    services/
      test_<nombre>_service.py      ← mock de providers, sin DB
    orchestrators/
      test_<nombre>_orchestrator.py ← mock de services y repos
    providers/
      test_<nombre>_provider.py     ← mock del cliente HTTP
    executors/
      test_<nombre>_executor.py     ← mock de provider, verifica context
  integration/
    api/
      test_<nombre>_endpoint.py     ← FastAPI TestClient, DB real
    repositories/
      test_<nombre>_repository.py   ← DB real, fixtures con factory
```

### Patrón correcto para unit tests async

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
class TestMyService:
    def setup_method(self):
        self.provider = AsyncMock(spec=MyProvider)
        self.service = MyService(provider=self.provider)

    async def test_process_happy_path(self):
        self.provider.get_data.return_value = {"result": "ok"}
        result = await self.service.process(entity_id=uuid4())
        assert result.status == "completed"
        self.provider.get_data.assert_called_once()

    async def test_process_provider_error(self):
        self.provider.get_data.side_effect = ProviderError("timeout")
        with pytest.raises(ProviderError):
            await self.service.process(entity_id=uuid4())
```

### ¿Qué NO mockear?

- **No mockear** el código que se está testeando (solo sus dependencias)
- **No mockear** los modelos Pydantic (son datos puros, testear directamente)
- **No mockear** `merge_metadata` — testear con objetos reales que tengan el campo JSONB
