---
name: add-backfill-script
description: >
  Crea un script de backfill o utilidad standalone en aura-core-ai-interviewer.
  Scripts que corren fuera de la app (sin FastAPI/Celery). Guía las prácticas
  de seguridad: dry-run por defecto, idempotencia, logging, no romper producción.
---

Crear script de backfill/utilidad para: $ARGUMENTS

## Antes de crear

```bash
ls scripts/
rg -l "<concepto>" scripts/  # ¿existe algo similar?
```

Lee un script existente para seguir el estilo (ej. `scripts/backfill_2025_interview_scores.py`)

## Reglas de seguridad

- **Dry-run por defecto** — `--no-dry-run` es opt-in
- **Idempotente** — chequea si el registro ya fue procesado
- **Logging por operación** — `[DRY-RUN]` / `[UPDATED]` / `[ERROR]` + resumen al final
- Sin FastAPI/Celery — conecta directo vía `db_manager`
- Si toca JSONB — usar `merge_metadata()`, nunca asignación directa

```bash
uv run python scripts/<nombre>.py           # dry-run (seguro)
uv run python scripts/<nombre>.py --no-dry-run --limit 10  # probar en DEV
```

**Ver template completo y checklist de producción en `reference.md`**
