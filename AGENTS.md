# AGENTS.md — Studio Marketing, Copywriting, AI UGC & CapCut Automation

Ce dépôt (`ba9379886-stack/teste`) est le **studio tout-en-un** de création marketing, copywriting publicitaire, scripts vidéo, publicités UGC IA et génération automatique de projets **CapCut Desktop Windows (`9:16`, `1080×1920`, `30 fps`)** dans Arena.

---

## 1. Préférences Permanentes & Conventions Utilisateur

- **Langue de communication :** Toujours répondre en **français** (sauf demande explicite d'écrire une copie en anglais).
- **Format vidéo par défaut :** Vertical **`9:16` (`1080×1920`, `30 fps`)** compatible **CapCut Desktop sur Windows**.
- **Zéro dépendance SaaS externe payante :** Tout se fait nativement dans Arena (`web_search`, `fetch_page`, `generate_image` avec images de référence, `add_voice` / `generate_speech`, Python/Pillow pour découpes RGBA `overlays/`, `tools/capcut_builder.py`, puis `git push` vers GitHub). Sur son PC Windows, l'utilisateur lance uniquement `sync_latest_to_capcut.bat` (ou la commande Python `capcut_builder`).

---

## 2. Routage Automatique des Skills (`skills/`)

Avant d'écrire un script, des hooks, une copie publicitaire ou de générer une vidéo, **lis systématiquement le fichier `SKILL.md` (et ses `references/`) correspondant à la demande** :

### Priorité Top 3 (Cœur du Studio)
| Intention / Demande Utilisateur | Skill à charger en premier | Rôle clé |
|---|---|---|
| Script prêt à tourner/monter (timings, B-roll, texte écran, sous-titres, shotlist) | `skills/video-script-writer/SKILL.md` | Mathématiques WPM (`135–150 mots/min`), découpage `4–7s`/scène, cues `[VISUAL]`, `[OVERLAY]`, `[CAPTION]` |
| Pub produit à partir d'une photo produit + tests multi-hooks TikTok/Reels/Meta | `skills/ugc-video-ads/SKILL.md` | Workflow 100 % natif Arena : photo produit -> 5 beats UGC + 3 à 5 hooks + découpe RGBA `overlays/` |
| Créateur IA réaliste (style iPhone selfie / Arcads) tenant un vrai produit | `skills/ai-ugc-ad-video/SKILL.md` + `references/prompts.md` | Casting crédible (âge = promesse, pièce = problème), physique caméra smartphone sans bokeh, conformité FTC/ARPP |

### Skills Copywriting, Validation, Conformité & Stratégie
| Intention / Demande Utilisateur | Skill à charger | Rôle clé |
|---|---|---|
| Script pub Direct-Response (`PAS`, `BAB`, `Hook-Story-Offer`, `4Ps`, `PASTOR`, `Mini VSL`) + texte Meta Ads | `skills/ad-scriptwriter/SKILL.md` + `references/{frameworks.md,hooks.md,offer-cta-library.md}` | Principe *99% Repel*, Hook 4 couches, *Second Hook (`3–15s`)*, Primary Text Meta (`<125 car.`) + Headline |
| Découpage beat-by-beat (`# \| time \| spoken \| on screen \| visual \| sound`) & audit anti-clichés IA | `skills/video-script/SKILL.md` + `scripts/check_script.py` | Connecteurs causaux *Mais / Donc*, *Question Ladder*, validation auto FR/EN via `check_script.py` |
| Audit d'un brief marque, conformité allégations santé/revenus (DGCCRF/ARPP/FTC), mentions légales | `skills/ugc-creator-skill/SKILL.md` + `references/{claims.md,disclosure.md,platforms.md}` | Tagging des claims (`experience`, `brand`, `none`, `cut`), règles *Collaboration commerciale* & anti-faux témoignage |
| Stratégie social media, durée optimale, safe zones `9:16`, rétention `3s` et calendrier éditorial | `skills/video-marketing/SKILL.md` | Fenêtres de hook par plateforme (TikTok `2s`, Reels `3s`, Shorts `3.5s`), test muet `85%`, piliers de contenu |

### Skills Spécialisés E-Commerce, Hooks, Stick Man & Storytelling
| Intention / Demande Utilisateur | Skill à charger | Rôle clé |
|---|---|---|
| Plan d'attaque pub e-commerce complet (`Buyer × Problem × Promise`, 30 formats, batch de test) | `skills/ecommerce-video-ads/SKILL.md` + `references/{formats.md,structure.md,platform-rules.md}` | Multiplicateurs Meta/Toluna, angles par niveau de conscience, plan de test créatif |
| Générer 5 à 20 hooks percutants (`0–3s`) pour un produit | `skills/product-video-hooks/SKILL.md` + `references/hook-bank.md` | Alignement 3 couches (Visuel Frame 0 + Voix `6–8 mots` + Texte écran safe-zone `≤ 8 mots`) |
| Vidéo **TikTok Shop / Affiliation** (panier orange, règles anti-ban 2025–2026) | `skills/tiktok-shop-video/SKILL.md` | Interdiction voix IA / slideshows sur Shop, script + shotlist iPhone `5 plans` + B-roll IA Arena |
| Vidéo **Stick Man / Bonhomme bâton** (Science/PubMed, Choix survie `JOUR 1`, POV, Contraste) | `skills/stickman-video/SKILL.md` + `references/rig.md` | Cohérence 100 % du personnage blanc sur `#0B0D13`, espace négatif haut pour `overlays/header_*.png` |
| Fidélité absolue d'un packaging produit ou d'un personnage sur toutes les scènes | `skills/product-and-character-lock/SKILL.md` | *Product Lock Sheet*, détourage RGBA `product_pouch.png`, calcul pixel `(cx, cy)` -> CapCut `(x, y)`, *Character Cards* |
| Storytelling / Documentaire **Faceless** haute rétention (type *Point Nemo*, histoire, mystère) | `skills/faceless-script-writer/SKILL.md` | *Cold Drop*, *Open Loops*, narration au présent, chiffres exacts toutes les `20–30s`, zéro remplissage IA |

---

## 3. Pipeline Technique Arena -> GitHub -> CapCut Windows

Lorsqu'une production vidéo complète est demandée :

1. **Recherche & Vérification des Faits :** Utiliser `web_search` / `fetch_page` pour vérifier les études (ex. PubMed), ingrédients ou chiffres réels.
2. **Script & Validation :** Structurer le script avec le skill approprié (et vérifier si besoin avec `python3 skills/video-script/scripts/check_script.py`).
3. **Verrouillage Produit / Personnage :**
   - Extraire un cutout transparent propre (`projects/<slug>/overlays/product_pouch.png`) si un vrai produit est fourni.
   - Générer les cartes de référence ou réutiliser `scene_01.png` comme ancre visuelle dans `generate_image(..., images=[...])`.
   - Vérifier visuellement les images clés avec `read_file`.
4. **Voix Off (`generate_speech`) :** Utiliser la voix enregistrée de la session (ou `add_voice` en `fr-FR` si aucune voix n'existe encore) et mesurer la durée exacte de chaque `.mp3` avec `mutagen` dans `.venv/bin/python`.
5. **Assemblage CapCut (`manifest.json` + `projects/latest.json`) :**
   - Renseigner `scenes`, `overlays` (piste dédiée au-dessus de la vidéo), `subtitles` (`3–6 mots` par segment), et `bgm` (`volume: 0.12`).
   - Tester systématiquement la génération du brouillon avec `.venv/bin/python -m tools.capcut_builder --project <slug>` dans un dossier temporaire existant (`tempfile.TemporaryDirectory()`).
6. **Git Commit & Push Fiable :**
   - Pousser uniquement sur la branche active de la session avec HTTP/1.1 pour éviter tout blocage sur les fichiers média :
     `git -c http.postBuffer=52428800 -c http.version=HTTP/1.1 push origin <current-branch>`
