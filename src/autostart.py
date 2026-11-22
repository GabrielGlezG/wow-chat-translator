"""
Módulo para gestión de inicio automático con Windows y lanzadores para WoW Chat Translator.
Permite que el traductor se inicie automáticamente en segundo plano cuando el usuario
enciende la PC o abre World of Warcraft.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
import sys

logger = logging.getLogger(__name__)

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "WoWChatTranslator"


def get_pythonw_executable() -> str:
    """Devuelve la ruta al ejecutable pythonw.exe para ejecución silenciosa sin ventana de consola."""
    exe = sys.executable
    if "python.exe" in exe.lower():
        pyw = exe.replace("python.exe", "pythonw.exe").replace("PYTHON.EXE", "pythonw.exe")
        if os.path.exists(pyw):
            return pyw
    return exe


def get_main_module_command(project_root: Path | None = None) -> str:
    """Construye la línea de comandos para ejecutar la aplicación en segundo plano."""
    pyw = get_pythonw_executable()
    root = (project_root or Path(__file__).resolve().parent.parent).resolve()
    run_py = root / "run.py"
    return f'"{pyw}" "{run_py}"'


def is_windows_autostart_enabled() -> bool:
    """Verifica si la aplicación está registrada en el inicio de Windows (HKCU Run)."""
    if sys.platform != "win32":
        return False
    try:
        import winreg

        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ)
        try:
            val, _ = winreg.QueryValueEx(key, APP_NAME)
            return bool(val)
        finally:
            winreg.CloseKey(key)
    except Exception:
        return False


def set_windows_autostart(enable: bool, project_root: Path | None = None) -> bool:
    """Registra o elimina la aplicación del inicio de Windows (HKCU Run)."""
    if sys.platform != "win32":
        return False
    try:
        import winreg

        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE)
        try:
            if enable:
                cmd = get_main_module_command(project_root)
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
                logger.info("Inicio automático con Windows ACTIVADO: %s", cmd)
            else:
                try:
                    winreg.DeleteValue(key, APP_NAME)
                    logger.info("Inicio automático con Windows DESACTIVADO.")
                except FileNotFoundError:
                    pass
            return True
        finally:
            winreg.CloseKey(key)
    except Exception as exc:
        logger.error("Error al configurar inicio automático: %s", exc)
        return False


def create_desktop_launcher(wow_exe_path: str = r"C:\Program Files (x86)\World of Warcraft\_forever_\Wow.exe") -> Path | None:
    """
    Crea un lanzador silencioso en el Escritorio del usuario ('Jugar WoW con Traductor.vbs')
    que inicia el traductor en segundo plano y abre World of Warcraft simultáneamente.
    """
    if sys.platform != "win32":
        return None
    try:
        desktop = Path(os.environ.get("USERPROFILE", "C:/Users/gonza")) / "Desktop"
        if not desktop.exists():
            return None

        project_root = Path(__file__).resolve().parent.parent.resolve()
        pyw = get_pythonw_executable()
        main_py = project_root / "src" / "main.py"

        # Archivo VBS para ejecución 100% silenciosa sin ventana negra de CMD
        vbs_path = desktop / "Jugar WoW con Traductor.vbs"
        vbs_content = (
            'Set WshShell = CreateObject("WScript.Shell")\r\n'
            f'WshShell.CurrentDirectory = "{project_root}"\r\n'
            f'WshShell.Run """{pyw}"" ""{main_py}""", 0, False\r\n'
            f'WshShell.Run """{wow_exe_path}""", 1, False\r\n'
        )
        vbs_path.write_text(vbs_content, encoding="utf-8")

        # También crear un .bat complementario por conveniencia
        bat_path = desktop / "Jugar WoW con Traductor.bat"
        bat_content = (
            '@echo off\r\n'
            f'cd /d "{project_root}"\r\n'
            f'start "" "{pyw}" "{main_py}"\r\n'
            f'start "" "{wow_exe_path}"\r\n'
        )
        bat_path.write_text(bat_content, encoding="utf-8")

        logger.info("Lanzadores creados en el escritorio: %s y %s", vbs_path, bat_path)
        return vbs_path
    except Exception as exc:
        logger.error("Error al crear lanzador en el escritorio: %s", exc)
        return None
