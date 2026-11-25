---
name: stickman-video
description: >-
  Create viral Stickman / Stick Figure vertical 9:16 videos (Science/Health Explainer with PubMed
  proof headers, Survival Choice "DAY 1 + 3 Rules", POV Story, Fake vs Real Contrast, History
  Deadpan Explainer) with 100% character consistency and CapCut overlays. Use whenever the user asks
  for a "Stick Man", "bonhomme bâton", minimalist black-and-white character explainer, or survival story.
metadata:
  source: vargHQ/skills/stickman-video + proven Arena Stick Man v3 pipeline
---

# Viral Stickman Video Skill (Arena + CapCut 9:16 Edition)

Stickman videos dominate TikTok, Reels, and Shorts because **extreme visual simplicity + deadpan/punchy narration + real proof overlays** creates unbeatable contrast and clarity on mobile screens.

See [references/rig.md](references/rig.md) for stick-figure anatomy proportions, pose angles, expressive eye/posture rules, and timing mechanics.

---

## 1. Five Viral Stickman Formats

| Format | Core Mechanics | Best Length |
|---|---|---|
| **1. Science / Product Explainer (Proven Arena Winner!)** | Expressive white stickman on deep dark background (`#0B0D13`) acting out physiological effects + **real PubMed header overlays** (`y = +0.60`) + **real RGBA product cutout** (`product_pouch.png`) & CTA | `45–60s` (`8–9 scenes`) |
| **2. Survival Choice (`JOUR 1` + Rules)** | *"Jour 1. Tu es le nouveau gardien… Il y a 3 règles."* Rules appear 1-by-1; Rule 3 breaks; ends on **`1: [Choix A] / 2: [Choix B] — ABONNE-TOI POUR LE JOUR 2`** | `22–30s` (`6–7 scenes`) |
| **3. POV Situation** | Frame 0 banner: `POV : ...` + 3 escalating beats + comment question | `18–25s` |
| **4. Contrast (`Attente vs Réalité` / `Erreur vs Solution`)** | Split or sequential staging showing the wrong habit vs. the right mechanism | `15–25s` |
| **5. Deadpan History / Weird Fact** | Grand historical or scientific anomaly told through one tiny stickman's absurd predicament | `45–60s` |

---

## 2. Non-Negotiable Stickman Consistency Rules in Arena (`generate_image`)

Viewers instantly notice if a stickman morphs from a thin line drawing into a 3D marshmallow figure between scenes. Lock **100% identical character design** across all scenes:

1. **Create Scene 1 First & Use It as Visual Style Anchor (`images=[".../scene_01.png"]`):**
   Pass the approved stickman reference image to subsequent `generate_image` calls whenever needed, AND repeat the exact character lock description verbatim:
   > *"Exact same minimalist 2D white chalk/vector stickman character: clean solid white round head (`no nose, no hair, expressive minimalist eyes`), smooth white line body and limbs of uniform stroke thickness on a deep matte charcoal-black background (`#0B0D13`), clean flat 2D illustration, vertical 9:16 (1080x1920)."*
2. **Leave Dedicated Negative Space for CapCut Overlays!**
   - When a scene carries a **PubMed / Study Proof Card** at the top (`y = +0.60`, `scale = 0.88`), instruct `generate_image` to keep the **top 28% of the 9:16 frame clean dark empty space** (no baked-in AI text!).
   - When a scene carries the **Real Product Pouch (`overlays/product_pouch.png`)** on a pedestal or corner spotlight, generate the glowing spotlight/pedestal *empty* in the scene image, measure the exact spotlight center `(cx, cy)` in pixels with Python/Pillow, and convert directly to CapCut normalized coordinates:
     - `capcut_x = (cx - 540) / 540`
     - `capcut_y = (960 - cy) / 960`
   - Never let the AI image model try to draw tiny product pouch text or PubMed citations — render proof headers cleanly via Python/Pillow (`overlays/header_*.png`) and composite the real badge-free `overlays/product_pouch.png` on CapCut's `"overlays"` track!
