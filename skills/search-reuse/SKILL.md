---
name: search-reuse
description: >
  Ejecuta el protocolo reuse-first del AGENTS.md antes de crear código nuevo.
  Busca en app/core/utils/, app/domain/providers/, app/domain/services/ y
  app/persistence/repositories/ para encontrar helpers existentes que se puedan
  extender en lugar de duplicar.
---

Ejecuta el protocolo reuse-first para: $ARGUMENTS

## Búsqueda

```bash
# Por intención
rg -ti -g '*.py' '$ARGUMENTS' app/core/utils app/domain app/persistence

# Por firma (ajusta el verbo según lo que se busca)
rg -ti -g '*.py' 'def .*$ARGUMENTS' app/core app/domain app/persistence
```

## Directorios a revisar según el tipo

| Si buscas... | Revisa |
|---|---|
| Helper general (parsing, fechas, texto) | `app/core/utils/` |
| Wrapper de API externa | `app/domain/providers/` |
| Adaptador de formato/protocolo | `app/domain/adapters/` |
| Tool de prompt execution | `app/domain/tools/` |
| Lógica de negocio | `app/domain/services/` |
| Queries de DB | `app/persistence/repositories/` |
| DTO / enum | `app/domain/models/` |

## Helpers que YA EXISTEN — no recrear

- `filename_parser` — `app/core/utils/filename_parser.py`
- `language_utils` — `app/core/utils/language_utils.py`
- `document_service` — `app/core/utils/document_service.py`
- `word_document_service` — `app/core/utils/word_document_service.py`
- `transcript_ingestion_s3` — `app/core/utils/transcript_ingestion_s3.py`
- `celery_task_decorator` — `app/core/utils/celery_task_decorator.py`
- `slack_service` — `app/core/utils/slack_service.py`
- `teams_service` — `app/core/utils/teams_service.py`
- `sendgrid_provider` — `app/core/utils/sendgrid_provider.py`

## Salida esperada

1. Lista de lo que se encontró (con paths y relevancia)
2. Recomendación: ¿extender algo existente o crear nuevo?
3. Si se recomienda extender: cómo hacerlo sin romper el código existente
