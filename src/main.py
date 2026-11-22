"""Punto de entrada principal con System Tray, Pestañas en Overlay y filtro estricto anti-NPC."""

from __future__ import annotations

import sys
from pathlib import Path

# Asegurar que la raíz del proyecto esté en sys.path al ejecutarse directamente como script
_ROOT = str(Path(__file__).resolve().parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import re
import argparse
from collections import deque
import ctypes
from datetime import datetime
import logging
from pathlib import Path
import random
import sys
import threading
import time
from typing import Any

from PySide6.QtCore import (
    QBuffer,
    QByteArray,
    QIODevice,
    QObject,
    Qt,
    QTimer,
    Signal,
    Slot,
)
from PySide6.QtGui import (
    QAction,
    QColor,
    QFont,
    QGuiApplication,
    QIcon,
    QImage,
    QPainter,
    QPixmap,
)
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon
import pyperclip

from src.config import DEFAULT_CONFIG_PATH, load_config
from src.hotkey_handler import HotkeyHandler
from src.overlay import ChatOverlay
from src.translator import WoWTranslator
from src.window_tracker import WoWWindowTracker, WoWWindowState
from src.watcher import ChatLogWatcher, ChatMessage, is_likely_npc_sender, is_obviously_spanish, is_own_player_sender

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

_user32 = ctypes.windll.user32 if sys.platform == "win32" else None


def is_wow_foreground() -> bool:
    """Verifica si la ventana activa en primer plano es World of Warcraft."""
    if _user32 is None:
        return False
    hwnd = _user32.GetForegroundWindow()
    if not hwnd:
        return False
    buf = ctypes.create_unicode_buffer(128)
    _user32.GetWindowTextW(hwnd, buf, 128)
    title = buf.value.strip().lower()
    return "world of warcraft" in title or title == "wow"


def compute_text_glyph_signature(img: QImage) -> tuple[int, ...]:
    """
    Calcula una huella ligera de los glifos de texto del chat de WoW
    (píxeles brillantes con sombra negra 1px abajo/derecha), ignorando el terreno 3D de fondo.
    """
    scaled = img.scaled(
        160, 72, Qt.AspectRatioMode.IgnoreAspectRatio
    ).convertToFormat(QImage.Format.Format_RGB32)
    w, h = scaled.width(), scaled.height()
    ptr = scaled.constBits()
    data = bytes(ptr)
    stride = scaled.bytesPerLine()

    band_counts: list[int] = [0] * 6
    band_h = max(1, (h - 1) // 6)

    for y in range(0, h - 1):
        row_off = y * stride
        next_row_off = (y + 1) * stride
        band_idx = min(5, y // band_h)
        count = 0
        for x in range(0, w - 1, 2):
            px_off = row_off + x * 4
            b, g, r = data[px_off], data[px_off + 1], data[px_off + 2]
            if r > 160 or g > 160 or b > 160:
                sh_off = next_row_off + (x + 1) * 4
                sb, sg, sr = data[sh_off], data[sh_off + 1], data[sh_off + 2]
                if sr < 42 and sg < 42 and sb < 42:
                    count += 1
        band_counts[band_idx] += count

    return tuple(band_counts)


def signatures_differ(
    sig_a: tuple[int, ...] | None, sig_b: tuple[int, ...]
) -> bool:
    """Determina si apareció o se desplazó una línea de texto en la caja de chat."""
    if sum(sig_b) < 6:
        return False
    if sig_a is None:
        return True
    diff = sum(abs(a - b) for a, b in zip(sig_a, sig_b))
    total = max(1, sum(sig_b))
    return diff >= 8 and (diff / total) >= 0.14


def create_tray_icon() -> QIcon:
    """Genera un icono vectorial en memoria estilo WoW ('W') para la bandeja del sistema."""
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    painter.setBrush(QColor("#1A2436"))
    painter.setPen(QColor("#FFD100"))
    painter.drawRoundedRect(4, 4, 56, 56, 12, 12)

    font = QFont("Segoe UI", 28, QFont.Weight.Bold)
    painter.setFont(font)
    painter.setPen(QColor("#FFD100"))
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "W")
    painter.end()
    return QIcon(pixmap)



VALID_SCREEN_CHANNELS = {
    "grupo": "Grupo",
    "party": "Grupo",
    "banda": "Banda",
    "raid": "Banda",
    "hermandad": "Hermandad",
    "guild": "Hermandad",
}

WORLD_ACTION_KEYWORDS = (
    "crea ", "recibes botín", "recibes botin", "obtienes ", "reputación", "reputacion",
    "misión", "mision", "logro", "abandona", "se une", "cambio de canal", "ausente",
    "creates", "loot", "gana ", "experiencia", "ha aumentado", "ha disminuido"
)


def parse_screen_chat_line(line: str) -> tuple[str, str, str] | None:
    """
    Parsea una línea de texto del OCR de pantalla de WoW.
    Devuelve (canal, remitente, texto) si y solo si es un mensaje de chat
    de jugadores reales en Grupo, Banda, Hermandad, Susurro o Decir.
    Descarta estrictamente loot, profesiones, acciones del mundo y NPCs.
    """
    raw = line.strip()
    if not raw or len(raw) < 4:
        return None

    lower = raw.lower()
    if any(k in lower for k in WORLD_ACTION_KEYWORDS):
        return None

    # Descartar lenguajes de fantasía de NPCs ([Viscerálico], [Orco], etc.)
    if re.search(r"\[(?:viscerálico|visceralico|orco|taurhe|kalimag|demónico|demonico|darnassiano)\]", lower):
        return None

    # 1. Susurros: "Sender te susurra: message" o "Sender whispers: message"
    for verb in ("te susurra:", "whispers:", "susurra:"):
        if verb in lower:
            idx = lower.find(verb)
            sender = re.sub(r"[^\w\s-]", "", raw[:idx]).strip()
            msg = raw[idx + len(verb):].strip()
            if sender and msg and not sender.lower().startswith("para ") and not sender.lower().startswith("to "):
                return ("Susurro", sender, msg)

    # 2. Decir: "Sender dice: message" o "Sender says: message"
    for verb in ("dice:", "says:"):
        if verb in lower:
            idx = lower.find(verb)
            sender = re.sub(r"[^\w\s-]", "", raw[:idx]).strip()
            msg = raw[idx + len(verb):].strip()
            if sender and msg:
                return ("Decir", sender, msg)

    # 3. Canales con corchetes: "[Grupo] [Sender]: message" o "[Party] Sender: message"
    cleaned = raw.replace("[Grupol", "[Grupo]").replace("[Bandal", "[Banda]").replace("[Hermandadl", "[Hermandad]")
    m = re.match(r"^\[(?P<chan>[^\]]+)\]\s*(?:\[(?P<snd1>[^\]]+)\]|(?P<snd2>[^:]+)):\s*(?P<msg>.+)$", cleaned)
    if m:
        chan_raw = m.group("chan").strip().lower()
        matched_chan = None
        for k, v in VALID_SCREEN_CHANNELS.items():
            if k in chan_raw:
                matched_chan = v
                break
        if matched_chan:
            sender = (m.group("snd1") or m.group("snd2") or "").strip().strip("[]")
            msg_text = m.group("msg").strip()
            if sender and msg_text:
                return (matched_chan, sender, msg_text)

    return None


class AppController(QObject):
    """Coordinador principal entre Watcher, Lector Visual de Chat, Translator y Overlay con Pestañas."""

    screen_messages_ready = Signal(list)

    def __init__(
        self,
        app: QApplication,
        config: dict[str, Any],
        config_path: Path = DEFAULT_CONFIG_PATH,
        read_from_start: bool = False,
    ) -> None:
        super().__init__()
        self.app = app
        self.config = config
        self.config_path = config_path

        self.translator = WoWTranslator(config=self.config)
        self.overlay = ChatOverlay(config=self.config, config_path=self.config_path)
        self.watcher = ChatLogWatcher(
            config=self.config,
            translator=self.translator,
            read_from_start=read_from_start,
        )
        self.hotkey_handler = HotkeyHandler(
            config=self.config,
            translator=self.translator,
        )

        self._seen_keys: deque[tuple[str, str]] = deque(maxlen=80)
        self._last_glyph_sig: tuple[int, ...] | None = None
        self._vision_busy = False
        self._last_file_log_time: float = 0.0

        self._screen_timer = QTimer(self)
        self._screen_timer.setInterval(1200)
        self._screen_timer.timeout.connect(self._auto_poll_screen_chat)

        self.window_tracker = WoWWindowTracker()
        self._anchor_timer = QTimer(self)
        self._anchor_timer.setInterval(120)
        self._anchor_timer.timeout.connect(self._sync_wow_window_state)

        self._setup_signals()
        self._setup_tray()

    def _setup_signals(self) -> None:
        self.watcher.message_ready.connect(self._on_file_message)
        self.screen_messages_ready.connect(self._on_screen_messages)

        # Botones y pestañas del Overlay
        self.overlay.scan_requested.connect(self.force_scan_screen_chat)
        self.overlay.translate_box_requested.connect(
            self._on_overlay_translate_box_clicked
        )
        self.overlay.pause_toggled.connect(self.toggle_pause)
        self.overlay.manual_es_en_requested.connect(self._on_manual_es_en)
        self.overlay.alt_t_toggled.connect(self.hotkey_handler.set_hotkey_enabled)
        self.overlay.test_message_requested.connect(self.inject_test_message)
        self.overlay.player_name_changed.connect(self._on_player_name_changed)
        self.overlay.wow_path_changed.connect(self._on_wow_path_changed)

        # Señales desde HotkeyHandler
        self.hotkey_handler.toggle_move_requested.connect(self.toggle_move_mode)
        self.hotkey_handler.toggle_pause_requested.connect(self.toggle_pause)
        self.hotkey_handler.scan_incoming_requested.connect(
            self.force_scan_screen_chat
        )
        self.hotkey_handler.clear_overlay_requested.connect(
            self.overlay.clear_messages
        )
        self.hotkey_handler.status_notice.connect(self.overlay.show_status_notice)
        self.hotkey_handler.outgoing_translated.connect(
            self.overlay.add_outgoing_translation
        )

    @Slot(str)
    def _on_player_name_changed(self, name: str) -> None:
        self.config["player_name"] = name
        self.watcher.set_player_name(name)
        self.overlay.show_status_notice(f"Personaje activo: {name or 'Todos'}")

    @Slot(str)
    def _on_wow_path_changed(self, path_str: str) -> None:
        self.config["wow_chat_log_path"] = path_str
        self.watcher.set_log_path(path_str)
        self.overlay.show_status_notice("Carpeta de WoW sincronizada.")

    def _normalize_dedup_key(self, sender: str, text: str) -> str:
        clean_t = "".join(ch for ch in text.lower() if ch.isalnum())[:40]
        return clean_t

    @Slot()
    def _on_overlay_translate_box_clicked(self) -> None:
        """Devuelve el foco a WoW y traduce el texto escrito en la caja de chat."""
        self.hotkey_handler.trigger_outgoing_translation_async(refocus_wow=True)

    @Slot(str)
    def _on_manual_es_en(self, spanish_text: str) -> None:
        """Traduce un texto escrito en la pestaña Rápidas/Escribir y lo copia al portapapeles."""
        self.overlay.show_status_notice(f"⏳ Traduciendo: {spanish_text[:36]}...")

        def _worker() -> None:
            translated = self.translator.translate_outgoing(spanish_text)
            if translated:
                try:
                    pyperclip.copy(translated)
                except Exception:
                    pass
                self.hotkey_handler.outgoing_translated.emit(
                    spanish_text, translated
                )
                self.hotkey_handler.status_notice.emit(
                    f'Copiado al portapapeles: "{translated}"'
                )
            else:
                self.hotkey_handler.status_notice.emit(
                    "No se pudo traducir el texto."
                )

        threading.Thread(
            target=_worker, name="wow-manual-es-en", daemon=True
        ).start()

    @Slot()
    def inject_test_message(self) -> None:
        """Inyecta un mensaje realista de prueba en inglés en el log de WoW y fuerza su lectura."""
        test_pool = [
            ("[Grupo] [Thunderfury]: hey healer oom need to drink a sec", "Thunderfury"),
            ("Shadowpriest te susurra: do you want to join our raid for Onyxia tonight?", "Shadowpriest"),
            ("[Hermandad] [Elunepriest]: don't pull yet, tank has high lag spike", "Elunepriest"),
            ("Frostmage te susurra: ty for the water and food earlier! mb on that wipe", "Frostmage"),
            ("[Banda] [Raidlead]: everyone stack behind the boss, watch out for tail swipe", "Raidlead"),
            ("[Grupo] [Ironclad]: rogue please sap the humanoid on the left mark square", "Ironclad"),
            ("Redsy Deadsy te susurra: are you ready for the dungeon run now?", "Redsy Deadsy"),
        ]

        raw_template, sender = random.choice(test_pool)
        now_str = datetime.now().strftime("%m/%d %H:%M:%S.%f")[:-3]
        log_line = f"{now_str}  {raw_template}\n"

        target_path = Path(self.config.get("wow_chat_log_path", self.watcher.log_path))
        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            with open(target_path, "a", encoding="utf-8") as f:
                f.write(log_line)
                f.flush()
            self.overlay.show_status_notice(f"Mensaje de prueba inyectado de {sender}")
            self.watcher.poll_now()
        except Exception as exc:
            logger.error("Error al inyectar mensaje de prueba: %s", exc)
            self.overlay.show_status_notice(f"Error al inyectar: {exc}")

    @Slot(object)
    def _on_file_message(self, msg: ChatMessage) -> None:
        self._last_file_log_time = time.time()
        pname = str(self.config.get("player_name", "Aptinstall"))
        if is_own_player_sender(msg.sender, pname):
            return
        if is_likely_npc_sender(msg.sender, msg.original_text):
            return
        if is_obviously_spanish(msg.original_text):
            return
        key = self._normalize_dedup_key(msg.sender, msg.original_text)
        if key in self._seen_keys:
            return
        self._seen_keys.append(key)
        self.overlay.add_message(msg)

    @Slot(list)
    def _on_screen_messages(
        self, items: list[tuple[str, str, str, str]]
    ) -> None:
        added = 0
        pname = str(self.config.get("player_name", "Aptinstall"))
        for channel, sender, orig, trans in items:
            if is_own_player_sender(sender, pname):
                continue
            if is_likely_npc_sender(sender, orig):
                continue
            if is_obviously_spanish(orig):
                continue
            key = self._normalize_dedup_key(sender, orig)
            if key in self._seen_keys:
                continue
            self._seen_keys.append(key)
            msg = ChatMessage(
                timestamp="",
                channel=channel,
                sender=sender.strip("[]").strip(),
                original_text=orig,
                translated_text=trans,
            )
            self.overlay.add_message(msg)
            added += 1
        if added > 0:
            self.overlay.show_status_notice(
                f"{added} mensaje(s) traducido(s) ({self.translator.last_latency_ms:.0f}ms)"
            )

    @Slot()
    def _auto_poll_screen_chat(self) -> None:
        if self.watcher.paused or self._vision_busy:
            return
        if not is_wow_foreground():
            return
        # Optimización de motor: Si el log en disco está recibiendo mensajes limpios en tiempo real,
        # evitar escaneo OCR para no consumir CPU ni arriesgar errores visuales.
        if (time.time() - self._last_file_log_time) < 3.5:
            return
        self.scan_screen_chat(force=False)

    @Slot()
    def force_scan_screen_chat(self) -> None:
        """Slot seguro en el hilo principal de Qt para forzar lectura del chat al presionar Leer."""
        new_msgs = self.watcher.poll_now()
        if new_msgs > 0:
            self.overlay.show_status_notice(
                f"{new_msgs} mensaje(s) nuevo(s) leido(s)"
            )
            return

        self.scan_screen_chat(force=True)

    def scan_screen_chat(self, force: bool = False) -> None:
        """Captura la región de la caja de chat de WoW y traduce mensajes nuevos de jugadores."""
        if self._vision_busy:
            return
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return

        geom = screen.geometry()
        sw, sh = geom.width(), geom.height()
        crop_x = 0
        crop_y = int(sh * 0.54)
        crop_w = int(sw * 0.30)
        crop_h = int(sh * 0.23)

        ov_rect = self.overlay.geometry()
        overlaps = ov_rect.intersects(
            geom.adjusted(
                crop_x, crop_y, -(sw - crop_w), -(sh - (crop_y + crop_h))
            )
        )
        if overlaps:
            self.overlay.setWindowOpacity(0.0)
            self.app.processEvents()

        pixmap = screen.grabWindow(0, crop_x, crop_y, crop_w, crop_h)

        if overlaps:
            self.overlay.setWindowOpacity(1.0)

        qimg = pixmap.toImage()
        sig = compute_text_glyph_signature(qimg)
        if not force and not signatures_differ(self._last_glyph_sig, sig):
            return
        self._last_glyph_sig = sig

        ba = QByteArray()
        buf = QBuffer(ba)
        buf.open(QIODevice.OpenModeFlag.WriteOnly)
        qimg.save(buf, "PNG")
        png_bytes = bytes(ba.data())

        if force:
            self.overlay.show_status_notice(
                "⏳ Escaneando chat de jugadores en WoW..."
            )

        self._vision_busy = True

        def _worker() -> None:
            try:
                if self.translator.provider == "local" or self.translator._client is None:
                    # Motor de lectura visual 100% local y offline vía Windows Native OCR
                    try:
                        import winocr
                        from PIL import Image
                        import io

                        pil_img = Image.open(io.BytesIO(png_bytes))
                        up = pil_img.resize((pil_img.width * 2, pil_img.height * 2), Image.Resampling.BICUBIC)
                        ocr_data = winocr.recognize_pil_sync(up, "en")
                        lines = [l["text"].strip() for l in ocr_data.get("lines", []) if l.get("text")]
                        results = []
                        pname = str(self.config.get("player_name", "")).strip().lower()
                        for raw_l in lines:
                            parsed_info = parse_screen_chat_line(raw_l)
                            if not parsed_info:
                                continue
                            chan, sender, body = parsed_info
                            if is_likely_npc_sender(sender, body):
                                continue
                            if is_obviously_spanish(body):
                                continue
                            if is_own_player_sender(sender, pname):
                                continue
                            trans = self.translator.translate_incoming(body)
                            results.append((chan, sender, body, trans))
                        if results:
                            self.screen_messages_ready.emit(results)
                        elif force:
                            self.hotkey_handler.status_notice.emit("ℹ️ Chat al día (100% Offline).")
                    except Exception as err:
                        logger.debug("Error en OCR local de pantalla: %s", err)
                        if force:
                            self.hotkey_handler.status_notice.emit("ℹ️ Chat al día.")
                else:
                    results = self.translator.translate_chat_image(png_bytes)
                    if results:
                        self.screen_messages_ready.emit(results)
                    elif force:
                        self.hotkey_handler.status_notice.emit(
                            "ℹ️ No se detectaron mensajes nuevos de jugadores en inglés."
                        )
            finally:
                self._vision_busy = False

        threading.Thread(
            target=_worker, name="wow-screen-chat-vision", daemon=True
        ).start()

    def _setup_tray(self) -> None:
        self.tray_icon = QSystemTrayIcon(create_tray_icon(), self.app)
        self.tray_icon.setToolTip("WoW Forever Chat Translator")

        self.tray_menu = QMenu()

        self.action_scan = QAction(
            "Leer y traducir chat visible", self.tray_menu
        )
        self.action_scan.triggered.connect(self.force_scan_screen_chat)
        self.tray_menu.addAction(self.action_scan)

        self.action_clear = QAction(
            "Limpiar historial", self.tray_menu
        )
        self.action_clear.triggered.connect(self.overlay.clear_messages)
        self.tray_menu.addAction(self.action_clear)

        self.action_min = QAction(
            "Plegar / Desplegar Overlay", self.tray_menu
        )
        self.action_min.triggered.connect(self.overlay.toggle_minimize_in_game)
        self.tray_menu.addAction(self.action_min)

        self.action_bilingual = QAction(
            "Alternar Modo Bilingue (EN+ES)", self.tray_menu
        )
        self.action_bilingual.triggered.connect(self.overlay.toggle_bilingual_mode)
        self.tray_menu.addAction(self.action_bilingual)

        self.action_pause = QAction("⏸ Pausar traducción", self.tray_menu)
        self.action_pause.setCheckable(True)
        self.action_pause.triggered.connect(self.toggle_pause)
        self.tray_menu.addAction(self.action_pause)

        self.tray_menu.addSeparator()

        self.action_quit = QAction("Cerrar", self.tray_menu)
        self.action_quit.triggered.connect(self.shutdown)
        self.tray_menu.addAction(self.action_quit)

        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.show()

    @Slot()
    def toggle_pause(self) -> None:
        """Pausa o reanuda el watcher y el traductor."""
        new_paused = not self.watcher.paused
        self.watcher.set_paused(new_paused)
        self.hotkey_handler.set_paused(new_paused)
        self.action_pause.setChecked(new_paused)
        self.overlay.set_paused_ui(new_paused)
        if new_paused:
            self.overlay.show_status_notice("⏸ Traducción en PAUSA", 0)
        else:
            self.overlay.show_status_notice("▶️ Traducción ACTIVA")

    @Slot()
    def _sync_wow_window_state(self) -> None:
        """
        Sincroniza la visibilidad y posición del overlay con el estado de WoW.
        Si WoW se minimiza o pierde el foco (según configuración), el overlay se oculta
        inmediatamente para no quedar flotando sobre el escritorio o sobre otras aplicaciones.
        """
        state = self.window_tracker.get_state()

        should_hide = False

        if not state.running:
            if self.overlay.auto_hide_on_minimize:
                should_hide = True
        elif state.minimized or not state.visible:
            if self.overlay.auto_hide_on_minimize:
                should_hide = True
        elif self.overlay.only_visible_with_wow:
            if not (state.foreground or state.our_foreground):
                should_hide = True

        if should_hide:
            if self.overlay.isVisible():
                self.overlay.hide()
        else:
            if not self.overlay.isVisible():
                self.overlay.show()

            dx, dy = state.delta
            if (dx != 0 or dy != 0) and state.rect:
                self.overlay.on_wow_window_moved(dx, dy, state.rect)

    @Slot()
    def toggle_move_mode(self) -> None:
        """Compatibilidad con alternancia de modo edición."""
        self.overlay.toggle_move_mode()

    def start(self) -> None:
        """Inicia el monitoreo de WoWChatLog.txt, el lector visual y el Overlay con pestañas."""
        self.overlay.show()
        self.translator.warmup_async()
        self.watcher.start()
        self.hotkey_handler.start()
        self._anchor_timer.start()
        self._sync_wow_window_state()
        if self.config.get("auto_screen_poll", False):
            self._screen_timer.start()
        mode_str = "Motor Local Offline" if self.translator.provider == "local" else f"Gemini ({self.translator.model})"
        self.overlay.show_status_notice(
            f"Listo [{mode_str}]: Pestañas activas",
            6500,
        )

    @Slot()
    def shutdown(self) -> None:
        """Detiene hilos, limpia hotkeys y cierra la aplicación de forma segura."""
        logger.info("Cerrando WoW Chat Translator...")
        self._anchor_timer.stop()
        self._screen_timer.stop()
        self.hotkey_handler.stop()
        self.watcher.stop()
        self.tray_icon.hide()
        self.overlay.close()
        self.app.quit()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="WoW Forever Real-Time Chat Translator (EN<->ES)"
    )
    parser.add_argument(
        "--config",
        type=str,
        default=str(DEFAULT_CONFIG_PATH),
        help="Ruta al archivo config.json",
    )
    parser.add_argument(
        "--log-path",
        type=str,
        default=None,
        help="Ruta opcional a WoWChatLog.txt (sobreescribe config.json)",
    )
    parser.add_argument(
        "--from-start",
        action="store_true",
        help="Leer WoWChatLog.txt desde el principio en lugar de hacer tail desde el final",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=0.0,
        help="Cerrar automáticamente después de N segundos (útil para pruebas automatizadas)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    config_path = Path(args.config)
    config = load_config(config_path)

    if args.log_path:
        config["wow_chat_log_path"] = args.log_path

    app = QApplication.instance() or QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    controller = AppController(
        app=app,  # type: ignore[arg-type]
        config=config,
        config_path=config_path,
        read_from_start=args.from_start,
    )
    controller.start()

    if args.duration > 0:
        QTimer.singleShot(int(args.duration * 1000), controller.shutdown)

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
