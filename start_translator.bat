@echo off
title WoW Forever Real-Time Chat Translator
cd /d "%~dp0"
echo ====================================================================
echo   WoW Forever Real-Time Chat Translator (Solo Jugadores EN ^<-^> ES)
echo   [MOTOR LOCAL OFFLINE ACTIVO - CTranslate2 + MarianMT (Sin API)]
echo ====================================================================
echo  - Todos los controles estan integrados como BOTONES y PESTANAS
echo    directamente en el Overlay para no chocar con teclas del juego:
echo    * Pestanas: [Chat] / [Rapidas y Escribir] / [Canales y Ajustes]
echo    * Botones superiores: [Leer] [ES-^>EN] [Limpiar] [Pausar] [-/+]
echo    * Boton [-/+] : Minimizar o Maximizar el Overlay dentro del juego
echo    * Scroll vertical para subir y bajar por el historial de chat
echo ====================================================================
echo.
python -m src.main
pause
