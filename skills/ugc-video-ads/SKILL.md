---
name: ugc-video-ads
description: >-
  Turn any product photo + product facts into scroll-stopping UGC video ads and multi-hook creative
  tests for TikTok, Instagram Reels, YouTube Shorts, and Meta Ads — 100% natively in Arena using
  generate_image (with product reference), generate_speech, RGBA product overlays, and CapCut 9:16
  draft generation (no paid Kliperio API required). Use when the user uploads a product image or
  asks for UGC ads, TikTok/Meta product creatives, or multi-hook ad tests.
metadata:
  source: kliperio/claude-skills/ugc-video-ads (adapted natively for Arena + CapCut 9:16)
  priority: "2 (Top 3)"
---

# UGC Video Ads from Product Photos (100% Native Arena Workflow)

Turn a single product photo and brief into high-converting vertical `9:16` (`1080x1920`) UGC video ads and hook variants — **without any external paid SaaS API**. Arena handles angle research, scriptwriting, visual generation with exact product references, voiceover synthesis, RGBA packshot overlays, and CapCut Windows timeline assembly.

---

## 1. Quick Intake (Infer First, Ask Only If Missing)

Before generating assets, verify these 4 inputs (use `web_search` / `fetch_page` if the user provides a product URL or brand name):
1. **Product Photo & Packaging Details:** Inspect the user's uploaded image via `read_file`. Note exact title text, subtitle, capsule/ml count, pouch/bottle geometry, and colors. (If a promotional badge like *"NEW LOOK"* must be removed, clean it first via `generate_image(images=[...])` and extract a transparent RGBA cutout `overlays/product_pouch.png`.)
2. **Core Selling Proposition:** Pain solved, key active ingredients / mechanism, verifiable proof (studies, reviews, count), and offer/CTA.
3. **Target Platform:** Meta Ads (Reels/Feed), TikTok Spark/In-Feed Ads, YouTube Shorts, or Organic Reels. *(Note: for TikTok Shop affiliate listings, route to `skills/tiktok-shop-video/SKILL.md` because TikTok Shop bans AI presenter voices and slideshows.)*
4. **Creative Style:**
   - **Creator UGC (Phone-Real):** Realistic creator holding/showing the product in a lived-in room (`skills/ai-ugc-ad-video/SKILL.md`).
   - **Product-Hero / Macro B-Roll:** Hands-on demo, ingredient explosion, unboxing, kitchen/bathroom counter lifestyle shots + clean RGBA packshot overlay.
   - **Educational / Stick Man / Proof Ad:** Visual metaphor + PubMed/clinical proof cards + product reveal & CTA.

---

## 2. The 5-Beat High-Converting UGC Ad Structure (`20–45s`)

| Beat | Window | Goal | Visual Strategy in Arena |
|---|---|---|---|
| **1. Scroll-Stopper Hook** | `0–3s` | Stop the target buyer; filter out non-buyers | Problem in action OR thumb-stopping visual contrast + bold hook text (`≤ 8 words`) |
| **2. Agitation / Failed Fixes** | `3–9s` | Show why usual solutions fail (*Second Hook*) | Relatable daily frustration (6am kitchen, office desk, bathroom mirror) |
| **3. Product Bridge & Reveal** | `9–16s` | Introduce the product as the mechanism | Lifestyle hero shot referencing exact product photo + crisp RGBA cutout overlay |
| **4. Specific Benefits & Proof** | `16–32s` | 2–3 concrete outcomes + 1 verifiable number/study | Ingredient/mechanism close-ups, proof header cards, real customer review quote |
| **5. Offer & Clear CTA** | `Last 4–6s` | Single unmistakable action | Hero packshot spotlight + spoken & on-screen CTA (*"Lien en bio"*, *"Commande aujourd'hui"*) |

---

## 3. Multi-Hook Creative Testing Protocol (3 Hooks × 1 Winning Body)

Performance marketers don't guess one ad — they test **hooks first**:
- Keep Scenes 3–5 (**Body + Proof + CTA**) identical.
- Write **3–5 distinct Scene 1 Hooks** using different psychological triggers (never mere synonyms):
  1. **Pain / Callout Hook:** *"Toujours épuisé à 15h malgré 8 heures de sommeil ?"*
  2. **Hidden Culprit / Mechanism Hook:** *"Ce n'est pas le manque de café ton problème, c'est..."*
  3. **Skeptical / Confession Hook:** *"Je pensais que l'huile de nigelle était juste une mode… jusqu'à ce que je lise ces 5 études."*
  4. **Price / Value Anchor Hook:** *"Pourquoi payer 4 flacons séparés quand une seule capsule réunit les deux actifs les plus concentrés ?"*
  5. **Visual Payoff First:** Start directly on the macro golden softgel + pouch reveal.

---

## 4. Arena Product-Fidelity Rules (Zero Melted Labels!)

AI image generators often warp small typography when generating a wide scene. Enforce **100% label fidelity** with our two-layer method:
1. **Reference-Guided Scene Generation:** Pass the clean product image in `generate_image(..., images=["path/to/clean_product.png"])` whenever a hand or counter holds the product so lighting, shape, and color match naturally.
2. **Exact RGBA Packshot Overlay (`overlays/`):** Extract a clean flood-fill RGBA cutout (`overlays/product_pouch.png`) with Pillow and place it on CapCut's `"overlays"` track (`scale`, `x`, `y` in `manifest.json`) over spotlight pedestals, corner badges, or CTA end-cards — guaranteeing razor-sharp packaging typography in `1080x1920`.

---

## 5. Compliance Check Before Delivery

- **Never invent reviews, clinical percentages, or discounts.**
- **FTC / ARPP AI Testimonial Rule:** If an AI-generated character appears on screen, write factual product statements, third-person customer quotes, or educational explanations — **never** fake a first-person personal testimony (*"J'en prends depuis 3 mois et j'ai guéri mon..."*) for a synthetic person.
- **Health & Supplements (DGCCRF / EFSA / Meta):** Avoid medical cure claims (*"guérit"*, *"soigne le diabète"*); use compliant physiological/study phrasing (*"étudié pour son action sur..."*, *"soutient l'immunité"*, *"contribue à..."*). Also avoid Meta personal-attribute traps (*"Souffrez-vous de diabète ?"* → prefer *"Pourquoi la glycémie s'emballe après les repas..."*).
