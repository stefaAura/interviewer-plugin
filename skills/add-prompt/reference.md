# add-prompt — Templates y referencia completa

## Flujo A: Prompt en DB

### 1. Agregar PromptType (si no existe)

```python
# app/persistence/models/agent_prompts.py
class PromptType(str, Enum):
    MI_NUEVO_PROMPT = "mi_nuevo_prompt"
```

### 2. Registrar en el mapping de generative_ai_service.py

```python
self.prompt_type_mapping = {
    ...
    "mi_nuevo_prompt": PromptType.MI_NUEVO_PROMPT,
}
```

### 3. Insertar en DB (ver scripts/populate_scoring_prompts.py)

```python
existing = db.query(AgentPrompt).filter_by(
    prompt_type=PromptType.MI_NUEVO_PROMPT,
    name="Mi Nuevo Prompt",  # ← display string, ver GOTCHA
).first()

if not existing:
    db.add(AgentPrompt(
        name="Mi Nuevo Prompt",
        prompt_type=PromptType.MI_NUEVO_PROMPT,
        content="<contenido del prompt>",
        model="gpt-4o",
        provider="openai",
        status="active",
        version=1,
    ))
    db.commit()
```

### ⚠️ GOTCHA CRÍTICO: el `name` es display string

```python
# ❌ INCORRECTO — no encontrará nada
db.query(AgentPrompt).filter_by(name="quality_scoring")

# ✅ CORRECTO
db.query(AgentPrompt).filter_by(name="Quality Scoring")
```

Names reales en DB:
- `"Review Names"` (PromptType.REVIEW_NAMES)
- `"Quality Scoring"` (PromptType.QUALITY_SCORING)
- `"MNPI"` (PromptType.MNPI)
- Ver `scripts/populate_*.py` para la lista completa

### 4. Cargar en el service

```python
prompt_data = self._get_scoring_prompt_data(
    PromptType.MI_NUEVO_PROMPT,
    "Mi Nuevo Prompt",  # mismo display string que en DB
)
if prompt_data:
    content = prompt_data["content"]
    model = prompt_data.get("model") or "gpt-4o"
```

---

## Flujo B: Template de archivo

### 1. Crear el archivo

```
app/domain/prompts/templates/<nombre>_prompt.txt
```

```
Analiza el siguiente transcript.

TRANSCRIPT:
{{FULL_TRANSCRIPT}}

Responde en JSON:
{
  "resultado": "...",
  "score": 0
}
```

Usar `{{DOUBLE_BRACES}}` — nunca f-strings ni `.format()`

### 2. Cargar en el executor

```python
from pathlib import Path

TEMPLATES_DIR = Path(__file__).parent.parent.parent / "prompts" / "templates"

class MiExecutor(Executor):
    def execute(self, context):
        template = (TEMPLATES_DIR / "<nombre>_prompt.txt").read_text()
        prompt = template.replace("{{FULL_TRANSCRIPT}}", context.full_transcript)
        ...
```

### Nota sobre DB + executor

Si el executor tiene entrada en DB, esa entrada solo configura `model` y `provider`.
El campo `content` en DB es **ignorado** por executors — siempre leen del template de archivo.
