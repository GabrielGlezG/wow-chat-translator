# WoW Chat Translator (ForeverChatLogger)

<p align="center">
  <img src="assets/icon.png" alt="WoW Chat Translator Logo" width="128" height="128"/>
</p>

<p align="center">
  <b>Traductor de Chat en Tiempo Real para World of Warcraft (100% Offline, Gratuito y Seguro)</b><br>
  <i>Comunícate fluidamente con la comunidad internacional de habla inglesa sin salir del juego.</i>
</p>

<p align="center">
  <a href="https://curseforge.com/wow/addons/foreverchatlogger"><img src="https://img.shields.io/badge/CurseForge-ForeverChatLogger-f16436.svg" alt="CurseForge"/></a>
  <a href="https://github.com/GabrielGlezG/wow-chat-translator/releases"><img src="https://img.shields.io/github/v/release/GabrielGlezG/wow-chat-translator?color=blue&label=App%20Release" alt="GitHub Release"/></a>
  <a href="#cumplimiento-anti-cheat"><img src="https://img.shields.io/badge/Anti--Cheat-100%25%20Legal-brightgreen.svg" alt="Anti-Cheat"/></a>
  <a href="#licencia"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License"/></a>
</p>

---

## 🇪🇸 Descripción en Español

**WoW Chat Translator** es una solución integral diseñada para jugadores hispanohablantes de World of Warcraft (compatible con servidores privados como **WoW Forever**, clientes **WotLK 3.3.5a**, Classic y Retail).

Consta de dos componentes que trabajan en sincronía perfecta:
1. **ForeverChatLogger (Addon en Lua):** Mantiene `/chatlog` activo en el juego y vacía el buffer de texto a disco cada 0.20 segundos ante cada evento de chat.
2. **WoW Chat Translator (App de Escritorio):** Lee pasivamente el archivo de log y traduce los mensajes de tus compañeros en **20 a 40 ms** utilizando inteligencia artificial local (**MarianMT / CTranslate2 int8**), proyectando las traducciones en un overlay visual dentro del juego sin interrumpir tu movimiento ni el combate.

### ✨ Características Principales

- ⚡ **100% Offline y Privado:** No realiza llamadas a internet ni APIs de terceros. Cero cuotas, cero suscripciones, sin lag.
- 🎮 **Preservación de Jerga Gamer:** Diccionario especializado que comprende términos como *oom, wipe, pull, aggro, need, greed, BiS, ty, mb, lfm*.
- 🛡️ **Zero Focus Interruption:** El overlay no roba el foco de teclado. Puedes hacer clic en pestañas, botones o desplazarte con la rueda del ratón sin que tu personaje deje de caminar (`W`) ni se corten tus lanzamientos de hechizos.
- 🔥 **Traducción Saliente Rápida (Alt+T):** Escribe en tu caja de chat en español, presiona `Alt+T` y tu texto se traducirá automáticamente al inglés informal de WoW en el portapapeles. Tú siempre confirmas el envío con Enter.
- 🎯 **Filtro Inteligente Anti-NPC:** Descarta diálogos de criaturas del juego, mensajes del sistema, loot y canales comerciales. Solo traduce jugadores reales en Grupo, Banda, Hermandad y Susurros.
- ⚙️ **Cero Configuración:** Auto-detecta la carpeta de WoW y el proceso en ejecución. Instala o actualiza el addon con 1 solo clic desde la interfaz.

---

## 🇬🇧 English Description

**WoW Chat Translator** is an all-in-one real-time translation tool designed for World of Warcraft players (compatible with **WoW Forever**, **WotLK 3.3.5a**, Classic, and Retail).

It bridges language gaps by translating party, raid, guild, and whisper messages locally using quantized offline neural machine translation models (**MarianMT / CTranslate2 int8**).

### Key Features:
- **100% Offline & Free:** Runs completely on your CPU with sub-40ms latency and ~200MB memory footprint. No API keys or internet connection required.
- **Zero Input Loss:** Window style `WS_EX_NOACTIVATE` guarantees that clicking the overlay or tabs never interrupts character movement or spell-casting.
- **Outbound Translator (Alt+T):** Type in your native language, press `Alt+T` to instantly translate to natural WoW gamer English, then press Enter to send.
- **Smart Anti-NPC & Channel Filter:** Ignores NPC chatter, monster yells, loot alerts, and trade spam—focusing strictly on real teammates.

---

## 🛡️ Cumplimiento Anti-Cheat y Normativa de Blizzard

| Regla de Blizzard / Servidores | Cómo lo cumple WoW Chat Translator | Estado |
| :--- | :--- | :---: |
| **No manipular la memoria del juego** | **Lectura 100% pasiva de archivos.** Lee únicamente `Logs/WoWChatLog.txt` y usa APIs de escritorio de Windows (`GetWindowRect`). Cero inyección de DLLs, cero hooks de DirectX. | ✅ 100% SEGURO |
| **No automatización de juego (Anti-Bot)** | El atajo `Alt+T` traduce y prepara el mensaje en la caja de chat, pero **NUNCA pulsa Enter automáticamente**. La decisión de envío siempre es manual del jugador. | ✅ 100% SEGURO |
| **Aislamiento de Addons** | Solo interactúa con su propio addon `ForeverChatLogger`. Jamás modifica ni interfiere con addons de terceros (`Questie`, `ElvUI`, `ForeverCore`, etc.). | ✅ 100% SEGURO |

---

## 📥 Instalación Rápida

### Opción 1: Aplicación Portátil (Recomendada)
1. Descarga la última versión de **[WoWChatTranslator-v1.0.0-Portable.zip](https://github.com/GabrielGlezG/wow-chat-translator/releases)**.
2. Descomprime la carpeta en el lugar que prefieras (ej: `C:\WoWChatTranslator`).
3. Ejecuta `WoWChatTranslator.exe`.
4. Abre World of Warcraft. El traductor detectará el juego automáticamente. Si es tu primera vez, haz clic en **Sincronizar Addon** en la pestaña de Ajustes del Overlay para instalar `ForeverChatLogger` en tu carpeta `Interface/AddOns/`.

### Opción 2: Solo Addon (desde CurseForge)
1. Descarga **ForeverChatLogger** desde CurseForge o mediante la aplicación de CurseForge.
2. Extrae la carpeta en `World of Warcraft/Interface/AddOns/ForeverChatLogger`.
3. Inicia el juego y asegúrate de que el Addon esté activado en la lista de Addons de la pantalla de selección de personaje.
4. Para ver las traducciones dentro de la pantalla del juego, ejecuta la aplicación de escritorio acompañante.

---

## 💬 Comandos dentro del Juego

Escribe en el chat de WoW:
- `/translator status` - Muestra si el logger de chat está activo y cuántos vaciados a disco se han realizado.
- `/translator flush` - Fuerza un vaciado inmediato del buffer a disco para pruebas.
- `/translator on` - Activa manualmente `/chatlog`.
- `/translator off` - Desactiva el logging.

---

## 🏗️ Estructura del Proyecto

```
wow-chat-translator/
├── addon/
│   └── ForeverChatLogger/       # Addon en Lua para CurseForge
│       ├── ForeverChatLogger.toc
│       └── ForeverChatLogger.lua
├── assets/                      # Iconos y logotipos oficiales
├── data/
│   └── wow_slang.json           # Diccionario especializado de jerga de WoW
├── models/                      # Modelos locales MarianMT int8 (CTranslate2)
│   ├── opus-mt-en-es/
│   └── opus-mt-es-en/
├── scripts/
│   ├── package_addon.py         # Empaquetador para CurseForge
│   └── build_exe.py             # Compilador PyInstaller para GitHub Releases
├── src/                         # Código fuente de la aplicación acompañante
│   ├── main.py                  # Loop principal y System Tray
│   ├── overlay.py               # Ventana flotante transparente anti-robo de foco
│   ├── translator.py            # Inferencia local en CPU (CTranslate2)
│   ├── watcher.py               # Monitor de WoWChatLog.txt y filtros anti-NPC
│   ├── addon_installer.py       # Sincronizador de 1 clic del addon
│   ├── window_tracker.py        # Seguimiento y re-enfoque de Wow.exe
│   └── config.py                # Cero-configuración y auto-detección
└── tests/                       # Suite de pruebas unitarias automatizadas (pytest)
```

---

## 🧪 Pruebas Unitarias

Para correr las pruebas automatizadas del proyecto:
```bash
pytest
```

---

## 📄 Licencia

Este proyecto está distribuido bajo la licencia **MIT**. World of Warcraft y Blizzard Entertainment son marcas registradas de Blizzard Entertainment, Inc. Este software es un proyecto independiente desarrollado por la comunidad sin afiliación oficial con Blizzard Entertainment.
