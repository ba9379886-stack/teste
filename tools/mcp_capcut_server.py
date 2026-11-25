"""Serveur MCP (Model Context Protocol) local pour Claude Desktop sur Windows.

Donne directement à Claude Desktop le pouvoir de :
1. Voir les projets d'images + voix générés par Arena sur GitHub (`list_arena_projects`)
2. Télécharger les images + voix depuis GitHub et monter automatiquement le projet
   dans CapCut Desktop sur Windows (`sync_and_build_capcut_project`)
3. Ajuster le montage CapCut à la volée : couleur/taille des sous-titres, intensité des zooms,
   transitions, pauses, musique de fond (`customize_capcut_project`)
4. Vérifier ou configurer l'emplacement du dossier CapCut Windows (`check_capcut_setup`)
"""

from __future__ import annotations

import contextlib
import json
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, Optional

# S'assurer que la racine du repo est dans sys.path même lancé depuis Claude Desktop
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Forcer l'UTF-8 sur Windows (évite les erreurs cp1252 avec les accents français)
for _stream in (sys.stdin, sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8")
        except Exception:
            pass

REAL_STDOUT = sys.stdout

TOOLS_SPEC = [
    {
        "name": "check_capcut_setup",
        "description": (
            "Vérifie l'installation locale CapCut Desktop sur Windows, détecte le dossier des brouillons "
            "(Drafts) et liste les brouillons CapCut existants. Permet aussi d'enregistrer un chemin "
            "personnalisé `set_capcut_drafts_dir` si l'utilisateur a déplacé ses projets CapCut sur un autre disque."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "set_capcut_drafts_dir": {
                    "type": "string",
                    "description": "Optionnel : chemin personnalisé du dossier 'CapCut Drafts' à sauvegarder.",
                }
            },
        },
    },
    {
        "name": "list_arena_projects",
        "description": (
            "Liste tous les projets vidéo (images + voix off) générés par Arena et poussés sur GitHub "
            "(inspecte automatiquement `main` et toutes les branches `arena/*`), ainsi que les projets déjà téléchargés."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "sync_and_build_capcut_project",
        "description": (
            "Télécharge un projet d'images et de voix off depuis GitHub (par défaut le plus récent) "
            "et crée automatiquement le montage complet dans CapCut Desktop (Windows) : format 9:16, "
            "voix off enchaînées, images calées à la microseconde près sans bandes noires, effets Ken Burns "
            "(zoom/pan), transitions gratuites et sous-titres dynamiques style TikTok/Shorts."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_slug": {
                    "type": "string",
                    "description": "Slug du projet sur GitHub (ex: '2026-11-25-pyramides'). Omettre pour prendre automatiquement le plus récent.",
                },
                "draft_name": {
                    "type": "string",
                    "description": "Nom personnalisé du projet tel qu'il apparaîtra dans CapCut.",
                },
                "subtitle_color": {
                    "type": "string",
                    "enum": ["white", "yellow", "cyan"],
                    "description": "Couleur des sous-titres TikTok (défaut: 'white').",
                },
                "zoom_intensity": {
                    "type": "number",
                    "description": "Intensité du zoom dynamique sur les images, ex: 0.12 pour 12% (défaut: 0.12).",
                },
                "scene_gap_sec": {
                    "type": "number",
                    "description": "Légère respiration en secondes entre deux scènes (défaut: 0.12).",
                },
                "bgm_path": {
                    "type": "string",
                    "description": "Chemin local optionnel vers une musique de fond (.mp3/.wav).",
                },
            },
        },
    },
    {
        "name": "customize_capcut_project",
        "description": (
            "Reconstruit instantanément un projet déjà téléchargé localement dans CapCut avec de nouveaux réglages "
            "(taille/couleur/position des sous-titres, désactivation des sous-titres, transitions, zooms, musique de fond)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_slug": {
                    "type": "string",
                    "description": "Slug du projet local dans projects/<slug>.",
                },
                "draft_name": {
                    "type": "string",
                    "description": "Nom du brouillon dans CapCut.",
                },
                "subtitle_color": {
                    "type": "string",
                    "enum": ["white", "yellow", "cyan"],
                },
                "subtitle_size": {
                    "type": "number",
                    "description": "Taille de police des sous-titres (défaut: 8.5).",
                },
                "subtitle_y": {
                    "type": "number",
                    "description": "Position verticale des sous-titres entre -1.0 (bas) et 1.0 (haut). Défaut: -0.45.",
                },
                "enable_subtitles": {
                    "type": "boolean",
                    "description": "Activer ou désactiver la piste de sous-titres (défaut: true).",
                },
                "zoom_intensity": {
                    "type": "number",
                    "description": "Intensité du zoom Ken Burns (défaut: 0.12).",
                },
                "scene_gap_sec": {
                    "type": "number",
                    "description": "Pause en secondes entre les scènes (défaut: 0.12).",
                },
                "transition_override": {
                    "type": "string",
                    "enum": ["cut", "dissolve", "fade_black", "flash", "blur", "slide"],
                    "description": "Forcer un type de transition gratuit partout.",
                },
                "bgm_path": {
                    "type": "string",
                    "description": "Chemin local vers une musique de fond (.mp3/.wav).",
                },
                "bgm_volume": {
                    "type": "number",
                    "description": "Volume de la musique de fond entre 0.0 et 1.0 (défaut: 0.12).",
                },
            },
            "required": ["project_slug"],
        },
    },
]


def _execute_tool(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    from tools.capcut_builder import (
        LOCAL_PROJECTS_DIR,
        build_capcut_draft,
        detect_capcut_drafts_dir,
        save_local_config,
    )
    from tools.github_sync import (
        get_repo_slug,
        list_local_projects,
        list_remote_projects,
        sync_project_from_github,
    )

    if name == "check_capcut_setup":
        custom_dir = arguments.get("set_capcut_drafts_dir")
        if custom_dir:
            p = Path(custom_dir).expanduser()
            if not p.exists():
                raise FileNotFoundError(f"Le dossier indiqué n'existe pas : {p}")
            save_local_config({"capcut_drafts_dir": str(p.resolve())})

        drafts_dir = detect_capcut_drafts_dir()
        existing_drafts = sorted(
            [d.name for d in drafts_dir.iterdir() if d.is_dir() and not d.name.startswith(".")]
        )
        return {
            "status": "ok",
            "github_repo": get_repo_slug(),
            "capcut_drafts_dir": str(drafts_dir),
            "existing_capcut_drafts_count": len(existing_drafts),
            "existing_capcut_drafts_sample": existing_drafts[:20],
            "local_projects": list_local_projects(),
        }

    if name == "list_arena_projects":
        remote = list_remote_projects()
        local = list_local_projects()
        return {
            "github_repo": get_repo_slug(),
            "remote_projects": remote,
            "local_projects": local,
        }

    if name == "sync_and_build_capcut_project":
        sync_result = sync_project_from_github(project_slug=arguments.get("project_slug"))
        proj_dir = Path(sync_result["local_dir"])
        build_result = build_capcut_draft(
            project_dir=proj_dir,
            draft_name=arguments.get("draft_name"),
            scene_gap_sec=float(arguments.get("scene_gap_sec", 0.12)),
            zoom_intensity=float(arguments.get("zoom_intensity", 0.12)),
            subtitle_color=str(arguments.get("subtitle_color", "white")),
            bgm_path=arguments.get("bgm_path"),
        )
        return {
            "status": "success",
            "sync": sync_result,
            "capcut": build_result,
            "next_step_for_user": (
                f"Ouvre CapCut Desktop sur Windows (ou reviens à l'accueil CapCut pour rafraîchir) "
                f"et clique sur le projet '{build_result['draft_name']}' !"
            ),
        }

    if name == "customize_capcut_project":
        slug = arguments["project_slug"]
        proj_dir = LOCAL_PROJECTS_DIR / slug
        if not proj_dir.exists():
            sync_result = sync_project_from_github(project_slug=slug)
            proj_dir = Path(sync_result["local_dir"])

        build_result = build_capcut_draft(
            project_dir=proj_dir,
            draft_name=arguments.get("draft_name"),
            scene_gap_sec=float(arguments.get("scene_gap_sec", 0.12)),
            zoom_intensity=float(arguments.get("zoom_intensity", 0.12)),
            subtitle_color=str(arguments.get("subtitle_color", "white")),
            subtitle_size=float(arguments.get("subtitle_size", 8.5)),
            subtitle_y=float(arguments.get("subtitle_y", -0.45)),
            enable_subtitles=bool(arguments.get("enable_subtitles", True)),
            transition_override=arguments.get("transition_override"),
            bgm_path=arguments.get("bgm_path"),
            bgm_volume=float(arguments.get("bgm_volume", 0.12)),
        )
        return {
            "status": "success",
            "capcut": build_result,
        }

    raise ValueError(f"Outil inconnu : {name}")


def _send_jsonrpc(payload: Dict[str, Any]) -> None:
    line = json.dumps(payload, ensure_ascii=False)
    REAL_STDOUT.write(line + "\n")
    REAL_STDOUT.flush()


def _read_message() -> Optional[Dict[str, Any]]:
    while True:
        line = sys.stdin.readline()
        if line == "":
            return None  # EOF
        stripped = line.strip()
        if not stripped:
            continue
        # Support optionnel de l'en-tête Content-Length si un client l'utilise
        if stripped.lower().startswith("content-length:"):
            length = int(stripped.split(":", 1)[1].strip())
            while True:
                header_line = sys.stdin.readline()
                if header_line in ("", "\r\n", "\n"):
                    break
            body = sys.stdin.read(length)
            if not body:
                return None
            return json.loads(body)
        return json.loads(stripped)


def _handle_request(msg: Dict[str, Any]) -> None:
    method = msg.get("method", "")
    req_id = msg.get("id")
    params = msg.get("params") or {}

    # Notifications (aucun id -> pas de réponse attendue)
    if req_id is None:
        return

    if method == "initialize":
        client_version = params.get("protocolVersion") or "2024-11-05"
        _send_jsonrpc({
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": client_version,
                "capabilities": {
                    "tools": {},
                },
                "serverInfo": {
                    "name": "arena-capcut-studio",
                    "version": "1.0.0",
                },
            },
        })
        return

    if method == "ping":
        _send_jsonrpc({"jsonrpc": "2.0", "id": req_id, "result": {}})
        return

    if method == "tools/list":
        _send_jsonrpc({
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": TOOLS_SPEC},
        })
        return

    if method == "resources/list":
        _send_jsonrpc({"jsonrpc": "2.0", "id": req_id, "result": {"resources": []}})
        return

    if method == "prompts/list":
        _send_jsonrpc({"jsonrpc": "2.0", "id": req_id, "result": {"prompts": []}})
        return

    if method == "tools/call":
        tool_name = params.get("name", "")
        tool_args = params.get("arguments") or {}
        try:
            with contextlib.redirect_stdout(sys.stderr):
                output = _execute_tool(tool_name, tool_args)
            _send_jsonrpc({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(output, indent=2, ensure_ascii=False),
                        }
                    ],
                    "isError": False,
                },
            })
        except Exception as exc:
            err_detail = f"Erreur lors de l'exécution de `{tool_name}` : {exc}\n{traceback.format_exc()}"
            _send_jsonrpc({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": err_detail}],
                    "isError": True,
                },
            })
        return

    _send_jsonrpc({
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Méthode non supportée : {method}"},
    })


def main() -> None:
    while True:
        try:
            msg = _read_message()
            if msg is None:
                break
            _handle_request(msg)
        except Exception as exc:
            sys.stderr.write(f"[arena-capcut-mcp] Erreur boucle: {exc}\n")
            sys.stderr.flush()


if __name__ == "__main__":
    main()
