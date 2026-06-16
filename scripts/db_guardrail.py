"""
Hook PreToolUse: detecta comandos bash destructivos sobre la DB y emite un aviso.
No bloquea — solo advierte para que el desarrollador pueda cancelar.
"""

import json
import re
import sys


DANGEROUS_PATTERNS = [
    (r"alembic downgrade", "alembic downgrade puede revertir migraciones con pérdida de datos"),
    (r"DROP\s+TABLE", "DROP TABLE destruye datos permanentemente"),
    (r"DROP\s+COLUMN", "DROP COLUMN puede causar pérdida de datos"),
    (r"DELETE\s+FROM\s+\w+\s*;", "DELETE sin WHERE borra todos los registros de la tabla"),
    (r"TRUNCATE\s+TABLE", "TRUNCATE borra todos los registros de la tabla"),
    (r"alembic\s+stamp\s+head", "alembic stamp head puede dejar el DB en estado inconsistente"),
]


def check(command: str) -> None:
    if not command:
        return

    for pattern, description in DANGEROUS_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            print(f"\n{'='*60}")
            print("⚠️  AURA DB GUARDRAIL")
            print("=" * 60)
            print(f"\nComando detectado como potencialmente destructivo:")
            print(f"  {description}")
            print(f"\nComando: {command.strip()}")
            print("\nVerifica que esto es intencional antes de proceder.")
            print("=" * 60)


if __name__ == "__main__":
    try:
        event = json.loads(sys.stdin.read())
        command = event.get("tool_input", {}).get("command", "")
    except (json.JSONDecodeError, AttributeError):
        command = sys.argv[1] if len(sys.argv) > 1 else ""
    check(command)
