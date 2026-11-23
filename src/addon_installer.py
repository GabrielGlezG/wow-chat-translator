"""
Módulo de instalación y sincronización automática del Addon ForeverChatLogger en World of Warcraft.
Permite que la aplicación de escritorio instale o actualice el addon con 1 solo clic
sin que el jugador tenga que buscar carpetas ni descomprimir archivos manualmente.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
import shutil
import sys

logger = logging.getLogger(__name__)

# Rutas estándar de instalación de World of Warcraft en Windows
STANDARD_WOW_LOCATIONS = [
    r"C:\Program Files (x86)\World of Warcraft\_forever_",
    r"C:\Program Files (x86)\World of Warcraft\_classic_",
    r"C:\Program Files (x86)\World of Warcraft\_classic_era_",
    r"C:\Program Files (x86)\World of Warcraft\_retail_",
    r"C:\World of Warcraft",
    r"D:\World of Warcraft",
    r"E:\World of Warcraft",
]

ADDON_FOLDER_NAME = "ForeverChatLogger"


def get_bundled_addon_source() -> Path:
    """Devuelve la ruta a los archivos del addon dentro del proyecto o paquete compilado."""
    if getattr(sys, "frozen", False):
        # Ejecutable compilado de PyInstaller
        base = Path(sys._MEIPASS)  # type: ignore[attr-defined]
    else:
        base = Path(__file__).resolve().parent.parent
    return base / "addon" / ADDON_FOLDER_NAME


def find_wow_addon_directory(custom_log_path: str = "") -> Path | None:
    """Encuentra la carpeta Interface/AddOns de WoW basándose en la configuración o rutas estándar."""
    # 1. Si hay una ruta configurada en config.json (ej: .../Logs/WoWChatLog.txt)
    if custom_log_path:
        log_p = Path(custom_log_path)
        wow_root = log_p.parent.parent if log_p.parent.name.lower() == "logs" else log_p.parent
        addons_dir = wow_root / "Interface" / "AddOns"
        if addons_dir.exists():
            return addons_dir
        if wow_root.exists():
            addons_dir.mkdir(parents=True, exist_ok=True)
            return addons_dir

    # 2. Búsqueda en rutas estándar de Windows
    for loc_str in STANDARD_WOW_LOCATIONS:
        loc = Path(loc_str)
        if loc.exists():
            addons_dir = loc / "Interface" / "AddOns"
            if addons_dir.exists():
                return addons_dir

    return None


def is_addon_installed(addons_dir: Path | None = None, custom_log_path: str = "") -> bool:
    """Comprueba si ForeverChatLogger está instalado en la carpeta de AddOns."""
    target_dir = addons_dir or find_wow_addon_directory(custom_log_path)
    if not target_dir or not target_dir.exists():
        return False
    toc = target_dir / ADDON_FOLDER_NAME / f"{ADDON_FOLDER_NAME}.toc"
    lua = target_dir / ADDON_FOLDER_NAME / f"{ADDON_FOLDER_NAME}.lua"
    return toc.exists() and lua.exists()


def install_addon_to_wow(addons_dir: Path | None = None, custom_log_path: str = "") -> tuple[bool, str]:
    """Copia los archivos del addon a Interface/AddOns/ForeverChatLogger/."""
    target_dir = addons_dir or find_wow_addon_directory(custom_log_path)
    if not target_dir:
        return False, "No se encontró la carpeta de instalación de World of Warcraft."

    src_addon_dir = get_bundled_addon_source()
    if not src_addon_dir.exists():
        return False, f"No se encontraron los archivos fuente del addon en {src_addon_dir}."

    dest_dir = target_dir / ADDON_FOLDER_NAME
    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
        for root, dirs, files in os.walk(src_addon_dir):
            rel_dir = Path(root).relative_to(src_addon_dir)
            target_sub = dest_dir / rel_dir
            target_sub.mkdir(parents=True, exist_ok=True)
            for file_name in files:
                p = Path(root) / file_name
                if p.suffix in (".lua", ".toc", ".xml", ".md"):
                    shutil.copy2(p, target_sub / file_name)

        logger.info("Addon ForeverChatLogger instalado con éxito en: %s", dest_dir)
        return True, f"Addon instalado con éxito en {dest_dir}"
    except Exception as exc:
        logger.error("Error al instalar addon: %s", exc)
        return False, f"Error al copiar archivos: {exc}"
