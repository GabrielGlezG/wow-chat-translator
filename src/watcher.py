"""Monitor en tiempo real (watcher) y parser de WoWChatLog.txt."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import logging
import os
from pathlib import Path
import re
import threading
import time
from typing import Any, Callable

from PySide6.QtCore import QThread, Signal

from src.config import PROJECT_ROOT, load_config
from src.translator import WoWTranslator, get_translator, should_translate_message

logger = logging.getLogger(__name__)

# Hipervínculos de canal y jugador que WoW Forever inyecta en WoWChatLog.txt:
# "|Hchannel:PARTY|h[Grupo]|h" -> "[Grupo]"
# "|Hplayer:Hairy Warrior:123:PARTY|h[Hairy Warrior]|h" -> "[Hairy Warrior]"
CHANNEL_LINK_WRAPPER_RE = re.compile(r"\|Hchannel:[^|]+\|h\[([^\]]+)\]\|h")
PLAYER_LINK_WRAPPER_RE = re.compile(r"\|H(?:BN)?player:[^|]+\|h\[([^\]]+)\]\|h")
BNET_PRESENCE_RE = re.compile(r"\|K(?:s\d+|[^|]*)\|k")
ROLE_TAG_RE = re.compile(
    r"\[(?:Tanque|Sanador|Healer|Tank|DPS)\]\s*", re.IGNORECASE
)

# Formato con canal entre corchetes:
# "11/21 18:42:10.125  [Grupo] [Hairy Warrior]: that sucked"
# "11/21 18:42:10.125  [Grupo] Hairy Warrior: that sucked"
CHANNEL_LINE_RE = re.compile(
    r"^(?P<timestamp>\d{1,2}/\d{1,2}\s+\d{2}:\d{2}:\d{2}\.\d{3})\s+"
    r"\[(?P<channel>[^\]]+)\]\s+"
    r"(?:\[(?P<sender_br>[^\]]+)\]|(?P<sender_plain>[^:\[\]]+?)):\s*"
    r"(?P<message>.+)$"
)

# Formato de susurros / decir / gritar en español e inglés:
# "11/21 18:42:25.331  Sylvanas te susurra: Hey there"
# "11/21 18:42:25.331  [Sylvanas] whispers: Hey there"
DIRECT_LINE_RE = re.compile(
    r"^(?P<timestamp>\d{1,2}/\d{1,2}\s+\d{2}:\d{2}:\d{2}\.\d{3})\s+"
    r"(?:\[(?P<sender_br>[^\]]+)\]|(?P<sender_plain>[^:\[\]]+?))\s+"
    r"(?P<verb>te\s+susurra|susurra|whispers|dice|says|grita|yells):\s*"
    r"(?P<message>.+)$",
    re.IGNORECASE,
)

# Mensajes automáticos de addons en español que no necesitan traducción
ADDON_SPAM_RE = re.compile(
    r"(?:\{rt\d\}\s*)?Polestar:\s+.+est[aá]\s+lista\s+para\s+entregar",
    re.IGNORECASE,
)

# Palabras/partículas propias de nombres de NPCs (en WoW los jugadores solo tienen 1 o 2 nombres propios sin artículos ni comas)
NPC_NAME_PARTICLES = {
    "el",
    "la",
    "los",
    "las",
    "de",
    "del",
    "the",
    "of",
    "and",
    "y",
    "guardia",
    "guard",
    "grunt",
    "peón",
    "peon",
    "capitán",
    "capitana",
    "captain",
    "comandante",
    "commander",
    "lord",
    "lady",
    "rey",
    "reina",
    "king",
    "queen",
    "príncipe",
    "princesa",
    "inquisidor",
    "inquisidora",
    "inquisitor",
    "archimago",
    "archmage",
    "ciudadano",
    "ciudadana",
    "aldeano",
    "aldeana",
    "jinete",
    "serpiente",
    "espíritu",
    "spirit",
    "sombra",
    "shadow",
    "anciano",
    "elder",
    "maestro",
    "maestra",
    "master",
    "instructor",
    "instructora",
    "vendedor",
    "vendedora",
    "tabernero",
    "tabernera",
    "innkeeper",
    "subastador",
    "subastadora",
    "auctioneer",
    "banquero",
    "banquera",
}


STRONG_SPANISH_WORDS = {
    "gracias", "hola", "buenas", "wenas", "adios", "terminamos", "termino", "terminos",
    "prueba", "amigo", "hermano", "jaja", "jajaja", "jajajaja", "entonces",
    "donde", "aqui", "aca", "estoy", "estan", "estupendo",
    "tengo", "hacer", "quiero", "puedo", "sabes", "tambien", "bueno", "vale", "dale"
}

SPANISH_VOCABULARY = {
    "el", "la", "los", "las", "un", "una", "unos", "unas",
    "de", "del", "al", "en", "para", "por", "con", "sin", "sobre",
    "que", "como", "donde", "cuando", "quien", "cual", "pero", "mas", "aunque", "porque",
    "si", "ya", "no", "ni",
    "hola", "ola", "buenas", "buena", "wenas", "wena", "adios", "chao",
    "gracias", "grax", "amigo", "hermano", "mijo",
    "terminamos", "termino", "terminos", "listo", "lista", "listos",
    "vamos", "dale", "oka", "okey", "vale", "bien", "bueno", "mal",
    "prueba", "probando", "jaja", "jajaja", "jajajaja", "xd", "oye",
    "aqui", "aca", "ahi", "alla", "arriba", "abajo", "lado",
    "tengo", "tiene", "tienen", "hacer", "hago", "hace", "sabes", "sabe",
    "pasa", "pinta", "monton", "entonces",
    "gastes", "solo", "recojes", "subes", "tirarme", "confias", "ayuda"
}

SPANISH_CODEPOINTS = {161, 191, 225, 233, 237, 241, 243, 250}  # ¡, ¿, á, é, í, ñ, ó, ú


def is_obviously_spanish(text: str) -> bool:
    """
    Verifica con precisión si un texto ya está en español.
    Descarta saludos informales, verbos en español y jerga hispana (wenas, ya terminamos, gracias).
    """
    if any(ord(c) in SPANISH_CODEPOINTS for c in text):
        return True
    words = re.findall(r"[a-z]+", text.lower())
    if not words:
        return False
    if any(w in STRONG_SPANISH_WORDS for w in words):
        return True
    matches = sum(1 for w in words if w in SPANISH_VOCABULARY)
    return len(words) >= 2 and (matches / len(words) >= 0.40)


def is_own_player_sender(sender: str, player_name: str = "") -> bool:
    """
    Detecta si el remitente es el propio jugador o una variante con ligero ruido OCR.
    Funciona dinámicamente con cualquier nombre de personaje configurado por el usuario.
    """
    cleaned = re.sub(r"[^\w]", "", sender.lower())
    if not cleaned:
        return False

    target_name = (player_name or "").strip()
    if not target_name:
        return False

    p_clean = re.sub(r"[^\w]", "", target_name.lower().split("-")[0])
    if not p_clean:
        return False

    # Coincidencia directa exacta o parcial
    if p_clean in cleaned or cleaned in p_clean:
        return True

    # Resistencia a pequeñas deformaciones OCR si comparten raíz y longitud similar
    if len(p_clean) >= 4 and len(cleaned) >= 4:
        if cleaned[:3] == p_clean[:3] and abs(len(cleaned) - len(p_clean)) <= 3:
            return True

    return False


def is_likely_npc_sender(sender: str, message: str = "") -> bool:
    """
    Determina si el remitente de un mensaje es un NPC del juego en lugar de un jugador real.
    En WoW Forever:
    - Los nombres de jugador tienen máximo 2 palabras (Nombre o Nombre Apellido), sin comas, sin números ni artículos.
    - Los amigos Battle.net ('Amigo BNet') siempre son jugadores reales.
    - Los NPCs suelen tener comas ('Min'loth, la Serpiente'), más de 2 palabras, artículos ('el', 'la', 'de', 'the', 'of')
      o títulos ('Guardia de Orgrimmar', 'Instructor de chamanes').
    """
    cleaned = sender.strip().strip("[]").strip()
    if not cleaned:
        return True

    # Los susurros de amigos Battle.net son jugadores reales
    if cleaned.lower().startswith("amigo bnet") or cleaned.lower() == "amigo bnet":
        return False

    # Si incluye reino ("Arthas-Ragnaros"), quedarse con la parte del nombre del personaje
    base_name = cleaned.split("-")[0].strip()
    if not base_name:
        return True

    # Los jugadores nunca tienen comas, puntos, dos puntos, dígitos ni guiones bajos
    if any(ch in base_name for ch in (",", ".", ":", ";", "_", "/", "\\")) or any(
        ch.isdigit() for ch in base_name
    ):
        return True

    words = base_name.split()
    # En WoW / WoW Forever los nombres de jugador tienen 1 o 2 palabras como máximo
    if len(words) > 2:
        return True

    lower_words = {w.lower().strip("'") for w in words}
    if lower_words & NPC_NAME_PARTICLES:
        return True

    # Frases típicas de sistema/NPC
    if message and (" intenta huir " in message.lower() or " comienza a lanzar " in message.lower()):
        return True

    return False

VERB_TO_CHANNEL: dict[str, str] = {
    "te susurra": "Susurro",
    "susurra": "Susurro",
    "whispers": "Susurro",
    "dice": "Decir",
    "says": "Decir",
    "grita": "Gritar",
    "yells": "Gritar",
}

DEFAULT_IGNORED_PREFIXES = (
    "comercio",
    "trade",
    "general",
    "defensalocal",
    "localdefense",
    "buscargrupo",
    "lookingforgroup",
    "mundo",
    "world",
    "loot",
    "botín",
    "sistema",
    "system",
)


@dataclass(frozen=True)
class ChatMessage:
    """Estructura tipada para un mensaje de chat de World of Warcraft."""

    timestamp: str
    channel: str
    sender: str
    original_text: str
    translated_text: str = ""


def normalize_channel_name(raw_channel: str) -> str:
    """Limpia prefijos numéricos de canal como '2. Comercio - Ciudad' -> 'Comercio - Ciudad'."""
    cleaned = re.sub(r"^\d+\.\s*", "", raw_channel.strip())
    return cleaned


def is_channel_allowed(
    raw_channel: str,
    allowed_channels: list[str] | None = None,
    ignored_channels: list[str] | None = None,
) -> bool:
    """Verifica si un canal de WoW debe procesarse o descartarse por spam."""
    raw_stripped = raw_channel.strip()
    if re.match(r"^\d+\.", raw_stripped):
        return False

    normalized = normalize_channel_name(raw_stripped)
    lower_norm = normalized.lower()

    ignored = [c.lower() for c in (ignored_channels or [])] + list(
        DEFAULT_IGNORED_PREFIXES
    )
    for ign in ignored:
        if ign and (lower_norm == ign or lower_norm.startswith(ign)):
            return False

    if not allowed_channels:
        return True

    allowed_lower = [c.lower() for c in allowed_channels]
    for allow in allowed_lower:
        if lower_norm == allow or lower_norm.startswith(allow):
            return True

    return False


def parse_chat_line(
    line: str,
    allowed_channels: list[str] | None = None,
    ignored_channels: list[str] | None = None,
    player_name: str = "",
) -> ChatMessage | None:
    """
    Analiza una línea de WoWChatLog.txt.
    Devuelve un ChatMessage si pertenece a un canal relevante y contiene texto conversacional,
    o None si es spam, canal ignorado, mensaje propio o solo un enlace de objeto/misión.
    """
    stripped = line.strip()
    if not stripped:
        return None

    # Desenvolver hipervínculos de canal, jugador y presencia Battle.net nativos de WoW Forever
    stripped = CHANNEL_LINK_WRAPPER_RE.sub(r"[\1]", stripped)
    stripped = PLAYER_LINK_WRAPPER_RE.sub(r"[\1]", stripped)
    stripped = BNET_PRESENCE_RE.sub("Amigo BNet", stripped)
    stripped = ROLE_TAG_RE.sub("", stripped)

    timestamp = ""
    channel = ""
    sender = ""
    message = ""

    match_channel = CHANNEL_LINE_RE.match(stripped)
    if match_channel:
        timestamp = match_channel.group("timestamp")
        raw_channel = match_channel.group("channel")
        if not is_channel_allowed(raw_channel, allowed_channels, ignored_channels):
            return None
        channel = normalize_channel_name(raw_channel)
        sender = (
            match_channel.group("sender_br")
            or match_channel.group("sender_plain")
            or ""
        ).strip()
        message = match_channel.group("message").strip()
    else:
        match_direct = DIRECT_LINE_RE.match(stripped)
        if not match_direct:
            return None
        timestamp = match_direct.group("timestamp")
        verb = re.sub(r"\s+", " ", match_direct.group("verb").strip().lower())
        channel = VERB_TO_CHANNEL.get(verb, "Susurro")
        if not is_channel_allowed(channel, allowed_channels, ignored_channels):
            return None
        sender = (
            match_direct.group("sender_br")
            or match_direct.group("sender_plain")
            or ""
        ).strip()
        message = match_direct.group("message").strip()

    if not sender or not message:
        return None

    # Ignorar susurros salientes ("Para [Jugador]: ...")
    if sender.lower().startswith("para ") or sender.lower().startswith("to "):
        return None

    # Ignorar diálogos de NPCs del juego (solo procesar jugadores reales)
    if is_likely_npc_sender(sender, message):
        return None

    # Ignorar anuncios automáticos de misiones de Polestar en español
    if ADDON_SPAM_RE.search(message):
        return None

    # Ignorar mensajes propios del jugador si está configurado
    if is_own_player_sender(sender, player_name):
        return None

    # Ignorar mensajes que ya están en español (diálogos locales de NPCs o jugadores que no requieren traducción)
    if is_obviously_spanish(message):
        return None

    # Ahorro de tokens: ignorar mensajes sin texto conversacional (ej. links puros de misión/ítem)
    if not should_translate_message(message):
        return None

    return ChatMessage(
        timestamp=timestamp,
        channel=channel,
        sender=sender,
        original_text=message,
    )


class ChatLogWatcher(QThread):
    """
    Hilo dedicado (QThread) que monitorea WoWChatLog.txt en modo solo lectura ('r', utf-8),
    traduce los mensajes relevantes y emite señales hacia el overlay de PySide6.
    """

    message_ready = Signal(object)  # Emite ChatMessage con translated_text
    status_changed = Signal(str)

    def __init__(
        self,
        config: dict[str, Any] | None = None,
        translator: WoWTranslator | None = None,
        read_from_start: bool = False,
        preload_recent_count: int = 4,
        poll_interval: float = 0.15,
    ) -> None:
        super().__init__()
        self.config = config or load_config()
        self.translator = translator or get_translator()
        self.read_from_start = read_from_start
        self.preload_recent_count = preload_recent_count
        self.poll_interval = poll_interval
        self._running = False
        self._paused = False
        self._read_lock = threading.Lock()
        self._file_offset: int | None = None

        raw_path = self.config.get("wow_chat_log_path", "tests/mock_WoWChatLog.txt")
        path_obj = Path(raw_path)
        if not path_obj.is_absolute():
            path_obj = PROJECT_ROOT / path_obj
        self.log_path: Path = path_obj

    @property
    def paused(self) -> bool:
        """Indica si el monitoreo/traducción está en pausa."""
        return self._paused

    def set_paused(self, paused: bool) -> None:
        """Pausa o reanuda el procesamiento de nuevas líneas del log."""
        self._paused = paused
        state_str = "Pausado" if paused else "Activo"
        self.status_changed.emit(state_str)

    def set_player_name(self, name: str) -> None:
        """Actualiza dinámicamente el nombre del jugador para el filtrado."""
        self.config["player_name"] = name.strip()

    def set_log_path(self, new_path: Path | str) -> None:
        """Actualiza dinámicamente la ruta de WoWChatLog.txt en caliente."""
        with self._read_lock:
            p = Path(new_path)
            self.log_path = p
            self._file_offset = None
            self.config["wow_chat_log_path"] = str(p).replace("\\", "/")

    def stop(self) -> None:
        """Detiene el bucle del hilo de forma segura."""
        self._running = False
        self.wait(2000)

    def process_raw_line(
        self,
        line: str,
        callback: Callable[[ChatMessage], None] | None = None,
    ) -> ChatMessage | None:
        """Procesa y traduce una línea individual del log."""
        if self._paused:
            return None

        allowed = self.config.get("allowed_channels")
        ignored = self.config.get("ignored_channels")
        player_name = str(self.config.get("player_name", ""))

        try:
            parsed = parse_chat_line(
                line,
                allowed_channels=allowed,
                ignored_channels=ignored,
                player_name=player_name,
            )
            if parsed is None:
                return None

            translated = self.translator.translate_incoming(parsed.original_text)
            final_msg = ChatMessage(
                timestamp=parsed.timestamp,
                channel=parsed.channel,
                sender=parsed.sender,
                original_text=parsed.original_text,
                translated_text=translated,
            )
            self.message_ready.emit(final_msg)
            if callback is not None:
                callback(final_msg)
            return final_msg
        except Exception as exc:
            logger.warning("Error procesando línea '%s': %s", line[:50], exc)
            return None

    def _preload_recent_lines(self) -> int:
        """Carga las últimas N líneas relevantes de WoWChatLog.txt al iniciar y devuelve el offset final."""
        if not self.log_path.exists():
            return 0
        try:
            with self.log_path.open("r", encoding="utf-8", errors="replace") as f:
                tail_lines = deque(f, maxlen=150)
                end_offset = f.tell()

            allowed = self.config.get("allowed_channels")
            ignored = self.config.get("ignored_channels")
            player_name = str(self.config.get("player_name", ""))

            candidates: list[str] = []
            for raw_line in tail_lines:
                if (
                    parse_chat_line(
                        raw_line,
                        allowed_channels=allowed,
                        ignored_channels=ignored,
                        player_name=player_name,
                    )
                    is not None
                ):
                    candidates.append(raw_line)

            for raw_line in candidates[-self.preload_recent_count :]:
                if not self._running:
                    break
                self.process_raw_line(raw_line)

            self._file_offset = end_offset
            return end_offset
        except OSError:
            return 0

    def _read_new_lines(self) -> int:
        """Lee y procesa cualquier línea nueva en WoWChatLog.txt (hilo seguro)."""
        if not self.log_path.exists():
            from src.config import auto_detect_wow_log_path
            detected = auto_detect_wow_log_path()
            if detected and detected.exists():
                self.log_path = detected
                self.config["wow_chat_log_path"] = str(detected).replace("\\", "/")
            else:
                return 0
        new_messages = 0
        with self._read_lock:
            try:
                current_size = os.path.getsize(self.log_path)
                if self._file_offset is None:
                    self._file_offset = current_size
                elif current_size < self._file_offset:
                    self._file_offset = 0

                if current_size > self._file_offset:
                    with self.log_path.open(
                        "r", encoding="utf-8", errors="replace"
                    ) as log_file:
                        log_file.seek(self._file_offset)
                        lines = log_file.readlines()
                        self._file_offset = log_file.tell()

                    for line in lines:
                        if not self._running:
                            break
                        msg = self.process_raw_line(line)
                        if msg is not None:
                            new_messages += 1
            except OSError as exc:
                logger.debug("Error de lectura temporal en WoWChatLog.txt: %s", exc)
            except Exception as exc:
                logger.exception("Error inesperado en tailing de WoWChatLog.txt: %s", exc)
        return new_messages

    def poll_now(self) -> int:
        """Fuerza la lectura y traducción inmediata de nuevas líneas (hilo seguro)."""
        return self._read_new_lines()

    def run(self) -> None:
        """Bucle principal de tailing pasivo sobre WoWChatLog.txt."""
        self._running = True

        if self.read_from_start:
            self._file_offset = 0
        elif self.preload_recent_count > 0 and self.log_path.exists():
            self._file_offset = self._preload_recent_lines()

        while self._running:
            self._read_new_lines()
            time.sleep(self.poll_interval)
