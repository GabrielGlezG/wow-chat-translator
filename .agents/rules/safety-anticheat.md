---
trigger: always_on
description: "Reglas estrictas de seguridad para evitar falsos positivos de anti-cheat (Warden) en WoW y garantizar la integridad del cliente."
---

# Reglas Anti-Cheat y Seguridad

1. **PROHIBIDO tocar la memoria del proceso:** Nunca usar `pymem`, `ReadProcessMemory`, `WriteProcessMemory`, inyección de DLLs ni hooks de DirectX sobre `Wow.exe`.
2. **Solo lectura pasiva de archivos e interfaces nativas:** La captura de chat entrante debe hacerse exclusivamente leyendo `WoWChatLog.txt` en modo solo lectura (`r`) con codificación `utf-8` (con fallback `errors="replace"`), con captura pasiva de pantalla (WinOCR) solo como respaldo.
3. **Automatización solo bajo demanda:** La traducción de salida (ES -> EN) solo puede ejecutarse cuando el usuario presiona explícitamente el hotkey configurado o el botón del Overlay. **NUNCA enviar `Enter` automáticamente**; el usuario siempre debe confirmar el envío del mensaje en el juego.
4. **100% Local y Offline:** No depender de APIs externas de terceros para la publicación en CurseForge. Mantener la inferencia 100% local con CTranslate2 / MarianMT int8.
5. **Aislamiento de Addons de Terceros:** Prohibido editar o modificar addons descargados por el usuario (`ForeverCore`, `Questie`, `ElvUI`, etc.). Cualquier funcionalidad de Lua debe residir exclusivamente en nuestro propio addon: `ForeverChatLogger`.
6. **Secretos seguros:** Nunca hardcodear API keys ni contraseñas en el código. Mantener `.env` en `.gitignore`.
