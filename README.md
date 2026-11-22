# WoW Chat Translator

<p align="center">
  <img src="assets/icon.png" alt="WoW Chat Translator" width="96" height="96"/>
  <br>
  <b>Traductor de Chat en Tiempo Real para World of Warcraft (100% Offline y Gratuito)</b>
</p>

<p align="center">
  <a href="https://github.com/GabrielGlezG/wow-chat-translator/releases"><img src="https://img.shields.io/github/v/release/GabrielGlezG/wow-chat-translator?color=blue&label=Descargar%20v1.0.0" alt="Release"/></a>
  <a href="https://curseforge.com/wow/addons/foreverchatlogger"><img src="https://img.shields.io/badge/CurseForge-Addon-f16436.svg" alt="CurseForge"/></a>
  <img src="https://img.shields.io/badge/Anti--Cheat-100%25%20Seguro-brightgreen.svg" alt="Anti-Cheat"/>
</p>

---

## ⚡ ¿Cómo funciona?

El sistema utiliza la misma arquitectura híbrida que **Raider.IO** o **TSM**:

1. **Addon en Lua (`ForeverChatLogger`):** Mantiene `/chatlog` activo y vacía el buffer a disco cada 0.20s ante cada mensaje recibido.
2. **App de Escritorio (`WoWChatTranslator.exe`):** Lee pasivamente el log, traduce en **20-40 ms** mediante modelos neuronales locales (**MarianMT int8**) y proyecta el overlay flotante dentro del juego.

---

## 📥 Instalación Rápida (3 Pasos)

1. **Descarga:** Baja el archivo portable **[WoWChatTranslator-v1.0.0-Portable.zip](https://github.com/GabrielGlezG/wow-chat-translator/releases)**.
2. **Ejecuta:** Descomprime y abre `WoWChatTranslator.exe` (no requiere instalar Python ni librerías).
3. **Instala el Addon:** Abre WoW. En la pestaña **Ajustes** del Overlay, pulsa **"Sincronizar Addon"** (instala `ForeverChatLogger` automáticamente en tu carpeta `Interface/AddOns/`).

---

## ✨ Características

* **100% Offline:** Modelos de IA embebidos. Cero costo, cero APIs, funciona sin internet.
* **Jerga de WoW:** Traduce correctamente *oom, wipe, pull, aggro, need, greed, BiS, mb, ty*.
* **Zero Focus Interruption:** El overlay no roba foco. Puedes hacer clic en pestañas sin detener tu personaje (`W`).
* **Traducción Saliente (`Alt+T`):** Escribe en español en tu caja de chat, pulsa `Alt+T` y traduce al inglés gamer antes de enviar.
* **Anti-NPC:** Filtra diálogos de PNJs del mundo, loot y comercio; solo traduce jugadores reales.

---

## 🛡️ Anti-Cheat y Seguridad

* **Lectura Pasiva:** Solo lee `Logs/WoWChatLog.txt`. Cero inyección de DLLs, cero memoria, cero hooks.
* **Control Total:** `Alt+T` nunca pulsa `Enter` automáticamente; el jugador siempre confirma el envío.

---

## ⌨️ Comandos en Juego

* `/translator status` — Muestra el estado del logger.
* `/translator flush` — Fuerza un vaciado manual a disco.
* `/translator on / off` — Enciende o apaga el logging.

---

## 📄 Licencia

Distribuido bajo licencia MIT. Desarrollado de forma independiente para la comunidad de WoW.
