---
name: slim-celery-task
description: >
  Migra una fat Celery task (>30 líneas de lógica de negocio) al patrón thin en
  aura-core-ai-interviewer. Extrae la lógica a un orchestrator, deja en la task
  solo: retry policy, idempotency lock, track_task_metrics, y delegación al
  orchestrator. Incluye guía para no romper retries en vuelo.
---

Migrar a thin task: $ARGUMENTS

## Referencias antes de empezar

1. `process_mp3_import_v2` en `celery_tasks.py` — thin task canónica
2. `mp3_import_orchestrator.py` — orchestrator canónico
3. `app/core/utils/celery_task_decorator.py` — `@track_task_metrics`

## Qué se queda en la task vs qué va al orchestrator

| En la task | Al orchestrator |
|---|---|
| `@celery_app.task`, `@track_task_metrics` | Lógica de negocio |
| `self.retry(exc=exc)` | Llamadas a services/repos |
| Idempotency lock | Webhooks y notificaciones |

## Pasos

1. Leer la task fat completa e identificar qué va dónde
2. Crear orchestrator en `app/domain/orchestrators/<nombre>_orchestrator.py`
3. Reducir task a <30 líneas que delegan a `orchestrator.run()`
4. Registrar orchestrator en `app/containers.py`
5. ⚠️ Verificar retries en vuelo antes de desplegar (ver `reference.md`)
6. Tests: invocar `@test-writer` para orchestrator y task

**Ver templates de código y estrategia de retries en `reference.md`**
