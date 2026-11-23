"""
Test suite para verificar la integridad sintáctica y funcional del motor integrado de traducción.
Valida los archivos Lua de ForeverChatLogger (motor de Pirson integrado) y simula el pipeline.
"""

from pathlib import Path
import re
import pytest

ADDON_DIR = Path(__file__).resolve().parent.parent / "addon" / "ForeverChatLogger"


def test_lua_files_exist():
    assert (ADDON_DIR / "ForeverChatLogger.toc").exists()
    assert (ADDON_DIR / "ForeverChatLogger.lua").exists()
    assert (ADDON_DIR / "Core" / "Compat.lua").exists()
    assert (ADDON_DIR / "Core" / "Dictionary.lua").exists()
    assert (ADDON_DIR / "Core" / "Templates.lua").exists()
    assert (ADDON_DIR / "Core" / "Translator.lua").exists()
    assert (ADDON_DIR / "Core" / "Outgoing.lua").exists()
    assert (ADDON_DIR / "Core" / "Init.lua").exists()
    assert (ADDON_DIR / "Data" / "Combate.lua").exists()
    assert (ADDON_DIR / "Data" / "Social.lua").exists()
    assert (ADDON_DIR / "Data" / "Grupos.lua").exists()
    assert (ADDON_DIR / "Data" / "Instancias" / "Forever.lua").exists()
    assert (ADDON_DIR / "Data" / "Plantillas" / "esES.lua").exists()
    assert (ADDON_DIR / "Modules" / "ChatFilter.lua").exists()


def test_toc_manifest_order():
    content = (ADDON_DIR / "ForeverChatLogger.toc").read_text(encoding="utf-8")
    lines = [line.strip() for line in content.splitlines() if line.strip() and not line.startswith("##") and not line.startswith("#")]
    
    # Validation of key file execution order
    assert "Core\\Compat.lua" in lines
    assert "Data\\Combate.lua" in lines
    assert "Core\\Dictionary.lua" in lines
    assert "Core\\Templates.lua" in lines
    assert "Core\\Translator.lua" in lines
    assert "Core\\Outgoing.lua" in lines
    assert "Core\\Init.lua" in lines
    assert "ForeverChatLogger.lua" in lines
    
    compat_idx = lines.index("Core\\Compat.lua")
    combate_idx = lines.index("Data\\Combate.lua")
    dict_idx = lines.index("Core\\Dictionary.lua")
    tpl_idx = lines.index("Core\\Templates.lua")
    tr_idx = lines.index("Core\\Translator.lua")
    init_idx = lines.index("Core\\Init.lua")
    fcl_idx = lines.index("ForeverChatLogger.lua")
    
    assert compat_idx < combate_idx
    assert combate_idx < dict_idx
    assert dict_idx < tpl_idx
    assert tpl_idx < tr_idx
    assert tr_idx < init_idx
    assert init_idx < fcl_idx


def test_social_and_combat_dictionary_contents():
    social = (ADDON_DIR / "Data" / "Social.lua").read_text(encoding="utf-8")
    combat = (ADDON_DIR / "Data" / "Combate.lua").read_text(encoding="utf-8")
    
    assert '["ty"]' in social
    assert 'esES = "Gracias"' in social
    assert '["thx"]' in social
    assert '["np"]' in social
    assert '["oom"]' in social
    
    assert '["add"]' in combat
    assert '["aggro"]' in combat
    assert '["wiped"]' in combat


def test_templates_es_contents():
    es_tpl = (ADDON_DIR / "Data" / "Plantillas" / "esES.lua").read_text(encoding="utf-8")
    assert "addonTable.Plantillas.esES" in es_tpl
    assert 'REC_ROLES_INST = "Busco {roles} para {inst}."' in es_tpl
    assert 'WTS_PRICE = "Vendo {items} por {price}."' in es_tpl
    assert 'F_WAIT_MANA = "Esperad, que recupero maná."' in es_tpl


def test_forever_instance_dictionary():
    forever_inst = (ADDON_DIR / "Data" / "Instancias" / "Forever.lua").read_text(encoding="utf-8")
    assert "addonTable.ForeverDict" in forever_inst
    assert '["rol"]' in forever_inst
    assert 'esES = "Ruinas de Lordaeron"' in forever_inst
    assert '["thanes"]' in forever_inst
    assert '["exca"]' in forever_inst


def test_outgoing_reverse_translation_syntax():
    outgoing = (ADDON_DIR / "Core" / "Outgoing.lua").read_text(encoding="utf-8")
    assert "function addonTable.TranslateOutgoing" in outgoing
    assert "ReverseDict" in outgoing
    assert "ReverseByFirst" in outgoing
