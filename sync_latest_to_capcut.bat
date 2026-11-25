@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Environnement non installe. Lancement de install_windows.bat d'abord...
    call install_windows.bat
)

".venv\Scripts\python.exe" -m tools.capcut_builder
echo.
pause
