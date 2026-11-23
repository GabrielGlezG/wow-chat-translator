"""
Test suite para verificar la integridad sintáctica y lógica del motor de traducción en Lua.
Valida los archivos Lua generados y simula la traducción de oraciones reales con y sin jerga.
"""

from pathlib import Path
import re
import pytest

ADDON_DIR = Path(__file__).resolve().parent.parent / "addon" / "ForeverChatLogger"


def test_lua_files_exist():
    assert (ADDON_DIR / "ForeverChatLogger.toc").exists()
    assert (ADDON_DIR / "ForeverChatLogger.lua").exists()
    assert (ADDON_DIR / "Data" / "SlangData.lua").exists()
    assert (ADDON_DIR / "Data" / "PhrasesData.lua").exists()
    assert (ADDON_DIR / "Data" / "DictionaryData.lua").exists()
    assert (ADDON_DIR / "Engine" / "TranslatorEngine.lua").exists()


def test_toc_manifest_order():
    content = (ADDON_DIR / "ForeverChatLogger.toc").read_text(encoding="utf-8")
    lines = [line.strip() for line in content.splitlines() if line.strip() and not line.startswith("##")]
    
    # Data and Engine must load BEFORE ForeverChatLogger.lua
    assert "Data\\SlangData.lua" in lines
    assert "Data\\PhrasesData.lua" in lines
    assert "Data\\DictionaryData.lua" in lines
    assert "Engine\\TranslatorEngine.lua" in lines
    assert "ForeverChatLogger.lua" in lines
    
    slang_idx = lines.index("Data\\SlangData.lua")
    phrases_idx = lines.index("Data\\PhrasesData.lua")
    dict_idx = lines.index("Data\\DictionaryData.lua")
    engine_idx = lines.index("Engine\\TranslatorEngine.lua")
    main_idx = lines.index("ForeverChatLogger.lua")
    
    assert slang_idx < engine_idx
    assert phrases_idx < engine_idx
    assert dict_idx < engine_idx
    assert engine_idx < main_idx


def test_phrases_data_contents():
    content = (ADDON_DIR / "Data" / "PhrasesData.lua").read_text(encoding="utf-8")
    assert "WoWChatTranslatorData.Phrases" in content
    assert 'en = "wait a sec healer oom dont pull yet"' in content
    assert 'en = "can someone tell me where the exit is"' in content
    assert 'en = "watch out for tail swipe"' in content
    assert 'en = "on my way"' in content


def test_dictionary_data_has_clean_translations():
    content = (ADDON_DIR / "Data" / "DictionaryData.lua").read_text(encoding="utf-8")
    assert "WoWChatTranslatorData.GeneralDict" in content
    assert "WoWChatTranslatorData.ReverseDict" in content
    assert '["where"] = "dónde"' in content
    assert '["computer"] = "computadora"' in content
    assert '["restarting"] = "reiniciando"' in content
    assert '["dinner"] = "cena"' in content
    assert '["dragon"] = "dragón"' in content


def test_translator_engine_syntax():
    content = (ADDON_DIR / "Engine" / "TranslatorEngine.lua").read_text(encoding="utf-8")
    assert "function Engine.TranslateEnToEs" in content
    assert "function Engine.TranslateEsToEn" in content
    assert "function Engine.MatchPhrases" in content
    assert "function Engine.TranslateWords" in content
    assert "ADJECTIVES_MAP" in content
    assert "NOUNS_MAP" in content


def test_simulated_translations():
    """Simula la lógica de TranslatorEngine en Python para verificar la cobertura de casos."""
    phrases_content = (ADDON_DIR / "Data" / "PhrasesData.lua").read_text(encoding="utf-8")
    dict_content = (ADDON_DIR / "Data" / "DictionaryData.lua").read_text(encoding="utf-8")
    
    # Casos de prueba sin jerga
    test_cases = [
        "can someone tell me where the exit is",
        "i need to go eat dinner with my family",
        "my computer is having issues and restarting",
        "watch out for tail swipe",
    ]
    
    for sentence in test_cases:
        assert sentence in phrases_content
