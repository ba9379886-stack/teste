---
name: video-script
description: >-
  Write tight, causal beat-by-beat scripts (`# | time | spoken | on screen | visual | sound`) for
  short social reels, faceless voiceover explainers, product demos, ads, and micro-dramas — backed
  by an automated bilingual (FR/EN) Python validator (`scripts/check_script.py`) that checks WPM,
  caption reading speed, hook timing, AI clichés, causal links, and numeric claims.
metadata:
  source: vargHQ/skills/video-script (upgraded with bilingual FR/EN check_script.py)
---

# Beat-Sheet Video Script & Automated Script Validator

Write scripts engineered for the **ear and eye simultaneously** — where every beat has an exact time window, spoken words sized to natural WPM, readable on-screen supers, concrete visuals, and zero AI-slop phrasing.

## Reference Playbooks by Format
- [references/social.md](references/social.md) — Viral Reels / TikTok / Shorts explainers & storytelling
- [references/ad.md](references/ad.md) — Direct-response product ads (`15–45s`)
- [references/demo.md](references/demo.md) — Hands-on product / software demonstrations
- [references/review.md](references/review.md) — Honest comparison & review scripts
- [references/drama.md](references/drama.md) — Narrative / POV / character conflict shorts
- [references/improve.md](references/improve.md) & [references/judge.md](references/judge.md) — Rewriting weak drafts & scoring scripts

---

## 1. Core Writing Laws

1. **But / Therefore (*Mais / Donc*), Never "And Then" (*Et ensuite*):**
   Link every beat by **contradiction (*Mais / Pourtant*)** or **consequence (*Donc / Résultat*)**. Lists of disconnected facts bleed retention; causal chains pull the viewer to the end.
2. **The Question Ladder:**
   Beat 1 plants a sharp question in the viewer's head. Beat 2 answers half of it while raising a bigger question. Hold the final synthesis until the penultimate beat.
3. **One Number = One Source:**
   Every percentage, date, study count, or dosage in Spoken or On-Screen columns must come from verified user facts or `web_search` — never invented.
4. **Ear-First Sentences:**
   Max `18–20 words` per spoken sentence. No nested relative clauses. Ban AI-slop phrases (*"Dans un monde où..."*, *"Plongeons dans..."*, *"Ce n'est pas juste X, c'est Y"*, *"Révolutionner"*, *"Dites adieu à"*).

---

## 2. Standard `script.md` Beat-Table Format

Write scripts using this exact header + 6-column Markdown table so `scripts/check_script.py` can measure them automatically:

```markdown
format: social
length: 55s
wpm: 145
hook_max: 3.5
max_shot: 8
cta: Lien en bio

| # | time | spoken | on screen | visual | sound |
|---|---|---|---|---|---|
| 1 | 0:00-0:03.5 | Cinq études cliniques ont testé cette graine noire sur le corps humain. | 5 ÉTUDES PUBMED | Stickman blanc tenant une graine noire lumineuse sur fond noir | Impact grave + nappe sombre |
| 2 | 0:03.5-0:10 | Mais un détail sur son dosage change complètement les résultats. | LE DÉTAIL CLÉ | Zoom sur deux gélules dorées + sachet Origan & Nigelle | Whoosh léger |
```

---

## 3. Automated Script QA (`scripts/check_script.py`)

Before generating voiceovers or images, validate any `script.md` in **1 second**:

```bash
python3 skills/video-script/scripts/check_script.py path/to/script.md
```

What `check_script.py` verifies automatically (supports **French & English**):
- **Contiguous Timing:** Zero gaps or overlaps > `0.25s` between beats; total matches `length`.
- **Spoken Pace (WPM):** Flags beats that cram too many words into too few seconds (`> 1.15×` target WPM = `FAIL`).
- **On-Screen Reading Speed:** Warns if supers exceed `~3 words/sec` (`0.33s/word` BBC caption standard).
- **Hook Gate:** Verifies Beat 1 starts at `0:00`, finishes within `hook_max`, and avoids weak openers (*"Salut à tous"*, *"Dans cette vidéo"*, *"Hey guys"*).
- **Bilingual AI-Tell Detector:** Flags machine-written clichés in both French and English.
- **Claim & CTA Check:** Verifies numbers against `facts:` / `[src: ...]` and checks for an actionable CTA in the closing two beats.
