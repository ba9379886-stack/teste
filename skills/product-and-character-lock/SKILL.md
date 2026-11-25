---
name: product-and-character-lock
description: >-
  Keep products (logos, typography, pouch/bottle geometry, badge removals) and characters/locations
  100% identical across every multi-scene image in Arena and CapCut. Combines Product Lock Sheets,
  RGBA flood-fill cutouts, pixel-measured CapCut overlay coordinates, and Frozen Character/Location
  Reference Cards.
metadata:
  source: vargHQ/skills/varg-product-lock + varg-consistent-characters (adapted natively for Arena)
---

# Product Lock & Character Consistency Engine (Arena + CapCut)

Eliminate the #1 giveaway of amateur AI ads: **melted packaging text, morphing pouch shapes, unwanted supplier badges, and characters whose face or clothes change between scenes.**

---

## Part A — Product Lock Protocol (100% Exact Packaging)

Whenever a video features a real physical product (pouch, bottle, jar, box, device):

### 1. Write a 4-Line Product Lock Sheet
Before generating any image, inspect the user's product photo with `read_file` and define:
- **Geometry:** e.g., *Matte black stand-up resealable pouch, rounded bottom gusset, vertical rectangular silhouette (`448×610` aspect)*
- **Surface & Graphics:** *Gold/green botanical artwork of oregano leaves + white Nigella flower & black seeds, two golden translucent softgels at bottom right*
- **Exact Text:** *"OIL OF OREGANO WITH BLACK SEED OIL — 60 Softgels — Dietary Supplement"*
- **Forbidden Drift:** *No round plastic pill bottle, no white pouch, no "NEW LOOK" corner sticker if badge-free requested, no misspelled gibberish text.*

### 2. Clean Badge & Extract Crisp RGBA Cutout (`overlays/product_pouch.png`)
1. If the raw photo has a sticker/badge to remove (e.g. *"NEW LOOK"*), call `generate_image(images=[raw_photo], prompt="Remove only the circular sticker badge on the upper right, reconstructing the clean matte black pouch corner seamlessly; keep every single letter, botanical illustration, softgel, and proportion 100% identical on pure white background.")` and visually inspect via `read_file`.
2. Run Python + Pillow border flood-fill alpha extraction (with smooth edge feathering and tight bounding-box crop) to save `projects/<slug>/overlays/product_pouch.png` (`RGBA`).

### 3. Pixel-Exact CapCut Overlay Placement
Never eyeball CapCut coordinates when placing `product_pouch.png` onto a glowing spotlight, hand, or pedestal:
1. Measure the target spotlight/pedestal center `(cx, cy)` on the `1080×1920` scene PNG using a quick Python/Pillow script.
2. Convert directly to `pyCapCut` `ClipSettings` coordinates:
   ```python
   transform_x = round((cx - 540) / 540, 2)   # -1.0 (left) to +1.0 (right)
   transform_y = round((960 - cy) / 960, 2)   # -1.0 (bottom) to +1.0 (top)
   ```
   *(Example proven in Stick Man v3: `scene_08` central hero spotlight → `scale=0.44, x=0.0, y=0.04`; `scene_02` & `scene_09` right-side spotlight → `scale=0.33, x=0.39, y=0.25..0.30`.)*

---

## Part B — Character & Location Lock Protocol

Whenever a human presenter, mascot, or Stick Man appears across multiple scenes:

1. **Generate Frozen Reference Cards First (`refs/`):**
   - `refs/character_card.png` — Exact face, hair, age, body build, and **one fixed outfit** for the entire video.
   - `refs/location_card.png` *(optional)* — Empty room/set (kitchen, studio, street) with zero people so lighting and walls never drift.
2. **Pass References to Every Scene (`generate_image(..., images=[...])`):**
   Start every scene prompt with the **exact same Lock Preamble** naming each reference image by index (*"First reference image is Character A — keep identical face, hair, age, and olive sweater. Second reference image is the exact matte black product pouch..."*), then describe **only** the new camera framing, gesture, and action for that beat.
3. **Inspect Before Building (`read_file`):**
   Always view generated key scenes with `read_file` to verify zero anatomical glitches, zero unwanted baked-in text collisions, and 100% character/product consistency before pushing to GitHub.
