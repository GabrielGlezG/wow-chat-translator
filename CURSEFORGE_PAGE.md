# WoW Chat Translator (ForeverChatLogger)

![CurseForge Category](https://img.shields.io/badge/Category-Chat%20%26%20Communication-f16436.svg)
![Compatibility](https://img.shields.io/badge/WoW-16001%20%7C%203.3.5a%20%7C%20Classic-00e5ff.svg)
![Anti-Cheat](https://img.shields.io/badge/Security-100%25%20Blizzard%20Policy%20Safe-brightgreen.svg)

---

## 🇪🇸 Español: Descripción para CurseForge

### ¿Qué es WoW Chat Translator?
**WoW Chat Translator** te permite jugar en servidores internacionales de habla inglesa (como **WoW Forever**, servidores WotLK 3.3.5a y clientes oficiales) sin la barrera del idioma. Traduce al instante los mensajes de tus compañeros en **Grupo, Banda, Susurros y Hermandad** al español natural de WoW, y te permite responder en inglés gamer con un simple atajo (`Alt+T`).

### 📦 Componentes de la Solución
Siguiendo el estándar de herramientas líderes de World of Warcraft como *Raider.IO*, *TradeSkillMaster (TSM)* o *Warcraft Logs*:
1. **ForeverChatLogger (Este Addon en CurseForge):**
   - Código 100% puro en Lua, libre de binarios.
   - Mantiene `/chatlog` activo y vacía el buffer a disco cada 0.20s ante cada mensaje recibido.
2. **WoW Chat Translator Companion (Aplicación de Escritorio en GitHub):**
   - Overlay transparente dentro del juego que no roba el foco de teclado (no interrumpe tu movimiento ni tus hechizos).
   - Inferencia con modelos de traducción neuronales locales (**MarianMT int8**).
   - **100% Offline y Gratuito:** No requiere internet para traducir, no usa APIs de pago y no tiene costo de suscripción.

👉 **Descarga la aplicación de escritorio acompañante aquí:**  
**[Descargar WoW Chat Translator en GitHub Releases](https://github.com/gabriel/wow-chat-translator/releases)**

---

### 🛡️ 100% Seguro y Conforme a las Políticas de Blizzard (Anti-Cheat)
- **Cero lectura/escritura en memoria:** No toca el proceso `Wow.exe`, no inyecta DLLs ni utiliza hooks de DirectX.
- **Lectura pasiva:** La aplicación solo lee el archivo estándar `Logs/WoWChatLog.txt` generado por el propio cliente de WoW.
- **Sin automatización (Anti-Bot):** La traducción saliente con `Alt+T` traduce tu texto en la caja de chat, pero **NUNCA pulsa Enter automáticamente**. El jugador siempre confirma el envío manualmente.

---

### ⌨️ Comandos en el Juego
- `/translator` o `/fcl`: Muestra el estado del registro y las estadísticas.
- `/translator flush`: Vaciado forzado de prueba a disco.
- `/translator on`: Enciende el registro de chat.
- `/translator off`: Apaga el registro de chat.

---

## 🇬🇧 English: CurseForge Description

### What is WoW Chat Translator?
**WoW Chat Translator** enables real-time offline translation for World of Warcraft players (compatible with **WoW Forever**, **WotLK 3.3.5a**, and Classic clients). It translates party, raid, whisper, and guild messages with under 40ms CPU latency using offline neural machine translation models, preserving in-game gaming terminology (*oom, wipe, pull, need, greed, aggro*).

### Architecture
- **ForeverChatLogger (CurseForge Addon):** Pure Lua addon that maintains and debounces `/chatlog` to disk at 0.20s intervals.
- **Desktop Companion App (GitHub Releases):** Transparent, zero-focus-stealing overlay powered by local MarianMT int8 models.

👉 **Download the free companion desktop app:**  
**[WoW Chat Translator Desktop App on GitHub](https://github.com/gabriel/wow-chat-translator/releases)**
