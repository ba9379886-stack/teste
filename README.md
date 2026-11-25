# Studio Vidéo Automatisé : Arena (Images + Voix) ↔ GitHub ↔ Claude Desktop ↔ CapCut (Windows)

Ce dépôt relie **Arena** (génération des images IA et des voix off), **GitHub** (stockage et transfert automatique) et **Claude Desktop sur Windows** (écriture du script + assemblage direct du montage dans **CapCut Desktop**).

---

## Installation sur ton PC Windows (une seule fois — 2 minutes)

### Prérequis
- **CapCut Desktop** installé sur Windows
- **Claude Desktop** installé sur Windows
- **Python 3.10+** installé sur Windows ([python.org](https://www.python.org/downloads/) — cocher *"Add python.exe to PATH"*)

### Étapes
1. Télécharge ou clone ce dépôt sur ton PC Windows :
   ```powershell
   git clone https://github.com/ba9379886-stack/teste.git
   cd teste
   ```
   *(Ou clique sur **Code → Download ZIP** sur GitHub et extrais le dossier, par exemple dans `C:\StudioCapCut\teste`).*

2. Double-clique sur **`install_windows.bat`** :
   - Crée l'environnement Python local (`.venv`) et installe `pyCapCut`
   - Détecte automatiquement ton dossier de projets CapCut Windows
   - Connecte automatiquement le serveur MCP **`arena-capcut`** dans ton **Claude Desktop** (`%APPDATA%\Claude\claude_desktop_config.json`)

3. **Redémarre complètement Claude Desktop** *(clic droit sur l'icône Claude dans la barre des tâches en bas à droite → Quitter, puis relance-le)*.

4. Ouvre le fichier **[`PROMPT_CLAUDE_DESKTOP.md`](PROMPT_CLAUDE_DESKTOP.md)** et copie-colle son bloc d'instructions dans un **Projet Claude Desktop**.

---

## Utilisation au quotidien (pour chaque vidéo)

1. **Dans Claude Desktop** : donne ton idée de TikTok / Short (ex. *« Fais-moi un Short de 40s sur l'énigme du triangle des Bermudes »*).
   - Claude écrit le script et te génère un bloc JSON prêt à copier.
2. **Dans Arena** : copie-colle ce bloc.
   - Arena génère toutes les images 9:16 + toutes les voix off (avec choix de voix à la première vidéo) et pousse tout sur GitHub dans `projects/<nom-du-projet>/`.
3. **Retour dans Claude Desktop** : dis simplement *« C'est généré, fais le montage CapCut ! »*.
   - Claude télécharge automatiquement les images et les voix depuis GitHub (même sans merger la branche !) et crée le projet complet dans CapCut Windows :
     - Format **9:16 (1080×1920)** sans bandes noires
     - Voix off enchaînées à la microseconde près
     - Animations **Ken Burns** (zooms et panoramiques fluides) sur chaque image
     - Transitions **100 % gratuites** (aucun blocage CapCut Pro)
     - **Sous-titres dynamiques** découpés façon TikTok/Shorts (+ fichier `.srt` inclus)
4. **Dans CapCut Windows** : ouvre le projet qui vient d'apparaître sur l'écran d'accueil *(si CapCut était déjà ouvert, entre/sors d'un brouillon ou relance CapCut pour rafraîchir l'accueil)*, ajuste si tu veux et clique sur **Exporter** !

> **Astuce sans même passer par Claude Desktop** : tu peux aussi double-cliquer à tout moment sur **`sync_latest_to_capcut.bat`** pour récupérer le dernier projet depuis GitHub et l'envoyer dans CapCut Windows en 1 clic.
