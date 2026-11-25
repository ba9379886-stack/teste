# Bibliothèque de Skills Marketing, Copywriting, UGC & Vidéo (100 % Arena + CapCut)

Ce dossier regroupe **13 skills professionnels** (vos **3 skills prioritaires**, les **4 skills complémentaires demandés**, ainsi que **6 pépites bonus** extraites des catalogues `vargHQ/skills` et `neromtoobad/creator-skills`), tous **adaptés nativement pour Arena et votre pipeline CapCut Windows `9:16` (`1080×1920`)** — sans aucune clé API externe payante (`Kliperio`, `varg`, `WoopSocial` ont été remplacés par les outils natifs d'Arena).

Grâce au fichier racine [`AGENTS.md`](../AGENTS.md), **Arena détecte et active automatiquement le bon skill** selon votre demande. Vous pouvez aussi nommer un skill directement si vous souhaitez forcer une méthode précise.

---

## 1. Les 3 Skills Prioritaires (Installés & Adaptés en Priorité)

| # | Dossier Skill | Origine | Ce qu'il fait dans Arena | Exemple de prompt pour l'utiliser |
|---|---|---|---|---|
| **1** | [`video-script-writer`](./video-script-writer/SKILL.md) | `xnomad-dev/claude-skills` | Rédige des scripts prêts à produire avec **hook 3 couches**, minutage exact (`135–150 mots/min`), indications `[VISUAL]`, `[OVERLAY]`, `[CAPTION]`, shotlist et conversion directe en `manifest.json` CapCut. | *« Écris un script vidéo de 50s sur [sujet/produit] avec `video-script-writer` puis génère le projet CapCut. »* |
| **2** | [`ugc-video-ads`](./ugc-video-ads/SKILL.md) | `kliperio/claude-skills` | Transforme **une simple photo produit** en publicité UGC verticale `9:16` en 5 beats + **3 à 5 variantes de hooks** à tester sur TikTok, Reels, Shorts et Meta Ads (avec détourage RGBA exact du produit). | *« Voici la photo de mon produit : crée une pub UGC de 35s + 3 hooks de test avec `ugc-video-ads`. »* |
| **3** | [`ai-ugc-ad-video`](./ai-ugc-ad-video/SKILL.md) *(+ `references/prompts.md`)* | `vargHQ/skills` | Génère des **créateurs UGC IA ultra-réalistes style selfie iPhone** (peau naturelle, zéro flou studio, âge adapté à la promesse, pièce réaliste, verrouillage visage + produit) conformes FTC / Meta / TikTok. | *« Fais une pub créateur AI UGC réaliste dans une cuisine le matin pour mon produit avec `ai-ugc-ad-video`. »* |

---

## 2. Les 4 Skills Spécifiques Complémentaires

| # | Dossier Skill | Origine | Ce qu'il fait dans Arena | Exemple de prompt pour l'utiliser |
|---|---|---|---|---|
| **4** | [`ad-scriptwriter`](./ad-scriptwriter/SKILL.md) *(+ 4 fichiers `references/`)* | `luckkeii21-dotcom/ad-scriptwriter-skill` | Copywriter Direct-Response complet : **12 frameworks** (`PAS`, `Hook-Story-Offer`, `BAB`, `AIDA`, `4Ps`, `PASTOR`, `Mini VSL 7 étapes`), règle *99% Repel*, *Second Hook (3–15s)*, **18 types de hooks** + **Primary Text & Headline Meta Ads**. | *« Rédige un script Mini VSL de 55s (framework PAS ou 7-Step) + le texte Meta Ads pour mon complément. »* |
| **5** | [`video-script`](./video-script/SKILL.md) *(+ `scripts/check_script.py` bilingue FR/EN + 8 `references/`)* | `vargHQ/skills` | Tableau beat-par-beat (`# \| time \| spoken \| on screen \| visual \| sound`), logique causale *Mais / Donc*, *Question Ladder*, et **script Python `check_script.py` bilingue FR/EN** qui vérifie les WPM, la vitesse de lecture, les hooks mous et les clichés IA. | *« Écris le beat-sheet de cette vidéo et vérifie-le avec `check_script.py`. »* |
| **6** | [`ugc-creator-skill`](./ugc-creator-skill/SKILL.md) *(+ 5 fichiers `references/`)* | `social-media-skills/ugc-creator-skill` | Analyse un brief marque, **tague chaque affirmation** (`experience`, `brand`, `none`, `cut`), vérifie la conformité **DGCCRF / Loi Influenceurs France / ARPP / EFSA / FTC** et génère une checklist de tournage smartphone. | *« Vérifie la conformité publicitaire de ce script santé pour Meta et la France avec `ugc-creator-skill`. »* |
| **7** | [`video-marketing`](./video-marketing/SKILL.md) | `gengirish/social-media-agency` | Stratégie vidéo multi-plateforme : fenêtres de hook exactes (**TikTok 2s, Reels 3s, Shorts 3.5s**), optimisation **85 % son coupé**, safe zones `1080×1920`, mix éditorial `40/25/20/15` et diagnostic des vidéos qui stagnent. | *« Construis un plan de 10 vidéos courtes pour lancer ce produit sur TikTok, Reels et Shorts. »* |

---

## 3. Les 6 Skills Bonus Extraits de Vos 4 Collections de Référence

| # | Dossier Skill | Origine | Pourquoi il est précieux pour vos projets |
|---|---|---|---|
| **8** | [`ecommerce-video-ads`](./ecommerce-video-ads/SKILL.md) *(+ 5 `references/`)* | `vargHQ/skills` | Planificateur maître e-commerce : angles `Acheteur × Problème × Promesse`, **30 formats pub prouvés**, multiplicateurs de conversion Meta/Toluna et plan de test créatif. |
| **9** | [`product-video-hooks`](./product-video-hooks/SKILL.md) *(+ `hook-bank.md`)* | `vargHQ/skills` | Banque de **60+ modèles d'accroches produits (`0–3s`)** alignant simultanément Visuel Frame 0 + Phrase parlée (`6–8 mots`) + Texte écran safe-zone. |
| **10** | [`tiktok-shop-video`](./tiktok-shop-video/SKILL.md) | `vargHQ/skills` | Règles strictes **TikTok Shop / Panier Orange 2025–2026** (pourquoi les voix IA et slideshows y sont pénalisés, comment combiner 15s filmées à l'iPhone + B-roll/overlays générés ici). |
| **11** | [`stickman-video`](./stickman-video/SKILL.md) *(+ `rig.md`)* | `vargHQ/skills` + Pipeline Arena v3 | Crée vos vidéos virales **Stick Man** (*Science/PubMed + Produit*, *Survie JOUR 1 + 3 règles*, *POV*, *Contraste*, *Histoire*) avec cohérence 100 % du personnage et overlays CapCut. |
| **12** | [`product-and-character-lock`](./product-and-character-lock/SKILL.md) | `vargHQ/skills` (`product-lock` + `consistent-characters`) | Verrouille à **100 % l'identité visuelle de vos sachets/flacons** (découpe RGBA `product_pouch.png` + calcul au pixel près des coordonnées CapCut `x, y`) et de vos personnages d'une scène à l'autre. |
| **13** | [`faceless-script-writer`](./faceless-script-writer/SKILL.md) | `neromtoobad/creator-skills` | Scripts **Faceless haute rétention** (comme *Point Nemo* : *Cold Drop*, *Open Loops*, narration au présent, chiffres précis toutes les 20s, zéro phrase robotique IA). |

---

## 4. Répertoire des 4 Catalogues GitHub Sources (Import à la demande)

Si vous souhaitez un jour ajouter un skill ultra-spécifique supplémentaire, Arena a accès direct via `gh api` à vos 4 dépôts de référence :
1. **`vargHQ/skills`** (`86 skills` orientés vidéo/ads : *`ad-creative-testing`, `varg-unboxing-video`, `podcast-clip-cutter`, `youtube-thumbnail`, `ai-ad-compliance-check`, etc.*)
2. **`f0rgent/claude-skills-catalog`** (méta-catalogue classé marketing, copywriting, SEO, growth)
3. **`neromtoobad/creator-skills`** (`55 skills` créateurs : *`anti-ai-slop-writing`, `structured-copywriting-skill`, `youtube-title-generator`, `faceless-video-prompts`, etc.*)
4. **`zhuyansen/awesome-claude-video-skills`** (répertoire curaté de workflows vidéo & montage)
