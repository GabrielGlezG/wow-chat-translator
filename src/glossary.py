"""
Glosario especializado de jerga, acrónimos y abreviaturas de World of Warcraft.
Carga las reglas desde data/wow_slang.json y las aplica antes y después del modelo de traducción.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
import re
from typing import Any

logger = logging.getLogger(__name__)

from src.config import PROJECT_ROOT
DEFAULT_GLOSSARY_PATH = PROJECT_ROOT / "data" / "wow_slang.json"


def _compile_patterns(raw_list: list[dict[str, str]]) -> list[tuple[re.Pattern[str], str]]:
    """Compila una lista de diccionarios {'pattern': '...', 'replace': '...'} en tuplas (Pattern, replace)."""
    compiled: list[tuple[re.Pattern[str], str]] = []
    for item in raw_list:
        pat_str = item.get("pattern", "")
        repl = item.get("replace", "")
        if not pat_str:
            continue
        try:
            compiled.append((re.compile(pat_str, re.IGNORECASE), repl))
        except re.error as err:
            logger.warning("Error compilando regex de jerga '%s': %s", pat_str, err)
    return compiled


class WoWSlangManager:
    """Administrador de glosario y normalización de jerga de WoW."""

    def __init__(self, glossary_path: Path | str = DEFAULT_GLOSSARY_PATH) -> None:
        self.glossary_path = Path(glossary_path)
        self.fast_exact: dict[str, str] = {}
        self.slang_en_to_es: list[tuple[re.Pattern[str], str]] = []
        self.post_corrections_es: list[tuple[re.Pattern[str], str]] = []
        self.slang_es_to_en: list[tuple[re.Pattern[str], str]] = []
        self.post_corrections_en: list[tuple[re.Pattern[str], str]] = []
        self.dungeons: dict[str, str] = {}
        self.load()

    def load(self) -> bool:
        """Carga o recarga data/wow_slang.json desde disco."""
        if not self.glossary_path.exists():
            logger.warning(
                "Archivo de jerga no encontrado en %s. Usando valores básicos.",
                self.glossary_path,
            )
            self._load_fallback()
            return False

        try:
            with open(self.glossary_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.fast_exact = {
                k.lower(): v for k, v in data.get("fast_exact_replacements", {}).items()
            }
            self.dungeons = {
                k.lower(): v for k, v in data.get("dungeons_and_raids", {}).items()
            }
            # Unir mazmorras al fast_exact para respuestas inmediatas si alguien solo escribe "brd" o "ubrs"
            for k, v in self.dungeons.items():
                if k not in self.fast_exact:
                    self.fast_exact[k] = v

            self.slang_en_to_es = _compile_patterns(data.get("slang_en_to_es", []))
            self.post_corrections_es = _compile_patterns(
                data.get("post_corrections_es", [])
            )
            self.slang_es_to_en = _compile_patterns(data.get("slang_es_to_en", []))
            self.post_corrections_en = _compile_patterns(
                data.get("post_corrections_en", [])
            )

            # Agregar patrones de mazmorras como palabras completas para EN -> ES
            for acr, name in self.dungeons.items():
                pat = re.compile(rf"\b{re.escape(acr)}\b", re.IGNORECASE)
                self.slang_en_to_es.append((pat, name))

            logger.info(
                "Glosario de WoW cargado exitosamente desde %s (%d exactos, %d reglas EN->ES, %d ES->EN)",
                self.glossary_path.name,
                len(self.fast_exact),
                len(self.slang_en_to_es),
                len(self.slang_es_to_en),
            )
            return True
        except Exception as exc:
            logger.exception("Error al parsear %s: %s", self.glossary_path, exc)
            self._load_fallback()
            return False

    def _load_fallback(self) -> None:
        """Reglas de respaldo en caso de ausencia o fallo de lectura del archivo JSON."""
        self.fast_exact = {
            "oom": "sin maná (OOM)",
            "dcd": "se desconectó (DC)",
            "dc": "desconectado (DC)",
            "ty": "gracias",
            "thx": "gracias",
            "np": "de nada",
            "mb": "mala mía",
            "brb": "ya vuelvo (BRB)",
            "afk": "ausente (AFK)",
            "gg": "buen juego (GG)",
            "rdy": "listo",
        }
        self.slang_en_to_es = [
            (re.compile(r"\bhealer\s+oom\b", re.IGNORECASE), "healer sin maná (OOM)"),
            (re.compile(r"\boom\b", re.IGNORECASE), "sin maná"),
            (re.compile(r"\bdon'?t\s+pull\b", re.IGNORECASE), "no puleen"),
            (re.compile(r"\bmb\b", re.IGNORECASE), "mala mía"),
            (re.compile(r"\bwipe\b", re.IGNORECASE), "wipe"),
        ]
        self.post_corrections_es = [
            (re.compile(r"\bno tires\b|\bno jales\b", re.IGNORECASE), "no puleen"),
            (re.compile(r"\btirar\b|\bjalar\b", re.IGNORECASE), "pulear"),
            (re.compile(r"\bsanador\b", re.IGNORECASE), "healer"),
        ]
        self.slang_es_to_en = [
            (re.compile(r"\bsin\s+man[aá]\b", re.IGNORECASE), "oom"),
            (re.compile(r"\blagazo\b", re.IGNORECASE), "huge lag spike"),
            (re.compile(r"\bcodicia\b", re.IGNORECASE), "greed"),
            (re.compile(r"\bnecesidad\b", re.IGNORECASE), "need"),
            (re.compile(r"\bno\s+puleen\b", re.IGNORECASE), "dont pull"),
        ]
        self.post_corrections_en = []

    def get_fast_exact(self, text: str) -> str | None:
        """Comprueba si el texto completo coincide de forma exacta con un término rápido (< 0.1ms)."""
        clean = text.strip().lower().rstrip("!?.")
        return self.fast_exact.get(clean)

    def preprocess_incoming(self, text: str) -> str:
        """Aplica sustitución de jerga y corrección de censura antes de traducir EN -> ES."""
        result = text
        for pat, repl in self.slang_en_to_es:
            result = pat.sub(repl, result)
        return result

    def postprocess_incoming(self, text: str) -> str:
        """Corrige traducciones literales o errores de estilo tras traducir al español."""
        result = text
        for pat, repl in self.post_corrections_es:
            result = pat.sub(repl, result)
        return result

    def preprocess_outgoing(self, text: str) -> str:
        """Aplica sustitución de jerga gamer antes de traducir ES -> EN."""
        result = text
        for pat, repl in self.slang_es_to_en:
            result = pat.sub(repl, result)
        return result

    def postprocess_outgoing(self, text: str) -> str:
        """Corrige traducciones literales tras traducir al inglés gamer."""
        result = text
        for pat, repl in self.post_corrections_en:
            result = pat.sub(repl, result)
        return result


# Instancia única singleton para todo el proyecto
_global_glossary: WoWSlangManager | None = None


def get_slang_manager(glossary_path: Path | str = DEFAULT_GLOSSARY_PATH) -> WoWSlangManager:
    """Devuelve la instancia global del gestor de jerga de WoW."""
    global _global_glossary
    if _global_glossary is None:
        _global_glossary = WoWSlangManager(glossary_path=glossary_path)
    return _global_glossary
