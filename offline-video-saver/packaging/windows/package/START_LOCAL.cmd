@echo off
chcp 65001 >nul
cd /d "%~dp0"
"runtime\python.exe" "runtime\launcher.py" --mode local
if errorlevel 1 pause
