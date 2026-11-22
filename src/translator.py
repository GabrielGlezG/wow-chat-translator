"""Motor de traducción para World of Warcraft (EN->ES y ES->EN) con soporte local offline y google-genai."""

from __future__ import annotations

from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from dataclasses import dataclass
import logging
from pathlib import Path
import re
import threading
import time
from typing import Any, Protocol

try:
    import ctranslate2
    import sentencepiece as spm
    HAS_LOCAL_ENGINE = True
except ImportError:
    ctranslate2 = None  # type: ignore[assignment]
    spm = None  # type: ignore[assignment]
    HAS_LOCAL_ENGINE = False

from src.config import PROJECT_ROOT, get_gemini_api_key, load_config
from src.glossary import get_slang_manager

logger = logging.getLogger(__name__)

# Patrones para hipervínculos del cliente de WoW, enlaces dobles de misión y marcadores de banda
WOW_FULL_HYPERLINK_RE = re.compile(
    r"\|c[0-9a-fA-F]{8}\|H[^|]+\|h\[[^\]]+\]\|h\|r|\|H[^|]+\|h\[[^\]]+\]\|h"
)
WOW_BRACKET_LINK_RE = re.compile(r"\[\[[^\]]+\][^\]]*\]|\[\[[^\]]+\]\]")
WOW_RAID_ICON_RE = re.compile(
    r"\{(?:rt[1-8]|skull|cross|square|moon|triangle|diamond|circle|star|calavera|cruz|cuadrado|luna|triángulo|diamante|círculo|estrella)\}",
    re.IGNORECASE,
)
WOW_TOKEN_COMBINED_RE = re.compile(
    r"(\|c[0-9a-fA-F]{8}\|H[^|]+\|h\[[^\]]+\]\|h\|r|\|H[^|]+\|h\[[^\]]+\]\|h|\[\[[^\]]+\][^\]]*\]|\[\[[^\]]+\]\]|\{(?:rt[1-8]|skull|cross|square|moon|triangle|diamond|circle|star)\})",
    re.IGNORECASE,
)

# Mensajes sin letras conversacionales (solo números, símbolos o espacios)
NON_CONVERSATIONAL_RE = re.compile(r"^[\d\s\W_]+$", re.UNICODE)

INCOMING_SYSTEM_PROMPT = (
    "Eres un traductor en tiempo real para el chat de World of Warcraft (WoW Forever). "
    "Traduce el mensaje del inglés al español natural de gamer/WoW.\n"
    "REGLAS ESTRICTAS:\n"
    "1. Devuelve ÚNICAMENTE la traducción en una sola línea, sin comillas envolventes ni explicaciones.\n"
    "2. Corrige errores de tipeo ('myu', 'bugge dwhen', 'trhe', 'recieve', 'thats') y censura ('%^&*', '!@#$') por su sentido real en contexto gamer.\n"
    "3. Interpreta o preserva la jerga de WoW con naturalidad: 'oom' (sin maná), 'DCd'/'DCs' (se desconectó/DC), "
    "'pull' (pulear), 'wipe' (wipe), 'aggro' (aggro), 'mb' (mala mía), 'ty' (gracias), 'lfm'/'lfg', 'healer', 'tank', 'dps', 'BiS', 'greed' (codicia), 'need' (necesidad).\n"
    "4. Mantén intactos los marcadores de posición como __WOW_TOKEN_0__.\n"
    "5. Si el mensaje ya está en español, devuélvelo en español tal cual."
)

OUTGOING_SYSTEM_PROMPT = (
    "Eres un traductor en tiempo real para el chat de World of Warcraft (WoW Forever). "
    "Traduce el mensaje del jugador del español al inglés natural de jugador de WoW (corto, informal, con jerga gamer).\n"
    "REGLAS ESTRICTAS:\n"
    "1. Devuelve ÚNICAMENTE el texto traducido en inglés en una sola línea, sin comillas envolventes ni explicaciones.\n"
    "2. Usa abreviaturas naturales de WoW cuando encajen ('oom', 'lag spike', 'mb', 'ty', 'pull', 'wipe', 'need', 'greed', 'sec', 'brb', 'pls').\n"
    "3. Mantén intactos los marcadores de posición como __WOW_TOKEN_0__."
)

VISION_CHAT_PROMPT = (
    "Analiza esta captura de la ventana de chat de World of Warcraft.\n"
    "OBJETIVO: Extraer y traducir al español únicamente los mensajes de chat conversacionales escritos EN INGLÉS por OTROS JUGADORES REALES.\n\n"
    "REGLAS PARA DIFERENCIAR JUGADORES DE NPCS:\n"
    "1. JUGADORES REALES:\n"
    "   - Hablan en lenguaje informal, gamer o cotidiano ('hello', 'where are u', 'what u doing', 'rdy', 'oom', 'pull', 'wait pls', 'wipe', 'can someone help').\n"
    "   - Nombres de jugadores: Requiem, Aptinstall, Bayard, o con corchetes [Hairy Warrior], o [Amigo BNet].\n"
    "   - Canales válidos: Susurro (ej. '[Jugador] susurra:', 'Jugador susurra:', 'whispers:'), Grupo ('[Grupo]'), Banda ('[Banda]'), Hermandad ('[Hermandad]') o Decir ('dice:').\n"
    "2. NPCS Y MONSTRUOS DEL JUEGO (DEBEN SER IGNORADOS):\n"
    "   - Diálogos de historia/lore, gritos teatrales, o nombres como 'Guardia de...', 'Instructor...', 'Abominación...', 'Calder Gray', 'Jefe...'.\n"
    "   - IGNORA mensajes en español (diálogos locales de NPCs de misiones o jugadores hispanohablantes).\n"
    "   - IGNORA mensajes de sistema, loot ('crea...', 'recibe botín'), addons o canales de comercio/general ('[1. General]', '[2. Comercio]').\n"
    "   - IGNORA mensajes enviados por mí ('Para [Jugador]:' o lo escrito en la caja de texto inferior).\n\n"
    "TRADUCCIÓN:\n"
    "Traduce cada mensaje del inglés al español natural de gamer de WoW.\n"
    "Formato de salida (una línea por mensaje, sin corchetes en los campos ni explicaciones):\n"
    "CANAL|JUGADOR|MENSAJE_ORIGINAL_EN|TRADUCCION_ES\n"
    "Si no hay mensajes válidos de jugadores en inglés, responde únicamente: NONE"
)

# Gestor centralizado de jerga de WoW cargado desde data/wow_slang.json
_slang_mgr = get_slang_manager()
FAST_INCOMING_GLOSSARY: dict[str, str] = _slang_mgr.fast_exact
WOW_SLANG_EN_TO_ES: list[tuple[re.Pattern[str], str]] = _slang_mgr.slang_en_to_es
WOW_POST_ES: list[tuple[re.Pattern[str], str]] = _slang_mgr.post_corrections_es
WOW_SLANG_ES_TO_EN: list[tuple[re.Pattern[str], str]] = _slang_mgr.slang_es_to_en
WOW_POST_EN: list[tuple[re.Pattern[str], str]] = _slang_mgr.post_corrections_en

# Respuestas de respaldo offline/deterministas para pruebas locales sin API key activa
OFFLINE_INCOMING_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"i even got all the loot and that sucked", re.IGNORECASE),
        "incluso me llevé todo el loot y aun así estuvo fatal",
    ),
    (
        re.compile(r"is that it.*bugge.*dc", re.IGNORECASE),
        "¿eso es todo? Se me bugeó la interfaz cuando me desconecté (DC)",
    ),
    (
        re.compile(r"wait.*healer\s+oom.*don'?t\s+pull", re.IGNORECASE),
        "esperen un seg, el healer está sin maná, no puleen",
    ),
    (
        re.compile(r"mb.*fat\s+fingered\s+blink", re.IGNORECASE),
        "mala mía, apreté traslación/blink por error",
    ),
]

OFFLINE_OUTGOING_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"esperen.*sin\s+man[aá]", re.IGNORECASE),
        "wait a sec, oom",
    ),
    (
        re.compile(r"lagazo\s+terrible", re.IGNORECASE),
        "sorry, huge lag spike",
    ),
    (
        re.compile(r"alguien\s+necesita\s+este.*codicia", re.IGNORECASE),
        "anyone need this or greed?",
    ),
]


class TranslatorProvider(Protocol):
    """Protocolo para proveedores de traducción."""

    def translate_incoming(self, text: str) -> str:
        """Traduce un mensaje entrante del inglés al español (EN -> ES)."""
        ...

    def translate_outgoing(self, text: str) -> str:
        """Traduce un mensaje saliente del español al inglés gamer (ES -> EN)."""
        ...


@dataclass
class MaskedText:
    """Representa un texto con hipervínculos/tokens de WoW enmascarados."""

    masked: str
    tokens: dict[str, str]
    has_conversational_text: bool


def mask_wow_tokens(text: str) -> MaskedText:
    """Enmascara hipervínculos de WoW e iconos de banda y evalúa si hay texto conversacional."""
    tokens: dict[str, str] = {}
    counter = 0

    def _replace(match: re.Match[str]) -> str:
        nonlocal counter
        placeholder = f"__WOW_TOKEN_{counter}__"
        tokens[placeholder] = match.group(0)
        counter += 1
        return placeholder

    masked = WOW_TOKEN_COMBINED_RE.sub(_replace, text)
    stripped_without_tokens = WOW_TOKEN_COMBINED_RE.sub("", text).strip()

    has_conversational = bool(
        stripped_without_tokens
        and not NON_CONVERSATIONAL_RE.match(stripped_without_tokens)
    )
    return MaskedText(
        masked=masked,
        tokens=tokens,
        has_conversational_text=has_conversational,
    )


def restore_wow_tokens(text: str, tokens: dict[str, str]) -> str:
    """Restaura los tokens de WoW previamente enmascarados."""
    restored = re.sub(r"__\s*WOW_TOKEN_(\d+)\s*__", r"__WOW_TOKEN_\1__", text)
    for placeholder, original in tokens.items():
        restored = restored.replace(placeholder, original)
    return restored


def should_translate_message(text: str) -> bool:
    """Determina si un mensaje merece enviarse al traductor para ahorrar tokens."""
    if not text or not text.strip():
        return False
    masked_info = mask_wow_tokens(text.strip())
    return masked_info.has_conversational_text


def clean_llm_output(raw: str) -> str:
    """Limpia saltos de línea, prefijos de relleno y comillas envolventes del LLM."""
    cleaned = raw.strip().replace("\r", " ").replace("\n", " ")
    cleaned = re.sub(
        r"^(?:aqu[ií]\s+tienes\s+la\s+traducci[oó]n|traducci[oó]n|translation)\s*:\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    ).strip()
    if "->" in cleaned:
        cleaned = cleaned.split("->")[-1].strip()
    cleaned = cleaned.strip("*").strip()
    if len(cleaned) >= 2 and (
        (cleaned.startswith('"') and cleaned.endswith('"'))
        or (cleaned.startswith("'") and cleaned.endswith("'"))
    ):
        cleaned = cleaned[1:-1].strip()
    return cleaned


class LocalOfflineEngine:
    """Motor de traducción neuronal 100% offline basado en CTranslate2 y MarianMT."""

    def __init__(self, models_dir: Path | None = None) -> None:
        self.models_dir = models_dir or (PROJECT_ROOT / "models")
        self.en_es_dir = self.models_dir / "opus-mt-en-es"
        self.es_en_dir = self.models_dir / "opus-mt-es-en"

        self._ct_en_es: Any = None
        self._ct_es_en: Any = None
        self._sp_en_src: Any = None
        self._sp_es_tgt: Any = None
        self._sp_es_src: Any = None
        self._sp_en_tgt: Any = None

        self._loaded: bool = False
        self._lock = threading.Lock()

    def is_available(self) -> bool:
        """Comprueba si las librerías y los modelos locales están presentes en disco."""
        if not HAS_LOCAL_ENGINE:
            return False
        return (
            (self.en_es_dir / "model.bin").is_file()
            and (self.en_es_dir / "source.spm").is_file()
            and (self.en_es_dir / "target.spm").is_file()
            and (self.es_en_dir / "model.bin").is_file()
            and (self.es_en_dir / "source.spm").is_file()
            and (self.es_en_dir / "target.spm").is_file()
        )

    def load(self) -> bool:
        """Carga los modelos en memoria si están disponibles (hilo seguro)."""
        if self._loaded:
            return True
        with self._lock:
            if self._loaded:
                return True
            if not self.is_available():
                logger.warning(
                    "Modelos locales no encontrados en %s o dependencias no instaladas.",
                    self.models_dir,
                )
                return False
            try:
                logger.info("Cargando modelos locales CTranslate2 (int8)...")
                t0 = time.perf_counter()
                self._sp_en_src = spm.SentencePieceProcessor(
                    model_file=str(self.en_es_dir / "source.spm")
                )
                self._sp_es_tgt = spm.SentencePieceProcessor(
                    model_file=str(self.en_es_dir / "target.spm")
                )
                self._ct_en_es = ctranslate2.Translator(
                    str(self.en_es_dir), device="cpu", compute_type="int8"
                )

                self._sp_es_src = spm.SentencePieceProcessor(
                    model_file=str(self.es_en_dir / "source.spm")
                )
                self._sp_en_tgt = spm.SentencePieceProcessor(
                    model_file=str(self.es_en_dir / "target.spm")
                )
                self._ct_es_en = ctranslate2.Translator(
                    str(self.es_en_dir), device="cpu", compute_type="int8"
                )
                elapsed = (time.perf_counter() - t0) * 1000.0
                logger.info(
                    "Modelos locales CTranslate2 cargados con éxito en %.1fms.",
                    elapsed,
                )
                self._loaded = True
                return True
            except Exception as exc:
                logger.exception("Error cargando modelos locales: %s", exc)
                return False

    def translate_en_to_es(self, text: str) -> str:
        """Traduce del inglés al español usando el modelo neuronal local + glosario de WoW."""
        if not self._loaded and not self.load():
            return text

        cleaned = _slang_mgr.preprocess_incoming(text)

        tokens = self._sp_en_src.encode(cleaned, out_type=str) + ["</s>"]
        results = self._ct_en_es.translate_batch([tokens], beam_size=1)
        raw_trans = self._sp_es_tgt.decode(results[0].hypotheses[0])

        raw_trans = _slang_mgr.postprocess_incoming(raw_trans)

        return clean_llm_output(raw_trans)

    def translate_es_to_en(self, text: str) -> str:
        """Traduce del español al inglés gamer usando el modelo neuronal local + glosario de WoW."""
        if not self._loaded and not self.load():
            return text

        cleaned = _slang_mgr.preprocess_outgoing(text)

        tokens = self._sp_es_src.encode(cleaned, out_type=str) + ["</s>"]
        results = self._ct_es_en.translate_batch([tokens], beam_size=1)
        raw_trans = self._sp_en_tgt.decode(results[0].hypotheses[0])

        raw_trans = _slang_mgr.postprocess_outgoing(raw_trans)

        return clean_llm_output(raw_trans)


class WoWTranslator:
    """Cliente de traducción con caché LRU, cadena de fallback de modelos y preservación de tokens."""

    FALLBACK_MODELS = (
        "gemini-3.1-flash-lite",
        "gemini-3.5-flash",
        "gemini-3.6-flash",
        "gemini-3.5-flash-lite",
    )

    def __init__(
        self,
        api_key: str | None = None,
        config: dict[str, Any] | None = None,
        cache_size: int = 256,
    ) -> None:
        self.config = config or load_config()
        llm_cfg = self.config.get("llm", {})
        self.provider: str = str(llm_cfg.get("provider", "local")).lower()
        configured_model = str(llm_cfg.get("model", "opus-mt"))
        if configured_model in ("gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-3.5-flash-lite"):
            configured_model = "gemini-3.1-flash-lite"
        self.model: str = configured_model
        self.timeout_seconds: float = max(
            float(llm_cfg.get("timeout_seconds", 8.0)), 7.0
        )
        self.temperature: float = float(llm_cfg.get("temperature", 0.1))
        self.max_output_tokens: int = int(llm_cfg.get("max_output_tokens", 96))
        self.thinking_budget: int = int(llm_cfg.get("thinking_budget", 0))

        self.local_engine = LocalOfflineEngine()

        resolved_key = api_key if api_key is not None else get_gemini_api_key()
        self.api_key = (
            ""
            if resolved_key in ("", "tu_api_key_aqui", "YOUR_API_KEY")
            else resolved_key
        )

        self._client: Any = None
        if self.api_key:
            try:
                from google import genai
                from google.genai import types

                self._client = genai.Client(
                    api_key=self.api_key,
                    http_options=types.HttpOptions(
                        retry_options=types.HttpRetryOptions(attempts=1)
                    ),
                )
            except Exception as exc:
                logger.warning("No se pudo inicializar google-genai Client: %s", exc)
                self._client = None

        self._cache: OrderedDict[tuple[str, str], str] = OrderedDict()
        self._cache_size = cache_size
        self._quarantined_models: dict[str, float] = {}
        self._executor = ThreadPoolExecutor(
            max_workers=4, thread_name_prefix="wow-llm"
        )
        self.last_latency_ms: float = 0.0
        self.warmup_async()

    def _is_model_quarantined(self, model_name: str) -> bool:
        """Verifica si un modelo está temporalmente en cuarentena por 429/cuota agotada."""
        until = self._quarantined_models.get(model_name)
        if until is None:
            return False
        if time.time() > until:
            del self._quarantined_models[model_name]
            return False
        return True

    def _quarantine_model(self, model_name: str, duration_sec: float = 1800.0) -> None:
        """Pone un modelo en cuarentena para no reintentarlo repetidamente."""
        self._quarantined_models[model_name] = time.time() + duration_sec
        logger.warning(
            "Modelo %s puesto en cuarentena por %.0fs debido a 429 / cuota agotada.",
            model_name,
            duration_sec,
        )

    def warmup_async(self) -> None:
        """Precalienta los motores de traducción en segundo plano para reducir latencia."""
        def _warmup() -> None:
            if self.provider == "local" or self.local_engine.is_available():
                self.local_engine.load()
            if self.provider == "gemini" and self._client is not None:
                try:
                    self._call_gemini_with_model(
                        self.model, "Respond only: ok", "ok"
                    )
                    logger.info("Conexión con Gemini (%s) precalentada.", self.model)
                except Exception as exc:
                    logger.debug("Warmup de Gemini omitido: %s", exc)

        threading.Thread(target=_warmup, name="wow-llm-warmup", daemon=True).start()

    def _get_cached(self, direction: str, text: str) -> str | None:
        key = (direction, text.lower().strip())
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        return None

    def _set_cached(self, direction: str, text: str, result: str) -> None:
        key = (direction, text.lower().strip())
        self._cache[key] = result
        self._cache.move_to_end(key)
        while len(self._cache) > self._cache_size:
            self._cache.popitem(last=False)

    def _call_gemini_with_model(
        self, model_name: str, system_prompt: str, user_text: str
    ) -> str:
        from google.genai import types

        cfg_kwargs: dict[str, Any] = {
            "system_instruction": system_prompt,
            "temperature": self.temperature,
            "max_output_tokens": self.max_output_tokens,
        }
        if "2.5" in model_name or "3.1" in model_name:
            cfg_kwargs["thinking_config"] = types.ThinkingConfig(
                thinking_budget=self.thinking_budget
            )
        elif "3.5" in model_name or "3.6" in model_name or "3.7" in model_name:
            cfg_kwargs["thinking_config"] = types.ThinkingConfig(
                thinking_level="MINIMAL"  # type: ignore[arg-type]
            )
        elif "3.8" in model_name:
            cfg_kwargs["thinking_config"] = types.ThinkingConfig(
                thinking_level="LOW"  # type: ignore[arg-type]
            )

        gen_cfg = types.GenerateContentConfig(**cfg_kwargs)
        response = self._client.models.generate_content(
            model=model_name,
            contents=user_text,
            config=gen_cfg,
        )
        return clean_llm_output(response.text or "")

    def _call_gemini(self, system_prompt: str, user_text: str) -> str:
        candidates = [self.model] + [
            m for m in self.FALLBACK_MODELS if m != self.model
        ]
        models_to_try = [m for m in candidates if not self._is_model_quarantined(m)]
        if not models_to_try:
            models_to_try = candidates

        last_exc: Exception | None = None
        for model_name in models_to_try:
            try:
                result = self._call_gemini_with_model(
                    model_name, system_prompt, user_text
                )
                if result:
                    return result
            except Exception as exc:
                last_exc = exc
                err_str = str(exc)
                if any(code in err_str for code in ("RESOURCE_EXHAUSTED", "429", "503", "UNAVAILABLE", "quota")):
                    duration = 1800.0 if ("429" in err_str or "quota" in err_str.lower() or "RESOURCE_EXHAUSTED" in err_str) else 180.0
                    self._quarantine_model(model_name, duration)
                logger.warning(
                    "Fallo con modelo %s (%s), probando siguiente...",
                    model_name,
                    exc,
                )
        if last_exc is not None:
            raise last_exc
        return ""

    def _offline_fallback(self, direction: str, text: str) -> str | None:
        normalized = text.strip()
        lower = normalized.lower()
        if direction == "EN->ES":
            if lower in FAST_INCOMING_GLOSSARY:
                return FAST_INCOMING_GLOSSARY[lower]
            for pattern, replacement in OFFLINE_INCOMING_PATTERNS:
                if pattern.search(normalized):
                    return replacement
        else:
            for pattern, replacement in OFFLINE_OUTGOING_PATTERNS:
                if pattern.search(normalized):
                    return replacement
        return None

    def translate_incoming(self, text: str) -> str:
        """Traduce un mensaje de chat entrante (EN -> ES) preservando enlaces y jerga."""
        start = time.perf_counter()
        raw = text.strip()
        if not should_translate_message(raw):
            self.last_latency_ms = (time.perf_counter() - start) * 1000.0
            return raw

        cached = self._get_cached("EN->ES", raw)
        if cached is not None:
            self.last_latency_ms = (time.perf_counter() - start) * 1000.0
            return cached

        lower = raw.lower()
        if lower in FAST_INCOMING_GLOSSARY:
            result = FAST_INCOMING_GLOSSARY[lower]
            self._set_cached("EN->ES", raw, result)
            self.last_latency_ms = (time.perf_counter() - start) * 1000.0
            return result

        masked_info = mask_wow_tokens(raw)

        # 1. Si el proveedor configurado es 'local' o no hay cliente Gemini, usar LocalOfflineEngine
        if self.provider == "local" and self.local_engine.is_available():
            try:
                translated_masked = self.local_engine.translate_en_to_es(masked_info.masked)
                if translated_masked:
                    result = restore_wow_tokens(translated_masked, masked_info.tokens)
                    self._set_cached("EN->ES", raw, result)
                    self.last_latency_ms = (time.perf_counter() - start) * 1000.0
                    return result
            except Exception as exc:
                logger.warning("Error en motor local al traducir entrante: %s", exc)

        # 2. Si el proveedor es 'gemini' y tenemos cliente
        if self._client is not None:
            try:
                future = self._executor.submit(
                    self._call_gemini, INCOMING_SYSTEM_PROMPT, masked_info.masked
                )
                translated_masked = future.result(timeout=self.timeout_seconds)
                if translated_masked:
                    result = restore_wow_tokens(translated_masked, masked_info.tokens)
                    self._set_cached("EN->ES", raw, result)
                    self.last_latency_ms = (time.perf_counter() - start) * 1000.0
                    return result
            except FuturesTimeoutError:
                logger.warning(
                    "Timeout (> %.1fs) traduciendo mensaje entrante con Gemini.",
                    self.timeout_seconds,
                )
            except Exception as exc:
                logger.warning("Error en API al traducir mensaje entrante: %s", exc)

        # 3. Respaldo salvavidas en motor local si falló la API
        if self.local_engine.is_available():
            try:
                translated_masked = self.local_engine.translate_en_to_es(masked_info.masked)
                if translated_masked:
                    result = restore_wow_tokens(translated_masked, masked_info.tokens)
                    self._set_cached("EN->ES", raw, result)
                    self.last_latency_ms = (time.perf_counter() - start) * 1000.0
                    return result
            except Exception as exc:
                logger.warning("Error en motor local de respaldo: %s", exc)

        # 4. Fallback determinista offline
        fallback_masked = self._offline_fallback("EN->ES", masked_info.masked)
        if fallback_masked is not None:
            result = restore_wow_tokens(fallback_masked, masked_info.tokens)
            self._set_cached("EN->ES", raw, result)
            self.last_latency_ms = (time.perf_counter() - start) * 1000.0
            return result

        self.last_latency_ms = (time.perf_counter() - start) * 1000.0
        return raw

    def translate_outgoing(self, text: str) -> str:
        """Traduce un mensaje saliente escrito por el jugador (ES -> EN gamer natural)."""
        start = time.perf_counter()
        raw = text.strip()
        if not should_translate_message(raw):
            self.last_latency_ms = (time.perf_counter() - start) * 1000.0
            return raw

        cached = self._get_cached("ES->EN", raw)
        if cached is not None:
            self.last_latency_ms = (time.perf_counter() - start) * 1000.0
            return cached

        masked_info = mask_wow_tokens(raw)

        # 1. Si el proveedor configurado es 'local' o no hay cliente Gemini, usar LocalOfflineEngine
        if self.provider == "local" and self.local_engine.is_available():
            try:
                translated_masked = self.local_engine.translate_es_to_en(masked_info.masked)
                if translated_masked:
                    result = restore_wow_tokens(translated_masked, masked_info.tokens)
                    self._set_cached("ES->EN", raw, result)
                    self.last_latency_ms = (time.perf_counter() - start) * 1000.0
                    return result
            except Exception as exc:
                logger.warning("Error en motor local al traducir saliente: %s", exc)

        # 2. Si el proveedor es 'gemini' y tenemos cliente
        if self._client is not None:
            try:
                future = self._executor.submit(
                    self._call_gemini, OUTGOING_SYSTEM_PROMPT, masked_info.masked
                )
                translated_masked = future.result(timeout=self.timeout_seconds)
                if translated_masked:
                    result = restore_wow_tokens(translated_masked, masked_info.tokens)
                    self._set_cached("ES->EN", raw, result)
                    self.last_latency_ms = (time.perf_counter() - start) * 1000.0
                    return result
            except FuturesTimeoutError:
                logger.warning(
                    "Timeout (> %.1fs) traduciendo mensaje saliente con Gemini.",
                    self.timeout_seconds,
                )
            except Exception as exc:
                logger.warning("Error en API al traducir mensaje saliente: %s", exc)

        # 3. Respaldo salvavidas en motor local si falló la API
        if self.local_engine.is_available():
            try:
                translated_masked = self.local_engine.translate_es_to_en(masked_info.masked)
                if translated_masked:
                    result = restore_wow_tokens(translated_masked, masked_info.tokens)
                    self._set_cached("ES->EN", raw, result)
                    self.last_latency_ms = (time.perf_counter() - start) * 1000.0
                    return result
            except Exception as exc:
                logger.warning("Error en motor local de respaldo: %s", exc)

        # 4. Fallback determinista offline
        fallback_masked = self._offline_fallback("ES->EN", masked_info.masked)
        if fallback_masked is not None:
            result = restore_wow_tokens(fallback_masked, masked_info.tokens)
            self._set_cached("ES->EN", raw, result)
            self.last_latency_ms = (time.perf_counter() - start) * 1000.0
            return result

        self.last_latency_ms = (time.perf_counter() - start) * 1000.0
        return raw

    def translate_chat_image(
        self, png_bytes: bytes
    ) -> list[tuple[str, str, str, str]]:
        """
        Lee visualmente una captura de la caja de chat de WoW y devuelve una lista de
        tuplas (canal, jugador, mensaje_original, traduccion_es).
        """
        if not png_bytes or self._client is None:
            return []

        start = time.perf_counter()
        from google.genai import types

        candidates = [self.model] + [
            m for m in self.FALLBACK_MODELS if m != self.model
        ]
        models_to_try = [m for m in candidates if not self._is_model_quarantined(m)]
        if not models_to_try:
            models_to_try = candidates
        raw_text = ""
        for model_name in models_to_try:
            try:
                cfg_kwargs: dict[str, Any] = {
                    "temperature": 0.1,
                    "max_output_tokens": 220,
                }
                if "2.5" in model_name or "3.1" in model_name:
                    cfg_kwargs["thinking_config"] = types.ThinkingConfig(
                        thinking_budget=0
                    )
                else:
                    cfg_kwargs["thinking_config"] = types.ThinkingConfig(
                        thinking_level="MINIMAL"  # type: ignore[arg-type]
                    )

                resp = self._client.models.generate_content(
                    model=model_name,
                    contents=[
                        types.Part.from_bytes(
                            data=png_bytes, mime_type="image/png"
                        ),
                        VISION_CHAT_PROMPT,
                    ],
                    config=types.GenerateContentConfig(**cfg_kwargs),
                )
                raw_text = (resp.text or "").strip()
                break
            except Exception as exc:
                err_str = str(exc)
                if any(code in err_str for code in ("RESOURCE_EXHAUSTED", "429", "503", "UNAVAILABLE", "quota")):
                    duration = 1800.0 if ("429" in err_str or "quota" in err_str.lower() or "RESOURCE_EXHAUSTED" in err_str) else 180.0
                    self._quarantine_model(model_name, duration)
                logger.warning(
                    "Fallo vision con %s (%s), probando siguiente...",
                    model_name,
                    exc,
                )

        self.last_latency_ms = (time.perf_counter() - start) * 1000.0
        if not raw_text or raw_text.upper() == "NONE":
            return []

        extracted: list[tuple[str, str, str, str]] = []
        for line in raw_text.splitlines():
            line = line.strip()
            if not line or line.upper() == "NONE" or "|" not in line:
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 4:
                channel, sender, orig, trans = (
                    parts[0],
                    parts[1],
                    parts[2],
                    parts[3],
                )
                if sender and trans:
                    extracted.append((channel, sender, orig, trans))
            elif len(parts) == 3:
                channel, sender, trans = parts[0], parts[1], parts[2]
                if sender and trans:
                    extracted.append((channel, sender, trans, trans))
        return extracted


_default_translator: WoWTranslator | None = None


def get_translator() -> WoWTranslator:
    """Devuelve la instancia singleton del traductor."""
    global _default_translator
    if _default_translator is None:
        _default_translator = WoWTranslator()
    return _default_translator


def translate_incoming(text: str) -> str:
    """Función de nivel de módulo para traducir chat entrante (EN -> ES)."""
    return get_translator().translate_incoming(text)


def translate_outgoing(text: str) -> str:
    """Función de nivel de módulo para traducir chat saliente (ES -> EN)."""
    return get_translator().translate_outgoing(text)
