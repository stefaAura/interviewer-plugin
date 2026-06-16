---
name: add-prompt
description: >
  Agrega un nuevo prompt a aura-core-ai-interviewer. Guía la decisión crítica:
  ¿prompt en DB (para generative_ai_service, scoring, editable desde admin) o
  template de archivo (para prompt execution pipeline/executors, versionado en git)?
  Incluye el GOTCHA del name display string en DB.
---

Agregar prompt para: $ARGUMENTS

## ⚠️ Decisión crítica: ¿DB o template de archivo?

**Regla de oro: executor → template de archivo. generative_ai_service → DB.**

- **DB-backed**: lo usa `generative_ai_service.py`, editable desde admin sin deploy.
- **Template de archivo**: lo usa un executor del pipeline, versionado en git.

## Flujo A — Prompt en DB

1. Agregar `PromptType` enum en `app/persistence/models/agent_prompts.py` (si no existe)
2. Registrar en `prompt_type_mapping` de `generative_ai_service.py`
3. Insertar en DB via script (ver `scripts/populate_scoring_prompts.py`)
4. ⚠️ **GOTCHA**: `name` en DB es display string (`"Quality Scoring"`), no snake_case (`"quality_scoring"`)

## Flujo B — Template de archivo

1. Crear `app/domain/prompts/templates/<nombre>_prompt.txt`
2. Usar `{{DOUBLE_BRACES}}` para placeholders — nunca f-strings
3. Cargar en el executor con `Path(...).read_text()`

**Ver snippets completos y lista de names en DB en `reference.md`**
