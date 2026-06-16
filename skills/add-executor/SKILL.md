---
name: add-executor
description: >
  Agrega un nuevo executor al Prompt Execution Pipeline de aura-core-ai-interviewer.
  Hereda de Executor, usa PromptExecutionContext mutable, registra en pipelines.py.
  Prompts siempre en template files, nunca en DB ni hardcodeados.
---

Crear nuevo executor para: $ARGUMENTS

## Antes de crear

1. Lee `app/domain/prompt_execution_pipeline/README.md` — arquitectura del pipeline
2. Lee `app/domain/prompt_execution_pipeline/executors/base.py` — clase base
3. Lee `app/domain/prompt_execution_pipeline/prompt_execution_context.py` — campos
4. Confirma: ¿pipeline destino?, ¿posición?, ¿qué campos del context lee y escribe?

## Pasos

1. Crear `app/domain/prompt_execution_pipeline/executors/<nombre>_executor.py`
2. Crear `app/domain/prompts/templates/<nombre>_prompt.txt`
3. Registrar en `pipelines.py` dentro de la factory function del pipeline
4. Exportar desde `__init__.py`
5. Tests en `tests/domain/prompt_execution_pipeline/` — invocar `@test-writer`

**Ver templates y reglas completas en `reference.md`**
