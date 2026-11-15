@echo off
title BarranquillaWare - Iniciando Juego
cd /d "%~dp0"

:: Limpiar variables de entorno dummy de testing para asegurar sonido y video reales
set "SDL_AUDIODRIVER="
set "SDL_VIDEODRIVER="

echo ========================================================
echo       Iniciando BarranquillaWare (Pygame)
echo ========================================================
echo Audio real activado (DirectSound / WASAPI).
echo.

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" main.py
) else (
    echo [AVISO] No se encontro entorno .venv local. Intentando con python del sistema...
    python main.py
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] El juego se cerro con codigo de error %ERRORLEVEL%.
    pause
)
