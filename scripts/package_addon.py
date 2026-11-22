"""
Script de empaquetado oficial del Addon ForeverChatLogger para CurseForge.
Genera dist/ForeverChatLogger-vX.X.X.zip con la estructura de carpetas exacta
requerida por los servidores de validación de CurseForge y Wago.io.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
import re
import sys
import zipfile

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ADDON_SRC_DIR = PROJECT_ROOT / "addon" / "ForeverChatLogger"
DIST_DIR = PROJECT_ROOT / "dist"


def get_addon_version() -> str:
    """Extrae la versión del archivo .toc."""
    toc_path = ADDON_SRC_DIR / "ForeverChatLogger.toc"
    if not toc_path.exists():
        raise FileNotFoundError(f"No se encontró {toc_path}")

    content = toc_path.read_text(encoding="utf-8")
    match = re.search(r"##\s*Version:\s*([0-9\.]+)", content)
    if match:
        return match.group(1).strip()
    return "1.0.0"


def compute_sha256(file_path: Path) -> str:
    """Calcula el hash SHA-256 del archivo empaquetado."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def package_addon() -> Path:
    """Crea el archivo ZIP para subir a CurseForge."""
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    version = get_addon_version()
    zip_name = f"ForeverChatLogger-v{version}.zip"
    zip_path = DIST_DIR / zip_name

    print(f"📦 Empaquetando Addon ForeverChatLogger v{version}...")

    # Crear ZIP con carpeta raíz ForeverChatLogger/
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for item in ADDON_SRC_DIR.iterdir():
            if item.name.startswith(".") or item.suffix in (".pyc", ".bak"):
                continue
            arcname = f"ForeverChatLogger/{item.name}"
            zf.write(item, arcname)
            print(f"  + {arcname} ({item.stat().st_size} bytes)")

    sha256_hash = compute_sha256(zip_path)
    file_size_kb = zip_path.stat().st_size / 1024.0

    print(f"\n✅ ZIP generado con éxito en: {zip_path}")
    print(f"   Tamaño: {file_size_kb:.1f} KB")
    print(f"   SHA-256: {sha256_hash}")

    # Generar notas de publicación para CurseForge
    release_notes_path = DIST_DIR / f"CurseForge_Release_Notes_v{version}.md"
    release_notes_content = f"""# WoW Chat Translator (ForeverChatLogger) v{version}

### 🇪🇸 Español
**ForeverChatLogger** es el addon ligero para World of Warcraft (compatible con WoW Forever, WotLK 3.3.5a y clientes Classic/Retail) que activa y vacía en tiempo real `/chatlog` a disco para permitir la traducción instantánea de chat mediante la aplicación de escritorio **WoW Chat Translator**.

#### Características:
- **100% Legal y Seguro (Anti-Cheat):** No toca memoria, no inyecta DLLs y no interactúa con procesos externos.
- **Vaciado inteligente:** Debouncer a los 0.20s de cada evento de chat para entrega instantánea de mensajes.
- **Multiversión:** Compatible con `C_Timer` y fallback automático con frame `OnUpdate`.
- **Comandos dentro del juego:** `/translator status`, `/translator on`, `/translator off`, `/translator flush`.

> 💡 **Nota importante:** Para ver las traducciones dentro del juego necesitas ejecutar la aplicación de escritorio gratuita y 100% offline **WoW Chat Translator**:
> [Descargar WoW Chat Translator en GitHub](https://github.com/GabrielGlezG/wow-chat-translator/releases)

---

### 🇬🇧 English
**ForeverChatLogger** is the companion lightweight World of Warcraft Addon that maintains and debounces `/chatlog` to disk in real-time, enabling instantaneous offline translation via the **WoW Chat Translator** desktop overlay application.

- **File:** `{zip_name}`
- **SHA-256:** `{sha256_hash}`
- **Size:** `{file_size_kb:.1f} KB`
"""
    release_notes_path.write_text(release_notes_content, encoding="utf-8")
    print(f"📝 Notas de publicación generadas en: {release_notes_path}")

    return zip_path


if __name__ == "__main__":
    package_addon()
