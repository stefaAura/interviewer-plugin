# aura-dev — Plugin para Claude Code

Plugin `v2.0.0` para desarrollar `aura-core-ai-interviewer` desde Claude Code, con agentes especializados y skills que aplican la arquitectura de 8 capas del proyecto.

> Los `commands` están deprecados — los `skills` los reemplazan completamente. Este plugin no usa commands.

---

## Estructura

```
interviewer-plugin/
├── .claude-plugin/
│   ├── plugin.json                          Manifiesto del plugin (agentes + MCP)
│   └── marketplace.json                     Definición de marketplace
│
├── agents/                                  Subagentes especializados
│   ├── planner.md          [sonnet-4-6]     Entrevista y produce un plan MD estructurado
│   ├── coder.md            [opus-4-8]        Implementa código siguiendo las 8 capas
│   └── codebase-expert.md  [sonnet-4-6]     Responde preguntas del codebase con citas
│
├── skills/                                  Workflows invocables por el usuario
│   ├── architecture/       [sonnet-4-6]     Explica la arquitectura de capas (self-contained)
│   ├── new-feature/        [opus-4-8]        Scaffold de feature bottom-up
│   │   └── layers-reference.md               Templates de código por capa
│   ├── refactor-or-extend/ [opus-4-8]        Refactor estructural o extensión segura
│   │   └── refactoring-patterns.md           Patrones: slim-task, DI, JSONB, prompts
│   ├── code-review/        [sonnet-4-6]      Revisión post-implementación con reporte
│   │   └── review-criteria.md                Criterios detallados por categoría
│   └── fix-bug/            [opus-4-8]        Debugging científico con test de regresión
│       └── debugging-recipes.md              Recetas: Celery, async, JSONB, DB, webhooks
│
└── .mcp.json                                Context7 MCP server
```

---

## Estrategia de modelos

| Tarea | Modelo | Componentes |
|---|---|---|
| Codear | `claude-opus-4-8` | `coder`, `new-feature`, `refactor-or-extend`, `fix-bug` |
| Planear / revisar / consultar | `claude-sonnet-4-6` | `planner`, `codebase-expert`, `architecture`, `code-review` |

---

## Agentes

### `planner` — entrada para tareas grandes
```
@planner quiero agregar [feature]
```
1. Hace 5 preguntas: Problema, Outcome, Appetite, No-gos, Restricciones
2. Explora el codebase para basar el plan en código real
3. Produce un plan MD: capas, archivos a crear/modificar, orden bottom-up, riesgos, Definition of Done
4. **No escribe código** — solo planifica (tools de solo lectura)

### `coder` — implementación
```
@coder implementa [tarea o plan del planner]
```
Proceso obligatorio: **Explore → Plan → Code (bottom-up) → Verify**. Aplica todos los patrones del proyecto (JSONB, DI, thin tasks, prompts en templates) y nunca rompe los límites de capa.

### `codebase-expert` — consultas
```
@codebase-expert ¿cómo funciona [X]? / ¿dónde está [Y]?
```
Siempre busca antes de responder y cita `archivo:línea`. Read-only, nunca modifica nada.

---

## Skills

```
/aura-dev:architecture        → Explica dónde va el código y por qué
/aura-dev:new-feature         → Scaffold de feature nueva (reuse-first + bottom-up)
/aura-dev:refactor-or-extend  → Refactor estructural o extender funcionalidad existente
/aura-dev:code-review         → Revisión post-implementación (arquitectura, calidad, escalabilidad, tests)
/aura-dev:fix-bug             → Debugging de causa raíz con test de regresión
```

Cada skill usa **progressive disclosure**: el `SKILL.md` carga el archivo de referencia (`*-reference.md` / `*-patterns.md` / `*-recipes.md`) solo cuando se necesita.

---

## Flujo recomendado

```
1. @planner            → entender y planificar la tarea
2. @coder              → implementar (o /aura-dev:new-feature | refactor-or-extend)
3. /aura-dev:fix-bug   → si surge un bug durante el desarrollo
4. /aura-dev:code-review → validar antes del PR
```

Para dudas puntuales en cualquier momento: `@codebase-expert` o `/aura-dev:architecture`.

---

## MCP Context7

Documentación actualizada de las librerías del proyecto en Claude Code: FastAPI, SQLAlchemy 2.0, Celery, Pydantic v2, Alembic, OpenAI SDK, Anthropic SDK, pytest, tenacity, httpx.
Requiere `npx` disponible y la variable de entorno `CONTEXT7_API_KEY`.

---

## Instalación

```bash
# Cargar localmente para testing
claude --plugin-dir "C:\Users\stefa\OneDrive\Desktop\interviewer-plugin"

# Instalar en scope de proyecto (compartido con el equipo vía git)
claude plugin install "C:\Users\stefa\OneDrive\Desktop\interviewer-plugin" --scope project

# Instalar en scope usuario (todos los proyectos)
claude plugin install "C:\Users\stefa\OneDrive\Desktop\interviewer-plugin" --scope user
```
