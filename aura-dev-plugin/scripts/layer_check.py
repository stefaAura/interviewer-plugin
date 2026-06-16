"""
Hook PostToolUse: verifica violaciones de capa después de Write/Edit.
Imprime warnings si el archivo recién escrito viola las reglas de arquitectura.
"""

import json
import re
import sys


def check(file_path: str) -> None:
    if not file_path or not file_path.endswith(".py"):
        return

    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()
    except (FileNotFoundError, OSError):
        return

    warnings = []

    # Service que persiste
    if "domain/services" in file_path:
        if re.search(r"db\.(merge|flush|commit|add)\(", content):
            warnings.append(
                "⚠️  LAYER VIOLATION: service hace persistencia directa. "
                "Los services deben retornar resultados; el orchestrator persiste."
            )
        if re.search(r"await.*repository\.(create|update|save|delete)", content):
            warnings.append(
                "⚠️  LAYER VIOLATION: service llama repository directamente. "
                "La persistencia es responsabilidad del orchestrator."
            )

    # Route con validación de dominio
    if "api/routes" in file_path:
        if re.search(r"\.(status|state)\s*!=|if.*\.status\s*==", content):
            warnings.append(
                "⚠️  LAYER VIOLATION: route contiene validación de estado del dominio. "
                "Mueve esta lógica a un Request Handler."
            )
        if re.search(r"db\.(query|get|execute)\(", content):
            warnings.append(
                "⚠️  LAYER VIOLATION: route accede directamente a la DB. "
                "Las routes solo llaman handlers o services."
            )

    # Orchestrator que llama API externa directamente
    if "domain/orchestrators" in file_path:
        external_api_patterns = [
            r"await openai\.",
            r"await anthropic\.",
            r"await assemblyai\.",
            r"await elevenlabs\.",
            r"requests\.(get|post|put)",
            r"aiohttp\.ClientSession",
        ]
        for pattern in external_api_patterns:
            if re.search(pattern, content):
                warnings.append(
                    "⚠️  LAYER VIOLATION: orchestrator llama API externa directamente. "
                    "Usa un Provider para wrappear APIs externas."
                )
                break

    # JSONB sobrescrito sin merge_metadata
    if re.search(r"\.(meta|metadata)\s*=\s*\{", content):
        warnings.append(
            "⚠️  JSONB WARNING: asignación directa a .meta/.metadata detectada. "
            "Usa merge_metadata() para updates parciales y evitar destruir claves existentes."
        )

    # Service que envía webhooks directamente
    if "domain/services" in file_path and "celery_tasks" not in file_path:
        if re.search(r"webhook_service\.(send|notify|dispatch)", content):
            warnings.append(
                "⚠️  LAYER VIOLATION: service envía webhooks directamente. "
                "Los webhooks/notificaciones son responsabilidad del orchestrator, no del service."
            )

    # Celery task fat (>30 líneas de cuerpo de función)
    if "celery_tasks" in file_path:
        task_bodies = re.findall(
            r"@celery_app\.task.*?\ndef \w+\(.*?\n((?:(?!^@celery_app\.task|^def \w+\().+\n)*)",
            content,
            re.MULTILINE,
        )
        for body in task_bodies:
            lines = [l for l in body.splitlines() if l.strip() and not l.strip().startswith("#")]
            if len(lines) > 30:
                warnings.append(
                    f"⚠️  FAT TASK: Celery task con {len(lines)} líneas de lógica (máx: 30). "
                    "Extrae la lógica a un Orchestrator y deja la task como thin wrapper. "
                    "Usa el skill /aura-dev:slim-celery-task."
                )
                break

    # Repository con lógica de negocio
    if "persistence/repositories" in file_path:
        business_logic_patterns = [
            (r"if.*status.*==.*['\"]pending['\"]", "condicional de estado de negocio"),
            (r"await.*provider\.(complete|generate|transcribe)", "llamada a provider externo"),
            (r"await.*service\.\w+\(", "llamada a service desde repository"),
        ]
        for pattern, description in business_logic_patterns:
            if re.search(pattern, content):
                warnings.append(
                    f"⚠️  LAYER VIOLATION: repository contiene {description}. "
                    "Los repositories solo hacen CRUD y queries — la lógica va en services/orchestrators."
                )
                break

    # Secrets hardcodeados
    secret_patterns = [
        (r"(?i)(api_key|secret_key|password|token)\s*=\s*['\"][a-zA-Z0-9_\-]{16,}['\"]",
         "posible secret hardcodeado"),
        (r"sk-[a-zA-Z0-9]{20,}", "posible OpenAI API key"),
        (r"Bearer\s+[a-zA-Z0-9_\-\.]{20,}", "posible Bearer token hardcodeado"),
    ]
    for pattern, description in secret_patterns:
        if re.search(pattern, content):
            warnings.append(
                f"⚠️  SECURITY: {description} detectado. "
                "Usa get_settings() para acceder a API keys desde variables de entorno."
            )
            break

    if warnings:
        print(f"\n{'='*60}")
        print(f"AURA LAYER CHECK — {file_path}")
        print("=" * 60)
        for w in warnings:
            print(f"\n{w}")
        print("=" * 60)


if __name__ == "__main__":
    try:
        event = json.loads(sys.stdin.read())
        file_path = event.get("tool_input", {}).get("file_path", "")
    except (json.JSONDecodeError, AttributeError):
        file_path = sys.argv[1] if len(sys.argv) > 1 else ""
    check(file_path)
