# aura-dev Plugin — Plan y Estado

Plugin para desarrollar `aura-core-ai-interviewer` desde Claude Code de forma eficiente.

> **Investigación:** Los `commands` están deprecados — los `skills` los reemplazan completamente.
> No se usan commands en este plugin.

---

## Estructura creada

```
aura-dev-plugin/
├── .claude-plugin/
│   └── plugin.json                     ✅ Manifiesto del plugin
│
├── agents/                             ← Subagentes especializados
│   ├── aura-planner.md                 ✅ EL AGENTE CLAVE — planifica antes de codear
│   ├── arch-reviewer.md                ✅ Revisa violaciones de arquitectura de capas
│   ├── test-writer.md                  ✅ Genera tests pytest completos
│   └── db-reviewer.md                  ✅ Revisa migraciones Alembic
│
├── skills/                             ← Invocados por el usuario
│   ├── new-feature/SKILL.md            ✅ Scaffold de feature siguiendo las capas
│   ├── layer-check/SKILL.md            ✅ Delegación a arch-reviewer
│   ├── search-reuse/SKILL.md           ✅ Protocolo reuse-first del AGENTS.md
│   ├── add-test/SKILL.md               ✅ Delegación a test-writer
│   ├── new-migration/SKILL.md          ✅ Flujo Alembic completo
│   ├── add-provider/SKILL.md           ✅ Scaffold de proveedor API externa
│   └── add-orchestrator/SKILL.md       ✅ Scaffold tipo MP3ImportOrchestrator
│
├── hooks/
│   └── hooks.json                      ✅ PostToolUse (Write/Edit) + PreToolUse (Bash)
│
├── scripts/
│   ├── layer_check.py                  ✅ Detecta violaciones de capa post-escritura
│   └── db_guardrail.py                 ✅ Advierte ante comandos bash destructivos
│
└── .mcp.json                           ✅ Context7 MCP server
```

---

## Cómo usar cada componente

### El agente planificador — punto de entrada principal

```
@aura-planner describe la feature o fix que quieres hacer
```

El agente:
1. Lee automáticamente `AGENTS.md` y `.windsurf/workflows/architecture.md`
2. Te pide que confirmes: Problema / Outcome / Appetite / No-gos
3. Busca código reutilizable antes de proponer nada nuevo
4. Produce un plan estructurado con capas, archivos y riesgos
5. NO escribe código

### Skills disponibles para el usuario

```
/aura-dev:new-feature       → Scaffoldear feature (con reuse-first automático)
/aura-dev:layer-check       → Revisar violaciones de arquitectura
/aura-dev:search-reuse      → Buscar código existente antes de crear nuevo
/aura-dev:add-test          → Generar tests pytest
/aura-dev:new-migration     → Crear y revisar migración Alembic
/aura-dev:add-provider      → Scaffold proveedor de API externa
/aura-dev:add-orchestrator  → Scaffold orquestador tipo MP3Import
```

### Agentes que Claude invoca internamente

```
@arch-reviewer  → Revisión de capas (invocado por /layer-check)
@test-writer    → Generación de tests (invocado por /add-test)
@db-reviewer    → Revisión de migraciones (invocado por /new-migration)
```

### Hooks automáticos (sin intervención del usuario)

- **PostToolUse Write/Edit** → `layer_check.py` revisa cada archivo Python escrito
- **PreToolUse Bash** → `db_guardrail.py` avisa antes de comandos destructivos en DB

### MCP Context7

Documentación actualizada de las librerías del proyecto disponible en Claude Code.
Librerías cubiertas: FastAPI, SQLAlchemy 2.0, Celery, Pydantic v2, Alembic, OpenAI SDK, Anthropic SDK, pytest, tenacity, httpx.

---

## Instalación en el repo interviewer

```bash
# Opción 1: Cargar localmente para testing
claude --plugin-dir "C:\Users\stefa\OneDrive\Desktop\New folder\aura-dev-plugin"

# Opción 2: Instalar en scope de proyecto (compartido con equipo vía git)
claude plugin install "C:\Users\stefa\OneDrive\Desktop\New folder\aura-dev-plugin" --scope project

# Opción 3: Instalar en scope usuario (todos los proyectos)
claude plugin install "C:\Users\stefa\OneDrive\Desktop\New folder\aura-dev-plugin" --scope user
```

---

## Próximos pasos sugeridos

1. Verificar que `npx` esté disponible para Context7 MCP
2. Probar `@aura-planner` con una tarea real del repo
3. Ajustar el prompt del planner según cómo responda en la práctica
4. Agregar más skills según lo que se use más frecuentemente
5. Crear `CLAUDE.md` en el repo interviewer que importe `@AGENTS.md`
