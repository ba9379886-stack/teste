#!/usr/bin/env python3
"""
Full 25.00-second (1080x1920 @ 30fps) Pixar-style 3D commercial renderer & sound-design mixer
for "OIL OF OREGANO WITH BLACK SEED OIL" featuring Ollie the muscular oregano leaf.

Outputs inside projects/2026-11-25-ollie-oregano-3d-ad/:
  - images/scene_01.png .. scene_06.png        (1080x1920 static keyframes with exact unaltered product)
  - audio/scene_01_trim.mp3 .. scene_06_trim.mp3 & audio/bgm.mp3 & audio/master_mix.wav
  - videos/scene_01.mp4 .. scene_06.mp4        (clean animated 30fps scene clips for CapCut)
  - ollie_oregano_commercial_25s.mp4           (complete standalone 25.0s mastered vertical ad with
                                                animated subtitles, SFX, commercial music & voiceovers)
"""

from __future__ import annotations

import math
import subprocess
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont
from scipy.io import wavfile

W, H = 1080, 1920
FPS = 30
TOTAL_SECONDS = 25.0
TOTAL_FRAMES = int(TOTAL_SECONDS * FPS)  # 750 frames
SR = 44100

REPO_ROOT = Path(__file__).resolve().parent.parent
PROJ_DIR = REPO_ROOT / "projects" / "2026-11-25-ollie-oregano-3d-ad"
FONT_ANTON = REPO_ROOT / "tools" / "fonts" / "Anton-Regular.ttf"
FONT_FALLBACK = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")


def get_font(size: int) -> ImageFont.FreeTypeFont:
    font_path = FONT_ANTON if FONT_ANTON.exists() else FONT_FALLBACK
    return ImageFont.truetype(str(font_path), size=size)


def fit_cover(im: Image.Image, target_w: int = W, target_h: int = H) -> Image.Image:
    im = im.convert("RGB")
    src_w, src_h = im.size
    scale = max(target_w / src_w, target_h / src_h)
    nw, nh = int(round(src_w * scale)), int(round(src_h * scale))
    resized = im.resize((nw, nh), Image.Resampling.LANCZOS)
    left = (nw - target_w) // 2
    top = (nh - target_h) // 2
    return resized.crop((left, top, left + target_w, top + target_h))


def zoom_pan(
    im: Image.Image,
    zoom: float = 1.0,
    dx: float = 0.0,
    dy: float = 0.0,
) -> Image.Image:
    """Smooth subpixel-like crop zoom & pan on a 1080x1920 RGB image."""
    zoom = max(1.0, float(zoom))
    cw = W / zoom
    ch = H / zoom
    cx = W * 0.5 + dx
    cy = H * 0.5 + dy
    x0 = max(0.0, min(W - cw, cx - cw * 0.5))
    y0 = max(0.0, min(H - ch, cy - ch * 0.5))
    return im.resize(
        (W, H),
        Image.Resampling.BICUBIC,
        box=(x0, y0, x0 + cw, y0 + ch),
    )


def make_radial_glow(size: int, rgb: tuple[int, int, int], max_alpha: int = 190) -> Image.Image:
    y, x = np.ogrid[-1.0 : 1.0 : size * 1j, -1.0 : 1.0 : size * 1j]
    r = np.sqrt(x * x + y * y)
    falloff = np.clip(1.0 - r, 0.0, 1.0) ** 2.2
    arr = np.zeros((size, size, 4), dtype=np.uint8)
    arr[..., 0] = rgb[0]
    arr[..., 1] = rgb[1]
    arr[..., 2] = rgb[2]
    arr[..., 3] = (falloff * max_alpha).astype(np.uint8)
    return Image.fromarray(arr, "RGBA")


def make_spotlight_cone(
    width: int,
    height: int,
    top_x: int,
    bottom_x: int,
    top_w: int,
    bottom_w: int,
    y_start: int,
    y_end: int,
    rgb: tuple[int, int, int] = (255, 214, 118),
    max_alpha: int = 115,
) -> Image.Image:
    """Volumetric golden spotlight cone for Scene 6 product pedestal."""
    yy = np.arange(height, dtype=np.float32)[:, None]
    xx = np.arange(width, dtype=np.float32)[None, :]
    t = np.clip((yy - y_start) / max(1.0, float(y_end - y_start)), 0.0, 1.0)
    cx = top_x + (bottom_x - top_x) * t
    half_w = (top_w + (bottom_w - top_w) * t) * 0.5
    dist = np.abs(xx - cx) / np.maximum(1.0, half_w)
    horiz = np.clip(1.0 - dist**1.8, 0.0, 1.0)
    vert = np.clip(1.0 - 0.35 * t, 0.0, 1.0) * (yy >= y_start) * (yy <= y_end)
    # Soft fade near bottom
    bottom_fade = np.clip((y_end - yy) / 140.0, 0.0, 1.0)
    alpha = horiz * vert * bottom_fade * max_alpha
    arr = np.zeros((height, width, 4), dtype=np.uint8)
    arr[..., 0] = rgb[0]
    arr[..., 1] = rgb[1]
    arr[..., 2] = rgb[2]
    arr[..., 3] = np.clip(alpha, 0, 255).astype(np.uint8)
    return Image.fromarray(arr, "RGBA").filter(ImageFilter.GaussianBlur(radius=14))


def apply_sheen_to_rgba(sprite: Image.Image, progress: float) -> Image.Image:
    """Applies a glossy diagonal golden-white light sweep across an RGBA product sprite without altering label text."""
    if progress < 0.0 or progress > 1.0:
        return sprite
    sw, sh = sprite.size
    yy = np.linspace(0.0, 1.0, sh, dtype=np.float32)[:, None]
    xx = np.linspace(0.0, 1.0, sw, dtype=np.float32)[None, :]
    diag = xx * 0.78 + yy * 0.22
    center = -0.25 + progress * 1.50
    band = np.exp(-((diag - center) ** 2) / (2.0 * 0.045 * 0.045))
    arr = np.array(sprite, dtype=np.float32)
    alpha_mask = (arr[..., 3:4] > 10).astype(np.float32)
    boost = band[..., None] * alpha_mask * np.array([58.0, 50.0, 32.0], dtype=np.float32)
    arr[..., :3] = np.clip(arr[..., :3] + boost, 0.0, 255.0)
    return Image.fromarray(arr.astype(np.uint8), "RGBA")


def pan_left_extend_dark(im: Image.Image, shift_px: int) -> Image.Image:
    """Shifts Scene 6 left by `shift_px` and seamlessly extends the studio gradient on the right."""
    arr = np.array(im)
    out = np.zeros_like(arr)
    out[:, : W - shift_px, :] = arr[:, shift_px:, :]
    edge_strip = np.mean(arr[:, W - 18 :, :], axis=1, keepdims=True)
    noise = np.random.default_rng(42).normal(0.0, 1.2, size=(H, shift_px, 3))
    out[:, W - shift_px :, :] = np.clip(edge_strip + noise, 0, 255).astype(np.uint8)
    return Image.fromarray(out, "RGB")


# Subtitle cues: (start_s, end_s, line1, line2, accent_rgb)
SUBTITLES = [
    (0.95, 1.82, "BRO!", "", (142, 255, 82)),
    (1.92, 4.15, "WHAT IS GOING ON", "WITH YOUR LIFE?!", (255, 222, 68)),
    (5.72, 8.20, "YOU NEED BACKUP,", "MY FRIEND!", (142, 255, 82)),
    (10.42, 11.95, "OREGANO OIL.", "", (142, 255, 82)),
    (12.15, 13.75, "BLACK SEED OIL.", "", (255, 214, 74)),
    (14.05, 15.35, "TWO LEGENDS.", "", (255, 255, 255)),
    (15.55, 16.92, "ONE TEAM!", "", (255, 214, 74)),
    (17.04, 19.00, "Wait… YOU'RE", "the boss?", (175, 228, 255)),
    (19.08, 19.95, "OBVIOUSLY!", "", (142, 255, 82)),
    (20.00, 21.96, "I'm literally the LEAF", "of the operation!", (142, 255, 82)),
    (22.35, 24.85, "STOP SLEEPING ON", "OREGANO!", (255, 214, 74)),
]


def draw_subtitle(canvas: Image.Image, t: float, font_big: ImageFont.FreeTypeFont, font_med: ImageFont.FreeTypeFont) -> Image.Image:
    active = None
    for cue in SUBTITLES:
        if cue[0] <= t <= cue[1]:
            active = cue
            break
    if active is None:
        return canvas

    s0, s1, line1, line2, accent_rgb = active
    local = t - s0
    # Elastic pop-in scale in first 0.14s
    if local < 0.14:
        u = local / 0.14
        pop = 0.78 + 0.28 * math.sin(u * math.pi * 0.72)
    else:
        pop = 1.0

    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    fnt = font_big if not line2 else font_med

    lines = [line1] if not line2 else [line1, line2]
    # Position captions in safe lower-third zone; lower on Scene 3 & 6 so Ollie's chains/body & pedestal stay 100% clear
    if 10.0 <= t < 17.0:
        base_y = 1720
    elif t >= 22.0:
        base_y = 1650
    else:
        base_y = 1565

    line_heights = []
    for ln in lines:
        bb = d.textbbox((0, 0), ln, font=fnt, stroke_width=10)
        line_heights.append((bb[2] - bb[0], bb[3] - bb[1]))

    total_h = sum(h for _, h in line_heights) + (14 if len(lines) == 2 else 0)
    max_w = max(w for w, _ in line_heights)

    # Subtle dark rounded pill backdrop behind text for ultra-clean commercial legibility
    pad_x, pad_y = 38, 22
    pill_box = [
        int(W * 0.5 - max_w * 0.5 - pad_x),
        int(base_y - total_h * 0.5 - pad_y),
        int(W * 0.5 + max_w * 0.5 + pad_x),
        int(base_y + total_h * 0.5 + pad_y),
    ]
    d.rounded_rectangle(pill_box, radius=30, fill=(10, 12, 16, 158))

    cy = base_y - total_h * 0.5
    for idx, ln in enumerate(lines):
        tw, th = line_heights[idx]
        tx = W * 0.5 - tw * 0.5
        fill_col = accent_rgb if (len(lines) == 1 or idx == 1) else (255, 255, 255)
        # Drop shadow
        d.text((tx + 5, cy + 7), ln, font=fnt, fill=(0, 0, 0, 220), stroke_width=10, stroke_fill=(0, 0, 0, 220))
        # Crisp main text with thick dark outline
        d.text((tx, cy), ln, font=fnt, fill=(*fill_col, 255), stroke_width=9, stroke_fill=(14, 16, 20, 255))
        cy += th + 14

    if abs(pop - 1.0) > 0.005:
        # Scale around caption center
        crop_y0 = max(0, pill_box[1] - 60)
        crop_y1 = min(H, pill_box[3] + 60)
        sub = overlay.crop((0, crop_y0, W, crop_y1))
        nw = max(1, int(round(W * pop)))
        nh = max(1, int(round((crop_y1 - crop_y0) * pop)))
        sub_s = sub.resize((nw, nh), Image.Resampling.BICUBIC)
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ox = int(round((W - nw) * 0.5))
        oy = int(round(base_y - nh * 0.5))
        overlay.alpha_composite(sub_s, (ox, oy))

    out = canvas.convert("RGBA")
    out.alpha_composite(overlay)
    return out.convert("RGB")


def draw_top_pill_badge(canvas: Image.Image, font_small: ImageFont.FreeTypeFont, alpha_scale: float = 1.0) -> Image.Image:
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    txt = "OIL OF OREGANO + BLACK SEED OIL"
    bb = d.textbbox((0, 0), txt, font=font_small)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    cx, cy = W // 2, 165
    a_bg = int(175 * alpha_scale)
    a_fg = int(255 * alpha_scale)
    box = [cx - tw // 2 - 36, cy - th // 2 - 18, cx + tw // 2 + 36, cy + th // 2 + 22]
    d.rounded_rectangle(box, radius=34, fill=(18, 22, 18, a_bg), outline=(235, 192, 88, a_fg), width=3)
    d.text((cx - tw // 2, cy - th // 2 - 2), txt, font=font_small, fill=(255, 232, 152, a_fg))
    out = canvas.convert("RGBA")
    out.alpha_composite(overlay)
    return out.convert("RGB")


def build_audio_tracks(ff: str) -> tuple[Path, Path]:
    """
    Synthesizes upbeat funky commercial music + humorous SFX, trims & places all 6 voice lines
    at exact storyboard timestamps, saves trimmed MP3s + bgm.mp3 + master_mix.wav.
    """
    audio_dir = PROJ_DIR / "audio"
    total_samples = int(TOTAL_SECONDS * SR)
    t = np.arange(total_samples, dtype=np.float32) / SR

    # --- 1. Upbeat Commercial Funk / Hip-Hop Beat (116 BPM) ---
    bpm = 116.0
    beat_dur = 60.0 / bpm
    beat_pos = t / beat_dur
    beat_idx = np.floor(beat_pos).astype(np.int32)
    beat_frac = beat_pos - beat_idx
    bt = beat_frac * beat_dur  # seconds into current quarter-note beat

    # Punchy kick on beats 0, 2 (and syncopated eighth before beat 2)
    is_kick = (beat_idx % 2 == 0)
    kick_freq = 52.0 + 115.0 * np.exp(-bt * 34.0)
    kick = np.sin(2.0 * np.pi * kick_freq * bt) * np.exp(-bt * 11.5) * is_kick

    # Crisp snare + clap on beats 1, 3
    rng = np.random.default_rng(2026)
    white = rng.normal(0.0, 1.0, size=total_samples).astype(np.float32)
    is_snare = (beat_idx % 2 == 1)
    snare = (white * np.exp(-bt * 24.0) * 0.55 + np.sin(2.0 * np.pi * 185.0 * bt) * np.exp(-bt * 28.0) * 0.45) * is_snare

    # Crisp sixteenth hi-hats
    sub16 = (beat_pos * 4.0) % 1.0 * (beat_dur * 0.25)
    hat = white * np.exp(-sub16 * 55.0) * 0.14

    # Groovy minor-pentatonic funk bassline (G2 - Bb2 - C3 - D3)
    bass_notes = np.array([98.0, 98.0, 116.54, 130.81, 98.0, 146.83, 130.81, 116.54], dtype=np.float32)
    eighth_idx = np.floor(beat_pos * 2.0).astype(np.int32)
    et = ((beat_pos * 2.0) % 1.0) * (beat_dur * 0.5)
    bf = bass_notes[eighth_idx % len(bass_notes)]
    bass = (
        0.70 * np.sin(2.0 * np.pi * bf * et)
        + 0.30 * np.sin(2.0 * np.pi * 2.0 * bf * et)
    ) * np.exp(-et * 6.5) * 0.42

    # Warm commercial chord stabs on bar starts (Gm7 / C9 feel)
    bar_t = (beat_pos % 4.0) * beat_dur
    chord = (
        np.sin(2.0 * np.pi * 392.00 * t)
        + np.sin(2.0 * np.pi * 466.16 * t)
        + np.sin(2.0 * np.pi * 587.33 * t)
        + np.sin(2.0 * np.pi * 698.46 * t)
    ) * 0.25 * np.exp(-bar_t * 3.8) * 0.24

    bgm_mono = (kick * 0.58 + snare * 0.38 + hat + bass + chord).astype(np.float32)
    # Pause beat slightly at 0.0..0.80s (sleepy low drone) then kick in full groove at 0.85s!
    intro_env = np.where(t < 0.82, 0.18, 1.0).astype(np.float32)
    # Smooth fade-out last 0.45s
    outro_env = np.clip((TOTAL_SECONDS - t) / 0.45, 0.0, 1.0).astype(np.float32)
    bgm_mono = bgm_mono * intro_env * outro_env

    # Stereo widen chord slightly
    bgm_l = bgm_mono.copy()
    bgm_r = np.roll(bgm_mono, 18)

    # Save standalone bgm.mp3 for CapCut
    bgm_wav = Path("/tmp/ollie_bgm.wav")
    bgm_i16 = np.clip(np.stack([bgm_l, bgm_r], axis=1) * 0.55 * 32767.0, -32767, 32767).astype(np.int16)
    wavfile.write(bgm_wav, SR, bgm_i16)
    bgm_mp3 = audio_dir / "bgm.mp3"
    subprocess.run([ff, "-y", "-i", str(bgm_wav), "-b:a", "192k", str(bgm_mp3)], check=True, capture_output=True)

    # --- 2. Humorous Synced Commercial Sound Effects ---
    sfx_l = np.zeros(total_samples, dtype=np.float32)
    sfx_r = np.zeros(total_samples, dtype=np.float32)

    def add_sfx(start_sec: float, sig_l: np.ndarray, sig_r: np.ndarray | None = None) -> None:
        if sig_r is None:
            sig_r = sig_l
        i0 = max(0, int(round(start_sec * SR)))
        n = min(len(sig_l), total_samples - i0)
        if n > 0:
            sfx_l[i0 : i0 + n] += sig_l[:n]
            sfx_r[i0 : i0 + n] += sig_r[:n]

    # SFX 1 (0.66s): Fast incoming cartoon WHOOSH + 0.80s HEAVY TABLE SLAM!
    wt = np.linspace(0.0, 0.18, int(0.18 * SR), dtype=np.float32)
    whoosh = rng.normal(0, 1, len(wt)).astype(np.float32) * np.sin(np.pi * wt / 0.18) * 0.45
    add_sfx(0.64, whoosh * 0.8, whoosh * 1.1)

    st = np.linspace(0.0, 0.45, int(0.45 * SR), dtype=np.float32)
    slam_freq = 38.0 + 150.0 * np.exp(-st * 26.0)
    slam = (
        np.sin(2.0 * np.pi * slam_freq * st) * np.exp(-st * 9.0) * 0.85
        + rng.normal(0, 1, len(st)).astype(np.float32) * np.exp(-st * 30.0) * 0.45
    )
    add_sfx(0.80, slam)

    # SFX 2 (5.02s): Classic Boxing Ring Bell "DING-DING!" + Glove Clash SMACK!
    bt_bell = np.linspace(0.0, 0.65, int(0.65 * SR), dtype=np.float32)
    bell_hit = (
        0.55 * np.sin(2.0 * np.pi * 1318.5 * bt_bell)
        + 0.30 * np.sin(2.0 * np.pi * 2690.0 * bt_bell)
        + 0.20 * np.sin(2.0 * np.pi * 3890.0 * bt_bell)
    ) * np.exp(-bt_bell * 7.5) * 0.36
    add_sfx(5.02, bell_hit)
    add_sfx(5.22, bell_hit * 1.08)
    gt = np.linspace(0.0, 0.22, int(0.22 * SR), dtype=np.float32)
    glove_smack = (
        np.sin(2.0 * np.pi * (90.0 + 180.0 * np.exp(-gt * 35.0)) * gt) * np.exp(-gt * 18.0) * 0.65
        + rng.normal(0, 1, len(gt)).astype(np.float32) * np.exp(-gt * 40.0) * 0.35
    )
    add_sfx(5.42, glove_smack)

    # SFX 3 (10.00s): Epic Golden Shimmer Reveal + Deep Cinematic Boom!
    rt = np.linspace(0.0, 1.40, int(1.40 * SR), dtype=np.float32)
    shimmer = np.zeros_like(rt)
    for f_hz in [587.33, 783.99, 987.77, 1174.66, 1567.98, 2349.32]:
        shimmer += np.sin(2.0 * np.pi * f_hz * rt) * np.exp(-rt * 2.4) * 0.08
    boom = np.sin(2.0 * np.pi * (42.0 + 70.0 * np.exp(-rt * 14.0)) * rt) * np.exp(-rt * 4.5) * 0.55
    add_sfx(10.00, shimmer + boom, np.roll(shimmer, 25) + boom)

    # SFX 4 (15.52s): Punch impact on "ONE TEAM!"
    add_sfx(15.52, slam * 0.55)

    # SFX 5 (17.00s): Comedic pluck / pop when human squints at Ollie
    pt = np.linspace(0.0, 0.18, int(0.18 * SR), dtype=np.float32)
    pluck = np.sin(2.0 * np.pi * (280.0 + 220.0 * pt / 0.18) * pt) * np.exp(-pt * 18.0) * 0.32
    add_sfx(17.00, pluck)

    # SFX 6 (19.06s): Muscle-flex whoosh + power pop on Scene 5!
    add_sfx(19.05, whoosh * 0.75)
    add_sfx(19.16, glove_smack * 0.60)

    # SFX 7 (22.00s): Final Luxury Golden Spotlight Hit!
    add_sfx(22.00, (shimmer + boom) * 0.85, (np.roll(shimmer, 25) + boom) * 0.85)

    # --- 3. Load, Trim & Place All 6 Dialogue Lines ---
    def load_vo(scene_num: int) -> np.ndarray:
        mp3_p = audio_dir / f"scene_{scene_num:02d}.mp3"
        wav_p = Path(f"/tmp/vo_raw_{scene_num}.wav")
        subprocess.run([ff, "-y", "-i", str(mp3_p), "-ac", "1", "-ar", str(SR), str(wav_p)], check=True, capture_output=True)
        _, raw = wavfile.read(wav_p)
        f = raw.astype(np.float32) / 32768.0
        idx = np.where(np.abs(f) > 0.012)[0]
        if len(idx) == 0:
            return f
        pad = int(0.04 * SR)
        i0 = max(0, idx[0] - pad)
        i1 = min(len(f), idx[-1] + pad)
        trimmed = f[i0:i1]
        # Peak normalize gently to 0.92
        pk = float(np.max(np.abs(trimmed)))
        if pk > 1e-4:
            trimmed = trimmed * (0.92 / pk)
        return trimmed

    vo1 = load_vo(1)
    vo2 = load_vo(2)
    vo3 = load_vo(3)
    vo4 = load_vo(4)
    vo5_raw = load_vo(5)
    # Tighten dead silence inside Scene 5 ("Obviously! [pause] I'm literally...") from 0.42s to 0.12s
    # In raw scene_05, speech starts at ~0.20s, so inside trimmed vo5_raw the pause is around 0.76s..1.14s
    cut_a = int(0.80 * SR)
    cut_b = int(1.10 * SR)
    if len(vo5_raw) > cut_b + int(0.5 * SR):
        vo5 = np.concatenate([vo5_raw[:cut_a], vo5_raw[cut_b:]])
    else:
        vo5 = vo5_raw
    vo6 = load_vo(6)

    # Save trimmed scene voiceovers for CapCut manifest synchronization too
    trimmed_vos = [vo1, vo2, vo3, vo4, vo5, vo6]
    for idx_v, v_arr in enumerate(trimmed_vos, start=1):
        twav = Path(f"/tmp/vo_trim_{idx_v:02d}.wav")
        wavfile.write(twav, SR, np.clip(v_arr * 32767.0, -32767, 32767).astype(np.int16))
        tmp3 = audio_dir / f"scene_{idx_v:02d}_trim.mp3"
        subprocess.run([ff, "-y", "-i", str(twav), "-b:a", "192k", str(tmp3)], check=True, capture_output=True)

    vo_track = np.zeros(total_samples, dtype=np.float32)
    placements = [
        (0.95, vo1),   # 0.95..3.58s  (Beat 1: 0..5s)
        (5.72, vo2),   # 5.72..7.12s  (Beat 2: 5..10s)
        (10.42, vo3),  # 10.42..16.60s (Beat 3: 10..17s)
        (17.02, vo4),  # 17.02..19.04s (Beat 4a: 17.00..19.05s)
        (19.08, vo5),  # 19.08..21.96s (Beat 4b: 19.05..22.00s)
        (22.35, vo6),  # 22.35..23.72s (Beat 5: 22.00..25.00s)
    ]
    for start_sec, v_arr in placements:
        i0 = int(round(start_sec * SR))
        n = min(len(v_arr), total_samples - i0)
        if n > 0:
            vo_track[i0 : i0 + n] += v_arr[:n]

    # Automatic sidechain ducking of BGM whenever dialogue is active
    win = int(0.06 * SR)
    vo_env = np.convolve(np.abs(vo_track), np.ones(win, dtype=np.float32) / win, mode="same")
    duck = np.where(vo_env > 0.015, 0.20, 0.46).astype(np.float32)
    # Smooth ducking envelope (120ms)
    smooth_win = int(0.12 * SR)
    duck = np.convolve(duck, np.ones(smooth_win, dtype=np.float32) / smooth_win, mode="same")

    mix_l = vo_track * 1.02 + bgm_l * duck + sfx_l * 0.52
    mix_r = vo_track * 1.02 + bgm_r * duck + sfx_r * 0.52

    # Soft limiter so peaks never clip
    mix_stereo = np.stack([mix_l, mix_r], axis=1)
    peak = float(np.max(np.abs(mix_stereo)))
    if peak > 0.96:
        mix_stereo = np.tanh(mix_stereo * 1.15) / np.tanh(1.15) * 0.95

    master_wav = audio_dir / "master_mix.wav"
    wavfile.write(master_wav, SR, np.clip(mix_stereo * 32767.0, -32767, 32767).astype(np.int16))
    return master_wav, bgm_mp3


def main() -> None:
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    img_dir = PROJ_DIR / "images"
    vid_dir = PROJ_DIR / "videos"
    vid_dir.mkdir(parents=True, exist_ok=True)

    print("1/4 Mixing stereo commercial soundtrack, SFX, and trimmed voiceovers...")
    master_wav, _ = build_audio_tracks(ff)

    print("2/4 Loading Pixar 3D keyframes and exact unaltered product RGBA sprites...")
    im_couch = fit_cover(Image.open(PROJ_DIR / "refs" / "human_couch_card.png"))
    im_s1 = fit_cover(Image.open(img_dir / "scene_01_raw.png"))
    im_s2 = fit_cover(Image.open(img_dir / "scene_02_raw.png"))
    im_s3_bg = fit_cover(Image.open(img_dir / "scene_03_bg.png"))
    im_s4 = fit_cover(Image.open(img_dir / "scene_04_raw.png"))
    im_s5 = fit_cover(Image.open(img_dir / "scene_05_raw.png"))
    im_s6_raw = fit_cover(Image.open(img_dir / "scene_06_bg.png"))
    # Shift Scene 6 left by only 35px so pedestal stays centered under spotlight and Ollie's glove tip sits at x=597
    im_s6_bg = pan_left_extend_dark(im_s6_raw, shift_px=35)
    # Extract Ollie's pointing crimson glove foreground mask (y=1060..1330, x=380..610) for true 3D foreground layering!
    s6_arr = np.array(im_s6_bg)
    glove_rgba_arr = np.zeros((H, W, 4), dtype=np.uint8)
    glove_rgba_arr[..., :3] = s6_arr
    sub_g = s6_arr[1060:1330, 380:615, :].astype(np.int16)
    g_mask = ((sub_g[..., 0] - sub_g[..., 1]) > 42) & (sub_g[..., 0] > 95)
    glove_alpha = np.zeros((H, W), dtype=np.uint8)
    glove_alpha[1060:1330, 380:615] = (g_mask * 255).astype(np.uint8)
    glove_rgba_arr[..., 3] = np.array(
        Image.fromarray(glove_alpha, "L").filter(ImageFilter.GaussianBlur(radius=1.2))
    )
    ollie_glove_fg = Image.fromarray(glove_rgba_arr, "RGBA")

    pouch_orig = Image.open(PROJ_DIR / "overlays" / "product_pouch.png").convert("RGBA")
    pbbox = pouch_orig.getbbox()
    if pbbox:
        pouch_orig = pouch_orig.crop(pbbox)

    softgel_orig = Image.open(PROJ_DIR / "overlays" / "softgel_3d.png").convert("RGBA")

    # Pre-scale product sprites for Scene 3 (levitating hero reveal) & Scene 6 (pedestal hero packshot)
    pw_orig, ph_orig = pouch_orig.size
    s3_h = 640
    s3_w = int(round(pw_orig * (s3_h / ph_orig)))
    pouch_s3 = pouch_orig.resize((s3_w, s3_h), Image.Resampling.LANCZOS)

    s6_h = 548
    s6_w = int(round(pw_orig * (s6_h / ph_orig)))
    pouch_s6 = pouch_orig.resize((s6_w, s6_h), Image.Resampling.LANCZOS)

    # Softgels pre-sized base
    sg_base = softgel_orig.resize((190, 104), Image.Resampling.LANCZOS)
    glow_gold = make_radial_glow(760, (255, 206, 92), max_alpha=155)
    glow_hero = make_radial_glow(860, (255, 212, 105), max_alpha=110)
    cone_s6 = make_spotlight_cone(
        W, H,
        top_x=545, bottom_x=715,
        top_w=160, bottom_w=520,
        y_start=0, y_end=1450,
        rgb=(255, 214, 118),
        max_alpha=95,
    )

    # Pedestal contact shadow for Scene 6 pouch
    shadow_s6 = Image.new("RGBA", (s6_w + 120, 90), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow_s6)
    sd.ellipse([20, 18, s6_w + 100, 72], fill=(0, 0, 0, 195))
    shadow_s6 = shadow_s6.filter(ImageFilter.GaussianBlur(radius=14))

    font_big = get_font(86)
    font_med = get_font(72)
    font_small = get_font(36)

    # Deterministic floating golden dust particles
    rng_p = np.random.default_rng(777)
    particles = np.column_stack([
        rng_p.uniform(80, W - 80, 46),   # x
        rng_p.uniform(160, H - 260, 46), # y
        rng_p.uniform(3.0, 8.5, 46),     # radius
        rng_p.uniform(35.0, 90.0, 46),   # upward speed px/s
        rng_p.uniform(0.0, 6.28, 46),    # phase
    ])

    def compose_scene_03_frame(local_t: float) -> Image.Image:
        # local_t in [0.0, 7.0]
        u = local_t / 7.0
        bg = zoom_pan(im_s3_bg, zoom=1.0 + 0.065 * u, dx=0.0, dy=-12.0 * u).convert("RGBA")

        # Pulsing golden aura centered at (605, 760)
        pulse = 0.92 + 0.10 * math.sin(local_t * 3.4)
        gw = int(round(760 * pulse))
        g_im = glow_gold.resize((gw, gw), Image.Resampling.BILINEAR)
        bg.alpha_composite(g_im, (605 - gw // 2, 760 - gw // 2))

        # Rising golden dust particles
        p_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        pd = ImageDraw.Draw(p_layer)
        for px, py, pr, pspd, pph in particles:
            yy = (py - local_t * pspd) % (H - 300) + 120
            xx = px + 18.0 * math.sin(local_t * 2.1 + pph)
            al = int(125 + 95 * math.sin(local_t * 4.0 + pph))
            pd.ellipse([xx - pr, yy - pr, xx + pr, yy + pr], fill=(255, 232, 145, al))
        bg.alpha_composite(p_layer)

        # 5 Orbiting 3D Golden Softgels with true front/back Z-depth sorting around pouch!
        orbit_specs = [
            (0.00, 315.0, 115.0, -14.0, 1.15),
            (1.26, 335.0, 130.0,  18.0, 1.15),
            (2.51, 295.0, 105.0, -22.0, 1.15),
            (3.77, 340.0, 125.0,  12.0, 1.15),
            (5.03, 310.0, 118.0,  -8.0, 1.15),
        ]
        back_gels = []
        front_gels = []
        for ph0, rx, ry, tilt_deg, spd in orbit_specs:
            ang = ph0 + local_t * spd
            ox = math.cos(ang) * rx
            oy = math.sin(ang) * ry
            z = math.sin(ang)  # z < 0 behind pouch, z >= 0 in front of pouch!
            # Rotate tilt in screen space
            ty = oy * math.cos(math.radians(tilt_deg)) - ox * math.sin(math.radians(tilt_deg)) * 0.35
            tx = ox
            sc = 0.82 + 0.28 * ((z + 1.0) * 0.5)
            rot = math.degrees(ang) * 0.35 + 22.0
            sg = sg_base.resize((int(190 * sc), int(104 * sc)), Image.Resampling.BICUBIC).rotate(
                rot, expand=True, resample=Image.Resampling.BICUBIC
            )
            item = (z, sg, int(round(605 + tx - sg.width * 0.5)), int(round(765 + ty - sg.height * 0.5)))
            if z < 0:
                back_gels.append(item)
            else:
                front_gels.append(item)

        for _, sg, gx, gy in sorted(back_gels, key=lambda x: x[0]):
            bg.alpha_composite(sg, (gx, gy))

        # Hero Pouch entrance spring (0.0..0.55s) + smooth levitation + diagonal sheen sweep
        if local_t < 0.55:
            su = local_t / 0.55
            p_scale = 0.42 + 0.58 * (1.0 - (1.0 - su) ** 3) + 0.06 * math.sin(su * math.pi)
        else:
            p_scale = 1.0
        hover_y = 14.0 * math.sin(local_t * 2.4)
        sheen_prog = (local_t - 1.1) / 1.35 if 1.1 <= local_t <= 2.45 else ((local_t - 4.4) / 1.35 if 4.4 <= local_t <= 5.75 else -1.0)
        pouch_cur = apply_sheen_to_rgba(pouch_s3, sheen_prog)
        if abs(p_scale - 1.0) > 0.004:
            pw = max(1, int(round(s3_w * p_scale)))
            ph = max(1, int(round(s3_h * p_scale)))
            pouch_cur = pouch_cur.resize((pw, ph), Image.Resampling.BICUBIC)
        px_pos = int(round(605 - pouch_cur.width * 0.5))
        py_pos = int(round(760 + hover_y - pouch_cur.height * 0.5))
        bg.alpha_composite(pouch_cur, (px_pos, py_pos))

        for _, sg, gx, gy in sorted(front_gels, key=lambda x: x[0]):
            bg.alpha_composite(sg, (gx, gy))

        return bg.convert("RGB")

    def compose_scene_06_frame(local_t: float) -> Image.Image:
        # local_t in [0.0, 3.0]
        u = local_t / 3.0
        bg = im_s6_bg.convert("RGBA")

        # Volumetric golden spotlight cone onto the exact product pouch on the pedestal (cx=725)
        bg.alpha_composite(cone_s6, (0, 0))
        bg.alpha_composite(glow_hero, (725 - glow_hero.width // 2, 1105 - glow_hero.height // 2))

        # Contact shadow squarely on the circular dark pedestal surface (y_bottom = 1398)
        pouch_cx = 728
        pouch_bottom_y = 1398
        bg.alpha_composite(shadow_s6, (pouch_cx - shadow_s6.width // 2, pouch_bottom_y - 46))

        # Hero pouch with subtle entrance settle + luxury light sweep across label
        if local_t < 0.35:
            su = local_t / 0.35
            sc = 0.90 + 0.10 * (1.0 - (1.0 - su) ** 3)
        else:
            sc = 1.0
        sheen_prog = (local_t - 0.55) / 1.25 if 0.55 <= local_t <= 1.80 else -1.0
        pouch_cur = apply_sheen_to_rgba(pouch_s6, sheen_prog)
        if abs(sc - 1.0) > 0.004:
            pw = int(round(s6_w * sc))
            ph = int(round(s6_h * sc))
            pouch_cur = pouch_cur.resize((pw, ph), Image.Resampling.BICUBIC)
        bg.alpha_composite(pouch_cur, (pouch_cx - pouch_cur.width // 2, pouch_bottom_y - pouch_cur.height))

        # Composite Ollie's pointing crimson glove in front of the left blank margin of the pouch (true 3D depth!)
        bg.alpha_composite(ollie_glove_fg, (0, 0))

        # Two gleaming 3D golden softgels resting on the pedestal in front of the pouch
        sg1 = sg_base.resize((128, 70), Image.Resampling.LANCZOS).rotate(-12, expand=True, resample=Image.Resampling.BICUBIC)
        sg2 = sg_base.resize((120, 66), Image.Resampling.LANCZOS).rotate(18, expand=True, resample=Image.Resampling.BICUBIC)
        bg.alpha_composite(sg1, (565, 1348))
        bg.alpha_composite(sg2, (665, 1358))

        # Shimmering golden dust motes in the spotlight
        p_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        pd = ImageDraw.Draw(p_layer)
        for px, py, pr, pspd, pph in particles[:28]:
            yy = (py - local_t * (pspd * 0.65)) % 1350 + 80
            xx = 440 + (px % 480) + 10.0 * math.sin(local_t * 2.5 + pph)
            al = int(95 + 85 * math.sin(local_t * 4.5 + pph))
            pd.ellipse([xx - pr * 0.7, yy - pr * 0.7, xx + pr * 0.7, yy + pr * 0.7], fill=(255, 228, 140, al))
        bg.alpha_composite(p_layer)

        # Apply smooth camera push to the entire unified 3D composite so glove & pouch stay locked together!
        rgb_frame = zoom_pan(bg.convert("RGB"), zoom=1.0 + 0.045 * u, dx=6.0 * u, dy=-6.0 * u)
        badge_alpha = min(1.0, local_t / 0.30)
        return draw_top_pill_badge(rgb_frame, font_small, alpha_scale=badge_alpha)

    def render_clean_frame(frame_idx: int) -> Image.Image:
        t = frame_idx / FPS

        # --- BEAT 1: 0.00s .. 5.00s ---
        if t < 5.0:
            if t < 0.80:
                u = t / 0.80
                frame = zoom_pan(im_couch, zoom=1.00 + 0.045 * u, dx=0.0, dy=8.0 * u)
                # Slight moody desaturation before Ollie crashes in!
                frame = ImageEnhance.Color(frame).enhance(0.86)
                if t > 0.70:
                    fl = (t - 0.70) / 0.10
                    frame = Image.blend(frame, Image.new("RGB", (W, H), (255, 232, 165)), fl * 0.65)
                return frame
            else:
                lt = t - 0.80
                # Damped high-energy table-smash camera shake for first 0.48s!
                shake_amp = 28.0 * math.exp(-lt * 8.5)
                sx = shake_amp * math.sin(lt * 58.0)
                sy = shake_amp * math.cos(lt * 71.0)
                # Dramatic zoom toward shouting Ollie on the coffee table
                zm = 1.02 + 0.11 * min(1.0, lt / 3.8)
                frame = zoom_pan(im_s1, zoom=zm, dx=sx, dy=sy + 24.0 * min(1.0, lt / 3.2))
                if lt < 0.14:
                    fl = 1.0 - (lt / 0.14)
                    frame = Image.blend(frame, Image.new("RGB", (W, H), (255, 236, 178)), fl * 0.72)
                # Whip-flash transition out at 4.90..5.00s
                if t > 4.90:
                    fl = (t - 4.90) / 0.10
                    frame = Image.blend(frame, Image.new("RGB", (W, H), (255, 224, 130)), fl * 0.75)
                return frame

        # --- BEAT 2: 5.00s .. 10.00s ---
        if t < 10.0:
            lt = t - 5.0
            # Elastic punch-in on boxing glove clash + subtle superhero bobbing
            if lt < 0.32:
                u = lt / 0.32
                zm = 1.15 - 0.11 * math.sin(u * math.pi * 0.5)
            else:
                zm = 1.04 + 0.06 * ((lt - 0.32) / 4.68) + 0.008 * math.sin(lt * 6.0)
            bob_y = 6.0 * math.sin(lt * 5.5)
            frame = zoom_pan(im_s2, zoom=zm, dx=0.0, dy=bob_y)
            # Pulsing golden hero brightness boost
            br = 1.0 + 0.05 * math.sin(lt * 4.2)
            frame = ImageEnhance.Brightness(frame).enhance(br)
            if lt < 0.12:
                fl = 1.0 - lt / 0.12
                frame = Image.blend(frame, Image.new("RGB", (W, H), (255, 226, 140)), fl * 0.70)
            if t > 9.82:
                fl = (t - 9.82) / 0.18
                frame = Image.blend(frame, Image.new("RGB", (W, H), (255, 218, 115)), fl * 0.88)
            return frame

        # --- BEAT 3: 10.00s .. 17.00s (Hero Product Reveal + Orbiting 3D Softgels) ---
        if t < 17.0:
            lt = t - 10.0
            frame = compose_scene_03_frame(lt)
            if lt < 0.18:
                fl = 1.0 - lt / 0.18
                frame = Image.blend(frame, Image.new("RGB", (W, H), (255, 220, 120)), fl * 0.82)
            # Extra punch zoom on "ONE TEAM!" (15.52..16.20s)
            if 15.52 <= t <= 16.35:
                pu = math.sin(((t - 15.52) / 0.83) * math.pi)
                frame = zoom_pan(frame, zoom=1.0 + 0.045 * pu, dx=0.0, dy=-10.0 * pu)
            return frame

        # --- BEAT 4a: 17.00s .. 19.05s (Human squints at Ollie: "Wait... YOU'RE the boss?") ---
        if t < 19.05:
            lt = t - 17.0
            u = lt / 2.05
            frame = zoom_pan(im_s4, zoom=1.01 + 0.065 * u, dx=-6.0 * u, dy=-12.0 * u)
            return frame

        # --- BEAT 4b: 19.05s .. 22.00s (Ollie double-bicep flex: "Obviously! I'm literally the LEAF...") ---
        if t < 22.0:
            lt = t - 19.05
            # Snappy comedic punch-in + muscle-flex pulse on "LEAF" (~t=20.75s)
            base_z = 1.10 - 0.07 * min(1.0, lt / 0.25) if lt < 0.25 else 1.03 + 0.04 * (lt / 2.95)
            leaf_pulse = 0.045 * math.exp(-((t - 20.85) ** 2) / 0.08)
            frame = zoom_pan(im_s5, zoom=base_z + leaf_pulse, dx=0.0, dy=-8.0 * (lt / 2.95))
            if t > 21.86:
                fl = (t - 21.86) / 0.14
                frame = Image.blend(frame, Image.new("RGB", (W, H), (255, 216, 112)), fl * 0.80)
            return frame

        # --- BEAT 5: 22.00s .. 25.00s (Final Premium Hero Shot on Pedestal) ---
        lt = t - 22.0
        frame = compose_scene_06_frame(lt)
        if lt < 0.16:
            fl = 1.0 - lt / 0.16
            frame = Image.blend(frame, Image.new("RGB", (W, H), (255, 218, 118)), fl * 0.78)
        return frame

    # Save static composite keyframes images/scene_01.png .. scene_06.png for CapCut fallback & inspection
    print("3/4 Saving static composite keyframes (scene_01.png .. scene_06.png)...")
    sample_times = [2.2, 6.5, 13.0, 18.0, 20.5, 23.6]
    for sc_idx, st_sec in enumerate(sample_times, start=1):
        kf = render_clean_frame(int(round(st_sec * FPS)))
        kf.save(img_dir / f"scene_{sc_idx:02d}.png", quality=95)

    # Stream all 750 clean frames (for scene_01..06.mp4) AND 750 subtitled frames (for master commercial MP4)!
    print("4/4 Rendering 750 frames @ 30fps (1080x1920) -> videos/scene_01..06.mp4 + ollie_oregano_commercial_25s.mp4...")

    scene_ranges = [
        (1, 0, 150),    # 0.00 .. 5.00s
        (2, 150, 300),  # 5.00 .. 10.00s
        (3, 300, 510),  # 10.00 .. 17.00s
        (4, 510, 572),  # 17.00 .. 19.07s
        (5, 572, 660),  # 19.07 .. 22.00s
        (6, 660, 750),  # 22.00 .. 25.00s
    ]

    master_out = PROJ_DIR / "ollie_oregano_commercial_25s.mp4"
    master_cmd = [
        ff, "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-i", str(master_wav),
        "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        "-shortest",
        str(master_out),
    ]
    master_proc = subprocess.Popen(master_cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)

    # Open scene encoders sequentially as frames advance so memory stays tiny
    cur_sc_idx = 0
    sc_num, sc_f0, sc_f1 = scene_ranges[cur_sc_idx]
    sc_proc = subprocess.Popen(
        [
            ff, "-y", "-loglevel", "error",
            "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
            "-c:v", "libx264", "-preset", "fast", "-crf", "19", "-pix_fmt", "yuv420p",
            str(vid_dir / f"scene_{sc_num:02d}.mp4"),
        ],
        stdin=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )

    for f_idx in range(TOTAL_FRAMES):
        if f_idx >= sc_f1 and cur_sc_idx + 1 < len(scene_ranges):
            assert sc_proc.stdin is not None
            sc_proc.stdin.close()
            sc_proc.wait()
            cur_sc_idx += 1
            sc_num, sc_f0, sc_f1 = scene_ranges[cur_sc_idx]
            sc_proc = subprocess.Popen(
                [
                    ff, "-y", "-loglevel", "error",
                    "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                    "-c:v", "libx264", "-preset", "fast", "-crf", "19", "-pix_fmt", "yuv420p",
                    str(vid_dir / f"scene_{sc_num:02d}.mp4"),
                ],
                stdin=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )

        clean_im = render_clean_frame(f_idx)
        assert sc_proc.stdin is not None
        sc_proc.stdin.write(clean_im.tobytes())

        sub_im = draw_subtitle(clean_im, f_idx / FPS, font_big, font_med)
        assert master_proc.stdin is not None
        master_proc.stdin.write(sub_im.tobytes())

        if (f_idx + 1) % 150 == 0:
            print(f"   Rendered {f_idx + 1}/{TOTAL_FRAMES} frames ({(f_idx + 1) / FPS:.1f}s)...")

    assert sc_proc.stdin is not None
    sc_proc.stdin.close()
    sc_proc.wait()

    assert master_proc.stdin is not None
    master_proc.stdin.close()
    m_err = master_proc.stderr.read() if master_proc.stderr is not None else b""
    master_proc.wait()
    if master_proc.returncode != 0:
        raise RuntimeError(f"FFmpeg master encode failed: {m_err.decode(errors='replace')[-800:]}")

    print(f"SUCCESS! Master commercial saved to: {master_out} ({master_out.stat().st_size / (1024 * 1024):.2f} MB)")


if __name__ == "__main__":
    main()
