@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo =======================================================
echo   INSTALLATION STUDIO ARENA + CLAUDE DESKTOP + CAPCUT
echo =======================================================
echo.

set "PY_CMD="
python --version >nul 2>nul
if %errorlevel% equ 0 (
    set "PY_CMD=python"
) else (
    py -3 --version >nul 2>nul
    if %errorlevel% equ 0 (
        set "PY_CMD=py -3"
    )
)

if "%PY_CMD%"=="" (
    echo [ERREUR] Python n'est pas installe sur ce PC Windows.
    echo Installe Python 3.11 ou 3.12 depuis https://www.python.org/downloads/
    echo ^(coche bien "Add python.exe to PATH" en bas de la fenetre d'installation^).
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo [1/3] Creation de l'environnement virtuel Python ^(.venv^)...
    %PY_CMD% -m venv .venv
)

echo [2/3] Installation de pyCapCut...
".venv\Scripts\python.exe" -m pip install --upgrade pip -q
".venv\Scripts\python.exe" -m pip install -r requirements.txt

echo [3/3] Connexion automatique a Claude Desktop et CapCut Windows...
".venv\Scripts\python.exe" tools\setup_windows.py

pause
