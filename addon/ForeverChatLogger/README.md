# WoW Chat Translator (ForeverChatLogger)

**ForeverChatLogger** is a lightweight, zero-overhead World of Warcraft addon designed to work seamlessly with the **WoW Chat Translator** companion desktop application.

---

## 🇪🇸 Descripción en Español

### ¿Qué hace este Addon?
El motor de World of Warcraft almacena los mensajes de chat en un buffer interno de 4KB antes de escribirlos en el disco (`Logs/WoWChatLog.txt`). **ForeverChatLogger** soluciona esto de manera transparente:
1. Activa automáticamente el registro de chat (`/chatlog ON`) al ingresar al mundo.
2. Cada vez que recibes un mensaje relevante en Grupo, Banda, Susurro o Hermandad, programa un vaciado suave (*debounced*) a disco a los **0.20 segundos**.
3. Permite que la aplicación de escritorio **WoW Chat Translator** lea el texto al instante y te lo muestre traducido en pantalla en **20-40 ms**.

### Comandos disponibles en el juego
- `/translator` o `/fcl`: Muestra el estado del Addon y estadísticas de vaciado.
- `/translator flush`: Fuerza un vaciado inmediato del chat a disco.
- `/translator on`: Enciende manualmente el logging de chat.
- `/translator off`: Apaga el logging de chat.

### Compatibilidad
- **WoW Forever & Servidores WotLK (3.3.5a):** 100% Compatible.
- **WoW Classic & Classic Era:** 100% Compatible (usa `C_Timer.After`).
- **Clientes Legacy:** Fallback automático con frame `OnUpdate`.

> 💡 **Nota Importante:** Para ver las traducciones dentro de la pantalla necesitas la aplicación de escritorio gratuita y 100% offline:
> 👉 **[Descargar WoW Chat Translator en GitHub](https://github.com/GabrielGlezG/wow-chat-translator/releases)**

---

## 🇬🇧 English Description

### What does this Addon do?
World of Warcraft buffers chat log writes to disk (`Logs/WoWChatLog.txt`) until 4KB of data accumulates. **ForeverChatLogger** solves this latency:
1. Automatically activates chat logging (`/chatlog ON`) on login.
2. Debounces an automatic flush to disk **0.20s** after each incoming chat event (`CHAT_MSG_PARTY`, `CHAT_MSG_RAID`, `CHAT_MSG_WHISPER`, etc.).
3. Enables the **WoW Chat Translator** companion application to translate messages in **20-40ms** offline.

### In-Game Slash Commands
- `/translator` or `/fcl` - View current logger status and flush count.
- `/translator flush` - Manually flush chat log buffer to disk.
- `/translator on` - Force chat logging ON.
- `/translator off` - Turn chat logging OFF.

### Companion Application
Get the free, offline companion application with the in-game overlay at:
👉 **[WoW Chat Translator on GitHub](https://github.com/GabrielGlezG/wow-chat-translator/releases)**
