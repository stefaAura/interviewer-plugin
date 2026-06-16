---
name: new-feature
description: >
  Scaffoldear una feature nueva en aura-core-ai-interviewer siguiendo la arquitectura
  de capas del proyecto. Primero busca código reutilizable, luego determina qué capas
  necesita, y genera los archivos en los directorios correctos.
---

Scaffold una nueva feature para `aura-core-ai-interviewer` siguiendo la arquitectura del proyecto.

## Primero: activa el planner

Si esta feature no tiene un plan aprobado todavía, invoca `@aura-planner` con la descripción de la feature antes de crear cualquier archivo.

Si ya hay un plan, usa este skill para ejecutarlo.

## Tarea

Feature a implementar: $ARGUMENTS

## Protocolo de ejecución

### Paso 1 — Reuse-first (siempre)

```bash
rg -ti -g '*.py' '<verbo_principal>' app/core/utils app/domain
rg -ti -g '*.py' 'def .*<concepto>' app/core app/domain app/persistence
```

Reporta lo que encontraste antes de crear nada.

### Paso 2 — Determinar capas necesarias

Consulta la tabla del architecture.md y determina qué capas necesita esta feature.
No crees capas que no se necesitan.

**Referencia de responsabilidades:**
- **Route** — binding HTTP, auth, response shape. Sin lógica de negocio.
- **Handler** — valida estado del dominio, delega a Celery. Sin HTTP.
- **Celery Task** — thin (<30 líneas), retry policy, delega a orchestrator.
- **Orchestrator** — paso A→B→C, error policies. Usa services y repos.
- **Service** — operación pura. Retorna resultado, no persiste.
- **Provider** — wrapper API externa. Sin lógica de negocio.
- **Repository** — fetch → mutate → merge(). Sin lógica de negocio.

### Paso 3 — Crear archivos en orden (de abajo hacia arriba)

1. Modelos/DTOs (`app/domain/models/`)
2. Migration si hay cambio de schema (`alembic/`)
3. Repository si hay nuevas queries (`app/persistence/repositories/`)
4. Provider si hay nueva API externa (`app/domain/providers/`)
5. Service (`app/domain/services/`)
6. Orchestrator si el flujo tiene múltiples pasos (`app/domain/orchestrators/`)
7. Celery task si es trabajo async (`app/domain/services/celery_tasks.py`)
8. Handler si hay validación de estado (`app/domain/handlers/`)
9. Route (`app/api/routes/`)
10. Schema Pydantic (`app/api/schemas/`)

### Paso 4 — Registro en DI container

Si agregas un nuevo service o provider, regístralo en `app/containers.py` siguiendo el patrón existente de `mp3_import_orchestrator`.

### Paso 5 — Verificación de capas

Antes de terminar, revisa cada archivo creado:
- ¿El service hace algún `db.merge` o `db.flush`? → ERROR
- ¿La route tiene validación de dominio? → ERROR
- ¿El Celery task tiene >30 líneas de lógica? → WARNING
- ¿El orchestrator llama directamente a una API externa? → ERROR

Al terminar, menciona qué tests se necesitan y sugiere invocar `@test-writer`.
