# WoW Forever Real-Time Chat Translator

## Objetivo del proyecto
Construir una solución completa y ligera de traducción en tiempo real para World of Warcraft (servidor WoW Forever y clientes compatibles), compuesta por un **Addon de WoW** (`ForeverChatLogger`) y una **Aplicación de Escritorio acompañante** (Windows, Python / PySide6 / CTranslate2), orientada a ser distribuida públicamente en **CurseForge** y GitHub Releases.

Permite a jugadores hispanohablantes comunicarse fluidamente con jugadores de habla inglesa sin salir del juego (sin Alt+Tab) de manera **100% offline, privada y sin costo de APIs**.

---

## Arquitectura del Sistema

### 1. Addon en Lua (`addon/ForeverChatLogger`)
- **Ubicación:** `addon/ForeverChatLogger/` (e instalado en `Interface/AddOns/ForeverChatLogger/`).
- **Mecanismo:** Mantiene `/chatlog` activo y resuelve el buffer interno de 4KB de WoW mediante un vaciado debounced a los 0.20s de cada evento de chat (`CHAT_MSG_PARTY`, `CHAT_MSG_WHISPER`, etc.) alternando `LoggingChat(false)` y `LoggingChat(true)`.
- **Compatibilidad:** Implementa soporte multiversión (fallback con frame `OnUpdate` si `C_Timer` no está disponible).
- **Regla estricta:** NUNCA modificar addons de terceros descargados por el usuario (`ForeverCore`, etc.). Solo se gestiona `ForeverChatLogger`.

### 2. Motor de Traducción 100% Local y Offline (`src/translator.py`)
- **Modelos:** MarianMT cuantizados en precisión `int8` con **CTranslate2** (`models/opus-mt-en-es` y `models/opus-mt-es-en`).
- **Rendimiento:** Latencia de **20-40 ms en CPU**, consumo de ~200 MB de RAM. Sin llamadas a APIs externas (cero cuotas, cero errores 429/404, funciona sin internet).
- **Pre/Post-procesamiento:**
  - Enmascarado de hipervínculos de WoW (`|c...|Hitem:...|h[...]|h|r`), misiones (`[[...]]`) y marcadores de banda (`{rt1}`...`{rt8}`).
  - Diccionario especializado de jerga de WoW y abreviaturas comunes (*oom, wipe, pull, dc, ty, mb, aggro, need, greed*).

### 3. Monitor de Log y Filtros Inteligentes (`src/watcher.py`)
- **Monitoreo pasivo:** Hilo `QThread` con lectura segura de `Logs/WoWChatLog.txt` en modo solo lectura (`utf-8` con `errors="replace"`).
- **Filtros estrictos:**
  - **Canales relevantes:** Solo Grupo, Banda, Hermandad, Susurro y Decir. Canales de comercio, general y defensa quedan descartados.
  - **Anti-NPC (`is_likely_npc_sender`):** Descarta diálogos de criaturas del mundo, textos con comas, títulos o frases de combate.
  - **Anti-Propios (`is_own_player_sender`):** Reconoce dinámicamente el nombre de personaje del jugador y variantes con ligeras alteraciones ópticas.
  - **Filtro de Español (`is_obviously_spanish`):** Detecta saludos y frases que ya están en español (*wenas, gracias, terminamos, hola, jaja*) para no saturar el overlay.

### 4. Lector Visual OCR de Respaldo (`src/main.py`)
- **OCR Nativo Windows (`winocr`):** Escaneo local offline de la caja de chat de WoW en 25-35 ms.
- **Silenciamiento inteligente:** Cuando el archivo de log en disco está activo entregando mensajes, el OCR se suspende automáticamente para ahorrar CPU y evitar errores ópticos. Solo actúa bajo demanda o si el log estuviera inactivo.

### 5. Interfaz Gráfica Overlay (`src/overlay.py`)
- Ventana PySide6 transparente, frameless, click-through (`WindowTransparentForInput`) y siempre visible (`WindowStaysOnTopHint`).
- 3 Pestañas interactivas:
  - **💬 Chat:** Historial con scroll vertical, selección de texto y modo bilingüe (EN+ES).
  - **⚡ Rápidas / Escribir:** Botones de respuesta rápida instantánea y traductor manual ES->EN con copiado al portapapeles.
  - **⚙️ Canales / Ajustes:** Filtros de canales, fuente, opacidad, auto-atenuación, nombre de personaje y selector gráfico de carpeta de WoW.

### 6. Cero Configuración (Zero-Config) (`src/config.py`)
- Detección automática del proceso activo `Wow.exe` con `psutil`, resolviendo la ruta `Logs/WoWChatLog.txt` sin requerir edición manual de archivos JSON.
- Actualización en caliente de personajes y rutas sin necesidad de reiniciar la app.

### 7. Traducción Saliente ES->EN (`src/hotkey_handler.py`)
- Al activar `Alt+T` o pulsar el botón `🔥 ES->EN` en la caja de chat de WoW:
  1. Selecciona todo (`Ctrl+A`) y copia (`Ctrl+C`).
  2. Traduce al inglés con jerga gamer en memoria.
  3. Pega la traducción (`Ctrl+V`) y restaura el portapapeles previo.
- **Anti-Cheat:** Nunca pulsa `Enter` automáticamente; el jugador siempre confirma el envío.

---

## Hoja de Ruta para Publicación (CurseForge)

1. [x] Addon independiente `ForeverChatLogger` con debouncer de vaciado.
2. [x] Motor 100% local MarianMT `int8` con latencia < 50ms.
3. [x] Filtros estrictos de canales, NPCs, mensajes propios y español.
4. [x] Cero configuración (auto-detección de proceso y carpetas).
5. [ ] Empaquetado en ejecutable único portable (`WoWChatTranslator.exe`) con PyInstaller incluyendo modelos locales.
6. [ ] Empaquetado del Addon `.zip` con metadatos de CurseForge y guía de instalación rápida.
