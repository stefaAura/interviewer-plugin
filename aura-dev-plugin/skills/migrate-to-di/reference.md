# migrate-to-di — Templates y referencia completa

## Cuándo usar Singleton vs Factory

| Tipo | Cuándo | Ejemplo |
|---|---|---|
| `providers.Singleton` | Sin estado por-ejecución | `GenerativeAIService`, providers |
| `providers.Factory` | Contexto por-ejecución | `MP3ImportOrchestrator` |
| `providers.Object` | Singletons externos | `db_manager` |

## Template de wiring en containers.py

```python
# Orden: providers → repositories → services → orchestrators

<nombre>_provider = providers.Singleton(
    <Nombre>Provider,
    api_key=config.provided.<NOMBRE>_API_KEY,
)

<nombre>_repository = providers.Singleton(
    <Nombre>Repository,
    db_manager=db_manager,
)

<nombre>_service = providers.Singleton(
    <Nombre>Service,
    repository=<nombre>_repository,
    provider=<nombre>_provider,
    webhook_service=webhook_service,
)

<nombre>_orchestrator = providers.Factory(
    <Nombre>Orchestrator,
    service=<nombre>_service,
    repository=<nombre>_repository,
)
```

## Agregar wiring

```python
# app/main.py (routes FastAPI)
container.wire(modules=[
    ...,
    "app.api.routes.<nombre>",
])

# app/celery_worker.py (tasks — ya está wired celery_tasks)
```

## Uso con @inject en routes

```python
from dependency_injector.wiring import inject, Provide
from app.containers import Container

@router.post("/mi-endpoint")
@inject
async def mi_endpoint(
    service: <Nombre>Service = Provide[Container.<nombre>_service],
):
    return await service.do_something()
```

## Uso con @inject en Celery tasks

```python
@celery_app.task(bind=True, ...)
@inject
def mi_task(
    self,
    entity_id: str,
    service: <Nombre>Service = Provide[Container.<nombre>_service],
) -> None:
    asyncio.run(service.process(UUID(entity_id)))
```

## Agregar al validate() si tiene API keys

```python
def validate(self) -> None:
    ...
    self.<nombre>_provider()  # falla rápido si falta la API key
```

## Limpiar instanciación manual

```bash
rg -n "<NombreServicio>(" app/ --include="*.py"
```

Solo eliminar después de validar en DEV y confirmar que no hay otros flujos que usen el camino manual.
