"""Gestión de configuración y variables de entorno para wow-chat-translator."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from typing import Any

from dotenv import load_dotenv

if getattr(sys, "frozen", False):
    BUNDLE_ROOT = Path(sys._MEIPASS)
    APP_ROOT = Path(sys.executable).parent
else:
    BUNDLE_ROOT = Path(__file__).resolve().parent.parent
    APP_ROOT = BUNDLE_ROOT

PROJECT_ROOT = BUNDLE_ROOT
DEFAULT_CONFIG_PATH = APP_ROOT / "config.json"

load_dotenv(APP_ROOT / ".env")
load_dotenv(BUNDLE_ROOT / ".env")


DEFAULT_CONFIG: dict[str, Any] = {
    "wow_chat_log_path": "C:/Program Files (x86)/World of Warcraft/_forever_/Logs/WoWChatLog.txt",
    "player_name": "",
    "allowed_channels": [
        "Grupo",
        "Party",
        "Líder del grupo",
        "Party Leader",
        "Banda",
        "Raid",
        "Líder de banda",
        "Raid Leader",
        "Alerta de banda",
        "Raid Warning",
        "Hermandad",
        "Guild",
        "Oficial",
        "Officer",
        "Campo de batalla",
        "Battleground",
        "Susurro",
        "Whisper",
        "Decir",
        "Say",
        "Gritar",
        "Yell",
    ],
    "ignored_channels": [
        "Comercio",
        "Trade",
        "General",
        "DefensaLocal",
        "LocalDefense",
        "BuscarGrupo",
        "LookingForGroup",
        "Mundo",
        "World",
    ],
    "hotkeys": {
        "scan_incoming": "f7",
        "translate_outgoing": "f8",
        "toggle_move_overlay": "f9",
        "pause_resume": "f10",
        "clear_overlay": "alt+l",
    },
    "hotkey_delays_ms": {
        "after_select_all": 60,
        "after_copy": 60,
        "after_paste": 60,
    },
    "restore_clipboard": True,
    "overlay": {
        "x": 32,
        "y": 416,
        "width": 480,
        "height": 220,
        "max_messages": 6,
        "font_family": "Segoe UI",
        "font_size": 11,
        "background_opacity": 140,
        "show_original_en": False,
        "auto_fade": True,
        "auto_fade_seconds": 35,
        "enabled_channel_filters": {
            "Grupo": True,
            "Susurro": True,
            "Hermandad": True,
            "Banda": True,
            "Decir": True,
        },
    },
    "llm": {
        "provider": "local",
        "model": os.getenv("WOW_MODEL", "opus-mt"),
        "timeout_seconds": 3.0,
        "temperature": 0.2,
        "max_output_tokens": 128,
        "thinking_budget": 0,
    },
}




def auto_detect_wow_log_path() -> Path | None:
    """
    Detecta automáticamente el directorio de Wow.exe activo o instalado
    y resuelve la ruta de Logs/WoWChatLog.txt (Cero Configuración).
    """
    # 1. Buscar en procesos activos de Windows
    try:
        import psutil

        for proc in psutil.process_iter(["name", "exe"]):
            try:
                pname = (proc.info.get("name") or "").lower()
                if pname == "wow.exe" or (pname.startswith("wow") and "voice" not in pname):
                    exe_path = proc.info.get("exe")
                    if exe_path and os.path.isfile(exe_path):
                        candidate = Path(exe_path).parent / "Logs" / "WoWChatLog.txt"
                        candidate.parent.mkdir(parents=True, exist_ok=True)
                        return candidate
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except ImportError:
        pass

    # 2. Rutas conocidas comunes para WoW Forever y WoW en Windows
    common_roots = [
        Path(r"C:\Program Files (x86)\World of Warcraft\_forever_"),
        Path(r"C:\Program Files\World of Warcraft\_forever_"),
        Path(r"C:\World of Warcraft\_forever_"),
        Path(r"D:\World of Warcraft\_forever_"),
        Path(r"C:\WoW Forever"),
        Path(r"D:\WoW Forever"),
        Path(r"C:\Program Files (x86)\World of Warcraft"),
        Path(r"C:\Program Files\World of Warcraft"),
    ]
    for root in common_roots:
        if (root / "Wow.exe").exists() or (root / "Logs").exists():
            log_p = root / "Logs" / "WoWChatLog.txt"
            log_p.parent.mkdir(parents=True, exist_ok=True)
            return log_p

    return None

def load_config(config_path: Path | str = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    """Carga la configuración desde config.json combinándola con los valores por defecto y auto-detección."""
    path = Path(config_path)
    config = json.loads(json.dumps(DEFAULT_CONFIG))
    if path.exists():
        try:
            with path.open("r", encoding="utf-8") as f:
                user_cfg = json.load(f)
            for key, value in user_cfg.items():
                if isinstance(value, dict) and isinstance(config.get(key), dict):
                    config[key].update(value)
                else:
                    config[key] = value
        except (OSError, json.JSONDecodeError):
            pass

    # Auto-detección Zero-Config de WoWChatLog.txt si la ruta configurada no existe
    current_log = Path(config.get("wow_chat_log_path", ""))
    if not current_log.exists():
        detected = auto_detect_wow_log_path()
        if detected:
            config["wow_chat_log_path"] = str(detected).replace("\\", "/")
            try:
                save_config(config, path)
            except Exception:
                pass

    return config


def save_config(
    config: dict[str, Any], config_path: Path | str = DEFAULT_CONFIG_PATH
) -> None:
    """Guarda la configuración actualizada en config.json."""
    path = Path(config_path)
    with path.open("w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
        f.write("\n")


def get_gemini_api_key() -> str:
    """Obtiene la API key de Gemini desde variables de entorno (.env)."""
    return os.getenv("GEMINI_API_KEY", "").strip()
