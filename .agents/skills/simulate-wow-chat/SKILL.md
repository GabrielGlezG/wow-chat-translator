---
name: simulate-wow-chat
description: Simula mensajes reales de chat de World of Warcraft escribiendo líneas en el archivo de log para testear el watcher, el parser de canales, el filtrado y el overlay en tiempo real. Úsala para depurar la lectura de chat con o sin el juego abierto.
---

# Simulador de Chat de WoW (WoWChatLog.txt)

## Objetivo
Verificar de extremo a extremo que el watcher detecta líneas nuevas del log en tiempo real, aplica los filtros multicapa (canales, NPCs, mensajes propios y español previo) y envía la traducción limpia al Overlay sin bloquear la UI.

## Instrucciones

1. **Para pruebas en vivo dentro del juego:**
   - Ejecuta `python scripts/probar_chat.py` (o `probar_chat.bat`).
   - El script detecta automáticamente la ruta activa de `Logs/WoWChatLog.txt` e inyecta 5 mensajes típicos de mazmorras/raids espaciados por 1.5s:
     - `[Grupo] [Thunderfury]: hey healer oom need to drink a sec`
     - `Frostmage te susurra: ty for the food earlier! mb on that wipe`
     - `[Banda] [Raidlead]: everyone stack behind the boss, watch out for tail swipe`
     - `[Hermandad] [Elunepriest]: don't pull yet, tank has high lag spike`
     - `Shadowpriest te susurra: do you want to join our raid for Onyxia tonight?`
   - Confirma visualmente que los 5 mensajes aparecen traducidos en el Overlay flotante en menos de 1 segundo.

2. **Para pruebas unitarias automáticas (CI/Tests):**
   - Ejecuta `python -m pytest tests/test_pipeline.py`.
   - Verifica:
     - Que los formatos nativos de WoW Forever (`|Hchannel:PARTY|h[Grupo]|h`) se desenvuelvan y analicen correctamente.
     - Que los mensajes propios del jugador (`Aptinstall`) se ignoren.
     - Que los mensajes de canales de spam (`[Comercio]`, `[General]`) se descarten.
     - Que los enlaces puros de ítems/misiones sin texto conversacional no se envíen a traducir.
     - Que los mensajes que ya están en español (*wenas, gracias, terminamos*) no se añadan al overlay.
