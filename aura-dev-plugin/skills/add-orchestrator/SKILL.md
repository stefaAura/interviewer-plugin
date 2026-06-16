---
name: add-orchestrator
description: >
  Scaffoldea un nuevo orquestador en aura-core-ai-interviewer siguiendo el patrón
  canónico de mp3_import_orchestrator.py. Incluye el thin Celery task que lo invoca
  y el registro en el DI container.
---

Crear nuevo orquestador para: $ARGUMENTS

## Antes de crear

1. Lee `app/domain/orchestrators/mp3_import_orchestrator.py` — orquestador canónico de referencia
2. Lee `app/domain/services/celery_tasks.py::process_mp3_import_v2` — thin task de referencia
3. Confirma con el planner qué pasos tiene el flujo y sus error policies

## Template de orchestrator

```python
# app/domain/orchestrators/<nombre>_orchestrator.py

import logging
from uuid import UUID

from app.domain.services.<nombre>_service import <Nombre>Service
from app.persistence.repositories.<nombre>_repository import <Nombre>Repository

logger = logging.getLogger(__name__)


class <Nombre>Orchestrator:
    """Orquesta el flujo de <descripción>.

    Responsabilidades:
    - Orden de pasos y error handling
    - Coordinación entre services y repositories
    - Persistencia de estado intermedio

    NO contiene lógica de negocio pura (eso va en el service).
    NO llama APIs externas directamente (usa providers vía services).
    """

    def __init__(
        self,
        service: <Nombre>Service,
        repository: <Nombre>Repository,
    ) -> None:
        self._service = service
        self._repository = repository

    async def run(self, entity_id: UUID) -> None:
        """Punto de entrada principal del orquestador."""
        logger.info("Iniciando <nombre> para entity_id=%s", entity_id)

        entity = await self._step_load(entity_id)
        result = await self._step_process(entity)
        await self._step_persist(entity_id, result)

        logger.info("Completado <nombre> para entity_id=%s", entity_id)

    async def _step_load(self, entity_id: UUID):
        """Carga y valida la entidad inicial."""
        entity = await self._repository.get_by_id(entity_id)
        if entity is None:
            raise ValueError(f"Entidad {entity_id} no encontrada")
        return entity

    async def _step_process(self, entity):
        """Ejecuta la lógica de negocio (delegada al service)."""
        return await self._service.process(entity)

    async def _step_persist(self, entity_id: UUID, result) -> None:
        """Persiste el resultado."""
        await self._repository.update(entity_id, result)
```

## Template de Celery task (thin)

```python
# En app/domain/services/celery_tasks.py

@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="tasks.<nombre>",
)
@track_task_metrics  # decorator de app/core/utils/celery_task_decorator.py
def process_<nombre>(self, entity_id: str) -> None:
    """Task thin que delega al orchestrator. <30 líneas."""
    orchestrator: <Nombre>Orchestrator = container.<nombre>_orchestrator()
    asyncio.run(orchestrator.run(UUID(entity_id)))
```

## Registro en DI container

```python
# app/containers.py

<nombre>_service = providers.Singleton(
    <Nombre>Service,
    repository=repository.<nombre>_repository,
)

<nombre>_orchestrator = providers.Factory(
    <Nombre>Orchestrator,
    service=<nombre>_service,
    repository=repository.<nombre>_repository,
)
```

## Reglas

- Cada paso del orchestrator es un método privado separado (`_step_X`)
- El Celery task SIEMPRE tiene <30 líneas — delega todo al orchestrator
- El orchestrator llama services para lógica, repositories para persistencia
- Errores de pasos individuales se loggean y pueden hacer retry o no según la policy
- Registrar en DI container si el flujo usa inyección de dependencias
