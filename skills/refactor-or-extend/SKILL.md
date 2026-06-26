---
name: refactor-or-extend
description: >
  Workflow to safely refactor or extend existing functionality in aura-core-ai-interviewer.
  Covers structural refactors (slim fat Celery tasks, move persistence out of services, migrate
  to DI container, fix JSONB overwrites, move hardcoded prompts to templates) and behavioral
  extensions (add step to pipeline, add field to model, add endpoint, extend a service).
  Use when modifying existing code rather than creating something new, fixing an anti-pattern,
  or adding behavior to an existing class/module.
argument-hint: "[description of what to refactor or extend]"
model: claude-opus-4-8
---

# Refactor / Extend: $ARGUMENTS

## Paso 0 — Determinar el tipo de cambio

**¿Qué vas a hacer?**

- **Refactor** → Cambiar estructura interna sin cambiar comportamiento observable  
  *(fat task → thin, service persiste → no, instanciación manual → DI, prompt hardcoded → template)*
- **Extensión** → Agregar nuevo comportamiento a código existente  
  *(nuevo step en pipeline, nuevo campo en modelo, nuevo endpoint en resource, nueva revision type)*

Selecciona el camino y copia su checklist:

---

## Camino A — REFACTOR

```
Progreso Refactor:
- [ ] A1: Leer el código a modificar completamente
- [ ] A2: Mapear todos los callers y dependencias
- [ ] A3: Identificar el patrón de refactor
- [ ] A4: Planificar el diff mínimo
- [ ] A5: Ejecutar cambios con loop de validación
- [ ] A6: Verificar comportamiento sin cambios
```

### A1 — Leer el código a modificar

Antes de cambiar una sola línea, lee completamente:

```bash
# Leer el archivo objetivo
cat <archivo>

# Entender el tamaño y complejidad
wc -l <archivo>

# Si es una función específica, buscarla
rg -n "def <nombre_funcion>" app/
```

**No empieces a modificar hasta haber leído todo el archivo.**

### A2 — Mapear callers y dependencias

```bash
# ¿Quién llama a esta función / instancia esta clase?
rg -n "<NombreClase>\|<nombre_funcion>\|<nombre_task>" app/ --include="*.py"

# ¿Desde dónde se importa?
rg -n "from .* import.*<Nombre>\|import.*<Nombre>" app/ --include="*.py"

# ¿Hay tests existentes que cubren este código?
rg -rn "<nombre>" tests/ --include="*.py"
```

**Lista todos los archivos que tocarás.** Si son más de 5, considera si el scope es correcto.

### A3 — Identificar el patrón de refactor

| Síntoma detectado | Patrón a aplicar | Referencia |
|---|---|---|
| Celery task con >30 líneas de lógica | Slim fat task → extraer a Orchestrator | [refactoring-patterns.md](refactoring-patterns.md#slim-fat-task) |
| Service hace `db.merge()` o `db.flush()` | Mover persistencia al Orchestrator | [refactoring-patterns.md](refactoring-patterns.md#service-no-persiste) |
| Service llama `webhook_service.send()` | Mover webhook al Orchestrator | [refactoring-patterns.md](refactoring-patterns.md#service-no-webhook) |
| `MiServicio()` instanciado manualmente en task | Migrar al DI container | [refactoring-patterns.md](refactoring-patterns.md#migrate-to-di) |
| `obj.meta = {"clave": valor}` | Reemplazar por `merge_metadata()` | [refactoring-patterns.md](refactoring-patterns.md#fix-jsonb) |
| Prompt hardcodeado en executor o service | Mover a `app/domain/prompts/templates/` | [refactoring-patterns.md](refactoring-patterns.md#prompt-template) |
| Route valida estado del dominio | Mover validación al Request Handler | [refactoring-patterns.md](refactoring-patterns.md#route-clean) |

Lee la sección del patrón en `refactoring-patterns.md` antes de continuar.

### A4 — Planificar el diff mínimo

**Regla de oro: toca lo menos posible.** Antes de editar, escribe explícitamente:

```
Cambios planificados:
1. [archivo] — [qué cambia exactamente y por qué]
2. [archivo] — [qué cambia exactamente y por qué]
Archivos que NO se tocan: [lista]
Comportamiento que NO cambia: [describir]
```

Si el refactor requiere un nuevo archivo (ej. orchestrator nuevo), crearlo antes de modificar el existente.

### A5 — Ejecutar con loop de validación

Por cada archivo modificado:

1. Haz el cambio
2. Verifica inmediatamente:
   ```bash
   # Syntax check
   uv run python -c "import app.<modulo>"
   
   # Si hay tests existentes, córrelos
   uv run pytest tests/ -k "<nombre_del_modulo>" -x -q
   ```
3. Si algo falla → revierte y replantea. No acumules errores.

**No modifiques el siguiente archivo hasta que el actual esté validado.**

### A6 — Verificar comportamiento sin cambios

```bash
# Correr la suite completa relacionada
uv run pytest tests/ -k "<dominio>" -q

# Si es una Celery task, verificar que el decorator y retry config son idénticos
rg -n "@celery_app.task\|@track_task_metrics\|max_retries" app/domain/services/celery_tasks.py
```

⚠️ **Si hay retries en vuelo en producción** (tareas con `acks_late=True` corriendo), coordina el deploy con rollout cuidadoso. Lee [refactoring-patterns.md](refactoring-patterns.md#retries-en-vuelo) antes de desplegar.

---

## Camino B — EXTENSIÓN

```
Progreso Extensión:
- [ ] B1: Leer el código existente que se va a extender
- [ ] B2: Identificar los puntos de extensión
- [ ] B3: Seleccionar el patrón de extensión
- [ ] B4: Ejecutar la extensión con validación
- [ ] B5: Verificar comportamiento existente intacto + nuevo comportamiento
```

### B1 — Leer el código existente

```bash
# Leer el módulo completo
cat <archivo_a_extender>

# Entender cómo se registra / invoca actualmente
rg -n "<NombreClase>\|<nombre_funcion>" app/ --include="*.py"
```

Entiende el patrón completo antes de agregar. **No supongas — lee.**

### B2 — Identificar los puntos de extensión

| Tipo de extensión | Dónde agregar | Qué más tocar |
|---|---|---|
| Nuevo paso en pipeline IA | Nuevo `Executor` + registrar en `pipelines.py` | `PromptExecutionContext` si necesita nuevo campo |
| Nuevo campo en modelo DB | `app/persistence/models/` + migration Alembic | Repository si necesita nueva query |
| Nuevo endpoint en resource existente | Agregar `@router.<method>` en route existente | Schema Pydantic si hay nuevo request/response |
| Nueva `revision_type` | Enum en models + Celery task + Orchestrator | `has_child_of_type()` en el flujo del árbol |
| Nuevo método en service existente | Agregar método al service | Tests unitarios |
| Nueva notificación | `slack_service` o `teams_service` ya existen — solo agregar llamada en orchestrator | — |

### B3 — Seleccionar el patrón de extensión

**Para nuevo executor en pipeline** (el más común):
1. Leer `app/domain/prompt_execution_pipeline/README.md` — el pipeline es order-dependent
2. Decidir la posición exacta del nuevo executor
3. Verificar qué campos del `PromptExecutionContext` lee y escribe
4. Ver template en `layers-reference.md` del skill `new-feature`

**Para nueva revision_type** (segundo más común):
1. Agregar al `RevisionType` enum
2. Crear thin Celery task en `celery_tasks.py`
3. Crear Orchestrator
4. Agregar al árbol de revisiones en `interview_auto_edit` si debe ser automático
5. `has_child_of_type()` ya evita duplicar ramas — no reimplementes este check

**Para nuevo campo en modelo + migration**:
Seguir el patrón seguro: nullable → backfill → NOT NULL. Ver template en `new-feature/layers-reference.md`.

### B4 — Ejecutar con validación

1. Crear el nuevo código (nuevo archivo o método)
2. Registrar en el punto de extensión (pipelines.py, enum, router, etc.)
3. Validar:
   ```bash
   uv run python -c "import app.<modulo>"
   uv run pytest tests/ -k "<nombre>" -x -q
   ```
4. No modificar código existente más de lo mínimo necesario para registrar la extensión.

### B5 — Verificar comportamiento doble

```
Checklist final:
- [ ] El comportamiento EXISTENTE sigue funcionando (tests pasan)
- [ ] La EXTENSIÓN funciona como se espera (nuevo test cubre el caso)
- [ ] No hay imports circulares nuevos
- [ ] Si se agregó executor: el orden en pipelines.py es el correcto
- [ ] Si se agregó campo DB: la migration tiene downgrade correcto
- [ ] Si se agregó revision_type: has_child_of_type() ya lo maneja
```

---

## Checklist final (ambos caminos)

```
- [ ] ¿Algún service hace db.merge() o db.flush()? → ERROR
- [ ] ¿Algún service llama webhook_service? → ERROR
- [ ] ¿Alguna Celery task tiene >30 líneas? → ERROR
- [ ] ¿Algún obj.meta = {...}? → ERROR: usar merge_metadata()
- [ ] ¿Hay imports circulares? → rg "from app" <archivo_nuevo>
- [ ] ¿Tests existentes siguen pasando? → uv run pytest -x -q
- [ ] ¿Se necesitan tests nuevos? → /aura-dev:add-test <archivo>
```
