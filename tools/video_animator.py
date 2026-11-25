"""Moteur d'animation Image-to-Video (Google Veo via Gemini/Vertex AI + PixVerse API v2).

Anime les images clés `projects/<slug>/images/scene_XX.png` en véritables clips vidéo `.mp4`
(`projects/<slug>/videos/scene_XX.mp4`) avant l'assemblage automatique dans CapCut Desktop Windows.

Sécurité :
- Les clés API sont lues exclusivement depuis `config.local.json` (ignoré par Git) ou les variables
  d'environnement (`VEO_API_KEY` / `GOOGLE_API_KEY` / `GEMINI_API_KEY` et `PIXVERSE_API_KEY`).
- Aucune clé n'est jamais stockée dans le dépôt Git.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parent.parent
LOCAL_PROJECTS_DIR = REPO_ROOT / "projects"
CONFIG_LOCAL_PATH = REPO_ROOT / "config.local.json"

DEFAULT_NEGATIVE_PROMPT = (
    "warped text, melted label, morphing bottle or pouch, extra fingers, extra hands, "
    "deformed face, fast spin, 360 rotation, blurry, watermark, subtitles, text overlay, cartoon"
)


def load_local_config() -> Dict[str, Any]:
    if CONFIG_LOCAL_PATH.exists():
        try:
            return json.loads(CONFIG_LOCAL_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_api_keys_locally(veo_key: Optional[str] = None, pixverse_key: Optional[str] = None) -> Path:
    cfg = load_local_config()
    if veo_key:
        cfg["veo_api_key"] = veo_key.strip()
    if pixverse_key:
        cfg["pixverse_api_key"] = pixverse_key.strip()
    CONFIG_LOCAL_PATH.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    return CONFIG_LOCAL_PATH


def resolve_keys(
    cli_veo_key: Optional[str] = None,
    cli_pixverse_key: Optional[str] = None,
) -> Dict[str, str]:
    cfg = load_local_config()
    veo = (
        cli_veo_key
        or os.environ.get("VEO_API_KEY")
        or os.environ.get("GOOGLE_API_KEY")
        or os.environ.get("GEMINI_API_KEY")
        or cfg.get("veo_api_key")
        or ""
    ).strip()
    pixverse = (
        cli_pixverse_key
        or os.environ.get("PIXVERSE_API_KEY")
        or cfg.get("pixverse_api_key")
        or ""
    ).strip()
    return {"veo": veo, "pixverse": pixverse}


# ---------------------------------------------------------------------------
# 1. Google Veo (via SDK unifié `google-genai` — clés `AQ.` Vertex Express ou `AIza` Gemini)
# ---------------------------------------------------------------------------

def generate_clip_veo(
    image_path: Path,
    prompt: str,
    output_mp4: Path,
    api_key: str,
    negative_prompt: str = DEFAULT_NEGATIVE_PROMPT,
    aspect_ratio: str = "9:16",
    preferred_model: Optional[str] = None,
    poll_timeout_sec: int = 360,
) -> Path:
    from google import genai
    from google.genai import types

    # Les clés commençant par "AQ." sont des clés Google Cloud Vertex AI Express Mode
    use_vertex = api_key.startswith("AQ.")
    clients_to_try = []
    if use_vertex:
        clients_to_try.append(("vertexai-express", lambda: genai.Client(vertexai=True, api_key=api_key)))
        clients_to_try.append(("gemini-api", lambda: genai.Client(api_key=api_key)))
    else:
        clients_to_try.append(("gemini-api", lambda: genai.Client(api_key=api_key)))

    models_to_try = (
        [preferred_model]
        if preferred_model
        else [
            "veo-3.1-fast-generate-001",
            "veo-3.1-lite-generate-preview",
            "veo-3.0-fast-generate-001",
            "veo-2.0-generate-001",
        ]
    )

    # Charger l'image de départ proprement via types.Image.from_file (ou PIL fallback)
    try:
        genai_img = types.Image.from_file(location=str(image_path))
    except Exception:
        genai_img = Image.open(image_path)

    last_err: Optional[Exception] = None
    for backend_label, make_client in clients_to_try:
        try:
            client = make_client()
        except Exception as e:
            last_err = e
            continue

        for model_id in models_to_try:
            for dur in (6, 8, 5):
                try:
                    print(f"    [Veo/{backend_label}] Essai modèle '{model_id}' ({dur}s)...")
                    cfg_kwargs: Dict[str, Any] = {
                        "aspect_ratio": aspect_ratio,
                        "number_of_videos": 1,
                        "duration_seconds": dur,
                    }
                    if negative_prompt:
                        cfg_kwargs["negative_prompt"] = negative_prompt

                    operation = client.models.generate_videos(
                        model=model_id,
                        prompt=prompt,
                        image=genai_img,
                        config=types.GenerateVideosConfig(**cfg_kwargs),
                    )

                    deadline = time.time() + poll_timeout_sec
                    while not operation.done:
                        if time.time() > deadline:
                            raise TimeoutError(f"Délai dépassé ({poll_timeout_sec}s) sur Veo {model_id}")
                        time.sleep(10)
                        operation = client.operations.get(operation)

                    resp_obj = getattr(operation, "response", None) or getattr(operation, "result", None)
                    gen_videos = getattr(resp_obj, "generated_videos", None) or []
                    if not gen_videos:
                        err_detail = getattr(operation, "error", None)
                        raise RuntimeError(f"Aucune vidéo retournée par Veo ({err_detail})")

                    vid_obj = gen_videos[0].video
                    output_mp4.parent.mkdir(parents=True, exist_ok=True)

                    # Cas 1 : octets MP4 déjà présents (Vertex AI)
                    raw_bytes = getattr(vid_obj, "video_bytes", None)
                    if raw_bytes:
                        output_mp4.write_bytes(raw_bytes)
                        return output_mp4

                    # Cas 2 : téléchargement via client.files.download (Gemini Developer API)
                    try:
                        downloaded = client.files.download(file=vid_obj)
                        if isinstance(downloaded, (bytes, bytearray)):
                            output_mp4.write_bytes(downloaded)
                            return output_mp4
                    except Exception:
                        pass

                    if hasattr(vid_obj, "save"):
                        vid_obj.save(str(output_mp4))
                        if output_mp4.exists() and output_mp4.stat().st_size > 1000:
                            return output_mp4

                    uri = getattr(vid_obj, "uri", None)
                    if uri and uri.startswith("http"):
                        r = requests.get(uri, headers={"x-goog-api-key": api_key}, timeout=120)
                        r.raise_for_status()
                        output_mp4.write_bytes(r.content)
                        return output_mp4

                    raise RuntimeError("Impossible d'extraire le flux MP4 depuis la réponse Veo.")
                except Exception as exc:
                    last_err = exc
                    msg = str(exc).lower()
                    # Si la durée seule est refusée, tester la durée suivante sur ce modèle
                    if "duration" in msg:
                        continue
                    # Sinon passer au modèle suivant
                    break

    raise RuntimeError(f"Échec Google Veo : {last_err}")


# ---------------------------------------------------------------------------
# 2. PixVerse OpenAPI v2 (`https://app-api.pixverse.ai/openapi/v2`)
# ---------------------------------------------------------------------------

PIXVERSE_BASE_URL = "https://app-api.pixverse.ai"


def _pixverse_upload_image(image_path: Path, api_key: str) -> int:
    with Image.open(image_path) as im:
        rgb = im.convert("RGB")
        buf = io.BytesIO()
        rgb.save(buf, format="JPEG", quality=92)
        jpeg_bytes = buf.getvalue()

    headers = {
        "API-KEY": api_key,
        "Ai-trace-id": str(uuid.uuid4()),
    }
    files = {"image": ("frame.jpg", jpeg_bytes, "image/jpeg")}
    resp = requests.post(
        f"{PIXVERSE_BASE_URL}/openapi/v2/image/upload",
        headers=headers,
        files=files,
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("ErrCode") != 0 or not isinstance(data.get("Resp"), dict):
        raise RuntimeError(f"PixVerse upload refusé : {data.get('ErrMsg', data)}")
    img_id = int(data["Resp"]["img_id"])
    return img_id


def generate_clip_pixverse(
    image_path: Path,
    prompt: str,
    output_mp4: Path,
    api_key: str,
    negative_prompt: str = DEFAULT_NEGATIVE_PROMPT,
    duration: int = 5,
    quality: str = "720p",
    preferred_model: Optional[str] = None,
    poll_timeout_sec: int = 300,
) -> Path:
    img_id = _pixverse_upload_image(image_path, api_key)
    models_to_try = [preferred_model] if preferred_model else ["v6", "v4.5", "v4", "v3.5"]

    video_id: Optional[int] = None
    last_err: Optional[str] = None

    for model_name in models_to_try:
        payload: Dict[str, Any] = {
            "model": model_name,
            "img_id": img_id,
            "prompt": prompt[:2000],
            "negative_prompt": negative_prompt[:2000],
            "duration": int(duration),
            "quality": quality.lower(),
            "motion_mode": "normal",
        }
        headers = {
            "API-KEY": api_key,
            "Ai-trace-id": str(uuid.uuid4()),
            "Content-Type": "application/json",
        }
        resp = requests.post(
            f"{PIXVERSE_BASE_URL}/openapi/v2/video/img/generate",
            headers=headers,
            json=payload,
            timeout=60,
        )
        try:
            data = resp.json()
        except Exception:
            last_err = f"HTTP {resp.status_code}: {resp.text[:200]}"
            continue

        if resp.status_code == 200 and data.get("ErrCode") == 0 and isinstance(data.get("Resp"), dict):
            video_id = int(data["Resp"]["video_id"])
            print(f"    [PixVerse/{model_name}] Tâche lancée (video_id={video_id})...")
            break
        else:
            last_err = f"{model_name} -> {data.get('ErrMsg', data)}"

    if video_id is None:
        raise RuntimeError(f"Échec création PixVerse : {last_err}")

    # Polling toutes les 5 secondes jusqu'à status == 1 (succès)
    deadline = time.time() + poll_timeout_sec
    while time.time() < deadline:
        time.sleep(5)
        poll_headers = {
            "API-KEY": api_key,
            "Ai-trace-id": str(uuid.uuid4()),
        }
        pr = requests.get(
            f"{PIXVERSE_BASE_URL}/openapi/v2/video/result/{video_id}",
            headers=poll_headers,
            timeout=30,
        )
        pr.raise_for_status()
        pdata = pr.json()
        if pdata.get("ErrCode") != 0:
            raise RuntimeError(f"Erreur polling PixVerse : {pdata.get('ErrMsg', pdata)}")

        resp_body = pdata.get("Resp") or {}
        status = resp_body.get("status")
        if status == 1:
            video_url = resp_body.get("url")
            if not video_url:
                raise RuntimeError(f"PixVerse status=1 mais URL absente : {resp_body}")
            dl = requests.get(video_url, timeout=120)
            dl.raise_for_status()
            output_mp4.parent.mkdir(parents=True, exist_ok=True)
            output_mp4.write_bytes(dl.content)
            return output_mp4
        if status in (2, 3, 4, 6, 7, 8):
            raise RuntimeError(f"PixVerse génération échouée/rejetée (status={status}) : {resp_body}")

    raise TimeoutError(f"Délai dépassé ({poll_timeout_sec}s) en attendant PixVerse video_id={video_id}")


# ---------------------------------------------------------------------------
# 3. Orchestrateur de Projet (`manifest.json` -> `videos/scene_XX.mp4`)
# ---------------------------------------------------------------------------

def animate_project_scenes(
    project_dir: Path,
    provider: str = "auto",
    veo_key: Optional[str] = None,
    pixverse_key: Optional[str] = None,
    force: bool = False,
    max_veo_clips: Optional[int] = None,
) -> Dict[str, Any]:
    """Anime toutes les scènes d'un projet en clips `.mp4`.

    En mode `auto` :
    - Utilise Google Veo si une clé Veo est présente (dans la limite `max_veo_clips` si précisée),
      puis bascule automatiquement et sans coupure sur PixVerse en cas de limite/quota ou d'erreur.
    - Si seule la clé PixVerse est renseignée, utilise PixVerse directement.
    """
    project_dir = Path(project_dir).resolve()
    manifest_path = project_dir / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"manifest.json introuvable dans {project_dir}")

    keys = resolve_keys(veo_key, pixverse_key)
    provider = provider.lower().strip()

    if provider == "veo" and not keys["veo"]:
        raise RuntimeError("Clé Google Veo absente. Enregistre-la avec --save-keys --veo-key ...")
    if provider == "pixverse" and not keys["pixverse"]:
        raise RuntimeError("Clé PixVerse absente. Enregistre-la avec --save-keys --pixverse-key ...")
    if provider == "auto" and not (keys["veo"] or keys["pixverse"]):
        raise RuntimeError(
            "Aucune clé API vidéo trouvée dans config.local.json ou l'environnement. "
            "Lance d'abord : python -m tools.video_animator --save-keys --veo-key ... --pixverse-key ..."
        )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    scenes: List[Dict[str, Any]] = manifest.get("scenes", [])
    fmt = str(manifest.get("format", "9:16"))
    aspect_ratio = "9:16" if fmt in ("9:16", "vertical") else ("16:9" if fmt in ("16:9", "horizontal") else "1:1")

    veo_used = 0
    veo_disabled_for_batch = False
    summary: List[Dict[str, Any]] = []

    for idx, scene in enumerate(scenes):
        scene_id = scene.get("id") or f"scene_{idx + 1:02d}"
        img_rel = scene.get("image") or f"images/{scene_id}.png"
        vid_rel = scene.get("video") or f"videos/{scene_id}.mp4"
        img_path = (project_dir / img_rel).resolve()
        out_mp4 = (project_dir / vid_rel).resolve()

        if out_mp4.exists() and out_mp4.stat().st_size > 10_000 and not force:
            print(f"[{idx + 1}/{len(scenes)}] {scene_id} : déjà animé ({out_mp4.name}), conservé.")
            summary.append({"id": scene_id, "status": "cached", "video": str(out_mp4)})
            continue

        if not img_path.exists():
            raise FileNotFoundError(f"Image source introuvable pour {scene_id} : {img_path}")

        v_prompt = (
            scene.get("video_prompt")
            or "Subtle natural handheld camera motion, lifelike lighting, keep subject and product packaging completely stable and identical."
        )
        neg_prompt = scene.get("negative_prompt") or DEFAULT_NEGATIVE_PROMPT

        print(f"[{idx + 1}/{len(scenes)}] Animation de {scene_id} depuis {img_rel}...")

        # Construire l'ordre des moteurs à tenter pour cette scène
        order: List[str] = []
        if provider == "veo":
            order = ["veo"]
        elif provider == "pixverse":
            order = ["pixverse"]
        else:  # auto
            can_try_veo = (
                bool(keys["veo"])
                and not veo_disabled_for_batch
                and (max_veo_clips is None or veo_used < max_veo_clips)
            )
            if can_try_veo:
                order.append("veo")
            if keys["pixverse"]:
                order.append("pixverse")

        used_engine = None
        scene_err: Optional[Exception] = None
        for engine in order:
            try:
                if engine == "veo":
                    generate_clip_veo(
                        image_path=img_path,
                        prompt=v_prompt,
                        output_mp4=out_mp4,
                        api_key=keys["veo"],
                        negative_prompt=neg_prompt,
                        aspect_ratio=aspect_ratio,
                    )
                    veo_used += 1
                else:
                    generate_clip_pixverse(
                        image_path=img_path,
                        prompt=v_prompt,
                        output_mp4=out_mp4,
                        api_key=keys["pixverse"],
                        negative_prompt=neg_prompt,
                        duration=5,
                        quality="720p",
                    )
                used_engine = engine
                break
            except Exception as exc:
                scene_err = exc
                print(f"    [!] {engine} indisponible sur {scene_id} ({exc})")
                if engine == "veo" and provider == "auto" and keys["pixverse"]:
                    print("    -> Bascule automatique sur PixVerse pour la suite...")
                    veo_disabled_for_batch = True

        if used_engine is None:
            raise RuntimeError(f"Impossible d'animer {scene_id} : {scene_err}")

        size_kb = round(out_mp4.stat().st_size / 1024, 1)
        print(f"    [OK] {out_mp4.name} généré via {used_engine} ({size_kb} Ko)")
        summary.append({"id": scene_id, "status": "generated", "provider": used_engine, "video": str(out_mp4)})

    return {"project": project_dir.name, "animated_scenes": len(summary), "scenes": summary}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Anime les scènes d'un projet Arena en vidéos MP4 via Google Veo et/ou PixVerse."
    )
    parser.add_argument("--save-keys", action="store_true", help="Enregistre localement les clés API dans config.local.json (ignoré par Git).")
    parser.add_argument("--veo-key", help="Clé API Google Veo / Vertex Express / Gemini.")
    parser.add_argument("--pixverse-key", help="Clé API PixVerse (sk-...).")
    parser.add_argument("--project", help="Slug du projet dans projects/<slug> (par défaut: plus récent).")
    parser.add_argument("--provider", default="auto", choices=["auto", "pixverse", "veo"], help="Moteur vidéo (auto = Veo puis fallback auto PixVerse).")
    parser.add_argument("--max-veo-clips", type=int, default=None, help="Limiter le nombre de clips Veo avant relais PixVerse (ex: 2).")
    parser.add_argument("--force", action="store_true", help="Régénérer même si videos/scene_XX.mp4 existe déjà.")
    parser.add_argument("--local-only", action="store_true", help="Ne pas synchroniser depuis GitHub avant d'animer.")
    args = parser.parse_args()

    if args.save_keys:
        saved_path = save_api_keys_locally(veo_key=args.veo_key, pixverse_key=args.pixverse_key)
        print(f"[OK] Clés enregistrées localement dans {saved_path} (fichier exclu de GitHub).")
        if not args.project and not args.local_only:
            return

    from tools.github_sync import list_local_projects, sync_project_from_github

    if args.local_only:
        if args.project:
            proj_dir = LOCAL_PROJECTS_DIR / args.project
        else:
            locals_list = list_local_projects()
            if not locals_list:
                print("Aucun projet local trouvé.", file=sys.stderr)
                sys.exit(1)
            proj_dir = Path(locals_list[0]["local_path"])
    else:
        sync_info = sync_project_from_github(project_slug=args.project)
        proj_dir = Path(sync_info["local_dir"])

    res = animate_project_scenes(
        project_dir=proj_dir,
        provider=args.provider,
        veo_key=args.veo_key,
        pixverse_key=args.pixverse_key,
        force=args.force,
        max_veo_clips=args.max_veo_clips,
    )
    print(json.dumps(res, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
