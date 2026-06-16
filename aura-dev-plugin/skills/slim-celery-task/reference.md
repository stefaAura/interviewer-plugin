# slim-celery-task — Templates y referencia completa

## Template de orchestrator

```python
# app/domain/orchestrators/<nombre>_orchestrator.py

import logging
from uuid import UUID

logger = logging.getLogger(__name__)


class <Nombre>Orchestrator:
    """Orquesta el flujo de <descripción>.

    Extraído de la fat task `<nombre_task>` en celery_tasks.py.
    """

    def __init__(self, service, repository, webhook_service=None) -> None:
        self._service = service
        self._repository = repository
        self._webhook_service = webhook_service

    async def run(self, entity_id: UUID, **kwargs) -> None:
        logger.info("[<Nombre>Orchestrator] Starting entity_id=%s", entity_id)

        entity = await self._step_load(entity_id)
        result = await self._step_process(entity, **kwargs)
        await self._step_persist(entity_id, result)

        logger.info("[<Nombre>Orchestrator] Completed entity_id=%s", entity_id)

    async def _step_load(self, entity_id: UUID):
        entity = await self._repository.get_by_id(entity_id)
        if entity is None:
            raise ValueError(f"Entity {entity_id} not found")
        return entity

    async def _step_process(self, entity, **kwargs):
        return await self._service.process(entity, **kwargs)

    async def _step_persist(self, entity_id: UUID, result) -> None:
        await self._repository.update(entity_id, result)
```

## Template de thin task

```python
@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="tasks.<nombre>",
    acks_late=True,
)
@track_task_metrics
@inject
def <nombre_task>(
    self,
    entity_id: str,
    orchestrator: <Nombre>Orchestrator = Provide[Container.<nombre>_orchestrator],
) -> None:
    """Thin task — delega toda la lógica al orchestrator."""
    try:
        asyncio.run(orchestrator.run(UUID(entity_id)))
    except Exception as exc:
        logger.error("[<nombre_task>] Failed entity_id=%s: %s", entity_id, exc)
        raise self.retry(exc=exc)
```

## Registro en DI container (app/containers.py)

```python
<nombre>_orchestrator = providers.Factory(
    <Nombre>Orchestrator,
    service=<nombre>_service,
    repository=<nombre>_repository,
    webhook_service=webhook_service,
)
```

Agregar wiring en `app/celery_worker.py` si la task usa `@inject`.

## ⚠️ Estrategia de retries en vuelo

Si hay tasks corriendo en producción con el código viejo:

1. Las tasks con `acks_late=True` se reintentan al reiniciar el worker
2. Si la firma cambia, los retries del código viejo fallan
3. Si el nombre cambia, tasks encoladas no encuentran el nuevo handler

**Estrategia segura:**
1. Crear la nueva thin task con nombre diferente: `tasks.<nombre>_v2`
2. Desplegar — ambas coexisten
3. Esperar a que las tasks `v1` en vuelo terminen
4. Redirigir el código que encola al nuevo nombre
5. Eliminar la versión vieja en el siguiente release

## Task regular vs Beat task

| Tipo | Disparada por | Dónde vive |
|---|---|---|
| Task regular | `task.delay()` | `celery_tasks.py` |
| Beat task | Schedule cron/interval | `celery_beat.py` |

Las beat tasks siguen el mismo patrón thin pero el orchestrator se instancia directamente en `celery_beat.py` (no vía DI).
