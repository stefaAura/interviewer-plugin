---
name: fix-bug
description: >
  Systematic debugging workflow for aura-core-ai-interviewer. Enforces root-cause analysis
  over symptom patching: reproduce, trace the call path, form a falsifiable hypothesis, apply
  a minimal fix at the source, and pin it with a regression test. Includes project-specific
  recipes for Celery task failures, async bugs, JSONB data loss, DB/session issues, provider
  timeouts, and webhook race conditions. Use when fixing a bug, analyzing a stack trace, or
  investigating unexpected behavior.
argument-hint: "[bug description, error message, or stack trace]"
model: claude-opus-4-8
---

# Fix Bug: $ARGUMENTS

**Principio central: encuentra la causa raíz ANTES de intentar cualquier fix. Parchar el síntoma es un fracaso.**

Copia esta lista y avanza fase por fase. No saltes fases.

```
Progreso debugging:
- [ ] Fase 1: Reproducir el bug de forma determinística
- [ ] Fase 2: Leer el error y trazar el call path
- [ ] Fase 3: Formular una hipótesis falsable y probarla
- [ ] Fase 4: Aplicar el fix mínimo en la causa raíz
- [ ] Fase 5: Pin con test de regresión
- [ ] Fase 6: Verificar (no rompí nada más)
```

⚠️ **No modifiques código de producción hasta confirmar la hipótesis en Fase 3.**

---

## Fase 1 — Reproducir

Un bug que no puedes reproducir no lo puedes arreglar.

1. **Lee el error completo** — stack trace entero, línea, archivo, tipo de excepción. A menudo contiene la solución exacta.
2. **Reproduce de forma determinística**: ¿qué pasos exactos lo disparan? ¿Pasa siempre o es intermitente?
   - Si es intermitente → probablemente **estado oculto compartido** (race condition, sesión DB filtrada, variable global). No adivines, junta más datos.
3. **Minimiza el reproductor**: quita inputs, campos, headers — todo lo no estrictamente necesario. Cada remoción es una hipótesis ("esto no importa"). Cuando el fallo desaparece, lo que quitaste **sí importaba**.

```bash
# ¿Qué cambió recientemente? Suele ser la causa.
git log -n 10 --oneline
git diff main...HEAD -- <archivo_sospechoso>
```

Si no puedes reproducir → **detente y junta más datos** (logs, Sentry, valores de input reales). No pases a la siguiente fase adivinando.

---

## Fase 2 — Trazar el call path

No asumas dónde está el bug. **Traza** desde el entry point hasta la línea que falla.

```bash
# Encontrar el entry point
rg -n "<funcion_o_endpoint_del_stacktrace>" app/ --include="*.py"

# Seguir cada llamada: route → handler → task → orchestrator → service → provider/repo
```

Pregunta clave: **¿de dónde viene el valor malo?**
- ¿Dónde se origina el valor incorrecto?
- ¿Qué lo llamó con ese valor?
- Sigue hacia arriba hasta encontrar el **origen**, no el lugar donde explota.

Agrega logging estratégico en los puntos sospechosos (no `print()` por todos lados):
```python
logger.debug("estado en X: entity_id=%s status=%s payload=%s", entity_id, entity.status, payload)
```

Para bugs específicos del stack → lee [debugging-recipes.md](debugging-recipes.md) (Celery, async, JSONB, DB, providers, webhooks).

---

## Fase 3 — Hipótesis falsable

Forma **UNA** hipótesis específica y escríbela:

```
Hipótesis: el bug ocurre porque [causa específica] en [archivo:línea],
lo que produce [efecto observable].
```

Luego **trata de probarla falsa**. Escribe una prueba mínima (script, print, o test) que confirme o descarte:
- Si el experimento confirma la predicción → la hipótesis es correcta, pasa a Fase 4
- Si no la confirma → **descarta la hipótesis y forma una nueva**. No acumules fixes encima.

> El test de si estás arreglando la causa: **¿un caller distinto, que aún no existe, toparía con el mismo bug?** Si sí → estás parchando un síntoma, la causa sigue ahí.

---

## Fase 4 — Fix mínimo en la causa raíz

Solo cuando la hipótesis está confirmada:

- Arregla **solo** la causa raíz
- **UN** cambio a la vez
- Sin refactors "ya que estoy aquí"
- Sin agregar features mientras arreglas
- El fix más simple posible

**Aplica los patrones del proyecto al arreglar** (no introduzcas nuevas violaciones):
- ¿El fix toca JSONB? → `merge_metadata()`, nunca asignación directa
- ¿El fix toca un service? → no agregar persistencia ni webhooks ahí
- ¿El fix toca una Celery task? → mantenerla thin

### Guard anti-shotgun debugging
```
Si el fix NO funciona:
- Cuenta cuántos fixes llevas intentados
- Si < 3 → vuelve a Fase 1 y re-analiza con la nueva información
- Si >= 3 → DETENTE. No intentes el fix #4.
            El problema probablemente es arquitectural, no un bug puntual.
            Discute el diseño con el usuario antes de seguir.
```

---

## Fase 5 — Pin con test de regresión

**Todo fix lleva un test de regresión. Siempre.**

1. Convierte tu reproductor mínimo (Fase 1) en un test automatizado
2. **Verifica que el test falla con el código viejo**:
   ```bash
   git stash                                    # guardar el fix
   uv run pytest tests/ -k "<nuevo_test>" -x    # debe FALLAR
   git stash pop                                # restaurar el fix
   ```
3. **Verifica que el test pasa con el fix**:
   ```bash
   uv run pytest tests/ -k "<nuevo_test>" -x    # debe PASAR
   ```

Si el test es difícil de escribir → el bug está en algo que aún no entiendes. **Sigue investigando.**

Ubicación del test según la capa afectada:
```
tests/unit/services/test_<nombre>_service.py        ← bug en lógica
tests/unit/orchestrators/test_<nombre>_orchestrator.py
tests/integration/repositories/test_<nombre>_repository.py  ← bug en queries
tests/integration/api/test_<nombre>_endpoint.py     ← bug en el flujo HTTP
```

---

## Fase 6 — Verificar

```bash
# El test de regresión pasa
uv run pytest tests/ -k "<nuevo_test>" -x -q

# No rompí nada más en el dominio afectado
uv run pytest tests/ -k "<dominio>" -q

# No introduje imports circulares
uv run python -c "import app.api.main"
```

Checklist final:
```
- [ ] El bug original ya no se reproduce
- [ ] El test de regresión falla en el código viejo y pasa en el nuevo
- [ ] Toda la suite del dominio pasa
- [ ] El fix es mínimo (no hay refactors ni features extra)
- [ ] No introduje violaciones de arquitectura (JSONB, service, task)
- [ ] Documenté la causa raíz (no solo el síntoma)
```

---

## Reporte final

```
## Bug Fix — $ARGUMENTS

### Síntoma
[Qué se observaba]

### Causa raíz
[Por qué pasaba realmente — archivo:línea del origen]

### Fix aplicado
[Qué se cambió y por qué resuelve la causa, no el síntoma]

### Test de regresión
[Archivo del test que ahora protege contra este bug]

### Verificación
[Confirmación de que la suite pasa]
```
