---
name: add-provider
description: >
  Scaffoldea un nuevo proveedor de API externa en app/domain/providers/ para
  aura-core-ai-interviewer. Sigue las convenciones: async, sin lógica de negocio,
  retry con tenacity, secretos vía get_settings(), registro en containers.py.
---

Crear nuevo provider para: $ARGUMENTS

## Template de provider

```python
# app/domain/providers/<nombre>_provider.py

import logging
from typing import Any

from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config.settings.base_config import get_settings

logger = logging.getLogger(__name__)


class <Nombre>Provider:
    """Wrapper para la API de <Nombre>.

    No contiene lógica de negocio ni conoce domain entities.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._api_key = settings.<NOMBRE>_API_KEY  # Nunca hardcodear — vía settings
        self._client = <ClienteAPI>(api_key=self._api_key)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def <metodo>(self, param: str) -> dict[str, Any]:
        """Descripción breve del método."""
        try:
            response = await self._client.<endpoint>(param)
            return response
        except <APIError> as e:
            logger.error("Error en <Nombre>Provider.<metodo>: %s", e)
            raise
```

## Registro en DI container

Agregar en `app/containers.py` siguiendo el patrón existente:

```python
# En la clase Container
<nombre>_provider = providers.Singleton(
    <Nombre>Provider,
)
```

## Agregar API key a settings

En `app/core/config/settings/base_config.py`:
```python
<NOMBRE>_API_KEY: str = ""
```

Y en `.env.example`:
```
<NOMBRE>_API_KEY=your_api_key_here
```

## Reglas

- `async` para todos los métodos que hacen I/O
- Retry con `tenacity` para llamadas que pueden fallar por rate limits o timeouts
- Secretos siempre vía `get_settings()` — nunca hardcodeados
- El provider no sabe nada del dominio (no recibe ni retorna domain entities)
- El provider no persiste nada
