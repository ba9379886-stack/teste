"""Assistant d'installation automatique sur Windows :
1. Vérifie la détection du dossier des projets CapCut Desktop
2. Ajoute proprement le serveur MCP `arena-capcut` dans Claude Desktop
   (supporte à la fois l'installateur classique ET la version Microsoft Store Windows 11 !)
"""

from __future__ import annotations

import glob
import json
import os
import shutil
import sys
from pathlib import Path
from typing import List

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _write_mcp_entry(config_file: Path, python_exe: Path, server_script: Path) -> None:
    config_file.parent.mkdir(parents=True, exist_ok=True)
    existing: dict = {}
    if config_file.exists():
        backup_file = config_file.with_name("claude_desktop_config.backup.json")
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

    existing["mcpServers"]["arena-capcut"] = {
        "command": str(python_exe.resolve()),
        "args": [str(server_script.resolve())],
    }

    config_file.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")


def configure_claude_desktop(python_exe: Path) -> List[Path]:
    server_script = (REPO_ROOT / "tools" / "mcp_capcut_server.py").resolve()
    written_paths: List[Path] = []

    # 1. Emplacement standard (installateur .exe depuis claude.ai)
    appdata = os.environ.get("APPDATA")
    std_claude_dir = (Path(appdata) / "Claude") if appdata else (Path.home() / "AppData" / "Roaming" / "Claude")
    std_config = std_claude_dir / "claude_desktop_config.json"

    # 2. Emplacement Microsoft Store (MSIX sous Windows 10/11)
    local_appdata = os.environ.get("LOCALAPPDATA")
    store_configs: List[Path] = []
    if local_appdata:
        pattern = str(Path(local_appdata) / "Packages" / "Claude_*" / "LocalCache" / "Roaming" / "Claude")
        for match in glob.glob(pattern):
            store_configs.append(Path(match) / "claude_desktop_config.json")

    # Si le dossier Microsoft Store existe, on écrit dedans ; on écrit aussi dans l'emplacement standard
    for cfg in store_configs:
        _write_mcp_entry(cfg, python_exe, server_script)
        written_paths.append(cfg)

    if std_claude_dir.exists() or not written_paths:
        _write_mcp_entry(std_config, python_exe, server_script)
        written_paths.append(std_config)

    return written_paths


def main() -> None:
    from tools.capcut_builder import detect_capcut_drafts_dir, save_local_config

    print("\n=======================================================")
    print("  CONFIGURATION ARENA <-> CLAUDE DESKTOP <-> CAPCUT")
    print("=======================================================\n")

    venv_win_py = REPO_ROOT / ".venv" / "Scripts" / "python.exe"
    python_exe = venv_win_py if venv_win_py.exists() else Path(sys.executable)

    # 1. Configurer Claude Desktop MCP (classique + Microsoft Store)
    config_paths = configure_claude_desktop(python_exe)
    print("[OK] Serveur MCP 'arena-capcut' enregistré dans Claude Desktop :")
    for p in config_paths:
        print(f"     -> {p}")
    print()

    # 2. Vérifier le dossier CapCut Desktop
    try:
        drafts_dir = detect_capcut_drafts_dir()
        print("[OK] Dossier CapCut Desktop détecté automatiquement :")
        print(f"     -> {drafts_dir}\n")
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
    print("  IMPORTANT SUR WINDOWS :")
    print("  1. Dans Claude Desktop, clique sur Menu (3 barres en haut à gauche)")
    print("     -> Fichier -> Quitter (la croix X ne ferme pas vraiment l'app !).")
    print("  2. Relance Claude Desktop et ouvre une NOUVELLE conversation.")
    print("=======================================================\n")


if __name__ == "__main__":
    main()
