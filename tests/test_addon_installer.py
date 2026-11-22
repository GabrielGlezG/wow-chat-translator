import shutil
from pathlib import Path
import pytest
from src.addon_installer import (
    find_wow_addon_directory,
    is_addon_installed,
    install_addon_to_wow,
    get_bundled_addon_source,
    ADDON_FOLDER_NAME,
)


def test_get_bundled_addon_source():
    source = get_bundled_addon_source()
    assert source.exists()
    assert (source / f"{ADDON_FOLDER_NAME}.toc").exists()
    assert (source / f"{ADDON_FOLDER_NAME}.lua").exists()


def test_find_wow_addon_directory_with_custom_log(tmp_path):
    fake_wow = tmp_path / "World of Warcraft"
    fake_logs = fake_wow / "Logs"
    fake_logs.mkdir(parents=True)
    fake_log_file = fake_logs / "WoWChatLog.txt"
    fake_log_file.write_text("test", encoding="utf-8")

    addons_dir = find_wow_addon_directory(str(fake_log_file))
    assert addons_dir is not None
    assert addons_dir == fake_wow / "Interface" / "AddOns"
    assert addons_dir.exists()


def test_is_addon_installed_and_install(tmp_path):
    fake_wow = tmp_path / "WoW_Test"
    fake_addons = fake_wow / "Interface" / "AddOns"
    fake_addons.mkdir(parents=True)

    # Initial check: not installed
    assert not is_addon_installed(addons_dir=fake_addons)

    # Install
    ok, msg = install_addon_to_wow(addons_dir=fake_addons)
    assert ok is True
    assert "éxito" in msg

    # Now it should be installed
    assert is_addon_installed(addons_dir=fake_addons)
    assert (fake_addons / ADDON_FOLDER_NAME / f"{ADDON_FOLDER_NAME}.toc").exists()
    assert (fake_addons / ADDON_FOLDER_NAME / f"{ADDON_FOLDER_NAME}.lua").exists()


def test_install_fails_gracefully_when_no_directory():
    ok, msg = install_addon_to_wow(addons_dir=None, custom_log_path="C:/non_existent_path_xyz/Logs/WoWChatLog.txt")
    # Should handle gracefully without raising unhandled exceptions
    assert isinstance(ok, bool)
    assert isinstance(msg, str)
