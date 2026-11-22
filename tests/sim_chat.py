"""Simulador de chat en tiempo real para WoWChatLog.txt (skill: simulate-wow-chat)."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import time

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MOCK_LOG = PROJECT_ROOT / "tests" / "mock_WoWChatLog.txt"

SIMULATED_MESSAGES: list[str] = [
    "[Grupo] [Hairy Warrior]: that sucked",
    "[Grupo] [Hairy Warrior]: i even got all the loot and that sucked",
    "[Grupo] [Ruby Daçherry]: is that it myu %^&* bugge dwhen i DCs",
    "[Grupo] [Ruby Daçherry]: DCd",
    "[Grupo] [Durotar Cowboy]: thats it",
    "[Comercio - Ciudad] [Spammer]: WTS boost 50g",
    "[Grupo] [Aptinstall Totem]: [[40C] Salvidentes sospechosos]",
]


def format_wow_log_line(raw_entry: str, now: datetime | None = None) -> str:
    """Formatea una línea con el timestamp oficial de WoWChatLog.txt: MM/DD HH:MM:SS.mmm."""
    dt = now or datetime.now()
    ms = int(dt.microsecond / 1000)
    ts = f"{dt.month:02d}/{dt.day:02d} {dt.hour:02d}:{dt.minute:02d}:{dt.second:02d}.{ms:03d}"
    return f"{ts}  {raw_entry}"


def run_simulation(
    log_path: Path = DEFAULT_MOCK_LOG,
    delay_seconds: float = 2.0,
    truncate: bool = True,
) -> list[str]:
    """Escribe mensajes simulados de WoW en el archivo de log con flush en tiempo real."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    if truncate and log_path.exists():
        log_path.write_text("", encoding="utf-8")

    written_lines: list[str] = []
    with log_path.open("a", encoding="utf-8") as f:
        for index, entry in enumerate(SIMULATED_MESSAGES):
            line = format_wow_log_line(entry)
            f.write(line + "\n")
            f.flush()
            written_lines.append(line)
            print(f"[sim_chat] ({index + 1}/{len(SIMULATED_MESSAGES)}) -> {line}")
            if delay_seconds > 0 and index < len(SIMULATED_MESSAGES) - 1:
                time.sleep(delay_seconds)

    return written_lines


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Simulador de flujo WoWChatLog.txt en tiempo real."
    )
    parser.add_argument(
        "--log-path",
        type=str,
        default=str(DEFAULT_MOCK_LOG),
        help="Ruta del archivo mock_WoWChatLog.txt",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="Segundos de pausa entre cada línea inyectada (default: 2.0)",
    )
    parser.add_argument(
        "--no-truncate",
        action="store_true",
        help="No limpiar el archivo antes de iniciar la simulación",
    )
    args = parser.parse_args()
    run_simulation(
        log_path=Path(args.log_path),
        delay_seconds=args.delay,
        truncate=not args.no_truncate,
    )


if __name__ == "__main__":
    main()
