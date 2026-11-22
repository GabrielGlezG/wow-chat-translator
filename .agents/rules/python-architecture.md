---
trigger: glob
globs: "*.py"
description: "Estándares de concurrencia, inferencia local offline, UI no bloqueante y arquitectura modular en Python."
---

# Estándares de Código Python

1. **UI nunca bloqueada:** La inferencia local de CTranslate2, el monitoreo del archivo de log (`ChatLogWatcher`) y los escaneos de OCR deben correr en hilos dedicados (`QThread` o `threading.Thread`), comunicándose con el Overlay de PySide6 exclusivamente mediante señales y slots (`Signal`/`Slot`).
2. **Inferencia 100% Local y Eficiente:** Usar modelos MarianMT cuantizados en `int8` con CTranslate2. Mantener la latencia de traducción por debajo de los 50ms en CPU sin generar picos de carga.
3. **Cero Configuración (Zero-Config):** La aplicación debe auto-detectar el proceso de `Wow.exe` mediante `psutil` y resolver la carpeta `Logs/WoWChatLog.txt` de manera transparente para el usuario. Cualquier ajuste en la UI (personaje o carpetas) debe actualizarse en caliente sin reiniciar.
4. **Filtrado previo estricto:** Antes de traducir, validar que el mensaje:
   - Pertenezca a los canales permitidos (Grupo, Banda, Hermandad, Susurro, Decir).
   - No sea del propio jugador (`is_own_player_sender`).
   - No provenga de un NPC o monstruo (`is_likely_npc_sender`).
   - No esté ya en español (`is_obviously_spanish`).
   - Enmascare y preserve hipervínculos de WoW y marcas de banda (`mask_wow_tokens`).
5. **Prioridad al Log de Disco vs. OCR:** El archivo `WoWChatLog.txt` es la fuente principal de alta fidelidad. Si hay actividad de log reciente (< 3.5s), el escaneo visual de pantalla debe suspenderse automáticamente para ahorrar CPU y evitar errores ópticos.
6. **Manejo seguro del portapapeles y atajos:** Al usar el traductor saliente (ES -> EN con `Alt+T`), asegurar que los modificadores (`Alt`, `Ctrl`, `Shift`) se liberen limpiamente, respetar tiempos de retención para DirectX y restaurar el contenido previo del portapapeles.
7. **Estructura modular:** Mantener separación clara: `config.py` (configuración y auto-detección), `watcher.py` (log), `translator.py` (CTranslate2 y glosario), `hotkey_handler.py` (ES->EN), `overlay.py` (PySide6 UI) y `main.py` (coordinador).
