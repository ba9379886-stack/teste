---
name: ai-ugc-ad-video
description: >-
  Create realistic phone-filmed AI UGC creator ads holding or presenting a real product — complete
  with casting rules (age matches claim, room matches problem), natural smartphone selfie prompts
  (imperfect skin, deep depth of field, zero studio bokeh), Arena character & product lock workflow,
  and strict FTC / Meta / TikTok compliance. Use when asked for an AI UGC creator ad, talking-head
  style product ad, Arcads-style AI actor ad, or realistic smartphone creator visuals.
metadata:
  source: vargHQ/skills/ai-ugc-ad-video (adapted natively for Arena + CapCut 9:16)
  priority: "3 (Top 3)"
---

# AI UGC Ad Video — Realistic Phone-Creator Workflow (Arena Edition)

Make an AI-generated creator ad look like an authentic iPhone front-camera recording in a lived-in home or car — **never** like a glossy stock photo or uncanny CGI avatar.

See [references/prompts.md](references/prompts.md) for detailed smartphone camera physics, skin texture cues, room staging, and prompt templates.

---

## 1. Platform Gate — Check Before Casting!

| Placement | AI Creator + AI Voice Allowed? | Required Action |
|---|---|---|
| **Meta Ads (Reels / Feed / Stories)** | **YES** (performs strongly when phone-real) | Keep copy compliant (no personal medical diagnosis callouts; Meta auto-applies AI info label). |
| **TikTok Paid Ads (In-Feed / Spark)** | **YES, with disclosure** | Enable **AIGC toggle** in TikTok Ads Manager (note: duplicating a campaign resets this toggle). |
| **TikTok Shop / Affiliate Video** | **NO — BANNED** | TikTok Shop bans AI voices/avatars as presenters. Switch immediately to `skills/tiktok-shop-video/SKILL.md` (real presenter + AI B-roll only). |

**Universal FTC / DGCCRF Rule:** Never put a first-person personal experience lie (*"Je l'utilise depuis 14 jours et mes douleurs ont disparu"*) in the mouth of an AI persona. Instead, have the AI presenter **demonstrate the mechanism, cite real published studies/reviews, compare ingredients, or explain who it's built for**:
- Bad (Illegal fake testimonial): *"Depuis que je prends ces softgels, je ne tombe plus jamais malade."*
- Good (Compliant & persuasive): *"Voici pourquoi de plus en plus de gens remplacent trois compléments d'hiver par cette seule formule origan + nigelle..."* or *"Sur plus de 400 avis vérifiés, la remarque qui revient le plus souvent, c'est..."*

---

## 2. Casting Rules — Credibility Wins Before Word One

1. **Match the Age to the Claim:** Never cast a 22-year-old model to talk about joint stiffness, blood sugar, or deep fatigue after 40. Cast `34–48` for family/energy/wellness, `50–62` for joints/longevity, `24–32` for skincare/productivity.
2. **Match the Room to the Problem:**
   - Morning energy / digestion / supplements → **Kitchen counter at 7:30 am**, mug, natural window light
   - Sleep / recovery → **Warm bedside lamp**, unmade linen sheet edge
   - Skincare / grooming → **Bathroom mirror / vanity**, real toiletries slightly out of frame
   - Honest confession / rant → **Parked car driver's seat**, seatbelt, overcast daylight through windshield
3. **Anti-AI Skin & Camera Physics (Crucial for `generate_image`):**
   - Always specify: *"Candid vertical 9:16 smartphone front-camera photo (24mm equivalent, deep depth of field f/2.2 where background room details remain sharp and readable — NO DSLR studio bokeh, NO blurred background), natural uneven window lighting, realistic human skin texture with visible pores, slight under-eye creases, stray flyaway hairs, casual everyday cotton t-shirt or sweater, eye-level slightly off-center framing."*
   - **Ban these words in prompts:** `cinematic lighting`, `8k octane render`, `bokeh`, `flawless skin`, `fashion model`, `studio backdrop`, `dramatic rim light`.

---

## 3. Arena Character Lock + Product Lock Pipeline

To keep the **exact same AI creator** and **exact same product** across all 6–9 scenes of a CapCut video:

1. **Step 1 — Generate 1 Frozen Creator Reference Card (`refs/creator_card.png`):**
   Generate one clean `9:16` smartphone portrait of your cast presenter in their fixed outfit and room before generating scenes.
2. **Step 2 — Prepare Clean Product Reference (`refs/product_clean.png` + `overlays/product_pouch.png`):**
   Clean any unwanted badges if requested, and save a crisp RGBA cutout for pixel-perfect label overlays where typography must be 100% legible.
3. **Step 3 — Multi-Reference Scene Generation (`generate_image`):**
   For every creator scene, pass `images=["projects/<slug>/refs/creator_card.png", "projects/<slug>/refs/product_clean.png"]` and start the prompt with a **Verbatim Lock Preamble**:
   > *"Keep the exact same person from the first reference image (same face, hair, age, skin texture, and exact outfit) and the exact same black pouch product from the second reference image. Candid vertical 9:16 iPhone front-camera shot in the same kitchen..."*
4. **Step 4 — Alternate Creator A-Roll with Macro Product B-Roll:**
   Real UGC ads cut away every `3–5s`! Alternate:
   - `Scene 1 (0–3s)`: Creator holding pouch near chest / pointing to problem (Hook)
   - `Scene 2 (3–8s)`: Macro B-roll of golden softgels / ingredients on kitchen counter
   - `Scene 3 (8–14s)`: Creator explaining mechanism + on-screen proof badge (`overlays/`)
   - `Scene 4–6`: Product in use / comparison / study headers
   - `Scene 7 (Last 5s)`: Creator holding product + sharp RGBA packshot overlay & spoken CTA
5. **Step 5 — Voiceover & CapCut Build:**
   Register a conversational voice via `add_voice(language="fr-FR", voice_identity={"use_case": "conversational"})` (or reuse active session voice), generate per-scene `.mp3` clips via `generate_speech`, assemble `manifest.json`, validate with `capcut_builder.py`, and push to GitHub.
