@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo =======================================================
echo   INSTALLATION STUDIO ARENA + CLAUDE DESKTOP + CAPCUT
echo =======================================================
echo.

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERREUR] Python n'est pas installe ou n'est pas dans le PATH Windows.
    echo Installe Python 3.10+ depuis https://www.python.org/downloads/
    echo ^(pense bien a cocher "Add python.exe to PATH" lors de l'installation^).
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo [1/3] Creation de l'environnement virtuel Python ^(.venv^)...
    python -m venv .venv
)

echo [2/3] Installation de pyCapCut...
".venv\Scripts\python.exe" -m pip install --upgrade pip -q
".venv\Scripts\python.exe" -m pip install -r requirements.txt

echo [3/3] Connexion automatique a Claude Desktop et CapCut Windows...
".venv\Scripts\python.exe" tools\setup_windows.py

pause
