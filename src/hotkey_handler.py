"""Manejador de traducción saliente (ES->EN) y atajo opcional Alt+T sin solapar teclas del juego."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import logging
import re
import sys
import threading
import time
from typing import Any

from PySide6.QtCore import QObject, Signal
import pyperclip

from src.config import load_config
from src.translator import WoWTranslator, get_translator, should_translate_message

logger = logging.getLogger(__name__)

# Códigos de tecla virtual Win32 (Virtual-Key Codes)
VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_MENU = 0x12  # Alt
VK_LMENU = 0xA4
VK_RMENU = 0xA5
VK_END = 0x23
VK_HOME = 0x24
VK_A = 0x41
VK_C = 0x43
VK_T = 0x54
VK_V = 0x56

KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002

_user32 = ctypes.windll.user32 if sys.platform == "win32" else None


def _is_vk_pressed(vk: int) -> bool:
    """Consulta directamente a Win32 si una tecla física está presionada en este instante."""
    if _user32 is None:
        return False
    return bool(_user32.GetAsyncKeyState(vk) & 0x8000)


def _key_down(vk: int, extended: bool = False) -> None:
    if _user32 is None:
        return
    scan = _user32.MapVirtualKeyW(vk, 0)
    flags = KEYEVENTF_EXTENDEDKEY if extended else 0
    _user32.keybd_event(vk, scan, flags, 0)


def _key_up(vk: int, extended: bool = False) -> None:
    if _user32 is None:
        return
    scan = _user32.MapVirtualKeyW(vk, 0)
    flags = KEYEVENTF_KEYUP | (KEYEVENTF_EXTENDEDKEY if extended else 0)
    _user32.keybd_event(vk, scan, flags, 0)


def _force_release_modifiers() -> None:
    """Asegura que Alt, Ctrl y Shift no queden lógicamente presionados antes de enviar atajos."""
    if _user32 is None:
        return
    for vk in (VK_MENU, VK_LMENU, VK_RMENU, VK_SHIFT):
        if _is_vk_pressed(vk):
            _key_up(vk)


def _send_ctrl_chord(letter_vk: int, hold_s: float = 0.035) -> None:
    """Envía Ctrl + Tecla con tiempos de retención reales para que DirectX 12 (Wow.exe) lo procese."""
    _key_down(VK_CONTROL)
    time.sleep(hold_s)
    _key_down(letter_vk)
    time.sleep(hold_s)
    _key_up(letter_vk)
    time.sleep(0.02)
    _key_up(VK_CONTROL)


def clean_captured_text(text: str) -> str:
    """Elimina 't' o 'T' espuria causada por la pulsación del atajo Alt+T."""
    if not text:
        return ""
    cleaned = text.strip()
    if cleaned.lower() == "t":
        return ""
    # Si termina con espacio y luego 't' o 'T' (ej. "hola amigos t")
    cleaned = re.sub(r"\s+[tT]$", "", cleaned)
    # Palabras legítimas en español / gaming que terminan en 't':
    legit_words_with_t = {
        "chat", "bot", "robot", "internet", "post", "test", "set",
        "ticket", "tuit", "loot", "reset", "target", "dot", "hot",
        "split", "slot", "talent", "cast", "frost", "quest"
    }
    words = cleaned.split()
    if words:
        last_word = words[-1]
        lower_last = last_word.lower().rstrip(".,!?:;")
        if lower_last.endswith("t") and lower_last not in legit_words_with_t and len(lower_last) > 2:
            words[-1] = last_word[:-1]
            cleaned = " ".join(words)
    return cleaned

def _send_end_shift_home(hold_s: float = 0.035) -> None:
    """Selecciona toda la línea en un EditBox de WoW usando End -> Shift+Home."""
    _key_down(VK_END, extended=True)
    time.sleep(hold_s)
    _key_up(VK_END, extended=True)
    time.sleep(0.025)

    _key_down(VK_SHIFT)
    time.sleep(hold_s)
    _key_down(VK_HOME, extended=True)
    time.sleep(hold_s)
    _key_up(VK_HOME, extended=True)
    time.sleep(0.02)
    _key_up(VK_SHIFT)


def focus_wow_window() -> bool:
    """Devuelve el foco a la ventana de World of Warcraft si se hizo clic en un botón del Overlay."""
    try:
        from src.window_tracker import refocus_wow_async
        refocus_wow_async()
        return True
    except Exception:
        pass
    if _user32 is not None:
        hwnd = _user32.FindWindowW(None, "World of Warcraft")
        if hwnd:
            _user32.SetForegroundWindow(hwnd)
            time.sleep(0.045)
            return True
    return False


class HotkeyHandler(QObject):
    """
    Controlador de traducción de salida (ES -> EN).
    - No registra F7/F8/F9/F10 ni otros atajos que colisionen con los binds de WoW.
    - Permite activar/desactivar el atajo único `Alt+T` desde la pestaña de Ajustes del Overlay,
      o disparar la traducción haciendo clic directamente en el botón `Traducir` del Overlay.
    """

    toggle_move_requested = Signal()
    toggle_pause_requested = Signal()
    scan_incoming_requested = Signal()
    clear_overlay_requested = Signal()
    status_notice = Signal(str)
    outgoing_translated = Signal(str, str)  # (original_es, translated_en)

    def __init__(
        self,
        config: dict[str, Any] | None = None,
        translator: WoWTranslator | None = None,
    ) -> None:
        super().__init__()
        self.config = config or load_config()
        self.translator = translator or get_translator()
        self._lock = threading.Lock()
        self._running = False
        self._paused = False
        self._hotkey_enabled: bool = bool(
            self.config.get("overlay", {}).get("enable_alt_t_hotkey", True)
        )
        self._poll_thread: threading.Thread | None = None
        self._thread_id: int | None = None

    @property
    def hotkey_enabled(self) -> bool:
        return self._hotkey_enabled

    def set_hotkey_enabled(self, enabled: bool) -> None:
        """Activa o desactiva el atajo global Alt+T para evitar cualquier solapamiento con el juego."""
        self._hotkey_enabled = enabled

    def set_paused(self, paused: bool) -> None:
        """Activa o desactiva la pausa de traducción."""
        self._paused = paused

    def start(self) -> bool:
        """Inicia el listener con RegisterHotKey que suprime Alt+T para que nunca se escriba 't'."""
        if self._running:
            return True
        if _user32 is None:
            return False

        self._running = True
        self._poll_thread = threading.Thread(
            target=self._hotkey_listener_thread,
            name="wow-win32-hotkey-listener",
            daemon=True,
        )
        self._poll_thread.start()
        logger.info(
            "Controlador ES->EN listo (atajo Alt+T con supresion nativa=%s)",
            self._hotkey_enabled,
        )
        return True

    def stop(self) -> None:
        """Detiene el hilo de monitoreo y libera el hotkey del sistema."""
        self._running = False
        if _user32 is not None and self._thread_id:
            WM_QUIT = 0x0012
            _user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
        if self._poll_thread is not None:
            self._poll_thread.join(timeout=1.0)
            self._poll_thread = None

    def _hotkey_listener_thread(self) -> None:
        """Registra Alt+T en Windows mediante RegisterHotKey.
        Al registrarse con el SO, Windows SUPRIME la tecla 't' y no la envía al EditBox de WoW."""
        if _user32 is None:
            return

        kernel32 = ctypes.windll.kernel32
        self._thread_id = kernel32.GetCurrentThreadId()

        HOTKEY_ID = 1001
        MOD_ALT = 0x0001
        MOD_NOREPEAT = 0x4000
        VK_T = 0x54
        WM_HOTKEY = 0x0312
        WM_QUIT = 0x0012

        # Intentar con MOD_NOREPEAT (Windows 7+)
        reg_ok = _user32.RegisterHotKey(None, HOTKEY_ID, MOD_ALT | MOD_NOREPEAT, VK_T)
        if not reg_ok:
            reg_ok = _user32.RegisterHotKey(None, HOTKEY_ID, MOD_ALT, VK_T)

        if not reg_ok:
            logger.warning("No se pudo registrar RegisterHotKey para Alt+T; usando fallback.")
            self._fallback_poll_loop()
            return

        class MSG(ctypes.Structure):
            _fields_ = [
                ("hwnd", wintypes.HWND),
                ("message", wintypes.UINT),
                ("wParam", wintypes.WPARAM),
                ("lParam", wintypes.LPARAM),
                ("time", wintypes.DWORD),
                ("pt", wintypes.POINT),
            ]

        msg = MSG()
        try:
            while self._running:
                has_msg = _user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1) # PM_REMOVE = 1
                if has_msg:
                    if msg.message == WM_HOTKEY and msg.wParam == HOTKEY_ID:
                        if self._hotkey_enabled and not self._paused:
                            self.trigger_outgoing_translation_async(refocus_wow=False)
                    elif msg.message == WM_QUIT:
                        break
                    _user32.TranslateMessage(ctypes.byref(msg))
                    _user32.DispatchMessageW(ctypes.byref(msg))
                else:
                    time.sleep(0.015)
        finally:
            _user32.UnregisterHotKey(None, HOTKEY_ID)

    def _fallback_poll_loop(self) -> None:
        """Sondeo alternativo en caso de que RegisterHotKey falle."""
        prev_translate = False
        while self._running:
            if not self._hotkey_enabled:
                prev_translate = False
                time.sleep(0.05)
                continue

            alt_down = (
                _is_vk_pressed(VK_MENU)
                or _is_vk_pressed(VK_LMENU)
                or _is_vk_pressed(VK_RMENU)
            )
            now_translate = alt_down and _is_vk_pressed(VK_T)
            if now_translate and not prev_translate:
                self.trigger_outgoing_translation_async(refocus_wow=False)

            prev_translate = now_translate
            time.sleep(0.018)

    def trigger_outgoing_translation_async(
        self, refocus_wow: bool = False
    ) -> None:
        """Lanza la traducción de la caja de chat de WoW en un hilo separado."""
        if self._paused:
            self.status_notice.emit("Traductor en pausa")
            return
        if self._lock.locked():
            return
        worker = threading.Thread(
            target=self.translate_active_chat_box,
            kwargs={"refocus_wow": refocus_wow},
            name="wow-hotkey-translate",
            daemon=True,
        )
        worker.start()

    def _wait_until_hotkey_released(self, timeout_s: float = 0.85) -> None:
        """Espera a que el usuario suelte físicamente Alt y T antes de enviar Ctrl+A / Ctrl+C."""
        deadline = time.perf_counter() + timeout_s
        while time.perf_counter() < deadline:
            if not (
                _is_vk_pressed(VK_MENU)
                or _is_vk_pressed(VK_LMENU)
                or _is_vk_pressed(VK_RMENU)
                or _is_vk_pressed(VK_T)
            ):
                break
            time.sleep(0.012)
        _force_release_modifiers()
        time.sleep(0.03)

    def _capture_text_from_editbox(self) -> str:
        """Selecciona y copia el texto del EditBox activo de WoW con fallback Shift+Home."""
        sentinel = "__WOW_EMPTY_CLIP__"
        try:
            pyperclip.copy(sentinel)
        except Exception:
            pass

        _send_ctrl_chord(VK_A, hold_s=0.035)
        time.sleep(0.065)
        _send_ctrl_chord(VK_C, hold_s=0.035)

        for _ in range(6):
            time.sleep(0.03)
            try:
                val = pyperclip.paste().strip()
                if val and val != sentinel:
                    return val
            except Exception:
                pass

        _send_end_shift_home(hold_s=0.035)
        time.sleep(0.065)
        _send_ctrl_chord(VK_C, hold_s=0.035)

        for _ in range(6):
            time.sleep(0.03)
            try:
                val = pyperclip.paste().strip()
                if val and val != sentinel:
                    return val
            except Exception:
                pass

        return ""

    def translate_active_chat_box(self, refocus_wow: bool = False) -> str | None:
        """
        Toma el texto de la caja de chat activa de WoW (Ctrl+A / Shift+Home -> Ctrl+C),
        lo traduce de ES -> EN gamer natural y lo pega (Ctrl+V) sin presionar Enter.
        """
        if not self._lock.acquire(blocking=False):
            return None

        try:
            self.status_notice.emit("Capturando texto del chat (ES -> EN)...")
            if refocus_wow:
                focus_wow_window()
            else:
                self._wait_until_hotkey_released()

            raw_text = self._capture_text_from_editbox()
            captured_text = clean_captured_text(raw_text)

            if not captured_text:
                self.status_notice.emit(
                    "No se detectó texto en la caja de chat de WoW."
                )
                return None

            if not should_translate_message(captured_text):
                self.status_notice.emit(
                    "El texto seleccionado no requiere traducción."
                )
                return None

            self.status_notice.emit(f"Traduciendo: {captured_text[:42]}...")
            translated = self.translator.translate_outgoing(captured_text)
            if not translated:
                self.status_notice.emit("No se pudo traducir el mensaje.")
                return None

            pyperclip.copy(translated)
            time.sleep(0.04)

            # Esperar que Alt y T estén 100% liberados antes de pegar
            self._wait_until_hotkey_released(timeout_s=0.25)
            _force_release_modifiers()
            _send_ctrl_chord(VK_V, hold_s=0.035)
            time.sleep(0.04)

            self.outgoing_translated.emit(captured_text, translated)
            self.status_notice.emit(
                f"ES->EN ({self.translator.last_latency_ms:.0f}ms): {translated}"
            )
            return translated
        except Exception as exc:
            logger.warning("Error durante traducción ES->EN: %s", exc)
            self.status_notice.emit(f"Error al traducir salida: {exc}")
            return None
        finally:
            self._lock.release()
