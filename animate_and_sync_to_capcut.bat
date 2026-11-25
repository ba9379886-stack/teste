@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Environnement non installe. Lancement de install_windows.bat d'abord...
    call install_windows.bat
)

echo Verification des dependances video IA (google-genai, requests, Pillow)...
".venv\Scripts\python.exe" -m pip install -q -r requirements.txt

echo.
echo Synchronisation GitHub + Animation IA (Veo / PixVerse) + Montage CapCut...
".venv\Scripts\python.exe" -m tools.capcut_builder --animate auto
echo.
pause
