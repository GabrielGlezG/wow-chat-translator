"""Overlay flotante en PySide6 con Pestañas, Scroll vertical y Minimizar/Maximizar dentro del juego."""

from __future__ import annotations

from collections import deque
from datetime import datetime
import html
from pathlib import Path
from typing import Any

from PySide6.QtCore import QCoreApplication, QEvent, QObject, QPoint, QRect, Qt, QTimer, Signal, Slot
from PySide6.QtGui import QColor, QFont, QGuiApplication, QMouseEvent, QPainter, QPen
import sys
import threading
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizeGrip,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
import pyperclip

from src.config import DEFAULT_CONFIG_PATH, load_config, save_config
from src.watcher import ChatMessage
from src.window_tracker import refocus_wow_async
from src.autostart import is_windows_autostart_enabled, set_windows_autostart

CHANNEL_COLORS: dict[str, str] = {
    "grupo": "#A8C8FF",
    "party": "#A8C8FF",
    "líder del grupo": "#76B4FF",
    "party leader": "#76B4FF",
    "banda": "#FF7F00",
    "raid": "#FF7F00",
    "líder de banda": "#FF4800",
    "raid leader": "#FF4800",
    "alerta de banda": "#FF3300",
    "raid warning": "#FF3300",
    "hermandad": "#40FF40",
    "guild": "#40FF40",
    "oficial": "#40C040",
    "officer": "#40C040",
    "campo de batalla": "#FF7F00",
    "battleground": "#FF7F00",
    "susurro": "#FF80FF",
    "whisper": "#FF80FF",
    "decir": "#FFFFFF",
    "say": "#FFFFFF",
    "gritar": "#FF4040",
    "yell": "#FF4040",
    "tú -> en": "#00E5FF",
}

CHANNEL_FILTER_GROUPS: dict[str, tuple[str, ...]] = {
    "Grupo": ("grupo", "party", "líder del grupo", "party leader"),
    "Susurro": ("susurro", "whisper"),
    "Hermandad": ("hermandad", "guild", "oficial", "officer"),
    "Banda": (
        "banda",
        "raid",
        "líder de banda",
        "raid leader",
        "alerta de banda",
        "raid warning",
        "campo de batalla",
        "battleground",
    ),
    "Decir": ("decir", "say", "gritar", "yell"),
}

QUICK_REPLIES: list[tuple[str, str]] = [
    ("OOM (Sin mana)", "wait a sec, oom"),
    ("RDY (Listo)", "rdy"),
    ("TY GG (Gracias)", "ty for group, gg!"),
    ("LAG (Lagazo)", "sorry, huge lag spike mb"),
    ("NEED (Codicia)", "anyone need this or greed?"),
    ("BRB (Ya vuelvo)", "brb 1 min"),
]

OPACITY_STEPS = (0, 35, 75, 130, 200)

CHIP_BTN_STYLE = (
    "QPushButton {"
    "  background-color: rgba(26, 38, 56, 220);"
    "  color: #76B4FF;"
    "  border: 1px solid #3F608F;"
    "  border-radius: 4px;"
    "  padding: 2px 5px;"
    "  font-size: 8pt;"
    "  font-weight: bold;"
    "}"
    "QPushButton:hover {"
    "  background-color: rgba(50, 75, 110, 245);"
    "  border-color: #00E5FF;"
    "  color: #FFFFFF;"
    "}"
)

WOW_TAB_BTN_STYLE = (
    "QPushButton {"
    "  background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(28, 22, 14, 220), stop:1 rgba(12, 9, 6, 240));"
    "  color: #C79C6E;"
    "  border: 1px solid #4A3A22;"
    "  border-bottom: none;"
    "  border-top-left-radius: 4px;"
    "  border-top-right-radius: 4px;"
    "  padding: 2px 10px;"
    "  font-family: 'Friz Quadrata TT', 'Trebuchet MS', 'Segoe UI', Arial, sans-serif;"
    "  font-size: 8.5pt;"
    "  font-weight: bold;"
    "}"
    "QPushButton:hover {"
    "  color: #FFD100;"
    "  border-color: #8C6F34;"
    "  background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(44, 34, 18, 240), stop:1 rgba(20, 15, 8, 250));"
    "}"
    "QPushButton:checked {"
    "  color: #FFFFFF;"
    "  border: 1px solid #C79C6E;"
    "  border-bottom: 2px solid transparent;"
    "  background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(50, 38, 18, 250), stop:1 rgba(22, 16, 8, 255));"
    "}"
)

WOW_TAB_BTN_WHISPER_STYLE = (
    "QPushButton {"
    "  background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(48, 14, 48, 240), stop:1 rgba(24, 8, 24, 250));"
    "  color: #FF80FF;"
    "  border: 1px solid #FF80FF;"
    "  border-bottom: none;"
    "  border-top-left-radius: 4px;"
    "  border-top-right-radius: 4px;"
    "  padding: 2px 10px;"
    "  font-family: 'Friz Quadrata TT', 'Trebuchet MS', 'Segoe UI', Arial, sans-serif;"
    "  font-size: 8.5pt;"
    "  font-weight: bold;"
    "}"
)

WOW_TAB_ACTION_STYLE = (
    "QPushButton {"
    "  background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2A241C, stop:0.5 #1C1813, stop:1 #12100D);"
    "  color: #C79C6E;"
    "  border: 1px solid #4A3A22;"
    "  border-radius: 3px;"
    "  padding: 1px 6px;"
    "  font-family: 'Friz Quadrata TT', 'Trebuchet MS', 'Segoe UI', Arial, sans-serif;"
    "  font-size: 8pt;"
    "  font-weight: bold;"
    "}"
    "QPushButton:hover {"
    "  color: #FFFFFF;"
    "  border-color: #C79C6E;"
    "  background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3D3428, stop:0.5 #28221B, stop:1 #1C1813);"
    "}"
    "QPushButton:checked {"
    "  background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4E3E22, stop:1 #221A0E);"
    "  color: #FFD100;"
    "  border-color: #FFD100;"
    "}"
)

TOP_BTN_STYLE = (
    "QPushButton {"
    "  background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2A241C, stop:0.5 #1C1813, stop:1 #12100D);"
    "  color: #D1C399;"
    "  border: 1px solid #5A472A;"
    "  border-radius: 3px;"
    "  padding: 2px 8px;"
    "  font-family: 'Friz Quadrata TT', 'Trebuchet MS', 'Segoe UI', Arial, sans-serif;"
    "  font-size: 8.5pt;"
    "  font-weight: bold;"
    "}"
    "QPushButton:hover {"
    "  background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3D3428, stop:0.5 #28221B, stop:1 #1C1813);"
    "  border-color: #C79C6E;"
    "  color: #FFFFFF;"
    "}"
    "QPushButton:checked {"
    "  background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4E3E22, stop:1 #221A0E);"
    "  color: #FFD100;"
    "  border-color: #FFD100;"
    "}"
)

TAB_BTN_STYLE = (
    "QPushButton {"
    "  background-color: rgba(20, 24, 34, 200);"
    "  color: #B0BAC9;"
    "  border: 1px solid #394457;"
    "  border-bottom: 2px solid transparent;"
    "  border-radius: 4px;"
    "  padding: 3px 8px;"
    "  font-size: 8.5pt;"
    "  font-weight: bold;"
    "}"
    "QPushButton:hover {"
    "  color: #FFFFFF;"
    "  background-color: rgba(38, 46, 64, 230);"
    "}"
    "QPushButton:checked {"
    "  background-color: rgba(45, 38, 15, 235);"
    "  color: #FFD100;"
    "  border: 1px solid #C9A000;"
    "  border-bottom: 2px solid #FFD100;"
    "}"
)

SCROLL_AREA_STYLE = (
    "QScrollArea { background: transparent; border: none; }"
    "QScrollBar:vertical {"
    "  background: rgba(18, 22, 30, 140);"
    "  width: 8px;"
    "  margin: 0px;"
    "  border-radius: 4px;"
    "}"
    "QScrollBar::handle:vertical {"
    "  background: rgba(255, 209, 0, 160);"
    "  min-height: 22px;"
    "  border-radius: 4px;"
    "}"
    "QScrollBar::handle:vertical:hover {"
    "  background: rgba(255, 209, 0, 230);"
    "}"
    "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {"
    "  height: 0px;"
    "}"
)


def get_channel_color(channel: str) -> str:
    """Devuelve el color hexadecimal estilo WoW para un canal dado."""
    lower = channel.strip().lower()
    for key, color in CHANNEL_COLORS.items():
        if lower == key or lower.startswith(key):
            return color
    return "#FFD100"


def map_channel_to_filter_group(channel: str) -> str | None:
    """Mapea el nombre de un canal a su grupo de filtro principal (Grupo, Susurro, etc.)."""
    lower = channel.strip().lower()
    if lower == "tú -> en":
        return None
    for group_name, prefixes in CHANNEL_FILTER_GROUPS.items():
        for prefix in prefixes:
            if lower == prefix or lower.startswith(prefix):
                return group_name
    return None


class ChatOverlay(QWidget):
    """
    Overlay interactivo para World of Warcraft con:
    - Barra superior con botones directos (Leer, ES->EN, Limpiar, Pausar y Minimizar/Maximizar [X]).
    - 3 Pestañas: `Chat` (con Scroll vertical), `Traducir` y `Ajustes`.
    - Modo Minimizado en forma de barra compacta flotante dentro del juego con contador de mensajes nuevos.
    """

    clear_requested = Signal()
    scan_requested = Signal()
    translate_box_requested = Signal()
    pause_toggled = Signal()
    manual_es_en_requested = Signal(str)
    alt_t_toggled = Signal(bool)
    test_message_requested = Signal()
    player_name_changed = Signal(str)
    wow_path_changed = Signal(str)

    def __init__(
        self,
        config: dict[str, Any] | None = None,
        config_path: Path | str = DEFAULT_CONFIG_PATH,
    ) -> None:
        super().__init__()
        self.config_path = Path(config_path)
        self.config = config or load_config(self.config_path)
        overlay_cfg = self.config.get("overlay", {})

        self.max_messages: int = max(int(overlay_cfg.get("max_messages", 60)), 60)
        self.font_family: str = str(overlay_cfg.get("font_family", "Segoe UI"))
        self.font_size: int = int(overlay_cfg.get("font_size", 11))
        self.bg_opacity: int = int(overlay_cfg.get("background_opacity", 150))
        self.show_original_en: bool = bool(
            overlay_cfg.get("show_original_en", False)
        )
        self.auto_fade_enabled: bool = bool(overlay_cfg.get("auto_fade", True))
        self.auto_fade_seconds: int = int(
            overlay_cfg.get("auto_fade_seconds", 35)
        )
        self.alt_t_enabled: bool = bool(
            overlay_cfg.get("enable_alt_t_hotkey", True)
        )
        self.auto_hide_on_minimize: bool = bool(
            overlay_cfg.get("auto_hide_on_minimize", True)
        )
        self.only_visible_with_wow: bool = bool(
            overlay_cfg.get("only_visible_with_wow", True)
        )
        self.autostart_enabled: bool = is_windows_autostart_enabled()

        default_filters = {k: True for k in CHANNEL_FILTER_GROUPS}
        saved_filters = overlay_cfg.get("enabled_channel_filters", {})
        if isinstance(saved_filters, dict):
            for k in default_filters:
                if k in saved_filters:
                    default_filters[k] = bool(saved_filters[k])
        self.channel_filters: dict[str, bool] = default_filters

        self._messages: deque[ChatMessage] = deque(maxlen=self.max_messages)
        self._move_mode: bool = False
        self._is_minimized_in_game: bool = bool(overlay_cfg.get("start_folded", False))
        self._unread_while_minimized: int = 0
        self._expanded_rect: QRect | None = None
        self._is_faded: bool = False
        self._drag_offset: QPoint | None = None
        self._is_dragging_right: bool = False
        self._is_dragging_left: bool = False
        self._whisper_glow: bool = False

        # Coordenadas desacopladas: posición de la pestaña camuflada vs posición del chat desplegado
        self._tab_x: int = int(overlay_cfg.get("tab_x", overlay_cfg.get("x", 265)))
        self._tab_y: int = int(overlay_cfg.get("tab_y", overlay_cfg.get("y", 835)))
        self._chat_x: int = int(overlay_cfg.get("chat_x", 36))
        self._chat_y: int = int(overlay_cfg.get("chat_y", 835))
        self._chat_w: int = max(int(overlay_cfg.get("chat_w", overlay_cfg.get("width", 450))), 360)
        self._chat_h: int = max(int(overlay_cfg.get("chat_h", overlay_cfg.get("height", 215))), 180)
        self._filter_buttons: dict[str, QPushButton] = {}
        self._tab_buttons: list[QPushButton] = []
        self._text_input_active: bool = False

        self._init_ui(overlay_cfg)

    @property
    def move_mode(self) -> bool:
        """Compatibilidad con tests y alternancia de modo bloqueo."""
        return self._move_mode

    @property
    def is_minimized_in_game(self) -> bool:
        """Indica si el overlay está minimizado como barra compacta dentro del juego."""
        return self._is_minimized_in_game

    @property
    def messages(self) -> list[ChatMessage]:
        """Devuelve la lista actual de mensajes almacenados en el overlay."""
        return list(self._messages)

    def is_channel_group_enabled(self, channel: str) -> bool:
        """Verifica si el canal pertenece a un filtro activo."""
        group = map_channel_to_filter_group(channel)
        if group is None:
            return True
        return self.channel_filters.get(group, True)

    def _init_ui(self, overlay_cfg: dict[str, Any]) -> None:
        self.setWindowTitle("WoW Chat Translator Overlay")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

        x = int(overlay_cfg.get("x", 36))
        y = int(overlay_cfg.get("y", 835))
        width = max(int(overlay_cfg.get("width", 450)), 360)
        height = max(int(overlay_cfg.get("height", 215)), 180)
        self.setGeometry(x, y, width, height)
        self._expanded_rect = QRect(x, y, width, height)
        self.setMinimumSize(60, 24)

        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(4, 2, 4, 4)
        self.root_layout.setSpacing(2)

        # =====================================================================
        # 1. PESTAÑA DOCKABLE ESTILO WOW (Header unificado idéntico a WoW Chat Tab)
        # =====================================================================
        self.top_tab_bar = QHBoxLayout()
        self.top_tab_bar.setContentsMargins(0, 0, 0, 0)
        self.top_tab_bar.setSpacing(3)

        # Pestañas estilo Blizzard WoW Forever
        self.tab_btn_chat = QPushButton("Traducción")
        self.tab_btn_chat.setFixedHeight(24)
        self.tab_btn_chat.setToolTip("Pestaña de chat: Clic para desplegar / plegar")
        self.tab_btn_chat.setStyleSheet(WOW_TAB_BTN_STYLE)

        self.tab_btn_quick = QPushButton("Traducir")
        self.tab_btn_quick.setFixedHeight(24)
        self.tab_btn_quick.setToolTip("Traductor manual ES->EN y copiado")
        self.tab_btn_quick.setStyleSheet(WOW_TAB_BTN_STYLE)

        self.tab_btn_settings = QPushButton("Ajustes")
        self.tab_btn_settings.setFixedHeight(24)
        self.tab_btn_settings.setToolTip("Filtros de canal y acoplamiento")
        self.tab_btn_settings.setStyleSheet(WOW_TAB_BTN_STYLE)

        self._tab_buttons = [
            self.tab_btn_chat,
            self.tab_btn_quick,
            self.tab_btn_settings,
        ]
        for idx, tbtn in enumerate(self._tab_buttons):
            tbtn.setCheckable(True)
            tbtn.setChecked(idx == 0)
            tbtn.clicked.connect(lambda _=False, i=idx: self._on_tab_clicked(i))
            self.top_tab_bar.addWidget(tbtn)

        self.top_tab_bar.addStretch(1)

        # Acciones discretas estilo WoW sin emojis
        self.btn_scan = QPushButton("Leer")
        self.btn_scan.setFixedHeight(22)
        self.btn_scan.setToolTip("Leer chat visible")
        self.btn_scan.setStyleSheet(WOW_TAB_ACTION_STYLE)
        self.btn_scan.clicked.connect(self.scan_requested.emit)
        self.top_tab_bar.addWidget(self.btn_scan)

        self.btn_clear = QPushButton("Limpiar")
        self.btn_clear.setFixedHeight(22)
        self.btn_clear.setToolTip("Limpiar historial de mensajes")
        self.btn_clear.setStyleSheet(WOW_TAB_ACTION_STYLE)
        self.btn_clear.clicked.connect(self.clear_messages)
        self.top_tab_bar.addWidget(self.btn_clear)

        self.btn_minimize = QPushButton("[X]")
        self.btn_minimize.setFixedHeight(22)
        self.btn_minimize.setToolTip("Plegar a pestaña")
        self.btn_minimize.setStyleSheet(WOW_TAB_ACTION_STYLE)
        self.btn_minimize.clicked.connect(self.toggle_minimize_in_game)
        self.top_tab_bar.addWidget(self.btn_minimize)

        self.root_layout.addLayout(self.top_tab_bar)

        # Referencia de compatibilidad
        self.title_label = self.tab_btn_chat

        # =====================================================================
        # 2. CONTENEDOR DE CHAT Y PÁGINAS (Se pliega/despliega bajo la pestaña)
        # =====================================================================
        self.body_container = QWidget(self)
        body_layout = QVBoxLayout(self.body_container)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(4)

        # Páginas de las Pestañas
        self.pages = QStackedWidget(self.body_container)
        self.pages.addWidget(self._build_chat_tab())
        self.pages.addWidget(self._build_quick_tab())
        self.pages.addWidget(self._build_settings_tab())
        body_layout.addWidget(self.pages, stretch=1)

        # Barra inferior de estado + grip para redimensionar
        bottom_bar = QHBoxLayout()
        bottom_bar.setContentsMargins(0, 0, 0, 0)
        self.status_label = QLabel("")
        self.status_label.setStyleSheet(
            "color: #CCCCCC; font-size: 8.5pt; background: transparent;"
        )
        bottom_bar.addWidget(self.status_label, stretch=1)

        self.size_grip = QSizeGrip(self.body_container)
        self.size_grip.setFixedSize(14, 14)
        bottom_bar.addWidget(
            self.size_grip,
            0,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
        )
        body_layout.addLayout(bottom_bar)

        self.root_layout.addWidget(self.body_container, stretch=1)

        self._status_timer = QTimer(self)
        self._status_timer.setSingleShot(True)
        self._status_timer.timeout.connect(lambda: self.status_label.setText(""))

        self._fade_timer = QTimer(self)
        self._fade_timer.setSingleShot(True)
        self._fade_timer.timeout.connect(self._enter_faded_state)
        self._restart_fade_timer()

        self._apply_window_flags()
        self._render_messages()

        # Configuración anti-robo de foco: ningún botón roba foco de teclado a WoW
        for btn in self.findChildren(QPushButton):
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.scroll_area.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.quick_input.installEventFilter(self)
        self.edit_player_name.installEventFilter(self)

    def _build_chat_tab(self) -> QWidget:
        """Pestaña 1: Historial de chat traducido con Scroll vertical y botones de desplazamiento."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)

        self.scroll_area = QScrollArea(page)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.scroll_area.setStyleSheet(SCROLL_AREA_STYLE)

        self.chat_label = QLabel()
        self.chat_label.setWordWrap(True)
        self.chat_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )
        self.chat_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self._apply_chat_font()
        self.chat_label.setStyleSheet(
            "color: #FFFFFF; background: transparent; padding: 2px;"
        )
        shadow_fx = QGraphicsDropShadowEffect(self.chat_label)
        shadow_fx.setBlurRadius(2.5)
        shadow_fx.setColor(QColor(0, 0, 0, 245))
        shadow_fx.setOffset(1.2, 1.2)
        self.chat_label.setGraphicsEffect(shadow_fx)
        self.scroll_area.setWidget(self.chat_label)
        layout.addWidget(self.scroll_area, stretch=1)

        # Mini barra inferior del chat estilo Blizzard WoW Forever
        chat_tools = QHBoxLayout()
        chat_tools.setContentsMargins(2, 1, 2, 1)
        chat_tools.setSpacing(4)

        btn_up = QPushButton("▲")
        btn_up.setFixedWidth(24)
        btn_up.setFixedHeight(22)
        btn_up.setStyleSheet(TOP_BTN_STYLE)
        btn_up.setToolTip("Subir historial")
        btn_up.clicked.connect(lambda: self.scroll_chat_by(-90))
        chat_tools.addWidget(btn_up)

        btn_down = QPushButton("▼")
        btn_down.setFixedWidth(24)
        btn_down.setFixedHeight(22)
        btn_down.setStyleSheet(TOP_BTN_STYLE)
        btn_down.setToolTip("Bajar al final")
        btn_down.clicked.connect(self.scroll_to_bottom)
        chat_tools.addWidget(btn_down)

        btn_copy = QPushButton("Copiar Último")
        btn_copy.setFixedHeight(22)
        btn_copy.setStyleSheet(TOP_BTN_STYLE)
        btn_copy.setToolTip("Copiar último mensaje traducido al portapapeles")
        btn_copy.clicked.connect(self.copy_last_message)
        chat_tools.addWidget(btn_copy)

        chat_tools.addStretch(1)

        btn_test = QPushButton("Prueba")
        btn_test.setFixedHeight(22)
        btn_test.setStyleSheet(TOP_BTN_STYLE)
        btn_test.setToolTip("Inyectar mensaje de prueba en inglés")
        btn_test.clicked.connect(self.test_message_requested.emit)
        chat_tools.addWidget(btn_test)
        layout.addLayout(chat_tools)
        return page

    def _build_quick_tab(self) -> QWidget:
        """Pestaña 2: Traducir ES->EN y Copiar al portapapeles para WoW."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(8)

        lbl = QLabel("Escribe en español para traducir a inglés gamer y copiarlo (Ctrl+V en WoW):")
        lbl.setStyleSheet("color: #C8B383; font-size: 8.5pt; font-weight: bold;")
        layout.addWidget(lbl)

        # Caja de entrada en español estilo EditBox de WoW
        input_row = QHBoxLayout()
        input_row.setSpacing(5)
        self.quick_input = QLineEdit()
        self.quick_input.setPlaceholderText("Ej: no jalen todavía, esperen un segundo...")
        self.quick_input.setStyleSheet(
            "QLineEdit {"
            "  background-color: rgba(0, 0, 0, 200);"
            "  color: #FFFFFF;"
            "  border: 1px solid #5A472A;"
            "  border-radius: 3px;"
            "  padding: 4px 8px;"
            "  font-size: 9pt;"
            "  font-family: 'Friz Quadrata TT', 'Segoe UI', Arial, sans-serif;"
            "}"
            "QLineEdit:focus {"
            "  border: 1px solid #FFD100;"
            "}"
        )
        self.quick_input.returnPressed.connect(self._on_manual_es_en_submit)
        input_row.addWidget(self.quick_input, stretch=1)

        btn_send_es = QPushButton("Traducir y Copiar")
        btn_send_es.setFixedHeight(26)
        btn_send_es.setStyleSheet(WOW_TAB_BTN_STYLE)
        btn_send_es.setToolTip("Traduce al inglés y lo copia al portapapeles para pegar en WoW con Ctrl+V")
        btn_send_es.clicked.connect(self._on_manual_es_en_submit)
        input_row.addWidget(btn_send_es)
        layout.addLayout(input_row)

        btn_copy_last = QPushButton("Copiar Último Mensaje")
        btn_copy_last.setFixedHeight(26)
        btn_copy_last.setStyleSheet(TOP_BTN_STYLE)
        btn_copy_last.setToolTip("Copia al portapapeles el último mensaje recibido")
        btn_copy_last.clicked.connect(self.copy_last_message)
        layout.addWidget(btn_copy_last)

        layout.addStretch(1)
        return page

    def _build_settings_tab(self) -> QWidget:
        """Pestaña 3: Filtros de canales y ajustes visuales."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 2, 0, 0)
        layout.setSpacing(5)

        lbl_c = QLabel("Canales activos (solo traduce jugadores reales, ignora NPCs):")
        lbl_c.setStyleSheet("color: #BBBBBB; font-size: 8.5pt; font-weight: bold;")
        layout.addWidget(lbl_c)

        chan_row = QHBoxLayout()
        chan_row.setSpacing(4)
        for group_name in CHANNEL_FILTER_GROUPS:
            btn = QPushButton(group_name)
            btn.setCheckable(True)
            btn.setChecked(self.channel_filters.get(group_name, True))
            btn.setStyleSheet(TOP_BTN_STYLE)
            btn.clicked.connect(
                lambda checked, g=group_name: self._on_channel_filter_toggled(
                    g, checked
                )
            )
            self._filter_buttons[group_name] = btn
            chan_row.addWidget(btn)
        layout.addLayout(chan_row)

        lbl_v = QLabel("Apariencia y Comportamiento:")
        lbl_v.setStyleSheet("color: #BBBBBB; font-size: 8.5pt; font-weight: bold;")
        layout.addWidget(lbl_v)

        vis_row = QHBoxLayout()
        vis_row.setSpacing(4)

        self.btn_bilingual = QPushButton("Bilingüe (EN+ES)")
        self.btn_bilingual.setCheckable(True)
        self.btn_bilingual.setChecked(self.show_original_en)
        self.btn_bilingual.setStyleSheet(TOP_BTN_STYLE)
        self.btn_bilingual.clicked.connect(self.toggle_bilingual_mode)
        vis_row.addWidget(self.btn_bilingual)

        btn_font_m = QPushButton("A-")
        btn_font_m.setStyleSheet(TOP_BTN_STYLE)
        btn_font_m.clicked.connect(lambda: self.adjust_font_size(-1))
        vis_row.addWidget(btn_font_m)

        btn_font_p = QPushButton("A+")
        btn_font_p.setStyleSheet(TOP_BTN_STYLE)
        btn_font_p.clicked.connect(lambda: self.adjust_font_size(1))
        vis_row.addWidget(btn_font_p)

        btn_op = QPushButton("Fondo")
        btn_op.setStyleSheet(TOP_BTN_STYLE)
        btn_op.clicked.connect(self.cycle_background_opacity)
        vis_row.addWidget(btn_op)

        layout.addLayout(vis_row)

        opt_row2 = QHBoxLayout()
        opt_row2.setSpacing(4)

        self.btn_autofade = QPushButton("Auto-Atenuar (35s)")
        self.btn_autofade.setCheckable(True)
        self.btn_autofade.setChecked(self.auto_fade_enabled)
        self.btn_autofade.setStyleSheet(TOP_BTN_STYLE)
        self.btn_autofade.clicked.connect(self.toggle_auto_fade)
        opt_row2.addWidget(self.btn_autofade)

        self.btn_alt_t = QPushButton(
            f"Atajo Alt+T: {'ON' if self.alt_t_enabled else 'OFF'}"
        )
        self.btn_alt_t.setCheckable(True)
        self.btn_alt_t.setChecked(self.alt_t_enabled)
        self.btn_alt_t.setToolTip(
            "Activa o desactiva el atajo Alt+T por si prefieres usar solo los botones del Overlay"
        )
        self.btn_alt_t.setStyleSheet(TOP_BTN_STYLE)
        self.btn_alt_t.clicked.connect(self._on_toggle_alt_t)
        opt_row2.addWidget(self.btn_alt_t)

        opt_row2.addStretch(1)
        layout.addLayout(opt_row2)

        lbl_game = QLabel("Configuración de WoW (Cero Configuración):")
        lbl_game.setStyleSheet("color: #BBBBBB; font-size: 8.5pt; font-weight: bold;")
        layout.addWidget(lbl_game)

        # Fila de Personaje
        player_row = QHBoxLayout()
        player_row.setSpacing(4)
        lbl_p = QLabel("Personaje:")
        lbl_p.setStyleSheet("color: #FFD100; font-size: 8.5pt;")
        self.edit_player_name = QLineEdit()
        self.edit_player_name.setPlaceholderText("Nombre de tu personaje (ej. Aptinstall)")
        self.edit_player_name.setText(str(self.config.get("player_name", "")))
        self.edit_player_name.setStyleSheet(
            "background-color: rgba(18, 24, 38, 220); color: #FFFFFF; "
            "border: 1px solid #4F5D75; border-radius: 4px; padding: 2px 6px; font-size: 8.5pt;"
        )
        self.edit_player_name.returnPressed.connect(self._on_save_player_name)
        btn_save_p = QPushButton("Guardar")
        btn_save_p.setStyleSheet(TOP_BTN_STYLE)
        btn_save_p.clicked.connect(self._on_save_player_name)
        player_row.addWidget(lbl_p)
        player_row.addWidget(self.edit_player_name, stretch=1)
        player_row.addWidget(btn_save_p)
        layout.addLayout(player_row)

        # Fila de Carpeta de WoW
        folder_row = QHBoxLayout()
        folder_row.setSpacing(4)
        lbl_f = QLabel("Carpeta WoW:")
        lbl_f.setStyleSheet("color: #BBBBBB; font-size: 8.5pt;")
        self.lbl_path_display = QLabel()
        curr_p = Path(self.config.get("wow_chat_log_path", ""))
        try:
            folder_name = curr_p.parent.parent.name if curr_p.parent.parent.name else curr_p.parent.name
        except Exception:
            folder_name = "Detectada"
        self.lbl_path_display.setText(f"{folder_name or 'Detectada'} (Logs/WoWChatLog.txt)")
        self.lbl_path_display.setStyleSheet("color: #88B04B; font-size: 8pt;")
        self.lbl_path_display.setToolTip(str(curr_p))
        btn_browse = QPushButton("Cambiar...")
        btn_browse.setStyleSheet(TOP_BTN_STYLE)
        btn_browse.clicked.connect(self._on_browse_wow_folder)
        folder_row.addWidget(lbl_f)
        folder_row.addWidget(self.lbl_path_display, stretch=1)
        folder_row.addWidget(btn_browse)
        layout.addLayout(folder_row)

        lbl_anchor = QLabel("Anclaje a WoW (Ocultación Inteligente):")
        lbl_anchor.setStyleSheet("color: #BBBBBB; font-size: 8.5pt; font-weight: bold;")
        layout.addWidget(lbl_anchor)

        anchor_row = QHBoxLayout()
        anchor_row.setSpacing(4)
        self.btn_auto_hide = QPushButton(
            f"Ocultar al minimizar: {'ON' if self.auto_hide_on_minimize else 'OFF'}"
        )
        self.btn_auto_hide.setCheckable(True)
        self.btn_auto_hide.setChecked(self.auto_hide_on_minimize)
        self.btn_auto_hide.setToolTip(
            "Oculta el overlay cuando WoW se minimiza a la barra de tareas y lo restaura al volver"
        )
        self.btn_auto_hide.setStyleSheet(TOP_BTN_STYLE)
        self.btn_auto_hide.clicked.connect(self._on_toggle_auto_hide)
        anchor_row.addWidget(self.btn_auto_hide)

        self.btn_only_wow = QPushButton(
            f"Solo con WoW activo: {'ON' if self.only_visible_with_wow else 'OFF'}"
        )
        self.btn_only_wow.setCheckable(True)
        self.btn_only_wow.setChecked(self.only_visible_with_wow)
        self.btn_only_wow.setToolTip(
            "Mantiene el overlay estrictamente dentro de WoW (se oculta al cambiar a Chrome/escritorio)"
        )
        self.btn_only_wow.setStyleSheet(TOP_BTN_STYLE)
        self.btn_only_wow.clicked.connect(self._on_toggle_only_wow)
        anchor_row.addWidget(self.btn_only_wow)

        self.btn_autostart = QPushButton(
            f"Iniciar con Windows: {'ON' if self.autostart_enabled else 'OFF'}"
        )
        self.btn_autostart.setCheckable(True)
        self.btn_autostart.setChecked(self.autostart_enabled)
        self.btn_autostart.setToolTip(
            "Inicia el traductor silenciosamente en segundo plano al encender la PC. Aparece automáticamente cuando abres WoW."
        )
        self.btn_autostart.setStyleSheet(TOP_BTN_STYLE)
        self.btn_autostart.clicked.connect(self._on_toggle_autostart)
        anchor_row.addWidget(self.btn_autostart)

        anchor_row.addStretch(1)
        layout.addLayout(anchor_row)

        snap_row = QHBoxLayout()
        snap_row.setSpacing(4)
        btn_snap = QPushButton("Auto-Acoplar")
        btn_snap.setStyleSheet(TOP_BTN_STYLE)
        btn_snap.setToolTip("Detecta la posición de WoW y acopla el overlay automáticamente sobre el chat estándar del juego")
        btn_snap.clicked.connect(self.auto_snap_to_wow)
        snap_row.addWidget(btn_snap)

        btn_free = QPushButton("Posición Libre")
        btn_free.setStyleSheet(TOP_BTN_STYLE)
        btn_free.setToolTip("Mueve el overlay al área libre media-izquierda para que no tape tus barras o habilidades")
        btn_free.clicked.connect(self.reset_to_free_position)
        snap_row.addWidget(btn_free)

        layout.addLayout(snap_row)

        layout.addStretch(1)
        return page

    @Slot(bool)
    def _on_toggle_auto_hide(self, checked: bool) -> None:
        self.auto_hide_on_minimize = checked
        self.btn_auto_hide.setText(f"Ocultar al minimizar: {'ON' if checked else 'OFF'}")
        self.save_geometry_to_config()
        self.show_status_notice(
            f"Ocultar al minimizar {'activado' if checked else 'desactivado'}"
        )

    @Slot(bool)
    def _on_toggle_only_wow(self, checked: bool) -> None:
        self.only_visible_with_wow = checked
        self.btn_only_wow.setText(f"Solo con WoW activo: {'ON' if checked else 'OFF'}")
        self.save_geometry_to_config()
        self.show_status_notice(
            f"Anclaje exclusivo a WoW {'activado' if checked else 'desactivado'}"
        )

    @Slot(bool)
    def _on_toggle_autostart(self, checked: bool) -> None:
        self.autostart_enabled = checked
        success = set_windows_autostart(checked)
        self.btn_autostart.setText(f"Iniciar con Windows: {'ON' if checked else 'OFF'}")
        if success:
            state_txt = "activado (se iniciará en segundo plano con tu PC)" if checked else "desactivado"
            self.show_status_notice(f"Inicio automático {state_txt}")
        else:
            self.show_status_notice("No se pudo modificar el registro de inicio de Windows.")

    def on_wow_window_moved(self, dx: int, dy: int, wow_rect: tuple[int, int, int, int]) -> None:
        """Desplaza el overlay en sincronía cuando la ventana de WoW se mueve en pantalla."""
        if dx == 0 and dy == 0:
            return
        self._tab_x += dx
        self._tab_y += dy
        self._chat_x += dx
        self._chat_y += dy
        if self._is_minimized_in_game:
            self.move(self._tab_x, self._tab_y)
        else:
            self.move(self._chat_x, self._chat_y)
            self._expanded_rect = self.geometry()

    @Slot()
    def _on_save_player_name(self) -> None:
        name = self.edit_player_name.text().strip()
        self.set_allow_text_input(False)
        self.config["player_name"] = name
        try:
            save_config(self.config, self.config_path)
        except Exception:
            pass
        self.player_name_changed.emit(name)
        self.show_status_notice(f"Personaje guardado: {name or 'Todos'}")
        refocus_wow_async()

    @Slot()
    def _on_browse_wow_folder(self) -> None:
        curr_p = Path(self.config.get("wow_chat_log_path", ""))
        init_dir = str(curr_p.parent.parent) if curr_p.parent.parent.exists() else "C:/"
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "Seleccionar carpeta de instalación de World of Warcraft",
            init_dir,
        )
        if dir_path:
            chosen = Path(dir_path)
            log_file = chosen / "Logs" / "WoWChatLog.txt"
            log_file.parent.mkdir(parents=True, exist_ok=True)
            self.config["wow_chat_log_path"] = str(log_file).replace("\\", "/")
            try:
                save_config(self.config, self.config_path)
            except Exception:
                pass
            self.wow_path_changed.emit(str(log_file))
            self.lbl_path_display.setText(f"{chosen.name} (Logs/WoWChatLog.txt)")
            self.lbl_path_display.setToolTip(str(log_file))
            self.show_status_notice(f"Carpeta de WoW: {chosen.name}")

    def _on_tab_clicked(self, index: int) -> None:
        """Comportamiento idéntico a pestaña de WoW: clic en activa pliega/despliega."""
        if self._is_minimized_in_game:
            self.toggle_minimize_in_game()
            self.switch_tab(index)
            return

        if self.pages.currentIndex() == index and index == 0:
            # Hacer clic en la pestaña activa pliega el chat para ver el chat nativo de WoW
            self.toggle_minimize_in_game()
        else:
            self.switch_tab(index)

    def switch_tab(self, index: int) -> None:
        """Cambia entre las pestañas del Overlay."""
        if index == 0:
            self.set_allow_text_input(False)
        self.pages.setCurrentIndex(index)
        for idx, btn in enumerate(self._tab_buttons):
            btn.setChecked(idx == index)

    def scroll_chat_by(self, delta_px: int) -> None:
        """Desplaza verticalmente el área de mensajes."""
        vbar = self.scroll_area.verticalScrollBar()
        vbar.setValue(vbar.value() + delta_px)

    @Slot()
    def scroll_to_bottom(self) -> None:
        """Desplaza el área de mensajes hasta el mensaje más reciente."""
        vbar = self.scroll_area.verticalScrollBar()
        vbar.setValue(vbar.maximum())

    @Slot()
    def toggle_minimize_in_game(self) -> None:
        """Alterna entre la pestaña camuflada nativa de WoW y el chat desplegado."""
        if not self._is_minimized_in_game:
            # 1. Guardar posición y tamaño actuales del chat desplegado
            self._chat_x = self.x()
            self._chat_y = self.y()
            self._chat_w = self.width()
            self._chat_h = self.height()
            self._expanded_rect = QRect(self._chat_x, self._chat_y, self._chat_w, self._chat_h)

            self._is_minimized_in_game = True

            # 2. Ocultar todos los botones secundarios y el cuerpo del chat
            self.body_container.setVisible(False)
            if hasattr(self, "btn_drag"):
                self.btn_drag.setVisible(False)
            self.tab_btn_quick.setVisible(False)
            self.tab_btn_settings.setVisible(False)
            self.btn_scan.setVisible(False)
            self.btn_clear.setVisible(False)
            self.btn_minimize.setVisible(False)

            # 3. Eliminar márgenes y acotar dimensiones al tamaño exacto de la pestaña
            self.root_layout.setContentsMargins(0, 0, 0, 0)
            self.setMinimumSize(60, 22)
            self.setMaximumSize(180, 28)

            # 4. Actualizar título y estilo de la pestaña
            self._update_minimized_title()

            # 5. Mover a la posición de estacionamiento de la pestaña
            tab_w = max(self.tab_btn_chat.sizeHint().width() + 14, 98)
            self.move(self._tab_x, self._tab_y)
            self.resize(tab_w, 24)
        else:
            # 1. Guardar la posición donde el usuario dejó la pestaña
            self._tab_x = self.x()
            self._tab_y = self.y()

            self._is_minimized_in_game = False
            self._unread_while_minimized = 0
            self._update_minimized_title()

            # 2. Restaurar restricciones de tamaño y márgenes
            self.setMaximumSize(16777215, 16777215)
            self.setMinimumSize(320, 160)
            self.root_layout.setContentsMargins(4, 2, 4, 4)

            # 3. Mostrar elementos del chat desplegado
            self.body_container.setVisible(True)
            if hasattr(self, "btn_drag"):
                self.btn_drag.setVisible(True)
            self.tab_btn_quick.setVisible(True)
            self.tab_btn_settings.setVisible(True)
            self.btn_scan.setVisible(True)
            self.btn_clear.setVisible(True)
            self.btn_minimize.setVisible(True)
            self.btn_minimize.setText("[X]")

            # 4. Mover a la posición del chat desplegado
            self.move(self._chat_x, self._chat_y)
            self.resize(self._chat_w, self._chat_h)
            QTimer.singleShot(20, self.scroll_to_bottom)

        self.save_geometry_to_config()
        self.update()
        refocus_wow_async()

    def _update_minimized_title(self) -> None:
        if not self._is_minimized_in_game:
            self.tab_btn_chat.setText("Traducción")
            self.tab_btn_chat.setChecked(self.pages.currentIndex() == 0)
        else:
            self.tab_btn_chat.setChecked(False)
            if self._unread_while_minimized > 0:
                self.tab_btn_chat.setText(
                    f"Traducción ({self._unread_while_minimized})"
                )
            else:
                self.tab_btn_chat.setText("Traducción")
            if self.isVisible():
                w = max(self.tab_btn_chat.sizeHint().width() + 14, 98)
                self.resize(w, 24)

    def _on_manual_es_en_submit(self) -> None:
        text = self.quick_input.text().strip()
        if not text:
            return
        self.quick_input.clear()
        self.set_allow_text_input(False)
        self.manual_es_en_requested.emit(text)
        self.switch_tab(0)
        refocus_wow_async()

    def _on_toggle_alt_t(self, checked: bool) -> None:
        self.alt_t_enabled = checked
        self.btn_alt_t.setText(f"⌨️ Atajo Alt+T: {'ON' if checked else 'OFF'}")
        self.save_geometry_to_config()
        self.alt_t_toggled.emit(checked)
        self.show_status_notice(
            f"Atajo Alt+T {'activado' if checked else 'desactivado'}"
        )

    def set_paused_ui(self, paused: bool) -> None:
        """Actualiza el icono del botón de pausa en la barra superior."""
        self.btn_pause.setChecked(paused)
        self.btn_pause.setText("▶️" if paused else "⏸")

    def _apply_chat_font(self) -> None:
        font = QFont(self.font_family, self.font_size)
        font.setBold(True)
        self.chat_label.setFont(font)

    def _restart_fade_timer(self) -> None:
        if self._is_faded:
            self._is_faded = False
            self.update()
        self._fade_timer.stop()
        if self.auto_fade_enabled:
            self._fade_timer.start(self.auto_fade_seconds * 1000)

    @Slot()
    def _enter_faded_state(self) -> None:
        if self.auto_fade_enabled:
            self._is_faded = True
            self.update()

    def _apply_window_flags(self) -> None:
        flags = (
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.show()

        if sys.platform == "win32":
            try:
                import ctypes
                user32 = ctypes.windll.user32
                hwnd = int(self.winId())
                GWL_EXSTYLE = -20
                WS_EX_NOACTIVATE = 0x08000000
                cur = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
                user32.SetWindowLongW(hwnd, GWL_EXSTYLE, cur | WS_EX_NOACTIVATE)
            except Exception:
                pass

    def set_allow_text_input(self, allow: bool) -> None:
        """Permite o bloquea la activación de la ventana para escribir en cajas de texto."""
        self._text_input_active = allow
        if sys.platform != "win32":
            return
        try:
            import ctypes
            user32 = ctypes.windll.user32
            hwnd = int(self.winId())
            GWL_EXSTYLE = -20
            WS_EX_NOACTIVATE = 0x08000000
            cur = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            if allow:
                user32.SetWindowLongW(hwnd, GWL_EXSTYLE, cur & ~WS_EX_NOACTIVATE)
                user32.SetForegroundWindow(hwnd)
                self.activateWindow()
            else:
                user32.SetWindowLongW(hwnd, GWL_EXSTYLE, cur | WS_EX_NOACTIVATE)
        except Exception:
            pass

    def nativeEvent(self, eventType: QByteArray | bytes, message: int) -> tuple[bool, int]:  # noqa: N802
        """
        Intercepta WM_MOUSEACTIVATE para no robar el foco a WoW al hacer clic en pestañas, botones o chat.
        Permite manipular completamente el overlay (cambiar pestañas, plegar/desplegar, scrollear y hacer clics)
        sin cortar el movimiento (WASD) ni interrumpir acciones en curso dentro de World of Warcraft.
        """
        if sys.platform == "win32" and eventType in (b"windows_generic_MSG", "windows_generic_MSG"):
            try:
                import ctypes
                from ctypes import wintypes
                msg = wintypes.MSG.from_address(message.__int__())
                if msg.message == 0x0021:  # WM_MOUSEACTIVATE
                    if not getattr(self, "_text_input_active", False):
                        # MA_NOACTIVATE = 3: Permite interacción y clics sin activar ventana (WoW conserva el foco total)
                        return True, 3
                    else:
                        # MA_ACTIVATE = 1: Permite activación cuando el usuario hace clic para escribir texto
                        return True, 1
            except Exception:
                pass
        return super().nativeEvent(eventType, message)

    @Slot(object)
    def add_message(self, msg: ChatMessage) -> None:
        """Agrega un nuevo mensaje traducido si su canal está activo y hace scroll al final."""
        if not self.is_channel_group_enabled(msg.channel):
            return
        msg_with_ts = msg
        if not msg.timestamp:
            msg_with_ts = ChatMessage(
                timestamp=datetime.now().strftime("%H:%M"),
                channel=msg.channel,
                sender=msg.sender,
                original_text=msg.original_text,
                translated_text=msg.translated_text,
            )
        self._messages.append(msg_with_ts)
        if msg.channel.lower() in ("susurro", "whisper"):
            self._trigger_whisper_alert(msg.sender)
        if self._is_minimized_in_game:
            self._unread_while_minimized += 1
            self._update_minimized_title()
        self._restart_fade_timer()
        self._render_messages()
        QTimer.singleShot(15, self.scroll_to_bottom)

    @Slot(str, str)
    def add_outgoing_translation(self, original_es: str, translated_en: str) -> None:
        """Muestra la traducción saliente (ES -> EN) en el overlay para confirmación visual."""
        msg = ChatMessage(
            timestamp=datetime.now().strftime("%H:%M"),
            channel="Tú -> EN",
            sender="Chat",
            original_text=original_es,
            translated_text=translated_en,
        )
        self._messages.append(msg)
        self._restart_fade_timer()
        self._render_messages()
        QTimer.singleShot(15, self.scroll_to_bottom)

    @Slot()
    def clear_messages(self) -> None:
        """Limpia todos los mensajes actuales del overlay."""
        self._messages.clear()
        self._unread_while_minimized = 0
        self._update_minimized_title()
        self._restart_fade_timer()
        self._render_messages()
        self.show_status_notice("Historial limpio")
        self.clear_requested.emit()

    @Slot()
    def toggle_bilingual_mode(self) -> None:
        """Alterna entre ver solo español o ver traducción + original en inglés."""
        self.show_original_en = not self.show_original_en
        self.btn_bilingual.setChecked(self.show_original_en)
        self.save_geometry_to_config()
        self._render_messages()
        mode_txt = "Bilingüe (EN+ES)" if self.show_original_en else "Solo Español (ES)"
        self.show_status_notice(f"Modo de vista: {mode_txt}")

    def adjust_font_size(self, delta: int) -> None:
        """Ajusta el tamaño de fuente entre 8pt y 18pt en vivo."""
        self.font_size = max(8, min(18, self.font_size + delta))
        self._apply_chat_font()
        self.save_geometry_to_config()
        self._render_messages()
        self.show_status_notice(f"Tamaño de letra: {self.font_size}pt")

    @Slot()
    def cycle_background_opacity(self) -> None:
        """Alterna entre los niveles de opacidad del fondo."""
        current_idx = 0
        for idx, val in enumerate(OPACITY_STEPS):
            if self.bg_opacity <= val:
                current_idx = idx
                break
        next_idx = (current_idx + 1) % len(OPACITY_STEPS)
        self.bg_opacity = OPACITY_STEPS[next_idx]
        self._is_faded = False
        self.save_geometry_to_config()
        self.update()
        if self.bg_opacity == 0:
            self.show_status_notice("Modo Fantasma (Fondo 0%)")
        else:
            pct = int((self.bg_opacity / 255.0) * 100)
            self.show_status_notice(f"Opacidad del fondo: {pct}%")

    @Slot()
    def toggle_auto_fade(self) -> None:
        """Activa o desactiva la atenuación automática por inactividad."""
        self.auto_fade_enabled = not self.auto_fade_enabled
        self.btn_autofade.setChecked(self.auto_fade_enabled)
        self.save_geometry_to_config()
        self._restart_fade_timer()
        state = "ACTIVO (35s)" if self.auto_fade_enabled else "DESACTIVADO"
        self.show_status_notice(f"Auto-Atenuar: {state}")

    def _on_channel_filter_toggled(self, group_name: str, checked: bool) -> None:
        self.channel_filters[group_name] = checked
        self.save_geometry_to_config()
        self._render_messages()
        state = "visible" if checked else "oculto"
        self.show_status_notice(f"Filtro [{group_name}]: {state}")

    def copy_quick_reply(self, phrase: str) -> None:
        """Copia una respuesta rápida en inglés gamer al portapapeles."""
        try:
            pyperclip.copy(phrase)
            self.show_status_notice(
                f'Copiado al portapapeles: "{phrase}"'
            )
        except Exception as exc:
            self.show_status_notice(f"Error copiando respuesta rápida: {exc}")

    @Slot()
    def copy_last_message(self) -> None:
        """Copia el nombre del último jugador y su mensaje al portapapeles."""
        if not self._messages:
            self.show_status_notice("No hay mensajes para copiar.")
            return
        last = self._messages[-1]
        text_to_copy = f"{last.sender}: {last.translated_text or last.original_text}"
        try:
            pyperclip.copy(text_to_copy)
            self.show_status_notice(f"Copiado: {text_to_copy[:48]}")
            refocus_wow_async()
        except Exception as exc:
            self.show_status_notice(f"Error al copiar: {exc}")

    @Slot(str)
    def show_status_notice(self, notice: str, duration_ms: int = 3800) -> None:
        """Muestra un aviso discreto en la barra inferior del overlay sin bloquear."""
        self.status_label.setText(notice)
        if duration_ms > 0:
            self._status_timer.start(duration_ms)

    @Slot()
    def toggle_move_mode(self) -> bool:
        """Alterna estado de edición/movimiento y persiste configuración."""
        self._move_mode = not self._move_mode
        self.save_geometry_to_config()
        self.update()
        return self._move_mode

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802
        """Permite mover el overlay manteniendo Clic Derecho en cualquier parte o Clic Derecho."""
        # Activación inteligente de foco solo al hacer clic dentro de cajas de texto
        if watched in (getattr(self, "quick_input", None), getattr(self, "edit_player_name", None)):
            if event.type() == QEvent.Type.MouseButtonPress:
                self.set_allow_text_input(True)
            elif event.type() == QEvent.Type.FocusOut:
                self.set_allow_text_input(False)
                refocus_wow_async()

        if event.type() == QEvent.Type.MouseButtonPress:
            mouse_event: QMouseEvent = event
            if mouse_event.button() == Qt.MouseButton.RightButton:
                self._is_dragging_right = True
                self._drag_offset = (
                    mouse_event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                )
                return True
            elif mouse_event.button() == Qt.MouseButton.LeftButton and hasattr(self, "btn_drag") and watched == self.btn_drag:
                self._is_dragging_left = True
                self._drag_offset = (
                    mouse_event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                )
                return True

        elif event.type() == QEvent.Type.MouseMove:
            mouse_event: QMouseEvent = event
            if (self._is_dragging_right and (mouse_event.buttons() & Qt.MouseButton.RightButton)) or \
               (self._is_dragging_left and (mouse_event.buttons() & Qt.MouseButton.LeftButton)):
                if self._drag_offset is not None:
                    self.move(mouse_event.globalPosition().toPoint() - self._drag_offset)
                return True

        elif event.type() == QEvent.Type.MouseButtonRelease:
            mouse_event: QMouseEvent = event
            if (mouse_event.button() == Qt.MouseButton.RightButton and self._is_dragging_right) or \
               (mouse_event.button() == Qt.MouseButton.LeftButton and self._is_dragging_left):
                self._is_dragging_right = False
                self._is_dragging_left = False
                self._drag_offset = None
                if self._is_minimized_in_game:
                    self._tab_x = self.x()
                    self._tab_y = self.y()
                    desc = "Pestaña"
                else:
                    self._chat_x = self.x()
                    self._chat_y = self.y()
                    self._chat_w = self.width()
                    self._chat_h = self.height()
                    self._expanded_rect = self.geometry()
                    desc = "Chat"
                self.save_geometry_to_config()
                self.show_status_notice(f"Posición {desc} guardada: [{self.x()}, {self.y()}]")
                refocus_wow_async()
                return True

        return super().eventFilter(watched, event)

    @Slot()
    def reset_to_free_position(self) -> None:
        """Mueve el overlay a una posición libre que no estorba la interfaz del juego."""
        screen = QGuiApplication.primaryScreen()
        sw, sh = (screen.geometry().width(), screen.geometry().height()) if screen else (1920, 1080)
        x = max(int(sw * 0.03), 45)
        y = max(int(sh * 0.32), 340)
        w = 440
        h = 220
        if self._is_minimized_in_game:
            self._is_minimized_in_game = False
            self.body_container.setVisible(True)
            self.btn_scan.setVisible(True)
            self.btn_clear.setVisible(True)
            self.btn_minimize.setText("[X]")
            self._update_minimized_title()

        self.move(x, y)
        self.resize(w, h)
        self._expanded_rect = self.geometry()
        self.save_geometry_to_config()
        self.show_status_notice(f"Posición libre activa: [{x}, {y}]. Arrástralo libremente con Clic Derecho.")

    @Slot()
    def auto_snap_to_wow(self) -> None:
        """Acopla automáticamente el overlay sobre el chat de WoW o la esquina inferior izquierda."""
        wow_rect = None
        try:
            from src.window_tracker import WoWWindowTracker
            tracker = WoWWindowTracker()
            state = tracker.get_state()
            if state.rect:
                wow_rect = state.rect
        except Exception as exc:
            pass

        screen = QGuiApplication.primaryScreen()
        if wow_rect:
            left, top, right, bottom = wow_rect
            total_w = right - left
            total_h = bottom - top
            # 1. Marco de chat desplegado (esquina inferior izquierda)
            self._chat_w = min(max(int(total_w * 0.25), 420), 480)
            self._chat_h = min(max(int(total_h * 0.21), 190), 230)
            self._chat_x = left + max(int(total_w * 0.019), 36)
            self._chat_y = bottom - self._chat_h - max(int(total_h * 0.042), 42)

            # 2. Posición de la pestaña camuflada (justo al lado de [General] y [Registro de combate])
            self._tab_x = self._chat_x + 230
            self._tab_y = self._chat_y
            origin_desc = f"WoW ({total_w}x{total_h})"
        elif screen:
            geom = screen.geometry()
            sw, sh = geom.width(), geom.height()
            self._chat_w = 440
            self._chat_h = 210
            self._chat_x = 36
            self._chat_y = sh - 255
            self._tab_x = 266
            self._tab_y = self._chat_y
            origin_desc = f"Pantalla ({sw}x{sh})"
        else:
            self._chat_w, self._chat_h = 440, 210
            self._chat_x, self._chat_y = 36, 835
            self._tab_x, self._tab_y = 266, 835
            origin_desc = "Estándar"

        # Plegar automáticamente a la pestaña para camuflaje inmediato en WoW
        if not self._is_minimized_in_game:
            self.toggle_minimize_in_game()
        else:
            self.move(self._tab_x, self._tab_y)
            w = max(self.tab_btn_chat.sizeHint().width() + 14, 98)
            self.resize(w, 24)

        self.save_geometry_to_config()
        self.show_status_notice(f"Pestaña acoplada en {origin_desc}: [{self._tab_x}, {self._tab_y}]")

    def _trigger_whisper_alert(self, sender: str = "") -> None:
        """Emite un destello morado suave (#FF80FF) al recibir un susurro de WoW."""
        self._whisper_glow = True
        self.tab_btn_chat.setStyleSheet(WOW_TAB_BTN_WHISPER_STYLE)
        self.update()

        def _beep() -> None:
            try:
                import winsound
                winsound.MessageBeep(winsound.MB_ICONASTERISK)
            except Exception:
                pass

        threading.Thread(target=_beep, daemon=True).start()
        QTimer.singleShot(2400, self._clear_whisper_alert)

    @Slot()
    def _clear_whisper_alert(self) -> None:
        self._whisper_glow = False
        self.tab_btn_chat.setStyleSheet(WOW_TAB_BTN_STYLE)
        self.update()

    def save_geometry_to_config(self) -> None:
        """Guarda geometría y preferencias visuales actuales del overlay en config.json."""
        rect = (
            self._expanded_rect
            if (self._is_minimized_in_game and self._expanded_rect is not None)
            else self.geometry()
        )
        current_disk_cfg = load_config(self.config_path)
        overlay_cfg = current_disk_cfg.setdefault("overlay", {})
        overlay_cfg["x"] = self.geometry().x()
        overlay_cfg["y"] = self.geometry().y()
        overlay_cfg["width"] = rect.width()
        overlay_cfg["height"] = rect.height()
        overlay_cfg["font_size"] = self.font_size
        overlay_cfg["background_opacity"] = self.bg_opacity
        overlay_cfg["show_original_en"] = self.show_original_en
        overlay_cfg["auto_fade"] = self.auto_fade_enabled
        overlay_cfg["enable_alt_t_hotkey"] = self.alt_t_enabled
        overlay_cfg["auto_hide_on_minimize"] = self.auto_hide_on_minimize
        overlay_cfg["only_visible_with_wow"] = self.only_visible_with_wow
        overlay_cfg["enabled_channel_filters"] = dict(self.channel_filters)
        self.config["overlay"] = overlay_cfg
        save_config(current_disk_cfg, self.config_path)

    def _render_messages(self) -> None:
        visible_msgs = [
            m
            for m in self._messages
            if self.is_channel_group_enabled(m.channel)
        ]
        if not visible_msgs:
            self.chat_label.setText(
                '<span style="color: #888888; font-style: italic;">'
                "[Esperando mensajes de jugadores en inglés... Usa los botones de arriba o las pestañas]"
                "</span>"
            )
            return

        html_lines: list[str] = []
        for msg in visible_msgs:
            color = get_channel_color(msg.channel)
            chan_esc = html.escape(msg.channel)
            sender_esc = html.escape(msg.sender)
            trans_esc = html.escape(msg.translated_text or msg.original_text)

            short_ts = ""
            if msg.timestamp:
                parts = msg.timestamp.split()
                time_part = parts[-1].split(".")[0] if parts else msg.timestamp
                short_ts = (
                    f'<span style="color: #888888; font-size: 8pt;">'
                    f"[{html.escape(time_part[:5])}] </span>"
                )

            orig_suffix = ""
            if (
                self.show_original_en
                and msg.original_text
                and msg.original_text.strip().lower()
                != (msg.translated_text or "").strip().lower()
            ):
                orig_esc = html.escape(msg.original_text)
                orig_suffix = (
                    f' <span style="color: #9AA5B4; font-size: 8.5pt; font-style: italic;">'
                    f"({orig_esc})</span>"
                )

            chan_lower = msg.channel.strip().lower()
            # Formato idéntico al chat de World of Warcraft Forever (3.3.5a)
            if chan_lower in ("susurro", "whisper"):
                prefix = f'<span style="color: {color}; font-weight: bold;">{sender_esc} te susurra:</span> '
            elif chan_lower in ("decir", "say"):
                prefix = f'<span style="color: {color}; font-weight: bold;">{sender_esc} dice:</span> '
            elif chan_lower == "tú -> en":
                prefix = f'<span style="color: #00E5FF; font-weight: bold;">A [{sender_esc}]:</span> '
            elif chan_lower in ("grupo", "party"):
                prefix = f'<span style="color: {color}; font-weight: bold;">[Grupo] [{sender_esc}]:</span> '
            elif chan_lower in ("líder del grupo", "party leader"):
                prefix = f'<span style="color: {color}; font-weight: bold;">[Líder] [{sender_esc}]:</span> '
            elif chan_lower in ("banda", "raid"):
                prefix = f'<span style="color: {color}; font-weight: bold;">[Banda] [{sender_esc}]:</span> '
            elif chan_lower in ("líder de banda", "raid leader"):
                prefix = f'<span style="color: {color}; font-weight: bold;">[Líder de banda] [{sender_esc}]:</span> '
            elif chan_lower in ("alerta de banda", "raid warning"):
                prefix = f'<span style="color: {color}; font-weight: bold;">[Alerta de banda] [{sender_esc}]:</span> '
            elif chan_lower in ("hermandad", "guild"):
                prefix = f'<span style="color: {color}; font-weight: bold;">[Hermandad] [{sender_esc}]:</span> '
            elif chan_lower in ("oficial", "officer"):
                prefix = f'<span style="color: {color}; font-weight: bold;">[Oficial] [{sender_esc}]:</span> '
            else:
                prefix = f'<span style="color: {color}; font-weight: bold;">[{chan_esc}] [{sender_esc}]:</span> '

            # En World of Warcraft Forever, el texto del mensaje tiene el color oficial del canal
            line_html = (
                f'<div style="margin-bottom: 2px; line-height: 1.25; text-shadow: 1px 1px 0px #000000;">'
                f"{short_ts}{prefix}"
                f'<span style="color: {color};">{trans_esc}</span>'
                f"{orig_suffix}"
                f"</div>"
            )
            html_lines.append(line_html)

        self.chat_label.setText("".join(html_lines))

    def paintEvent(self, event: Any) -> None:  # noqa: N802
        """Dibuja el marco del chat desplegado; en modo pestaña plegada es 100% invisible para camuflaje total."""
        if self._is_minimized_in_game:
            # En modo pestaña, NO dibujamos ningún fondo ni borde de ventana.
            # Solo flota el botón nativo de la pestaña sobre el marco de chat de WoW.
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        is_ghost = (self.bg_opacity == 0)
        effective_opacity = (
            0
            if is_ghost
            else (
                max(20, int(self.bg_opacity * 0.4))
                if self._is_faded
                else self.bg_opacity
            )
        )
        # Fondo oscuro translúcido idéntico a ChatFrame1 de WoW Forever
        bg_color = QColor(0, 0, 0, effective_opacity)
        painter.setBrush(bg_color)

        if self._whisper_glow:
            border_color = QColor("#FF80FF")
            pen = QPen(border_color, 1.5, Qt.PenStyle.SolidLine)
        elif is_ghost:
            pen = Qt.PenStyle.NoPen
        else:
            # Borde sutil casi invisible idéntico al marco de chat de WoW 3.3.5a
            border_color = QColor(0, 0, 0, 160)
            pen = QPen(border_color, 1, Qt.PenStyle.SolidLine)

        painter.setPen(pen)
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))

        # Línea de separación sutil bajo las pestañas estilo Blizzard
        if not is_ghost:
            painter.setPen(QPen(QColor(60, 48, 25, 140), 1))
            painter.drawLine(0, 26, self.width(), 26)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() in (Qt.MouseButton.LeftButton, Qt.MouseButton.RightButton):
            self._drag_offset = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if (
            self._drag_offset is not None
            and (event.buttons() & (Qt.MouseButton.LeftButton | Qt.MouseButton.RightButton))
        ):
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() in (Qt.MouseButton.LeftButton, Qt.MouseButton.RightButton):
            self._drag_offset = None
            if not self._is_minimized_in_game:
                self._expanded_rect = self.geometry()
            self.save_geometry_to_config()
            self.show_status_notice(f"Posición guardada: [{self.x()}, {self.y()}]")
        super().mouseReleaseEvent(event)
