"""Synchronisation automatique des projets (images + voix + manifest) depuis GitHub.

Fonctionne sans aucune manipulation Git manuelle côté Windows :
- Inspecte automatiquement la branche `main` AINSI que toutes les branches `arena/*`
  du dépôt `ba9379886-stack/teste`.
- Utilise l'API Git Trees (seulement 2 requêtes API) + téléchargement direct des fichiers
  binaires (images PNG/JPG et voix MP3/WAV) via raw.githubusercontent.com (sans limite API).
"""

from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_REPO = "ba9379886-stack/teste"
REPO_ROOT = Path(__file__).resolve().parent.parent
LOCAL_PROJECTS_DIR = REPO_ROOT / "projects"


def _load_local_config() -> Dict[str, Any]:
    cfg_path = REPO_ROOT / "config.local.json"
    if cfg_path.exists():
        try:
            return json.loads(cfg_path.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def get_repo_slug() -> str:
    cfg = _load_local_config()
    return os.environ.get("ARENA_GITHUB_REPO") or cfg.get("github_repo") or DEFAULT_REPO


def _github_headers(accept: str = "application/vnd.github+json") -> Dict[str, str]:
    cfg = _load_local_config()
    token = os.environ.get("GITHUB_TOKEN") or cfg.get("github_token")
    headers = {
        "Accept": accept,
        "User-Agent": "arena-capcut-studio/1.0",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _api_get_json(url: str, timeout: int = 20) -> Any:
    req = urllib.request.Request(url, headers=_github_headers())
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _download_file(
    repo: str,
    commit_sha: str,
    repo_rel_path: str,
    dest_path: Path,
    blob_sha: Optional[str] = None,
) -> None:
    """Télécharge un fichier du dépôt vers dest_path (via raw URL puis fallback Git Blobs API)."""
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    quoted_path = "/".join(urllib.parse.quote(part) for part in repo_rel_path.split("/"))
    raw_url = f"https://raw.githubusercontent.com/{repo}/{commit_sha}/{quoted_path}"

    cfg = _load_local_config()
    token = os.environ.get("GITHUB_TOKEN") or cfg.get("github_token")
    headers = {"User-Agent": "arena-capcut-studio/1.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        req = urllib.request.Request(raw_url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            dest_path.write_bytes(resp.read())
            return
    except Exception:
        pass

    # Fallback 1 : Git Blobs API en flux brut (supporte les images/audios jusqu'à 100 Mo)
    if blob_sha:
        blob_url = f"https://api.github.com/repos/{repo}/git/blobs/{urllib.parse.quote(blob_sha)}"
        req = urllib.request.Request(blob_url, headers=_github_headers(accept="application/vnd.github.raw"))
        with urllib.request.urlopen(req, timeout=60) as resp:
            dest_path.write_bytes(resp.read())
            return

    # Fallback 2 : GitHub Contents API
    api_url = (
        f"https://api.github.com/repos/{repo}/contents/{quoted_path}"
        f"?ref={urllib.parse.quote(commit_sha)}"
    )
    data = _api_get_json(api_url, timeout=30)
    if isinstance(data, dict) and data.get("encoding") == "base64" and "content" in data:
        dest_path.write_bytes(base64.b64decode(data["content"]))
        return
    raise RuntimeError(f"Impossible de télécharger {repo_rel_path} depuis {repo}@{commit_sha}")


def list_remote_projects(repo: Optional[str] = None) -> List[Dict[str, Any]]:
    """Liste tous les projets disponibles sur GitHub (main + branches arena/*)."""
    repo = repo or get_repo_slug()
    branches_url = f"https://api.github.com/repos/{repo}/branches?per_page=100"
    branches = _api_get_json(branches_url)

    # Prioriser les branches arena/* puis main
    candidate_branches = [
        b for b in branches
        if b.get("name") == "main" or str(b.get("name", "")).startswith("arena/")
    ]
    # Mettre les branches arena/* en premier (souvent là où Arena vient tout juste de pousser)
    candidate_branches.sort(
        key=lambda b: (0 if str(b.get("name", "")).startswith("arena/") else 1, b.get("name", ""))
    )

    projects_by_slug: Dict[str, Dict[str, Any]] = {}

    for branch in candidate_branches:
        branch_name = branch["name"]
        commit_sha = branch["commit"]["sha"]
        tree_url = f"https://api.github.com/repos/{repo}/git/trees/{commit_sha}?recursive=1"
        try:
            tree_data = _api_get_json(tree_url)
        except Exception:
            continue

        tree_entries = tree_data.get("tree", [])
        blob_shas = {e["path"]: e.get("sha") for e in tree_entries if e.get("type") == "blob"}
        all_paths = list(blob_shas.keys())

        for path in all_paths:
            parts = path.split("/")
            # Format attendu : projects/<project_slug>/manifest.json
            if len(parts) == 3 and parts[0] == "projects" and parts[2] == "manifest.json":
                slug = parts[1]
                if slug.startswith("_"):
                    continue
                prefix = f"projects/{slug}/"
                project_files = [p for p in all_paths if p.startswith(prefix)]
                entry = {
                    "project_slug": slug,
                    "branch": branch_name,
                    "commit_sha": commit_sha,
                    "file_count": len(project_files),
                    "files": project_files,
                    "blob_shas": {p: blob_shas[p] for p in project_files},
                }
                # Si un projet existe à la fois sur arena/* et main, garder celui avec le plus de fichiers / arena/*
                existing = projects_by_slug.get(slug)
                if existing is None or len(project_files) > existing["file_count"]:
                    projects_by_slug[slug] = entry

    return sorted(projects_by_slug.values(), key=lambda x: x["project_slug"], reverse=True)


def list_local_projects(projects_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Liste les projets déjà présents localement dans projects/."""
    base = projects_dir or LOCAL_PROJECTS_DIR
    if not base.exists():
        return []
    result = []
    for sub in sorted(base.iterdir(), reverse=True):
        if not sub.is_dir() or sub.name.startswith("_"):
            continue
        manifest_path = sub / "manifest.json"
        if manifest_path.exists():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except Exception:
                manifest = {}
            result.append({
                "project_slug": sub.name,
                "local_path": str(sub),
                "title": manifest.get("title", sub.name),
                "scene_count": len(manifest.get("scenes", [])),
                "format": manifest.get("format", "9:16"),
            })
    return result


def sync_project_from_github(
    project_slug: Optional[str] = None,
    repo: Optional[str] = None,
    dest_root: Optional[Path] = None,
    force: bool = True,
) -> Dict[str, Any]:
    """Télécharge un projet complet (manifest + images + audios) depuis GitHub vers projects/<slug>/.

    Si `project_slug` est omis, télécharge automatiquement le projet le plus récent.
    """
    repo = repo or get_repo_slug()
    dest_root = dest_root or LOCAL_PROJECTS_DIR
    remote_projects = list_remote_projects(repo=repo)

    if not remote_projects:
        raise FileNotFoundError(
            f"Aucun projet trouvé sur GitHub ({repo}) dans le dossier 'projects/'. "
            "Assure-toi qu'Arena a bien généré et poussé les images/voix sur GitHub."
        )

    if project_slug:
        matches = [p for p in remote_projects if p["project_slug"] == project_slug]
        if not matches:
            available = ", ".join(p["project_slug"] for p in remote_projects)
            raise FileNotFoundError(
                f"Projet '{project_slug}' introuvable sur GitHub ({repo}). "
                f"Projets disponibles : {available}"
            )
        target = matches[0]
    else:
        target = remote_projects[0]

    slug = target["project_slug"]
    commit_sha = target["commit_sha"]
    local_project_dir = dest_root / slug
    local_project_dir.mkdir(parents=True, exist_ok=True)

    downloaded: List[str] = []
    prefix = f"projects/{slug}/"
    blob_shas = target.get("blob_shas", {})
    for repo_rel_path in target["files"]:
        rel_inside_project = repo_rel_path[len(prefix):]
        local_file = local_project_dir / rel_inside_project
        if force or not local_file.exists():
            _download_file(
                repo,
                commit_sha,
                repo_rel_path,
                local_file,
                blob_sha=blob_shas.get(repo_rel_path),
            )
            downloaded.append(rel_inside_project)

    return {
        "project_slug": slug,
        "branch": target["branch"],
        "commit_sha": commit_sha,
        "local_dir": str(local_project_dir),
        "downloaded_files": downloaded,
        "total_files": len(target["files"]),
    }
