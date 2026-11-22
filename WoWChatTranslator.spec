# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
import sys

block_cipher = None
PROJECT_ROOT = Path(SPECPATH).resolve() if 'SPECPATH' in globals() else Path('.').resolve()

added_files = [
    (str(PROJECT_ROOT / 'models'), 'models'),
    (str(PROJECT_ROOT / 'data' / 'wow_slang.json'), 'data'),
    (str(PROJECT_ROOT / 'addon' / 'ForeverChatLogger'), 'addon/ForeverChatLogger'),
    (str(PROJECT_ROOT / 'config.json'), '.'),
    (str(PROJECT_ROOT / 'assets'), 'assets'),
]

a = Analysis(
    ['run.py'],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=added_files,
    hiddenimports=[
        'ctranslate2',
        'sentencepiece',
        'tokenizers',
        'winocr',
        'pyperclip',
        'psutil',
        'win32gui',
        'win32con',
        'win32process',
        'win32api',
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'unittest', 'IPython', 'notebook', 'tornado'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='WoWChatTranslator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(PROJECT_ROOT / 'assets' / 'icon.ico'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='WoWChatTranslator',
)
