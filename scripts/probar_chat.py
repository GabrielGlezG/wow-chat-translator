"""
Script interactivo para simular la llegada de mensajes reales de chat en World of Warcraft.
Escribe líneas en tiempo real en Logs/WoWChatLog.txt para verificar que el Watcher y el Overlay
las detecten y traduzcan al español instantáneamente.
"""

from datetime import datetime
import json
from pathlib import Path
import sys
import time

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config.json"


def get_log_path() -> Path:
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                p = cfg.get("wow_chat_log_path")
                if p:
                    return Path(p)
        except Exception:
            pass
    return Path(r"C:\Program Files (x86)\World of Warcraft\_forever_\Logs\WoWChatLog.txt")


SIMULATED_MESSAGES = [
    ("[Grupo] [Thunderfury]: hey healer oom need to drink a sec", "Thunderfury (Grupo)"),
    ("Frostmage te susurra: ty for the food earlier! mb on that wipe", "Frostmage (Susurro)"),
    ("[Banda] [Raidlead]: everyone stack behind the boss, watch out for tail swipe", "Raidlead (Banda)"),
    ("[Hermandad] [Elunepriest]: don't pull yet, tank has high lag spike", "Elunepriest (Hermandad)"),
    ("Shadowpriest te susurra: do you want to join our raid for Onyxia tonight?", "Shadowpriest (Susurro)"),
]


def main():
    log_path = get_log_path()
    print("=" * 65)
    print("  SIMULADOR DE CHAT DE WORLD OF WARCRAFT (EN -> ES)")
    print("=" * 65)
    print(f"Destino: {log_path}")
    print()

    if not log_path.parent.exists():
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"[ERROR] No se pudo crear la carpeta: {e}")
            return 1

    print("Enviando 5 mensajes de prueba espaciados por 1.5 segundos...")
    print("Mira la ventana del Overlay en pantalla para ver la traduccion en vivo.")
    print("-" * 65)

    for i, (msg_template, label) in enumerate(SIMULATED_MESSAGES, start=1):
        now_str = datetime.now().strftime("%m/%d %H:%M:%S.%f")[:-3]
        line = f"{now_str}  {msg_template}\n"
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(line)
            f.flush()
        print(f"[{i}/5] Enviado ({label}): {msg_template}")
        time.sleep(1.5)

    print("-" * 65)
    print("Todos los mensajes de prueba fueron inyectados exitosamente!")
    print("Revisa tu Overlay: deben aparecer traducidos al espanol.")
    print("=" * 65)
    return 0


if __name__ == "__main__":
    sys.exit(main())
