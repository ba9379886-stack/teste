"""Générateur automatique de projets CapCut Desktop (Windows) à partir d'un projet Arena.

Prend un dossier `projects/<project_slug>/` (contenant `manifest.json`, `images/` et `audio/`)
et assemble directement un brouillon CapCut prêt à ouvrir et exporter :
- Format Vertical 9:16 (1080x1920) par défaut (ou 16:9 / 1:1)
- Voix off calées à la microseconde près
- Images mises à l'échelle sans bandes noires + animations Ken Burns (zoom/pan) fluides
- Transitions CapCut 100 % gratuites (sans blocage CapCut Pro)
- Sous-titres dynamiques style TikTok/Shorts (découpés en groupes courts) + export .srt
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import shutil
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pycapcut as cc
from pycapcut import (
    ClipSettings,
    KeyframeProperty,
    SEC,
    TextBorder,
    TextShadow,
    TextStyle,
    Timerange,
    TrackType,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
LOCAL_PROJECTS_DIR = REPO_ROOT / "projects"

FORMAT_RESOLUTIONS: Dict[str, Tuple[int, int]] = {
    "9:16": (1080, 1920),
    "vertical": (1080, 1920),
    "16:9": (1920, 1080),
    "horizontal": (1920, 1080),
    "1:1": (1080, 1080),
}

COLOR_PRESETS: Dict[str, Tuple[float, float, float]] = {
    "white": (1.0, 1.0, 1.0),
    "blanc": (1.0, 1.0, 1.0),
    "yellow": (1.0, 0.92, 0.18),
    "jaune": (1.0, 0.92, 0.18),
    "cyan": (0.25, 0.95, 1.0),
}

DEFAULT_MOTION_CYCLE = ["zoom_in", "zoom_out", "pan_up", "zoom_in", "pan_down", "zoom_out"]


def _load_local_config() -> Dict[str, Any]:
    cfg_path = REPO_ROOT / "config.local.json"
    if cfg_path.exists():
        try:
            return json.loads(cfg_path.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_local_config(updates: Dict[str, Any]) -> Path:
    cfg_path = REPO_ROOT / "config.local.json"
    current = _load_local_config()
    current.update(updates)
    cfg_path.write_text(json.dumps(current, indent=2, ensure_ascii=False), encoding="utf-8")
    return cfg_path


def _read_capcut_custom_draft_path(local_appdata: Path) -> Optional[Path]:
    """Vérifie si l'utilisateur a personnalisé l'emplacement des brouillons dans les paramètres CapCut."""
    global_setting = local_appdata / "CapCut" / "User Data" / "Config" / "globalSetting"
    if not global_setting.exists():
        return None
    try:
        content = global_setting.read_text(encoding="utf-8", errors="ignore")
        for line in content.splitlines():
            if "custom_draft_path" in line:
                _, _, val = line.partition("=")
                candidate = val.strip().strip('"').strip("'")
                if candidate and Path(candidate).exists():
                    return Path(candidate)
    except Exception:
        pass
    return None


def detect_capcut_drafts_dir(explicit_dir: Optional[str] = None) -> Path:
    """Détecte automatiquement le dossier des projets (Drafts) de CapCut Desktop sur Windows."""
    if explicit_dir:
        p = Path(os.path.expandvars(os.path.expanduser(explicit_dir)))
        if p.exists():
            return p
        raise FileNotFoundError(f"Le dossier CapCut spécifié n'existe pas : {p}")

    env_dir = os.environ.get("CAPCUT_DRAFTS_DIR")
    if env_dir:
        p = Path(os.path.expandvars(os.path.expanduser(env_dir)))
        if p.exists():
            return p

    cfg = _load_local_config()
    if cfg.get("capcut_drafts_dir"):
        p = Path(os.path.expandvars(os.path.expanduser(cfg["capcut_drafts_dir"])))
        if p.exists():
            return p

    local_appdata_str = os.environ.get("LOCALAPPDATA")
    candidates: List[Path] = []

    if local_appdata_str:
        local_appdata = Path(local_appdata_str)
        custom = _read_capcut_custom_draft_path(local_appdata)
        if custom:
            candidates.append(custom)

        # Installation Windows standard
        candidates.append(
            local_appdata / "CapCut" / "User Data" / "Projects" / "com.lveditor.draft"
        )

        # Installation Windows via Microsoft Store
        store_glob = str(
            local_appdata
            / "Packages"
            / "BytedancePte.Ltd.CapCut*"
            / "LocalCache"
            / "Local"
            / "CapCut"
            / "User Data"
            / "Projects"
            / "com.lveditor.draft"
        )
        for match in glob.glob(store_glob):
            candidates.append(Path(match))

    # Fallback macOS au cas où
    home = Path.home()
    candidates.append(
        home / "Movies" / "CapCut" / "User Data" / "Projects" / "com.lveditor.draft"
    )

    for candidate in candidates:
        if candidate.exists() and candidate.is_dir():
            return candidate

    raise FileNotFoundError(
        "Dossier des projets CapCut Desktop introuvable automatiquement. "
        "Ouvre CapCut sur Windows -> Paramètres (icône engrenage en haut à droite) -> "
        "'Enregistrer dans' (Drafts Location), copie ce chemin, puis passe-le à l'outil "
        "ou enregistre-le dans config.local.json sous la clé 'capcut_drafts_dir'."
    )


def split_into_tiktok_chunks(text: str, max_chars: int = 28, max_words: int = 5) -> List[str]:
    """Découpe une phrase de narration en courts blocs dynamiques adaptés aux Shorts/TikTok."""
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return []

    # Découper d'abord aux pauses naturelles fortes tout en gardant la ponctuation attachée
    clauses = re.split(r"(?<=[,.;:!?…])\s+", cleaned)
    chunks: List[str] = []

    for clause in clauses:
        words = clause.split(" ")
        current: List[str] = []
        for word in words:
            if not word:
                continue
            tentative = " ".join(current + [word])
            if current and (len(tentative) > max_chars or len(current) >= max_words):
                chunks.append(" ".join(current))
                current = [word]
            else:
                current.append(word)
        if current:
            chunks.append(" ".join(current))

    return [c.strip() for c in chunks if c.strip()]


def _format_srt_timestamp(us: int) -> str:
    total_ms = max(0, int(round(us / 1000)))
    hours = total_ms // 3_600_000
    rem = total_ms % 3_600_000
    minutes = rem // 60_000
    rem %= 60_000
    seconds = rem // 1000
    millis = rem % 1000
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def write_srt_file(srt_entries: List[Tuple[int, int, str]], srt_path: Path) -> None:
    """Écrit un fichier .srt standard à partir d'une liste de tuples (start_us, end_us, text)."""
    lines: List[str] = []
    for idx, (start_us, end_us, text) in enumerate(srt_entries, start=1):
        lines.append(str(idx))
        lines.append(f"{_format_srt_timestamp(start_us)} --> {_format_srt_timestamp(end_us)}")
        lines.append(text)
        lines.append("")
    srt_path.write_text("\n".join(lines), encoding="utf-8")


def _resolve_free_transition(name: Optional[str]) -> Optional[cc.TransitionType]:
    if not name:
        return None
    key = name.strip().lower()
    mapping = {
        "cut": None,
        "none": None,
        "aucune": None,
        "dissolve": cc.TransitionType.叠化,
        "fade": cc.TransitionType.叠化,
        "mix": cc.TransitionType.叠化,
        "fade_black": cc.TransitionType.闪黑,
        "black": cc.TransitionType.闪黑,
        "flash": cc.TransitionType.White_Flash,
        "white_flash": cc.TransitionType.White_Flash,
        "blur": cc.TransitionType.转场_模糊,
        "slide": cc.TransitionType.滑动,
    }
    return mapping.get(key)


def _apply_motion_keyframes(
    seg: cc.VideoSegment,
    motion: str,
    cover_scale: float,
    duration_us: int,
    zoom_intensity: float = 0.12,
) -> None:
    """Applique un effet Ken Burns fluide (zoom ou panoramique) sans jamais afficher de bords noirs."""
    m = (motion or "zoom_in").strip().lower()
    s_min = round(cover_scale * 1.005, 4)
    s_max = round(cover_scale * (1.0 + max(0.02, zoom_intensity)), 4)
    pan_offset = min(0.05, max(0.015, zoom_intensity * 0.4))

    if m == "zoom_in":
        seg.add_keyframe(KeyframeProperty.uniform_scale, 0, s_min)
        seg.add_keyframe(KeyframeProperty.uniform_scale, duration_us, s_max)
    elif m == "zoom_out":
        seg.add_keyframe(KeyframeProperty.uniform_scale, 0, s_max)
        seg.add_keyframe(KeyframeProperty.uniform_scale, duration_us, s_min)
    elif m == "pan_up":
        seg.add_keyframe(KeyframeProperty.uniform_scale, 0, s_max)
        seg.add_keyframe(KeyframeProperty.position_y, 0, -pan_offset)
        seg.add_keyframe(KeyframeProperty.position_y, duration_us, pan_offset)
    elif m == "pan_down":
        seg.add_keyframe(KeyframeProperty.uniform_scale, 0, s_max)
        seg.add_keyframe(KeyframeProperty.position_y, 0, pan_offset)
        seg.add_keyframe(KeyframeProperty.position_y, duration_us, -pan_offset)
    elif m == "pan_left":
        seg.add_keyframe(KeyframeProperty.uniform_scale, 0, s_max)
        seg.add_keyframe(KeyframeProperty.position_x, 0, pan_offset)
        seg.add_keyframe(KeyframeProperty.position_x, duration_us, -pan_offset)
    elif m == "pan_right":
        seg.add_keyframe(KeyframeProperty.uniform_scale, 0, s_max)
        seg.add_keyframe(KeyframeProperty.position_x, 0, -pan_offset)
        seg.add_keyframe(KeyframeProperty.position_x, duration_us, pan_offset)
    else:
        seg.add_keyframe(KeyframeProperty.uniform_scale, 0, s_min)


def _enrich_draft_meta_info(
    draft_dir: Path,
    drafts_root: Path,
    draft_name: str,
    total_duration_us: int,
    cover_source_image: Optional[Path],
) -> None:
    """Renseigne les métadonnées CapCut (ID unique, titre, miniature, durée, dates)."""
    meta_path = draft_dir / "draft_meta_info.json"
    if not meta_path.exists():
        return

    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception:
        return

    now_us = int(time.time() * 1_000_000)
    cover_path_str = ""
    if cover_source_image and cover_source_image.exists():
        ext = cover_source_image.suffix or ".png"
        cover_dest = draft_dir / f"draft_cover{ext}"
        shutil.copy2(cover_source_image, cover_dest)
        cover_path_str = str(cover_dest.resolve()).replace("\\", "/")

    meta["draft_id"] = str(uuid.uuid4()).upper()
    meta["draft_name"] = draft_name
    meta["draft_fold_path"] = str(draft_dir.resolve()).replace("\\", "/")
    meta["draft_root_path"] = str(drafts_root.resolve()).replace("\\", "/")
    meta["draft_cover"] = cover_path_str
    meta["tm_duration"] = total_duration_us
    meta["tm_draft_create"] = now_us
    meta["tm_draft_modified"] = now_us

    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")


def build_capcut_draft(
    project_dir: Path,
    drafts_dir: Optional[Path] = None,
    draft_name: Optional[str] = None,
    scene_gap_sec: float = 0.12,
    zoom_intensity: float = 0.12,
    subtitle_color: str = "white",
    subtitle_size: float = 8.5,
    subtitle_y: float = -0.45,
    enable_subtitles: bool = True,
    transition_override: Optional[str] = None,
    bgm_path: Optional[str] = None,
    bgm_volume: float = 0.12,
) -> Dict[str, Any]:
    """Construit le brouillon CapCut complet à partir de `project_dir/manifest.json`."""
    project_dir = Path(project_dir).resolve()
    manifest_path = project_dir / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"manifest.json introuvable dans {project_dir}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    scenes = manifest.get("scenes", [])
    if not scenes:
        raise ValueError(f"Aucune scène trouvée dans {manifest_path}")

    target_drafts_dir = detect_capcut_drafts_dir(str(drafts_dir) if drafts_dir else None)
    final_draft_name = draft_name or manifest.get("draft_name") or manifest.get("project_slug") or project_dir.name
    # Nettoyer les caractères interdits dans les noms de dossiers Windows
    final_draft_name = re.sub(r'[<>:"/\\|?*]', "-", final_draft_name).strip()

    fmt = str(manifest.get("format", "9:16")).lower()
    canvas_w, canvas_h = FORMAT_RESOLUTIONS.get(fmt, (1080, 1920))
    fps = int(manifest.get("fps", 30))

    draft_folder = cc.DraftFolder(str(target_drafts_dir))
    script = draft_folder.create_draft(
        final_draft_name,
        canvas_w,
        canvas_h,
        fps=fps,
        allow_replace=True,
    )

    has_any_overlay = any(bool(s.get("overlay")) for s in scenes)
    script.add_track(TrackType.video, "scenes", relative_index=0)
    if has_any_overlay:
        script.add_track(TrackType.video, "overlays", relative_index=2)
    script.add_track(TrackType.audio, "voiceover")
    if bgm_path:
        script.add_track(TrackType.audio, "bgm")
    if enable_subtitles:
        script.add_track(TrackType.text, "subtitles")

    gap_us = max(0, int(round(scene_gap_sec * SEC)))
    timeline_cursor_us = 0
    canvas_ratio = canvas_w / canvas_h
    text_rgb = COLOR_PRESETS.get(subtitle_color.lower(), (1.0, 1.0, 1.0))

    srt_entries: List[Tuple[int, int, str]] = []
    first_image_path: Optional[Path] = None
    built_scenes_summary: List[Dict[str, Any]] = []

    for idx, scene in enumerate(scenes):
        scene_id = scene.get("id") or f"scene_{idx + 1:02d}"
        img_rel = scene.get("image") or f"images/{scene_id}.png"
        aud_rel = scene.get("audio") or f"audio/{scene_id}.mp3"

        img_path = (project_dir / img_rel).resolve()
        aud_path = (project_dir / aud_rel).resolve()

        if not img_path.exists():
            raise FileNotFoundError(f"Image manquante pour {scene_id} : {img_path}")
        if first_image_path is None:
            first_image_path = img_path

        # Durée de la scène pilotée par la voix off (ou fallback duration_sec si scène muette)
        has_audio = aud_path.exists()
        if has_audio:
            audio_mat = cc.AudioMaterial(str(aud_path))
            voice_duration_us = audio_mat.duration
        else:
            fallback_sec = float(scene.get("duration_sec", 4.0))
            voice_duration_us = int(round(fallback_sec * SEC))
            audio_mat = None

        clip_duration_us = voice_duration_us + gap_us
        clip_range = Timerange(timeline_cursor_us, clip_duration_us)

        # 1. Segment Voix Off
        if audio_mat is not None:
            voice_range = Timerange(timeline_cursor_us, voice_duration_us)
            audio_seg = cc.AudioSegment(
                audio_mat,
                voice_range,
                volume=float(scene.get("volume", 1.0)),
            )
            if voice_duration_us > int(0.15 * SEC):
                audio_seg.add_fade("0.02s", "0.03s")
            script.add_segment(audio_seg, "voiceover")

        # 2. Segment Image + Cover Fit + Ken Burns + Transition
        video_mat = cc.VideoMaterial(str(img_path))
        img_ratio = (video_mat.width / video_mat.height) if video_mat.height else canvas_ratio
        cover_scale = max(canvas_ratio / img_ratio, img_ratio / canvas_ratio)

        video_seg = cc.VideoSegment(
            video_mat,
            clip_range,
            clip_settings=ClipSettings(scale_x=cover_scale, scale_y=cover_scale),
        )
        video_seg.add_background_filling("blur", 0.0625)

        motion = scene.get("motion") or DEFAULT_MOTION_CYCLE[idx % len(DEFAULT_MOTION_CYCLE)]
        _apply_motion_keyframes(
            video_seg,
            motion=motion,
            cover_scale=cover_scale,
            duration_us=clip_duration_us,
            zoom_intensity=zoom_intensity,
        )

        # Ajouter une transition gratuite (sauf sur la toute dernière scène)
        if idx < len(scenes) - 1 and clip_duration_us >= int(0.8 * SEC):
            trans_name = transition_override if transition_override is not None else scene.get("transition")
            trans_enum = _resolve_free_transition(trans_name)
            if trans_enum is not None:
                video_seg.add_transition(trans_enum, duration="0.4s")

        script.add_segment(video_seg, "scenes")

        # 2b. Incrustation / Overlay optionnel sur piste vidéo supérieure (produit détouré, preuve PubMed, etc.)
        overlay_cfg = scene.get("overlay")
        if overlay_cfg and isinstance(overlay_cfg, dict) and overlay_cfg.get("file"):
            ov_path = (project_dir / str(overlay_cfg["file"])).resolve()
            if ov_path.exists():
                ov_scale = float(overlay_cfg.get("scale", 0.5))
                ov_x = float(overlay_cfg.get("x", 0.0))
                ov_y = float(overlay_cfg.get("y", 0.5))
                ov_mat = cc.VideoMaterial(str(ov_path))
                ov_seg = cc.VideoSegment(
                    ov_mat,
                    clip_range,
                    clip_settings=ClipSettings(
                        scale_x=ov_scale,
                        scale_y=ov_scale,
                        transform_x=ov_x,
                        transform_y=ov_y,
                    ),
                )
                if overlay_cfg.get("pop_in", True) and clip_duration_us > int(0.4 * SEC):
                    pop_dur = int(0.25 * SEC)
                    ov_seg.add_keyframe(KeyframeProperty.uniform_scale, 0, round(ov_scale * 0.86, 4))
                    ov_seg.add_keyframe(KeyframeProperty.uniform_scale, pop_dur, round(ov_scale, 4))
                    ov_seg.add_keyframe(KeyframeProperty.alpha, 0, 0.0)
                    ov_seg.add_keyframe(KeyframeProperty.alpha, int(0.2 * SEC), 1.0)
                script.add_segment(ov_seg, "overlays")

        # 3. Sous-titres dynamiques synchronisés sur la voix off de la scène
        subtitle_raw = scene.get("subtitle") if scene.get("subtitle") is not None else scene.get("narration", "")
        chunks = split_into_tiktok_chunks(str(subtitle_raw))
        if chunks and voice_duration_us > 0:
            weights = [max(1, len(c)) for c in chunks]
            total_weight = sum(weights)
            sub_cursor_us = timeline_cursor_us

            for c_idx, chunk_text in enumerate(chunks):
                if c_idx == len(chunks) - 1:
                    chunk_dur_us = (timeline_cursor_us + voice_duration_us) - sub_cursor_us
                else:
                    chunk_dur_us = int(round(voice_duration_us * (weights[c_idx] / total_weight)))
                chunk_dur_us = max(int(0.2 * SEC), chunk_dur_us)

                srt_entries.append((sub_cursor_us, sub_cursor_us + chunk_dur_us, chunk_text))

                if enable_subtitles:
                    text_seg = cc.TextSegment(
                        chunk_text,
                        Timerange(sub_cursor_us, chunk_dur_us),
                        style=TextStyle(
                            size=subtitle_size,
                            bold=True,
                            color=text_rgb,
                            align=1,
                            auto_wrapping=True,
                            max_line_width=0.82,
                        ),
                        clip_settings=ClipSettings(transform_y=subtitle_y),
                        border=TextBorder(color=(0.0, 0.0, 0.0), width=40.0),
                        shadow=TextShadow(alpha=0.8, color=(0.0, 0.0, 0.0), diffuse=15.0, distance=5.0),
                    )
                    script.add_segment(text_seg, "subtitles")

                sub_cursor_us += chunk_dur_us

        built_scenes_summary.append({
            "id": scene_id,
            "duration_sec": round(clip_duration_us / SEC, 2),
            "motion": motion,
            "subtitle_chunks": len(chunks),
        })
        timeline_cursor_us += clip_duration_us

    # 4. Musique de fond optionnelle
    if bgm_path:
        bgm_file = Path(os.path.expandvars(os.path.expanduser(bgm_path))).resolve()
        if not bgm_file.exists():
            candidate_in_proj = (project_dir / bgm_path).resolve()
            if candidate_in_proj.exists():
                bgm_file = candidate_in_proj
        if bgm_file.exists() and timeline_cursor_us > 0:
            bgm_mat = cc.AudioMaterial(str(bgm_file))
            usable_dur = min(bgm_mat.duration, timeline_cursor_us)
            bgm_seg = cc.AudioSegment(
                bgm_mat,
                Timerange(0, usable_dur),
                source_timerange=Timerange(0, usable_dur),
                volume=bgm_volume,
            )
            if usable_dur > int(2.0 * SEC):
                bgm_seg.add_fade("0.5s", "1.5s")
            script.add_segment(bgm_seg, "bgm")

    # Sauvegarder le fichier .srt dans le dossier du projet également
    srt_output_path = project_dir / "subtitles.srt"
    if srt_entries:
        write_srt_file(srt_entries, srt_output_path)

    script.save()

    created_draft_dir = target_drafts_dir / final_draft_name
    _enrich_draft_meta_info(
        draft_dir=created_draft_dir,
        drafts_root=target_drafts_dir,
        draft_name=final_draft_name,
        total_duration_us=timeline_cursor_us,
        cover_source_image=first_image_path,
    )

    return {
        "draft_name": final_draft_name,
        "draft_path": str(created_draft_dir),
        "capcut_drafts_dir": str(target_drafts_dir),
        "resolution": f"{canvas_w}x{canvas_h}",
        "total_duration_sec": round(timeline_cursor_us / SEC, 2),
        "scene_count": len(built_scenes_summary),
        "srt_path": str(srt_output_path) if srt_entries else None,
        "scenes": built_scenes_summary,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Synchronise un projet depuis GitHub et génère le montage dans CapCut Windows."
    )
    parser.add_argument("--project", help="Slug du projet (ex: 2026-11-25-pyramides). Par défaut: le plus récent.")
    parser.add_argument("--local-only", action="store_true", help="Ne pas télécharger depuis GitHub, utiliser projects/<slug> local.")
    parser.add_argument("--drafts-dir", help="Chemin explicite vers le dossier CapCut Drafts si non standard.")
    parser.add_argument("--draft-name", help="Nom du projet affiché dans CapCut.")
    parser.add_argument("--subtitle-color", default="white", choices=["white", "yellow", "cyan"])
    parser.add_argument("--zoom", type=float, default=0.12, help="Intensité du zoom Ken Burns (défaut: 0.12).")
    parser.add_argument("--gap", type=float, default=0.12, help="Pause en secondes entre deux scènes (défaut: 0.12).")
    parser.add_argument("--bgm", help="Chemin optionnel vers une musique de fond (.mp3/.wav).")
    args = parser.parse_args()

    from tools.github_sync import list_local_projects, sync_project_from_github

    if args.local_only:
        if args.project:
            proj_dir = LOCAL_PROJECTS_DIR / args.project
        else:
            locals_list = list_local_projects()
            if not locals_list:
                print("Aucun projet local trouvé dans projects/.", file=sys.stderr)
                sys.exit(1)
            proj_dir = Path(locals_list[0]["local_path"])
    else:
        print("Synchronisation depuis GitHub en cours...")
        sync_info = sync_project_from_github(project_slug=args.project)
        print(
            f"Projet '{sync_info['project_slug']}' récupéré depuis la branche '{sync_info['branch']}' "
            f"({sync_info['total_files']} fichiers)."
        )
        proj_dir = Path(sync_info["local_dir"])

    chosen_drafts_dir = Path(args.drafts_dir) if args.drafts_dir else None
    if chosen_drafts_dir is None:
        try:
            chosen_drafts_dir = detect_capcut_drafts_dir()
        except FileNotFoundError:
            print("\n[!] Dossier des projets CapCut introuvable à l'emplacement par défaut.")
            print("    Dans CapCut -> Paramètres (icône engrenage en haut à droite) -> 'Enregistrer dans',")
            user_input = input("    Colle ici le chemin de ton dossier CapCut Drafts puis appuie sur Entrée : ").strip().strip('"')
            if not user_input or not Path(user_input).exists():
                print(f"[ERREUR] Chemin invalide ou introuvable : {user_input}", file=sys.stderr)
                sys.exit(1)
            chosen_drafts_dir = Path(user_input).resolve()
            save_local_config({"capcut_drafts_dir": str(chosen_drafts_dir)})

    result = build_capcut_draft(
        project_dir=proj_dir,
        drafts_dir=chosen_drafts_dir,
        draft_name=args.draft_name,
        scene_gap_sec=args.gap,
        zoom_intensity=args.zoom,
        subtitle_color=args.subtitle_color,
        bgm_path=args.bgm,
    )
    print("\n=== MONTAGE CAPCUT PRÊT ===")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print(
        "\nOuvre CapCut Desktop sur Windows (ou reviens à l'écran d'accueil de CapCut pour rafraîchir la liste) : "
        f"ton projet '{result['draft_name']}' est prêt à être prévisualisé et exporté !"
    )


if __name__ == "__main__":
    main()
