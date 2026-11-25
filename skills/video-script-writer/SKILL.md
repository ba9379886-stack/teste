---
name: video-script-writer
description: >-
  Write ready-to-produce video scripts with scroll-stopping hooks, timed segments, B-roll cues,
  on-screen text overlays, burned-in captions, sound cues, and shot lists — adapted directly for
  Arena's native image/speech generation and 9:16 CapCut Desktop Windows pipeline. Use when asked
  to write a YouTube, TikTok, Instagram Reels, Shorts, explainer, tutorial, or promo script.
metadata:
  source: xnomad-dev/claude-skills/video-script-writer (adapted for Arena + CapCut 9:16)
  priority: "1 (Top 3)"
---

# Video Script Writer (Arena + CapCut Edition)

Turn any topic, product, or premise into a **ready-to-produce script** with exact timing math, visual cues, overlays, captions, and a direct path into `projects/<slug>/manifest.json` for 1-click CapCut Windows export.

---

## Phase 1 — Clarify Context (Ask Once or Default Smartly)

Only ask what is missing; default everything else clearly:

| Parameter | Options | Workspace Default |
|---|---|---|
| **Platform & Ratio** | TikTok / Reels / Shorts (`9:16`, `1080x1920`), YouTube (`16:9`) | **Vertical 9:16 (`1080x1920`, 30 fps)** |
| **Target Length** | `15–30s` (fast ad/hook), `45–60s` (story/explainer/UGC), `90s–3m` (Mini VSL / deep dive) | **`45–55s` (7–9 scenes)** |
| **Language & Voice** | French (`fr-FR`, natural energetic/calm narration) or English | **French (`fr-FR`)** |
| **Goal & CTA** | Vente produit (lien en bio / panier), Abonnement ("Abonne-toi"), Commentaire / Débat | Adapté au brief |
| **Visual Mode** | Stick Man, Réaliste / Cinématique, Créateur AI UGC, Faceless Documentaire | Adapté au sujet |

---

## Phase 2 — Timing & Word-Count Math (Non-Negotiable)

Never guess duration. Size every spoken segment to natural speech speed:

- **Conversational / Explainer pace (FR & EN):** `135–150 WPM` (~`2.3–2.5 words/sec`).
  - `15s` ≈ **35–38 words**
  - `30s` ≈ **70–75 words**
  - `45s` ≈ **105–115 words**
  - `55–60s` ≈ **130–150 words**
- **Fast energetic TikTok / Ad pace:** `155–165 WPM` (~`2.6–2.7 words/sec`).
- **Rule of One Scene = One Visual Change:** Cut scenes every **4–7 seconds** (`7–9 scenes` for a `50–55s` vertical video) so retention never drops.
- **Plain Spoken Text for TTS:** Write numbers and symbols out naturally for `generate_speech` (no SSML, no `[pause]` tags inside the TTS string).

---

## Phase 3 — 4-Part Script Architecture & Production Cues

Structure every script with explicit production cues before generating media:

### 1. Hook (`0:00–0:03`) — 3 Agreeing Layers
- **Frame 0 Visual (`[VISUAL]`):** Immediate action, contrast, or product/problem on screen at `0.0s` (never fade from black).
- **Spoken Opener:** 1 punchy sentence (`6–10 words`) — cold drop, counterintuitive stat, pain callout, or curiosity gap. Never open with *"Bonjour à tous"* or *"Dans cette vidéo"*.
- **On-Screen Hook (`[TEXT ON SCREEN]`):** `≤ 8 words`, readable in `< 1.5s`, inside the 9:16 safe zone.

### 2. Context / Agitation (`0:03–0:12`)
- Raise the stakes immediately (**Second Hook**): why the viewer's current assumption fails or what the problem costs them.
- Introduce the visual anchor (e.g. real product cutout in `overlays/` or core visual metaphor).

### 3. Value / Proof / Escalation (`0:12–0:45`)
- Connect beats with **"Mais / Donc" (*But / Therefore*)**, never *"et ensuite"*.
- Anchor every claim to a **concrete number, study, or visible demonstration** (1 proof element per scene).
- Use production cues per scene:
  - `[VISUAL / SCENE PROMPT]` — exact 9:16 composition for Arena `generate_image`
  - `[OVERLAY]` — optional RGBA cutout (`product_pouch.png`, PubMed header card, UI badge) with CapCut `(scale, x, y)`
  - `[CAPTION]` — short subtitle chunks (`3–6 words` per chunk, max ~36–42 chars)
  - `[CAMERA / MOTION]` — Ken Burns `zoom_in`, `zoom_out`, `pan_up` + CapCut transition (`Fondu`, `Fondu au noir`, hard cut)
  - `[SFX / BGM]` — subtle ambient bed (`12%` volume) or transition cue

### 4. Payoff & Single CTA (`Last 5–8s`)
- Deliver the synthesis / hero product reveal + **one unmistakable action** (e.g., *"Le lien est juste en dessous — clique dans la bio pour commander aujourd'hui."*).
- Leave `0.25–0.4s` breathing room at scene end so speech never clips.

---

## Phase 4 — Deliverables & Arena-to-CapCut Execution

When the user asks for **script only**, output:
1. **3 Hook Variants** (Curiosity, Pain/Problem, Proof/Stat)
2. **Timed Scene-by-Scene Script Table** (`Scene | Time | Spoken VO | Visual / B-Roll | Overlay / Text | Motion`)
3. **Shot / Asset List** (which scenes need reference images, product cutouts, or study headers)

When the user asks to **produce the full video**, chain directly in Arena:
1. Lock character/product references (`skills/product-and-character-lock/SKILL.md`).
2. Generate 9:16 scenes via `generate_image` (`offer_options=false` inside multi-scene builds) and RGBA overlays in `projects/<slug>/overlays/`.
3. Synthesize each scene's voiceover in parallel via `generate_speech` (reusing registered `voice_id` or calling `add_voice` once if none exists).
4. Write `projects/<slug>/manifest.json` (measured audio durations, Ken Burns presets, `overlays` array, chunked `subtitles`), update `projects/latest.json`, validate with `.venv/bin/python -m tools.capcut_builder`, and push to GitHub.
