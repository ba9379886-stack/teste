# Protocole Arena (Génération Images + Voix -> GitHub)

Lorsqu'un bloc JSON de projet est envoyé par l'utilisateur dans Arena :

1. **Voix off (`add_voice` puis `generate_speech`)** :
   - Si aucune voix correspondant à `voice` n'a encore été sélectionnée dans la session courante, appeler `add_voice` une seule fois avec la première phrase de narration (~30–45 mots) dans la langue demandée (`fr-FR` ou `fr` si l'accent régional n'est pas supporté).
   - Une fois le `voice_id` obtenu, générer chaque scène dans `projects/<project_slug>/audio/<id>.mp3` en parallèle (jusqu'à 10 appels `generate_speech` par tour).

2. **Images (`generate_image`)** :
   - Générer chaque scène dans `projects/<project_slug>/images/<id>.png` avec `offer_options: false` (puisqu'il s'agit d'assets d'un projet complet et que l'utilisateur demande une génération directe en lot).

3. **Manifest (`projects/<project_slug>/manifest.json`)** :
   - Écrire le fichier `projects/<project_slug>/manifest.json` contenant toutes les métadonnées et les chemins relatifs (`"image": "images/scene_01.png"`, `"audio": "audio/scene_01.mp3"`).

4. **Publication GitHub (`git commit` + `git push`)** :
   - Commiter `projects/<project_slug>/` sur la branche active de la session Arena et pousser sur `origin`.
   - `tools/github_sync.py` côté Windows détecte automatiquement les projets sur toutes les branches `arena/*` ainsi que sur `main` !
