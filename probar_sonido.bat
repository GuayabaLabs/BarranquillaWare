@echo off
title Diagnostico de Sonido - BarranquillaWare
cd /d "%~dp0"

set "SDL_AUDIODRIVER="
set "SDL_VIDEODRIVER="

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" tools/probar_sonido.py
) else (
    python tools/probar_sonido.py
)

echo.
pause
