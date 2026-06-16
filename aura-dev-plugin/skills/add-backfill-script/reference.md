# add-backfill-script — Template y checklist completo

## Template de script

```python
#!/usr/bin/env python3
"""
<descripción de una línea>

Uso:
    uv run python scripts/<nombre>.py [--no-dry-run] [--limit N]
"""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.manager import db_manager, get_settings
from app.persistence.repositories.<nombre>_repository import <Nombre>Repository

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-dry-run", action="store_true", default=False)
    parser.add_argument("--limit", type=int, default=None)
    return parser.parse_args()


def run(dry_run: bool, limit: int | None) -> None:
    get_settings()
    db_manager.initialize()

    with db_manager.get_session("core-db"):
        repo = <Nombre>Repository(db_manager=db_manager)
        records = repo.get_<condición>(limit=limit)
        logger.info("Encontrados %d registros a procesar", len(records))

        updated = skipped = errors = 0

        for record in records:
            try:
                if record.<campo_ya_tiene_valor>:
                    skipped += 1
                    continue

                new_value = _compute(record)

                if dry_run:
                    logger.info("[DRY-RUN] id=%s → %s", record.id, new_value)
                else:
                    repo.update(record.id, {<campo>: new_value})
                    logger.info("[UPDATED] id=%s → %s", record.id, new_value)
                    updated += 1

            except Exception as exc:
                logger.error("[ERROR] id=%s: %s", record.id, exc)
                errors += 1

    logger.info("Resumen: updated=%d, skipped=%d, errors=%d (dry_run=%s)", updated, skipped, errors, dry_run)
    if errors > 0:
        sys.exit(1)


def _compute(record) -> <tipo>:
    """Lógica de cómputo pura — sin side effects."""
    ...


if __name__ == "__main__":
    args = parse_args()
    dry_run = not args.no_dry_run
    if dry_run:
        logger.info("=== DRY-RUN MODE — no se escribirá nada ===")
    run(dry_run=dry_run, limit=args.limit)
```

## Checklist de seguridad antes de producción

- [ ] Dry-run corrido: `uv run python scripts/<nombre>.py`
- [ ] Output revisado — ¿los cambios son los esperados?
- [ ] Prueba con límite: `--no-dry-run --limit 10` en DEV
- [ ] Script es idempotente — ¿qué pasa si se corre dos veces?
- [ ] ¿Tiene plan de rollback si algo sale mal?
- [ ] ¿Afecta tablas con FKs o caches que hay que invalidar?
