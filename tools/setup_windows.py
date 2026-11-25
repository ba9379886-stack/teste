"""Assistant d'installation automatique sur Windows :
1. Vérifie la détection du dossier des projets CapCut Desktop
2. Ajoute proprement le serveur MCP `arena-capcut` dans Claude Desktop (`claude_desktop_config.json`)
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def configure_claude_desktop(python_exe: Path) -> Path:
    appdata = os.environ.get("APPDATA")
    if appdata:
        claude_dir = Path(appdata) / "Claude"
    else:
        claude_dir = Path.home() / "AppData" / "Roaming" / "Claude"

    claude_dir.mkdir(parents=True, exist_ok=True)
    config_file = claude_dir / "claude_desktop_config.json"

    existing: dict = {}
    if config_file.exists():
        backup_file = claude_dir / "claude_desktop_config.backup.json"
        shutil.copy2(config_file, backup_file)
        try:
            content = config_file.read_text(encoding="utf-8").strip()
            if content:
                existing = json.loads(content)
        except Exception as exc:
            print(f"[Attention] Fichier config existant invalide ({exc}), sauvegarde créée dans {backup_file}")
            existing = {}

    if "mcpServers" not in existing or not isinstance(existing["mcpServers"], dict):
        existing["mcpServers"] = {}

    server_script = (REPO_ROOT / "tools" / "mcp_capcut_server.py").resolve()
    existing["mcpServers"]["arena-capcut"] = {
        "command": str(python_exe.resolve()),
        "args": [str(server_script)],
    }

    config_file.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")
    return config_file


def main() -> None:
    from tools.capcut_builder import detect_capcut_drafts_dir, save_local_config

    print("\n=======================================================")
    print("  CONFIGURATION ARENA <-> CLAUDE DESKTOP <-> CAPCUT")
    print("=======================================================\n")

    venv_win_py = REPO_ROOT / ".venv" / "Scripts" / "python.exe"
    python_exe = venv_win_py if venv_win_py.exists() else Path(sys.executable)

    # 1. Configurer Claude Desktop MCP
    config_path = configure_claude_desktop(python_exe)
    print(f"[OK] Serveur MCP 'arena-capcut' enregistré dans Claude Desktop :")
    print(f"     {config_path}\n")

    # 2. Vérifier le dossier CapCut Desktop
    try:
        drafts_dir = detect_capcut_drafts_dir()
        print(f"[OK] Dossier CapCut Desktop détecté automatiquement :")
        print(f"     {drafts_dir}\n")
    except FileNotFoundError:
        print("[!] Dossier CapCut non trouvé à l'emplacement par défaut.")
        print("    Dans CapCut -> Paramètres (icône engrenage) -> 'Enregistrer dans',")
        user_path = input("    Colle ici le chemin de ton dossier CapCut Drafts (ou Entrée pour passer) : ").strip().strip('"')
        if user_path and Path(user_path).exists():
            cfg_file = save_local_config({"capcut_drafts_dir": str(Path(user_path).resolve())})
            print(f"[OK] Chemin CapCut enregistré dans {cfg_file}\n")
        else:
            print("    (Tu pourras l'indiquer plus tard directement à Claude Desktop.)\n")

    print("=======================================================")
    print("  INSTALLATION TERMINÉE !")
    print("  -> Ferme complètement Claude Desktop (barre des tâches -> Quitter)")
    print("     puis relance-le pour activer les outils CapCut.")
    print("=======================================================\n")


if __name__ == "__main__":
    main()
