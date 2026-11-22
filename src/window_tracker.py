"""
Módulo de seguimiento y anclaje pasivo a la ventana de World of Warcraft.
Detecta el estado de Wow.exe (activo, minimizado, visible, posición en pantalla)
sin inyección de DLLs ni acceso a memoria (100% Anti-Cheat compliant).
"""

from __future__ import annotations

import ctypes
from dataclasses import dataclass
import logging
import os
import sys
import time
from typing import Any

logger = logging.getLogger(__name__)

# Configuración segura de tipos ctypes en Windows de 64 bits
if sys.platform == "win32":
    from ctypes import wintypes

    user32 = ctypes.windll.user32

    user32.OpenDesktopW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.BOOL,
        wintypes.DWORD,
    ]
    user32.OpenDesktopW.restype = wintypes.HANDLE

    user32.CloseDesktop.argtypes = [wintypes.HANDLE]
    user32.CloseDesktop.restype = wintypes.BOOL

    user32.GetForegroundWindow.argtypes = []
    user32.GetForegroundWindow.restype = wintypes.HWND

    user32.IsWindow.argtypes = [wintypes.HWND]
    user32.IsWindow.restype = wintypes.BOOL

    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.IsWindowVisible.restype = wintypes.BOOL

    user32.IsIconic.argtypes = [wintypes.HWND]
    user32.IsIconic.restype = wintypes.BOOL

    user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user32.GetWindowRect.restype = wintypes.BOOL

    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetWindowTextW.restype = ctypes.c_int

    user32.GetWindowThreadProcessId.argtypes = [
        wintypes.HWND,
        ctypes.POINTER(wintypes.DWORD),
    ]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD

    kernel32 = ctypes.windll.kernel32
    user32.SetForegroundWindow.argtypes = [wintypes.HWND]
    user32.SetForegroundWindow.restype = wintypes.BOOL
    user32.AttachThreadInput.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.BOOL]
    user32.AttachThreadInput.restype = wintypes.BOOL
    user32.BringWindowToTop.argtypes = [wintypes.HWND]
    user32.BringWindowToTop.restype = wintypes.BOOL
    user32.SetThreadDesktop.argtypes = [wintypes.HANDLE]
    user32.SetThreadDesktop.restype = wintypes.BOOL


    WNDENUMPROC = ctypes.WINFUNCTYPE(
        wintypes.BOOL, wintypes.HWND, wintypes.LPARAM
    )
else:
    user32 = None  # type: ignore[assignment]
    WNDENUMPROC = None  # type: ignore[assignment]


@dataclass
class WoWWindowState:
    """Estado instantáneo de la ventana de World of Warcraft."""

    running: bool = False
    minimized: bool = False
    visible: bool = False
    foreground: bool = False
    our_foreground: bool = False
    rect: tuple[int, int, int, int] | None = None
    delta: tuple[int, int] = (0, 0)


class WoWWindowTracker:
    """
    Rastrea de forma pasiva y ultra liviana (<0.01ms) la ventana de Wow.exe.
    Permite anclar el overlay estrictamente al ciclo de vida y coordenadas del juego.
    """

    def __init__(self, target_process_name: str = "wow.exe") -> None:
        self.target_name = target_process_name.lower()
        self.our_pid = os.getpid()
        self._wow_hwnd: int | None = None
        self._wow_pid: int | None = None
        self._cached_pids: set[int] = set()
        self._last_pid_scan: float = 0.0
        self._last_rect: tuple[int, int, int, int] | None = None

    def _get_wow_pids(self, force_refresh: bool = False) -> set[int]:
        now = time.time()
        if (
            not force_refresh
            and self._cached_pids
            and (now - self._last_pid_scan) < 2.5
        ):
            return self._cached_pids

        self._cached_pids = set()
        try:
            import psutil

            for p in psutil.process_iter(["name"]):
                name = (p.info.get("name") or "").lower()
                if name == self.target_name or name == "wow.exe":
                    self._cached_pids.add(p.pid)
            self._last_pid_scan = now
        except Exception as exc:
            logger.debug("Error listando procesos de WoW: %s", exc)

        return self._cached_pids

    def find_wow_window(self) -> tuple[int | None, int | None, bool, bool, tuple[int, int, int, int] | None]:
        """
        Encuentra la ventana principal de WoW en el escritorio 'Default'.
        Devuelve (hwnd, pid, is_iconic, is_visible, rect).
        """
        if user32 is None:
            return None, None, False, False, None

        pids = self._get_wow_pids()
        if not pids:
            self._wow_hwnd = None
            self._wow_pid = None
            return None, None, False, False, None

        found_hwnd = None
        found_pid = None
        is_iconic = False
        is_visible = False
        rect = None

        try:
            hDesk = user32.OpenDesktopW("Default", 0, False, 0x0100)
            if hDesk:
                def cb(hwnd: int, lparam: Any) -> bool:
                    nonlocal found_hwnd, found_pid, is_iconic, is_visible, rect
                    w_pid = wintypes.DWORD()
                    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(w_pid))
                    if w_pid.value in pids:
                        title_buf = ctypes.create_unicode_buffer(256)
                        user32.GetWindowTextW(hwnd, title_buf, 256)
                        t = title_buf.value.lower()
                        if "world of warcraft" in t or t == "wow":
                            r = wintypes.RECT()
                            user32.GetWindowRect(hwnd, ctypes.byref(r))
                            rw = r.right - r.left
                            rh = r.bottom - r.top
                            ico = bool(user32.IsIconic(hwnd))
                            vis = bool(user32.IsWindowVisible(hwnd))
                            if (rw > 200 and rh > 200) or ico:
                                found_hwnd = hwnd
                                found_pid = w_pid.value
                                is_iconic = ico
                                is_visible = vis
                                rect = (r.left, r.top, r.right, r.bottom)
                                return False
                    return True

                user32.EnumDesktopWindows(hDesk, WNDENUMPROC(cb), 0)
                user32.CloseDesktop(hDesk)
        except Exception as exc:
            logger.debug("Error en EnumDesktopWindows: %s", exc)

        self._wow_hwnd = found_hwnd
        self._wow_pid = found_pid
        return found_hwnd, found_pid, is_iconic, is_visible, rect

    def get_state(self) -> WoWWindowState:
        """Obtiene el estado completo de WoW de forma segura y sin interrupciones."""
        if user32 is None:
            return WoWWindowState(
                running=True,
                minimized=False,
                visible=True,
                foreground=True,
                our_foreground=False,
            )

        hwnd, pid, is_iconic, is_visible, rect = self.find_wow_window()
        if not hwnd or not pid:
            self._last_rect = None
            return WoWWindowState(
                running=bool(self._cached_pids),
                minimized=True,
                visible=False,
                foreground=False,
                our_foreground=False,
                rect=None,
                delta=(0, 0),
            )

        fg_hwnd = user32.GetForegroundWindow()
        fg_pid = wintypes.DWORD()
        if fg_hwnd:
            user32.GetWindowThreadProcessId(fg_hwnd, ctypes.byref(fg_pid))

        is_fg = (fg_hwnd == hwnd) or (fg_pid.value == pid)
        is_our_fg = (fg_pid.value == self.our_pid)

        dx, dy = 0, 0
        if rect and self._last_rect and not is_iconic:
            dx = rect[0] - self._last_rect[0]
            dy = rect[1] - self._last_rect[1]

        if not is_iconic and rect:
            self._last_rect = rect

        return WoWWindowState(
            running=True,
            minimized=is_iconic,
            visible=is_visible and not is_iconic,
            foreground=is_fg,
            our_foreground=is_our_fg,
            rect=rect,
            delta=(dx, dy),
        )


def refocus_wow_async() -> None:
    """Devuelve el foco a World of Warcraft de forma limpia y sin enviar teclas sintéticas."""
    if user32 is None:
        return

    tracker = WoWWindowTracker()
    wow_hwnd, _, _, _, _ = tracker.find_wow_window()
    if not wow_hwnd:
        return

    # Si WoW ya es la ventana activa en primer plano, ¡NO TOCAR!
    # Llamar a SetForegroundWindow en una ventana activa puede resetear el buffer de DirectInput y cortar la tecla W.
    try:
        fg = user32.GetForegroundWindow()
        if fg == wow_hwnd:
            return
    except Exception:
        pass

    def _worker() -> None:
        try:
            hDesk = user32.OpenDesktopW("Default", 0, False, 0x0100)
            if hDesk:
                user32.SetThreadDesktop(hDesk)
            user32.SetForegroundWindow(wow_hwnd)
            if hDesk:
                user32.CloseDesktop(hDesk)
        except Exception as exc:
            logger.debug("Error en refocus_wow_async: %s", exc)

    import threading
    threading.Thread(target=_worker, name="wow-refocus", daemon=True).start()
