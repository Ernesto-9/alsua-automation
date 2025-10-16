@echo off
REM Script para iniciar el Panel Web Alsua automáticamente
REM Este script se ejecuta al iniciar Windows

cd /d "%~dp0"
echo Iniciando Panel Web Alsua...
python app.py
pause
