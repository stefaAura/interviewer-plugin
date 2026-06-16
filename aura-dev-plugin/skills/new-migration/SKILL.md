---
name: new-migration
description: >
  Crea una migración Alembic en aura-core-ai-interviewer. Genera la migración,
  la revisa con @db-reviewer para detectar problemas (NOT NULL sin default,
  operaciones destructivas, índices faltantes, JSONB mal manejado), y guía el proceso.
---

Crear migración Alembic para: $ARGUMENTS

## Pasos

### 1 — Verificar que los modelos SQLAlchemy estén actualizados

Revisa que los cambios en `app/persistence/models/` están correctamente definidos antes de generar la migración.

### 2 — Generar la migración

```bash
uv run alembic revision --autogenerate -m "$ARGUMENTS"
```

### 3 — Revisar el archivo generado

Lee el archivo de migración generado en `alembic/versions/` y verifica:

- ¿Hay columnas NOT NULL sin `server_default`? → Problema si la tabla tiene datos
- ¿Hay DROP TABLE o DROP COLUMN? → ¿Se verificó que no hay datos o FKs?
- ¿Hay nuevas FKs sin índice? → Agregar `op.create_index`
- ¿El `downgrade()` revierte exactamente el `upgrade()`?

### 4 — Delegar revisión a @db-reviewer

Invocar `@db-reviewer` con el path del archivo de migración generado para revisión completa.

### 5 — Aplicar (cuando esté aprobada)

```bash
# Local
uv run alembic upgrade head

# Docker
docker-compose run migrations
```

## Convención de JSONB en este proyecto

Si la migración o el código relacionado hace updates a columnas JSONB (`meta`), siempre usar `merge_metadata()`:

```python
# ❌ NUNCA — destruye datos existentes
obj.meta = {"nueva_clave": valor}

# ✅ SIEMPRE
merge_metadata(obj, {"nueva_clave": valor})
```
