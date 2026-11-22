"""
Script de compilación y empaquetado para distribución pública de WoW Chat Translator.
Construye el ejecutable standalone con PyInstaller e integra los modelos MarianMT int8
generando WoWChatTranslator-vX.X.X-Portable.zip para GitHub Releases.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = PROJECT_ROOT / "dist"
SPEC_FILE = PROJECT_ROOT / "WoWChatTranslator.spec"


def get_version() -> str:
    from scripts.package_addon import get_addon_version
    try:
        return get_addon_version()
    except Exception:
        return "1.0.0"


def compute_sha256(file_path: Path) -> str:
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def build_executable() -> bool:
    print("🚀 Iniciando compilación con PyInstaller...")
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        str(SPEC_FILE),
        "--clean",
        "--noconfirm",
    ]
    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    if result.returncode != 0:
        print(f"❌ Error en la compilación con PyInstaller (código {result.returncode})")
        return False

    exe_path = DIST_DIR / "WoWChatTranslator" / "WoWChatTranslator.exe"
    if not exe_path.exists():
        print(f"❌ No se encontró el ejecutable en {exe_path}")
        return False

    print(f"✅ Ejecutable generado con éxito: {exe_path}")
    return True


def package_portable_zip() -> Path | None:
    version = get_version()
    output_dir = DIST_DIR / "WoWChatTranslator"
    if not output_dir.exists():
        print(f"❌ No existe la carpeta {output_dir}")
        return None

    zip_filename = f"WoWChatTranslator-v{version}-Portable.zip"
    zip_path = DIST_DIR / zip_filename
    print(f"📦 Creando archivo portable comprimido: {zip_path}...")

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for root_path, _, files in os.walk(output_dir):
            rpath = Path(root_path)
            for f in files:
                full_f = rpath / f
                arcname = full_f.relative_to(output_dir.parent)
                zf.write(full_f, arcname)

    sha256_hash = compute_sha256(zip_path)
    size_mb = zip_path.stat().st_size / (1024.0 * 1024.0)

    print(f"✅ Paquete Portable generado con éxito!")
    print(f"   Archivo: {zip_path.name}")
    print(f"   Tamaño: {size_mb:.2f} MB")
    print(f"   SHA-256: {sha256_hash}")

    hash_file = DIST_DIR / f"SHA256SUMS-v{version}.txt"
    with open(hash_file, "a", encoding="utf-8") as hf:
        hf.write(f"{sha256_hash}  {zip_filename}\n")

    return zip_path


def main() -> int:
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    if not build_executable():
        return 1
    zip_p = package_portable_zip()
    return 0 if zip_p else 1


if __name__ == "__main__":
    sys.exit(main())
