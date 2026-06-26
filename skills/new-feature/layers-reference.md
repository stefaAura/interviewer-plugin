# Layers Reference — Templates de código por capa

## Provider

```python
# app/domain/providers/<nombre>_provider.py
import logging
from typing import Any

from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config.settings.base_config import get_settings

logger = logging.getLogger(__name__)


class <Nombre>Provider:
    """Wrapper para la API de <Nombre>. Sin lógica de negocio."""

    def __init__(self) -> None:
        settings = get_settings()
        self._api_key = settings.<NOMBRE>_API_KEY  # nunca hardcodear
        self._client = <ClienteAPI>(api_key=self._api_key)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def <metodo>(self, param: str) -> dict[str, Any]:
        """Descripción breve."""
        try:
            return await self._client.<endpoint>(param)
        except <APIError> as e:
            logger.error("Error en <Nombre>Provider.<metodo>: %s", e)
            raise
```

**API key en settings:**
```python
# app/core/config/settings/base_config.py
<NOMBRE>_API_KEY: str = ""
```

---

## Repository

```python
# app/persistence/repositories/<nombre>_repository.py
import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.persistence.models.<nombre> import <NombreModel>
from app.core.utils.metadata_utils import merge_metadata

logger = logging.getLogger(__name__)


class <Nombre>Repository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_id(self, entity_id: UUID) -> <NombreModel> | None:
        return self._db.query(<NombreModel>).filter(<NombreModel>.id == entity_id).first()

    def create(self, **kwargs) -> <NombreModel>:
        entity = <NombreModel>(**kwargs)
        self._db.add(entity)
        self._db.flush()
        return entity

    def update_status(self, entity_id: UUID, status: str) -> None:
        entity = self.get_by_id(entity_id)
        if entity:
            entity.status = status
            self._db.merge(entity)

    def update_meta(self, entity_id: UUID, meta_update: dict) -> None:
        """SIEMPRE usar merge_metadata — nunca asignación directa a .meta."""
        entity = self.get_by_id(entity_id)
        if entity:
            merge_metadata(entity, meta_update)
            self._db.merge(entity)
```

---

## Service

```python
# app/domain/services/<nombre>_service.py
import logging

logger = logging.getLogger(__name__)


class <Nombre>Service:
    """Lógica pura de <descripción>. No persiste. No envía webhooks."""

    def __init__(self, provider: <Nombre>Provider) -> None:
        self._provider = provider

    async def process(self, entity) -> <ResultType>:
        """Transforma/procesa y retorna resultado. El caller persiste."""
        logger.info("Processing %s", entity.id)
        result = await self._provider.<metodo>(entity.<campo>)
        return <ResultType>(**result)
```

---

## Orchestrator

```python
# app/domain/orchestrators/<nombre>_orchestrator.py
import logging
from uuid import UUID

logger = logging.getLogger(__name__)


class <Nombre>Orchestrator:
    """Orquesta el flujo de <descripción>.

    Responsabilidades: orden de pasos, error policies, persistencia.
    NO contiene lógica de negocio pura (eso va en el service).
    NO llama APIs externas directamente (usa providers vía services).
    """

    def __init__(self, service: <Nombre>Service, repository: <Nombre>Repository) -> None:
        self._service = service
        self._repository = repository

    async def run(self, entity_id: UUID) -> None:
        logger.info("Iniciando <nombre> para entity_id=%s", entity_id)
        entity = await self._step_load(entity_id)
        result = await self._step_process(entity)
        await self._step_persist(entity_id, result)
        logger.info("Completado <nombre> para entity_id=%s", entity_id)

    async def _step_load(self, entity_id: UUID):
        entity = await self._repository.get_by_id(entity_id)
        if entity is None:
            raise ValueError(f"Entidad {entity_id} no encontrada")
        return entity

    async def _step_process(self, entity):
        return await self._service.process(entity)

    async def _step_persist(self, entity_id: UUID, result) -> None:
        await self._repository.update_status(entity_id, result.status)
```

---

## Celery Task (thin)

```python
# En app/domain/services/celery_tasks.py

@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="tasks.<nombre>",
    acks_late=True,
)
@track_task_metrics
def process_<nombre>(self, entity_id: str) -> None:
    """Thin task — delega al orchestrator. Máximo 30 líneas."""
    try:
        orchestrator: <Nombre>Orchestrator = container.<nombre>_orchestrator()
        asyncio.run(orchestrator.run(UUID(entity_id)))
    except Exception as exc:
        logger.exception("Error en process_<nombre> para entity_id=%s", entity_id)
        raise self.retry(exc=exc)
```

---

## Request Handler

```python
# app/domain/handlers/request_handlers/<nombre>_handler.py
import logging
from uuid import UUID

from fastapi import HTTPException

from app.persistence.repositories.<nombre>_repository import <Nombre>Repository
from app.domain.services.celery_tasks import process_<nombre>

logger = logging.getLogger(__name__)


class <Nombre>Handler:
    """Valida estado del dominio y dispara la task. No sabe de HTTP."""

    def __init__(self, repository: <Nombre>Repository) -> None:
        self._repository = repository

    def handle(self, entity_id: UUID) -> None:
        entity = self._repository.get_by_id(entity_id)
        if entity is None:
            raise HTTPException(status_code=404, detail="Entidad no encontrada")
        if entity.status not in ("pending", "failed"):
            raise HTTPException(status_code=409, detail=f"Estado inválido: {entity.status}")
        process_<nombre>.delay(str(entity_id))
```

---

## Route

```python
# app/api/routes/<nombre>.py
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, require_api_key
from app.api.schemas.<nombre> import <Nombre>Request, <Nombre>Response
from app.domain.handlers.request_handlers.<nombre>_handler import <Nombre>Handler
from app.persistence.repositories.<nombre>_repository import <Nombre>Repository

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/<nombre>", tags=["<nombre>"])


@router.post("/{entity_id}/process", response_model=<Nombre>Response)
async def process_<nombre>(
    entity_id: UUID,
    db: Session = Depends(get_db),
    _: str = Depends(require_api_key),
) -> <Nombre>Response:
    handler = <Nombre>Handler(repository=<Nombre>Repository(db))
    handler.handle(entity_id)
    return <Nombre>Response(status="processing")
```

---

## Executor (Pipeline)

```python
# app/domain/prompt_execution_pipeline/executors/<nombre>_executor.py
import logging

from app.domain.prompt_execution_pipeline.executors.base import Executor
from app.domain.prompt_execution_pipeline.prompt_execution_context import PromptExecutionContext

logger = logging.getLogger(__name__)


class <Nombre>Executor(Executor):
    """<Descripción>. Lee <campos_de_entrada> del context, escribe <campos_de_salida>."""

    def execute(self, context: PromptExecutionContext) -> PromptExecutionContext:
        logger.info("Ejecutando <Nombre>Executor")
        prompt = self._load_prompt()
        result = self._llm_provider.complete(prompt.format(text=context.transcript))
        context.<campo_resultado> = result
        return context

    def _load_prompt(self) -> str:
        from pathlib import Path
        return (Path(__file__).parent.parent.parent / "prompts/templates/<nombre>_prompt.txt").read_text()
```

**Registrar en `pipelines.py`:**
```python
def create_<pipeline>_pipeline(...) -> PromptPipeline:
    return PromptPipeline(executors=[
        ...,
        <Nombre>Executor(llm_provider=...),  # agregar en la posición correcta
        ...,
    ])
```

---

## Schema Pydantic (API)

```python
# app/api/schemas/<nombre>.py
from uuid import UUID
from pydantic import BaseModel


class <Nombre>Request(BaseModel):
    <campo>: str


class <Nombre>Response(BaseModel):
    status: str
    id: UUID | None = None
```

---

## Alembic Migration — patrones seguros

```python
# Agregar columna nullable → backfill → NOT NULL (evita downtime en prod)
def upgrade() -> None:
    # 1. Nullable primero
    op.add_column("tabla", sa.Column("nueva_col", sa.String(), nullable=True))
    # 2. Backfill
    op.execute("UPDATE tabla SET nueva_col = 'default' WHERE nueva_col IS NULL")
    # 3. NOT NULL
    op.alter_column("tabla", "nueva_col", nullable=False)
    # 4. Index en FK SIEMPRE
    op.create_index("ix_tabla_nueva_col", "tabla", ["nueva_col"])

def downgrade() -> None:
    op.drop_index("ix_tabla_nueva_col", table_name="tabla")
    op.drop_column("tabla", "nueva_col")
```

---

## DI Container — orden correcto

```python
# app/containers.py — agregar en este orden:
# 1. Provider (Singleton — sin estado)
<nombre>_provider = providers.Singleton(<Nombre>Provider)

# 2. Repository (Singleton)
<nombre>_repository = providers.Singleton(<Nombre>Repository, db=db_session)

# 3. Service (Singleton)
<nombre>_service = providers.Singleton(
    <Nombre>Service,
    provider=<nombre>_provider,
)

# 4. Orchestrator (Factory — nuevo contexto por llamada)
<nombre>_orchestrator = providers.Factory(
    <Nombre>Orchestrator,
    service=<nombre>_service,
    repository=<nombre>_repository,
)
```
