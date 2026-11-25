"""Moteur d'animation Image-to-Video (Google Veo REST direct + Vertex AI + PixVerse API v2).

Anime les images clés `projects/<slug>/images/scene_XX.png` en véritables clips vidéo `.mp4`
(`projects/<slug>/videos/scene_XX.mp4`) avant l'assemblage automatique dans CapCut Desktop Windows.

Points clés :
- Appels REST directs (`requests`) vers Google Veo (`generativelanguage.googleapis.com` pour les clés
  Google AI Studio `AIza...` et `aiplatform.googleapis.com` pour Vertex AI `AQ...` / OAuth), contournant
  la restriction locale du SDK Python `google-genai 3.6+` et forçant `personGeneration="allow_adult"`
  requis en mode Image-to-Video.
- Bascule automatique entre Google Veo et PixVerse, et **tolérance aux quotas / crédits épuisés** :
  si seuls 2 clips passent (quota journalier) ou si le solde API est à 0, les scènes déjà animées
  sont conservées et `capcut_builder.py` complète automatiquement le montage CapCut sans planter.
"""

from __future__ import annotations

import argparse
import base64
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

VEO_MODELS_ORDER = [
    "veo-3.1-fast-generate-preview",
    "veo-3.1-generate-preview",
    "veo-3.0-fast-generate-001",
    "veo-3.0-generate-001",
    "veo-2.0-generate-001",
]


def load_local_config() -> Dict[str, Any]:
    if CONFIG_LOCAL_PATH.exists():
        try:
            return json.loads(CONFIG_LOCAL_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_api_keys_locally(
    veo_key: Optional[str] = None,
    pixverse_key: Optional[str] = None,
    gcp_project: Optional[str] = None,
) -> Path:
    cfg = load_local_config()
    if veo_key:
        cfg["veo_api_key"] = veo_key.strip()
    if pixverse_key:
        cfg["pixverse_api_key"] = pixverse_key.strip()
    if gcp_project:
        cfg["gcp_project"] = gcp_project.strip()
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
# 1. Google Veo — Client REST Direct (AI Studio `AIza...` & Vertex Express `AQ...`)
# ---------------------------------------------------------------------------

def _encode_image_for_veo(image_path: Path) -> Dict[str, str]:
    mime_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }
    mime_type = mime_map.get(image_path.suffix.lower(), "image/png")
    raw = image_path.read_bytes()
    return {
        "bytesBase64Encoded": base64.b64encode(raw).decode("utf-8"),
        "mimeType": mime_type,
    }


def _extract_and_save_veo_video(result: Dict[str, Any], output_mp4: Path, headers: Dict[str, str], api_key: str) -> Path:
    video_data: Optional[Dict[str, Any]] = None
    gvr = result.get("generateVideoResponse")
    if isinstance(gvr, dict) and gvr.get("generatedSamples"):
        video_data = gvr["generatedSamples"][0].get("video")
    elif result.get("generatedVideos"):
        video_data = result["generatedVideos"][0].get("video")
    elif result.get("videos"):
        video_data = result["videos"][0]

    if not isinstance(video_data, dict):
        raise RuntimeError(f"Format de réponse Veo inattendu : {str(result)[:300]}")

    output_mp4.parent.mkdir(parents=True, exist_ok=True)

    if "bytesBase64Encoded" in video_data:
        output_mp4.write_bytes(base64.b64decode(video_data["bytesBase64Encoded"]))
        return output_mp4

    uri = video_data.get("uri")
    if uri and uri.startswith("http"):
        dl_headers = dict(headers)
        r = requests.get(uri, headers=dl_headers, timeout=180)
        if r.status_code != 200 and "key=" not in uri:
            sep = "&" if "?" in uri else "?"
            r = requests.get(f"{uri}{sep}key={api_key}", timeout=180)
        r.raise_for_status()
        output_mp4.write_bytes(r.content)
        return output_mp4

    raise RuntimeError(f"Flux vidéo introuvable dans la réponse Veo : {list(video_data.keys())}")


def generate_clip_veo(
    image_path: Path,
    prompt: str,
    output_mp4: Path,
    api_key: str,
    negative_prompt: str = DEFAULT_NEGATIVE_PROMPT,
    aspect_ratio: str = "9:16",
    preferred_model: Optional[str] = None,
    poll_timeout_sec: int = 420,
) -> Path:
    models_to_try = [preferred_model] if preferred_model else VEO_MODELS_ORDER
    is_vertex_express_key = api_key.startswith("AQ.")

    # Définir les passerelles REST à tester selon le préfixe de la clé
    endpoints_to_try = []
    if is_vertex_express_key:
        endpoints_to_try.append((
            "Vertex-Express",
            "https://aiplatform.googleapis.com/v1beta1/publishers/google/models/{model}:predictLongRunning",
            "https://aiplatform.googleapis.com/v1beta1/{op_name}",
        ))
    else:
        endpoints_to_try.append((
            "Gemini-AI-Studio",
            "https://generativelanguage.googleapis.com/v1beta/models/{model}:predictLongRunning",
            "https://generativelanguage.googleapis.com/v1beta/{op_name}",
        ))

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key,
    }
    encoded_img = _encode_image_for_veo(image_path)
    errors_collected: List[str] = []

    for ep_label, submit_tmpl, poll_tmpl in endpoints_to_try:
        for model_id in models_to_try:
            dur = 6 if "veo-3" in model_id else 5
            submit_url = submit_tmpl.format(model=model_id)

            parameters: Dict[str, Any] = {
                "aspectRatio": aspect_ratio,
                "durationSeconds": dur,
                "sampleCount": 1,
                "personGeneration": "allow_adult",
            }
            if negative_prompt:
                parameters["negativePrompt"] = negative_prompt

            body = {
                "instances": [
                    {
                        "prompt": prompt,
                        "image": encoded_img,
                    }
                ],
                "parameters": parameters,
            }

            print(f"    [Veo/{ep_label}] Envoi vers '{model_id}' ({dur}s)...")
            resp = requests.post(submit_url, headers=headers, json=body, timeout=60)

            if resp.status_code != 200:
                short_err = resp.text.strip().replace("\n", " ")[:260]
                errors_collected.append(f"{ep_label}/{model_id} -> HTTP {resp.status_code}: {short_err}")
                # Si la clé elle-même est refusée pour predictLongRunning (401/403 API key not supported / Express mode)
                if resp.status_code in (401, 403) and (
                    "api keys are not supported" in short_err.lower()
                    or "express" in short_err.lower()
                    or "permission_denied" in short_err.lower()
                    or "billing" in short_err.lower()
                ):
                    break
                if resp.status_code == 429:
                    raise RuntimeError(f"Quota Google Veo atteint (HTTP 429) : {short_err}")
                continue

            op_data = resp.json()
            op_name = op_data.get("name")
            if not op_name:
                errors_collected.append(f"{ep_label}/{model_id} -> Réponse sans 'name': {op_data}")
                continue

            print(f"    [Veo/{ep_label}] Opération démarrée : {op_name}")
            poll_url = poll_tmpl.format(op_name=op_name.lstrip("/"))
            start_t = time.time()

            while time.time() - start_t < poll_timeout_sec:
                time.sleep(10)
                pr = requests.get(poll_url, headers=headers, timeout=30)
                if pr.status_code != 200:
                    raise RuntimeError(f"Erreur polling Veo ({pr.status_code}) : {pr.text[:240]}")
                pjson = pr.json()
                if pjson.get("done"):
                    if "error" in pjson:
                        raise RuntimeError(f"Erreur génération Veo : {pjson['error']}")
                    result_payload = pjson.get("response") or pjson.get("result") or {}
                    return _extract_and_save_veo_video(result_payload, output_mp4, headers, api_key)
                elapsed = int(time.time() - start_t)
                print(f"    [Veo/{ep_label}] Génération en cours... ({elapsed}s)")

            raise TimeoutError(f"Délai dépassé ({poll_timeout_sec}s) sur Veo {model_id}")

    hint = ""
    if is_vertex_express_key:
        hint = (
            " | ASTUCE : Votre clé commence par 'AQ.' (Vertex AI Express Mode), or Google bloque souvent "
            "les opérations longues Veo (predictLongRunning) en mode Express. Créez une clé Google AI Studio "
            "classique commençant par 'AIza...' sur https://aistudio.google.com/apikey (reliée au même projet Cloud) !"
        )
    raise RuntimeError(" ; ".join(errors_collected[:2]) + hint)


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
    return int(data["Resp"]["img_id"])


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
            err_msg = str(data.get("ErrMsg", data))
            last_err = f"{model_name} -> {err_msg}"
            # Si solde insuffisant sur le compte API PixVerse, inutile de retenter 4 modèles
            if "insufficient balance" in err_msg.lower() or "top up" in err_msg.lower():
                break

    if video_id is None:
        raise RuntimeError(f"Échec création PixVerse : {last_err}")

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
# 3. Orchestrateur résilient (`manifest.json` -> `videos/scene_XX.mp4`)
# ---------------------------------------------------------------------------

def animate_project_scenes(
    project_dir: Path,
    provider: str = "auto",
    veo_key: Optional[str] = None,
    pixverse_key: Optional[str] = None,
    force: bool = False,
    max_veo_clips: Optional[int] = None,
    strict: bool = False,
) -> Dict[str, Any]:
    """Anime les scènes d'un projet en clips `.mp4` sans bloquer le montage CapCut en cas de quota épuisé."""
    project_dir = Path(project_dir).resolve()
    manifest_path = project_dir / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"manifest.json introuvable dans {project_dir}")

    keys = resolve_keys(veo_key, pixverse_key)
    provider = provider.lower().strip()

    if not keys["veo"] and not keys["pixverse"]:
        msg = (
            "Aucune clé API vidéo trouvée dans config.local.json. "
            "Montage CapCut poursuivi avec animations caméra natives haute fluidité."
        )
        if strict:
            raise RuntimeError(msg)
        print(f"[!] {msg}")
        return {"project": project_dir.name, "animated_scenes": 0, "fallback_scenes": 0, "scenes": []}

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    scenes: List[Dict[str, Any]] = manifest.get("scenes", [])
    fmt = str(manifest.get("format", "9:16"))
    aspect_ratio = "9:16" if fmt in ("9:16", "vertical") else ("16:9" if fmt in ("16:9", "horizontal") else "1:1")

    veo_used = 0
    veo_disabled = not bool(keys["veo"]) or provider == "pixverse"
    pixverse_disabled = not bool(keys["pixverse"]) or provider == "veo"
    summary: List[Dict[str, Any]] = []

    for idx, scene in enumerate(scenes):
        scene_id = scene.get("id") or f"scene_{idx + 1:02d}"
        img_rel = scene.get("image") or f"images/{scene_id}.png"
        vid_rel = scene.get("video") or f"videos/{scene_id}.mp4"
        img_path = (project_dir / img_rel).resolve()
        out_mp4 = (project_dir / vid_rel).resolve()

        if out_mp4.exists() and out_mp4.stat().st_size > 10_000 and not force:
            print(f"[{idx + 1}/{len(scenes)}] {scene_id} : clip MP4 déjà présent ({out_mp4.name}), conservé.")
            summary.append({"id": scene_id, "status": "cached", "video": str(out_mp4)})
            continue

        if veo_disabled and pixverse_disabled:
            summary.append({"id": scene_id, "status": "native_capcut_motion"})
            continue

        if not img_path.exists():
            raise FileNotFoundError(f"Image source introuvable pour {scene_id} : {img_path}")

        v_prompt = (
            scene.get("video_prompt")
            or "Subtle natural handheld camera motion, lifelike lighting, keep subject and product packaging completely stable and identical."
        )
        neg_prompt = scene.get("negative_prompt") or DEFAULT_NEGATIVE_PROMPT

        print(f"[{idx + 1}/{len(scenes)}] Animation de {scene_id} depuis {img_rel}...")

        order: List[str] = []
        if not veo_disabled and (max_veo_clips is None or veo_used < max_veo_clips):
            order.append("veo")
        if not pixverse_disabled:
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
                print(f"    [!] {engine} indisponible sur {scene_id} : {exc}")
                if engine == "veo":
                    veo_disabled = True
                elif engine == "pixverse":
                    pixverse_disabled = True

        if used_engine is None:
            if strict:
                raise RuntimeError(f"Impossible d'animer {scene_id} : {scene_err}")
            print(
                f"    -> Aucun moteur cloud actif pour {scene_id} ; "
                "bascule automatique sur l'animation caméra native CapCut (handheld UGC / Ken Burns)."
            )
            summary.append({"id": scene_id, "status": "native_capcut_motion", "reason": str(scene_err)})
            continue

        size_kb = round(out_mp4.stat().st_size / 1024, 1)
        print(f"    [OK] {out_mp4.name} généré via {used_engine} ({size_kb} Ko)")
        summary.append({"id": scene_id, "status": "generated", "provider": used_engine, "video": str(out_mp4)})

    animated_count = sum(1 for s in summary if s["status"] in ("generated", "cached"))
    fallback_count = len(summary) - animated_count
    return {
        "project": project_dir.name,
        "animated_mp4_scenes": animated_count,
        "native_motion_scenes": fallback_count,
        "scenes": summary,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Anime les scènes d'un projet Arena en vidéos MP4 via Google Veo et/ou PixVerse."
    )
    parser.add_argument("--save-keys", action="store_true", help="Enregistre localement les clés API dans config.local.json.")
    parser.add_argument("--veo-key", help="Clé API Google AI Studio (AIza...) ou Vertex.")
    parser.add_argument("--pixverse-key", help="Clé API PixVerse (sk-...).")
    parser.add_argument("--project", help="Slug du projet dans projects/<slug> (par défaut: plus récent).")
    parser.add_argument("--provider", default="auto", choices=["auto", "pixverse", "veo"])
    parser.add_argument("--max-veo-clips", type=int, default=None)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--strict", action="store_true", help="Échouer avec code d'erreur si aucune vidéo MP4 ne peut être générée.")
    parser.add_argument("--local-only", action="store_true")
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
        strict=args.strict,
    )
    print(json.dumps(res, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
