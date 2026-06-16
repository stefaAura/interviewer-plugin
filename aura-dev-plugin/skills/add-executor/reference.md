# add-executor — Templates y referencia completa

## Template de executor

```python
# app/domain/prompt_execution_pipeline/executors/<nombre>_executor.py

from pathlib import Path

from app.domain.prompt_execution_pipeline.executors.base import Executor
from app.domain.prompt_execution_pipeline.prompt_execution_context import (
    PromptExecutionContext,
)
from app.core.config.logging import logger

TEMPLATES_DIR = Path(__file__).parent.parent.parent / "prompts" / "templates"


class <Nombre>Executor(Executor):
    """<Descripción de una línea>.

    Lee:  context.<campo_de_entrada>
    Escribe: context.<campo_de_salida>
    """

    def __init__(self, llamaindex_provider) -> None:
        self._provider = llamaindex_provider

    @property
    def processes_full_transcript(self) -> bool:
        return True

    def execute(self, context: PromptExecutionContext) -> PromptExecutionContext:
        logger.info("[<Nombre>Executor] Starting")

        template = (TEMPLATES_DIR / "<nombre>_prompt.txt").read_text()
        prompt = template.replace("{{FULL_TRANSCRIPT}}", context.full_transcript)

        response = self._provider.complete(
            prompt=prompt,
            provider=context.provider,
            model=context.model,
        )

        context.<nombre>_result = response

        logger.info("[<Nombre>Executor] Completed")
        return context
```

## Template del prompt

```
# app/domain/prompts/templates/<nombre>_prompt.txt

<Instrucciones para el LLM>

Usa {{DOUBLE_BRACES}} — nunca f-strings ni .format()

TRANSCRIPT:
{{FULL_TRANSCRIPT}}

Responde en JSON:
{
  "resultado": "..."
}
```

## Registro en `pipelines.py`

```python
def create_<nombre>_pipeline(llamaindex_provider) -> PromptPipeline:
    return PromptPipeline(
        executors=[
            ExistingExecutor(llamaindex_provider),
            <Nombre>Executor(llamaindex_provider),
        ]
    )
```

## Exportar desde `__init__.py`

```python
from .pipelines import create_<nombre>_pipeline
```

## Template de tests

```python
class Test<Nombre>Executor:
    @pytest.fixture
    def executor(self):
        mock_provider = AsyncMock(spec=LlamaIndexProvider)
        return <Nombre>Executor(mock_provider)

    def test_execute_populates_result(self, executor):
        context = PromptExecutionContext(...)
        context.full_transcript = "test transcript"
        result = executor.execute(context)
        assert result.<nombre>_result is not None

    def test_execute_with_empty_transcript(self, executor): ...

    def test_execute_raises_when_provider_fails(self, executor):
        executor._provider.complete.side_effect = Exception("LLM error")
        with pytest.raises(Exception):
            executor.execute(context)
```

## Reglas críticas

- Executor NO persiste nada — solo lee/escribe en el context
- Executor NO conoce domain entities
- Context es mutable y order-dependent — el orden importa, reordenar rompe el flujo
- Si falla → todo el pipeline falla (fail-fast)
- Prompts SIEMPRE en template files, nunca en DB ni hardcodeados
