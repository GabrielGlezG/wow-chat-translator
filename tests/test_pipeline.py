"""Pruebas unitarias e integración para parser, translator, watcher y overlay (skills: simulate-wow-chat & eval-wow-translator)."""

from __future__ import annotations

from pathlib import Path
import time

from PySide6.QtWidgets import QApplication
import pytest

from src.overlay import ChatOverlay
from src.translator import (
    WoWTranslator,
    mask_wow_tokens,
    restore_wow_tokens,
    should_translate_message,
)
from src.watcher import (
    ChatLogWatcher,
    ChatMessage,
    is_likely_npc_sender,
    parse_chat_line,
)
from tests.sim_chat import SIMULATED_MESSAGES, format_wow_log_line, run_simulation


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app  # type: ignore[return-value]


def test_mask_and_restore_wow_hyperlinks() -> None:
    raw = (
        "WTS |cffa335ee|Hitem:19019::::::::80:::::|h[Thunderfury, Blessed Blade of the Windseeker]|h|r "
        "focus {rt8} and {skull}!"
    )
    masked_info = mask_wow_tokens(raw)
    assert masked_info.has_conversational_text is True
    assert "__WOW_TOKEN_0__" in masked_info.masked
    assert "__WOW_TOKEN_1__" in masked_info.masked
    assert "__WOW_TOKEN_2__" in masked_info.masked

    restored = restore_wow_tokens(masked_info.masked, masked_info.tokens)
    assert restored == raw


def test_pure_quest_or_item_link_is_not_translated() -> None:
    pure_quest = "[[40C] Salvidentes sospechosos]"
    assert should_translate_message(pure_quest) is False

    pure_item = "|cffa335ee|Hitem:19019::::::::80:::::|h[Thunderfury]|h|r"
    assert should_translate_message(pure_item) is False

    only_numbers = "12345 !!!"
    assert should_translate_message(only_numbers) is False


def test_watcher_filters_channels_and_links() -> None:
    results = [
        parse_chat_line(format_wow_log_line(msg))
        for msg in SIMULATED_MESSAGES
    ]
    valid_messages = [r for r in results if r is not None]

    # De los 7 mensajes simulados:
    # - 5 de [Grupo] con texto conversacional deben pasar
    # - 1 de [Comercio - Ciudad] debe ser filtrado
    # - 1 de [Grupo] con solo link [[40C] Salvidentes sospechosos] debe ser filtrado para ahorrar tokens
    assert len(valid_messages) == 5
    channels = {m.channel for m in valid_messages}
    assert channels == {"Grupo"}
    senders = [m.sender for m in valid_messages]
    assert "Spammer" not in senders
    assert "Aptinstall Totem" not in senders

    # Verificar formato real de WoW Forever con |Hchannel:PARTY|h[Grupo]|h
    real_wow_forever_line = (
        "11/21 10:21:09.043  |Hchannel:PARTY|h[Grupo]|h Hairy Warrior: wtf, wheres trhe heals"
    )
    parsed_real = parse_chat_line(real_wow_forever_line)
    assert parsed_real is not None
    assert parsed_real.channel == "Grupo"
    assert parsed_real.sender == "Hairy Warrior"
    assert parsed_real.original_text == "wtf, wheres trhe heals"


def test_eval_wow_translator_bidirectional_and_latency() -> None:
    translator = WoWTranslator()

    incoming_cases = [
        ("is that it myu %^&* bugge dwhen i DCs", ["buge", "dc", "desconect"]),
        ("wait sec, healer oom, dont pull", ["healer", "maná", "mana", "oom", "puleen", "pull"]),
        ("mb, fat fingered blink", ["mala mía", "blink", "traslación"]),
    ]

    for source, expected_keywords in incoming_cases:
        start = time.perf_counter()
        translated = translator.translate_incoming(source)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        assert elapsed_ms < 3000.0, f"Latencia excesiva: {elapsed_ms:.1f}ms"
        assert "\n" not in translated
        assert not (translated.startswith('"') and translated.endswith('"'))
        assert any(
            kw.lower() in translated.lower() for kw in expected_keywords
        ), f"Traducción inesperada para {source!r}: {translated!r}"

    outgoing_cases = [
        ("esperen un poco que estoy sin mana", ["oom", "sec", "wait", "mana"]),
        ("me pegó un lagazo terrible, perdón", ["lag", "sorry", "mb"]),
        ("¿alguien necesita este ítem o le doy codicia?", ["need", "greed"]),
    ]

    for source, expected_keywords in outgoing_cases:
        start = time.perf_counter()
        translated = translator.translate_outgoing(source)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        assert elapsed_ms < 3000.0, f"Latencia excesiva: {elapsed_ms:.1f}ms"
        assert "\n" not in translated
        assert not (translated.startswith('"') and translated.endswith('"'))
        assert any(
            kw.lower() in translated.lower() for kw in expected_keywords
        ), f"Traducción inesperada para {source!r}: {translated!r}"


def test_end_to_end_simulation_with_overlay(
    tmp_path: Path, qapp: QApplication
) -> None:
    mock_log = tmp_path / "mock_WoWChatLog.txt"
    cfg_path = tmp_path / "config.json"

    run_simulation(log_path=mock_log, delay_seconds=0.0, truncate=True)

    config = {
        "wow_chat_log_path": str(mock_log),
        "player_name": "",
        "overlay": {
            "x": 40,
            "y": 500,
            "width": 500,
            "height": 200,
            "max_messages": 6,
        },
    }

    translator = WoWTranslator(config=config)
    overlay = ChatOverlay(config=config, config_path=cfg_path)
    watcher = ChatLogWatcher(
        config=config,
        translator=translator,
        read_from_start=True,
    )
    watcher.message_ready.connect(overlay.add_message)

    for line in mock_log.read_text(encoding="utf-8").splitlines():
        watcher.process_raw_line(line)

    qapp.processEvents()

    displayed: list[ChatMessage] = overlay.messages
    assert len(displayed) == 5
    assert all(m.channel == "Grupo" for m in displayed)
    assert any(w in displayed[0].translated_text.lower() for w in ("fatal", "asco", "mal", "horrible"))
    assert any(w in displayed[1].translated_text.lower() for w in ("loot", "botín", "llevé"))
    assert any(w in displayed[2].translated_text.lower() for w in ("buge", "dc", "desconect"))
    assert "dc" in displayed[3].translated_text.lower()

    # Verificar alternancia de modo mover/redimensionar y guardado en config.json
    assert overlay.move_mode is False
    overlay.toggle_move_mode()
    assert overlay.move_mode is True
    overlay.toggle_move_mode()
    assert overlay.move_mode is False

    # Verificar minimizar y maximizar dentro del juego y pestañas
    assert overlay.is_minimized_in_game is False
    overlay.toggle_minimize_in_game()
    assert overlay.is_minimized_in_game is True
    overlay.toggle_minimize_in_game()
    assert overlay.is_minimized_in_game is False

    overlay.switch_tab(1)
    overlay.switch_tab(2)
    overlay.switch_tab(0)
    overlay.scroll_chat_by(-50)
    overlay.scroll_to_bottom()

    assert cfg_path.exists()
    overlay.close()


def test_strict_npc_filtering() -> None:
    # Jugadores reales de WoW Forever (1 o 2 palabras, sin artículos ni comas)
    assert is_likely_npc_sender("Hairy Warrior") is False
    assert is_likely_npc_sender("Ruby Daçherry") is False
    assert is_likely_npc_sender("Warpscream Sickman") is False
    assert is_likely_npc_sender("Aptinstall Totem") is False
    assert is_likely_npc_sender("Arthas-Ragnaros") is False
    assert is_likely_npc_sender("Amigo BNet") is False
    assert is_likely_npc_sender("Requiem Egothic") is False

    # NPCs del juego (comas, títulos, >2 palabras, artículos)
    assert is_likely_npc_sender("Min'loth, la Serpiente") is True
    assert is_likely_npc_sender("Guardia de Orgrimmar") is True
    assert is_likely_npc_sender("High Inquisitor Whitemane") is True
    assert is_likely_npc_sender("Lord Tirion Fordring") is True
    assert is_likely_npc_sender("Hostigador escamasalada", "¡Hostigador escamasalada intenta huir despavorido!") is True

    # Susurro de amigo Battle.net (|Ks...|k) debe ser aceptado y parseado como Amigo BNet
    bnet_line = "11/21 15:27:30.568  |Ks7|k susurra: what are u doing?"
    parsed_bnet = parse_chat_line(bnet_line)
    assert parsed_bnet is not None
    assert parsed_bnet.sender == "Amigo BNet"
    assert parsed_bnet.channel == "Susurro"
    assert parsed_bnet.original_text == "what are u doing?"

    # Diálogos y gritos de NPCs en español deben ser ignorados por parse_chat_line
    npc_line = "11/21 10:23:27.103  Min'loth, la Serpiente grita: ¡Por Var'gazul!"
    assert parse_chat_line(npc_line) is None

    calder_line = "11/21 15:29:01.870  Calder Gray grita: Sí... ¡SÍ! ¡¡VIVE!!"
    assert parse_chat_line(calder_line) is None

    abom_line = "11/21 15:28:24.002  Abominación incompleta grita: ¡¡UUUUUuuuuurrrgh!!"
    assert parse_chat_line(abom_line) is None


def test_model_quarantine() -> None:
    translator = WoWTranslator()
    assert translator._is_model_quarantined("dummy-model") is False
    translator._quarantine_model("dummy-model", 300.0)
    assert translator._is_model_quarantined("dummy-model") is True


def test_wow_window_tracker_state() -> None:
    from src.window_tracker import WoWWindowTracker, WoWWindowState
    tracker = WoWWindowTracker()
    state = tracker.get_state()
    assert isinstance(state, WoWWindowState)
    assert hasattr(state, "running")
    assert hasattr(state, "minimized")
    assert hasattr(state, "visible")
    assert hasattr(state, "foreground")
    assert hasattr(state, "our_foreground")
    assert hasattr(state, "rect")
    assert hasattr(state, "delta")
    assert isinstance(state.delta, tuple)
    assert len(state.delta) == 2


def test_overlay_window_anchoring_and_tracking(qapp: QApplication, tmp_path: Path) -> None:
    cfg_path = tmp_path / "config.json"
    cfg = {
        "overlay": {
            "tab_x": 100,
            "tab_y": 200,
            "chat_x": 100,
            "chat_y": 200,
            "auto_hide_on_minimize": True,
            "only_visible_with_wow": True,
        }
    }
    overlay = ChatOverlay(config=cfg, config_path=cfg_path)
    assert overlay.auto_hide_on_minimize is True
    assert overlay.only_visible_with_wow is True

    # Test toggles
    overlay._on_toggle_auto_hide(False)
    assert overlay.auto_hide_on_minimize is False
    assert "OFF" in overlay.btn_auto_hide.text()

    overlay._on_toggle_only_wow(False)
    assert overlay.only_visible_with_wow is False
    assert "OFF" in overlay.btn_only_wow.text()

    # Test window movement tracking
    init_tab_x = overlay._tab_x
    init_tab_y = overlay._tab_y
    overlay.on_wow_window_moved(25, 15, (50, 50, 1920, 1080))
    assert overlay._tab_x == init_tab_x + 25
    assert overlay._tab_y == init_tab_y + 15
    assert overlay._chat_x == 125
    assert overlay._chat_y == 215

    overlay.close()
