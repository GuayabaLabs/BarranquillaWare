@echo off
title BarranquillaWare - Verificacion Directa Modal
cd /d "%~dp0"
echo Abriendo BarranquillaWare directamente en el mapa con el nuevo modal...
.\.venv\Scripts\python.exe probar_modal_directo.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Ocurrio un error al ejecutar el juego.
    pause
)
