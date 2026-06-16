---
name: migrate-to-di
description: >
  Migra un servicio de instanciación manual al DI container (dependency-injector)
  de aura-core-ai-interviewer. Proceso incremental: old world y new world coexisten
  hasta que la migración esté validada. Incluye wiring en routes y celery tasks.
---

Migrar al DI container: $ARGUMENTS

**Regla de oro**: coexistencia primero — NO toques el código legacy hasta que el nuevo esté validado.

## Antes de empezar

```bash
rg -n "<NombreServicio>" app/containers.py  # ¿ya está containerizado?
```

Lee `app/containers.py` completo para entender el orden y estilo.

## Pasos

1. Decidir `Singleton` (servicios sin estado) vs `Factory` (orchestrators con contexto)
2. Agregar al container en orden: providers → repositories → services → orchestrators
3. Agregar wiring en `app/main.py` (routes) o `app/celery_worker.py` (tasks)
4. Usar `@inject` + `Provide[Container.<nombre>]` en el punto de consumo
5. Agregar al `validate()` si tiene API keys externas
6. Validar en DEV y solo entonces eliminar la instanciación manual

**Test de wiring**: `tests/api/dependencies/test_di_wiring.py` — corre en CI

**Ver snippets completos de container, routes y tasks en `reference.md`**
