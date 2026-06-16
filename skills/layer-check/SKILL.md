---
name: layer-check
description: >
  Revisa archivos modificados o nuevos en aura-core-ai-interviewer para detectar
  violaciones de la arquitectura de capas. Detecta anti-patrones: service que persiste,
  route con validación de dominio, Celery task fat, orchestrator que llama APIs directamente.
---

Delega a `@arch-reviewer` para hacer la revisión completa de arquitectura.

Si se especifican archivos concretos: $ARGUMENTS

Si no se especifican, el arch-reviewer revisará los archivos modificados en el diff actual.
