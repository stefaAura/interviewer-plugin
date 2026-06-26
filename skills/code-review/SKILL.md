---
name: code-review
description: >
  Post-implementation code review for aura-core-ai-interviewer. Verifies architecture layer
  compliance, code quality (type hints, error handling, logging, method length), scalability
  (async correctness, N+1 queries, Celery design), project-specific patterns (JSONB safety,
  DI container, thin tasks, prompt templates, secrets), and test coverage. Produces a
  structured report with PASS/FAIL/WARNING per category and a fix-and-recheck loop for
  any issues found. Use after implementing a feature, refactor, or migration — before
  opening a PR or deploying.
argument-hint: "[files or feature to review]"
model: claude-sonnet-4-6
---

# Code Review: $ARGUMENTS

Copia el reporte y complétalo durante la revisión.

```
## Reporte — $ARGUMENTS

### 1. Arquitectura          [ ] PASS  [ ] FAIL  [ ] WARNINGS
### 2. Calidad de código     [ ] PASS  [ ] FAIL  [ ] WARNINGS
### 3. Escalabilidad         [ ] PASS  [ ] FAIL  [ ] WARNINGS
### 4. Patrones del proyecto [ ] PASS  [ ] FAIL  [ ] WARNINGS
### 5. Tests                 [ ] PASS  [ ] FAIL  [ ] WARNINGS

VEREDICTO: [ ] ✅ LISTO  [ ] ❌ REQUIERE FIXES  [ ] ⚠️ MEJORAS OPCIONALES

Issues críticos (bloquean merge):
-

Issues opcionales:
-
```

---

## Paso 0 — Identificar los archivos a revisar

```bash
# Ver todos los archivos modificados desde main
git diff --name-only main...HEAD

# O revisar archivos específicos
ls -la app/api/routes/<nombre>.py app/domain/services/<nombre>_service.py ...
```

Listar explícitamente cada archivo que revisarás antes de empezar.

---

## 1. Arquitectura — ¿Cada clase está en la capa correcta?

Para cada archivo, verifica:

```bash
# Detectar persistence en services
rg -n "db\.merge\|db\.flush\|db\.add\|db\.commit" app/domain/services/ --include="*.py"

# Detectar webhooks en services
rg -n "webhook_service\|slack_service\|teams_service" app/domain/services/ --include="*.py"

# Detectar lógica de dominio en routes
rg -n "\.status\s*!=\|\.status\s*==\|if.*status\|if.*entity" app/api/routes/ --include="*.py"

# Detectar llamadas a API externa fuera de providers
rg -n "openai\.\|anthropic\.\|boto3\.\|assemblyai\." app/domain/services/ app/domain/orchestrators/ --include="*.py"

# Detectar Celery tasks fat (>30 líneas entre @task y el siguiente @)
rg -c "" app/domain/services/celery_tasks.py
```

**Tabla de violaciones críticas:**

| Si encuentras | En | Veredicto |
|---|---|---|
| `db.merge()` / `db.flush()` | `app/domain/services/` | ❌ FAIL |
| `webhook_service.send()` | `app/domain/services/` | ❌ FAIL |
| `if entity.status != ...` | `app/api/routes/` | ❌ FAIL |
| `openai.chat.complete(...)` | fuera de `providers/` | ❌ FAIL |
| Celery task >30 líneas | `celery_tasks.py` | ❌ FAIL |
| `executor.repository.save(...)` | `executors/` | ❌ FAIL |

Para detalles de cada capa → lee [review-criteria.md](review-criteria.md#arquitectura).

---

## 2. Calidad de código — ¿Es mantenible?

Revisa cada archivo nuevo o modificado:

### Type hints
```bash
# Funciones sin return type
rg -n "def [a-z_]+\(.*\):" app/<modulo> --include="*.py" | rg -v "->"
```
Cada función pública debe tener type hints en parámetros y return type.

### Error handling
```bash
# Excepciones silenciadas
rg -n "except.*:\s*$\|except.*pass\|except.*continue" app/<modulo> --include="*.py"
```
- `except Exception` sin logging → ❌
- `except Exception: pass` → ❌ siempre
- Solo captura lo específico; re-raise si no puedes manejar

### Logging
```bash
# Métodos públicos sin logging
rg -n "^    def [a-z]" app/<modulo> --include="*.py"
```
Cada método público con efectos secundarios debe tener al menos un `logger.info` o `logger.debug`.
Nunca `print()` en producción.

### Longitud de métodos
```bash
# Método más largo del archivo
awk '/def /{if(NR>1)print NR-start, name; start=NR; name=$0} END{print NR-start, name}' app/<archivo>
```
- Métodos >50 líneas → ⚠️ considerar extraer
- Función `run()` en orchestrator >80 líneas → ❌ extraer steps

### Secretos y configuración
```bash
rg -n "api_key\s*=\s*['\"]sk-\|password\s*=\s*['\"]" app/ --include="*.py"
rg -n "hardcoded\|TODO.*key\|FIXME.*secret" app/ --include="*.py"
```
Toda configuración via `get_settings().<CAMPO>`. Nunca literal de string para credenciales.

---

## 3. Escalabilidad — ¿Aguanta carga?

### Async correcto
```bash
# await en funciones síncronas (bug silencioso)
rg -n "def [a-z_]+.*:\s*$" app/ --include="*.py" -A3 | rg "await"

# I/O bloqueante en funciones async (puede bloquear el event loop)
rg -n "time\.sleep\|requests\." app/domain/ --include="*.py"
```
Reglas:
- Todo I/O (DB, HTTP, S3) → debe ser `async def` + `await`
- `time.sleep()` en async → reemplazar por `asyncio.sleep()`
- `requests.` en async → usar `httpx` async

### Queries DB — N+1 y carga innecesaria
```bash
# Queries dentro de loops (N+1 clásico)
rg -n "for.*:\s*$" app/persistence/ --include="*.py" -A5 | rg "\.query\|\.get\|repository\."
```
Reglas:
- Query dentro de un loop → ❌ reescribir con `IN` clause o join
- `SELECT *` o `.all()` sobre tabla grande sin `.limit()` → ⚠️
- Cargar relaciones lazy dentro de un loop → ⚠️ usar `.joinedload()`

### Diseño de Celery tasks para carga
Verifica en cada task nueva o modificada:
- `acks_late=True` → task se reencola si el worker muere ✅
- `bind=True` + `self.retry(exc=exc)` → retry correcto ✅
- Idempotencia: ¿puede correrse dos veces sin efectos negativos? ✅
- `max_retries` definido (no infinito) ✅
- `@track_task_metrics` presente ✅

Para criterios detallados → lee [review-criteria.md](review-criteria.md#escalabilidad).

---

## 4. Patrones del proyecto — ¿Sigue las convenciones?

```bash
# JSONB asignado directamente (destruye datos)
rg -n "\.meta\s*=\s*{\|\.analysis\s*=\s*{\|\.agent_metadata\s*=\s*{" app/ --include="*.py"

# Prompts hardcodeados (deben estar en templates/)
rg -n "\"\"\".*[Aa]nalyze\|\"\"\".*[Ss]ummarize\|prompt\s*=\s*f\"" app/domain/services/ app/domain/prompt_execution_pipeline/executors/ --include="*.py"

# Instanciación manual de clases que ya están en el DI
rg -n "= GenerativeAiService(\|= ConversationRepository(\|= MergeService(" app/ --include="*.py"

# Executor persistiendo fuera del context
rg -n "repository\.\|db\." app/domain/prompt_execution_pipeline/executors/ --include="*.py"
```

**Checklist de patrones:**

```
- [ ] JSONB: solo via merge_metadata(), nunca asignación directa
- [ ] Prompts: en app/domain/prompts/templates/*.txt, no hardcodeados
- [ ] Secretos: en get_settings(), nunca literal de string
- [ ] DI: clases en container.py no se instancian manualmente
- [ ] Executors: solo escriben a PromptExecutionContext, no persisten
- [ ] Migrations: NOT NULL tiene server_default o backfill previo
- [ ] Migrations: nueva FK tiene índice en la misma migración
- [ ] Migrations: downgrade() revierte exactamente el upgrade()
```

---

## 5. Tests — ¿Está cubierto?

```bash
# Ver tests existentes para el módulo
find tests/ -name "*<nombre>*" -type f

# Cobertura actual del archivo
uv run pytest tests/ -k "<nombre>" --cov=app/<modulo> --cov-report=term-missing -q
```

**Cobertura mínima: 85%**

| Qué se implementó | Tests requeridos |
|---|---|
| Service nuevo | Unit: happy path + edge cases + error paths |
| Orchestrator nuevo | Unit: cada `_step_X()` por separado |
| Provider nuevo | Unit: mock del cliente externo |
| Repository nuevo | Integration: con DB real |
| Route nueva | Integration: request completo end-to-end |
| Executor nuevo | Unit: context antes y después de `execute()` |
| Migration | Integration: upgrade + downgrade |

Si faltan tests → invoca `/aura-dev:add-test <archivo>` antes de considerar el PR listo.

---

## Loop de fix y re-verificación

Si cualquier sección tiene ❌ FAIL:

```
Fix loop:
1. Toma el primer issue crítico del reporte
2. Lee el patrón correcto en review-criteria.md o refactor-or-extend/refactoring-patterns.md
3. Aplica el fix mínimo necesario
4. Re-corre solo la verificación del punto afectado (bash commands de arriba)
5. Actualiza el reporte
6. Repite hasta que no queden ❌

No pases a un ⚠️ WARNING hasta limpiar todos los ❌ FAIL.
```

---

## Completar el reporte final

Cuando todas las secciones estén PASS o WARNINGS:

```
## Reporte Final — $ARGUMENTS
Fecha: <hoy>

### 1. Arquitectura          ✅ PASS
### 2. Calidad de código     ✅ PASS
### 3. Escalabilidad         ⚠️ WARNINGS
### 4. Patrones del proyecto ✅ PASS
### 5. Tests                 ✅ PASS

VEREDICTO: ✅ LISTO PARA PR

Issues críticos resueltos:
- [describir qué se encontró y cómo se resolvió]

Issues opcionales pendientes:
- [mejoras no bloqueantes para futuros PRs]
```
