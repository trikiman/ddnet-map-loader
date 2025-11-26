# DDNet Map Loader v2 (Portable)

Petit outil pour double‑cliquer un `.map` et le recharger à chaud sur votre serveur DDNet local. Crée aussi des sauvegardes et des journaux.

## 📋 Prérequis
- Windows 10/11 (sans admin)
- Client/serveur DDNet installés et serveur local accessible

## 🤔 Quoi et pourquoi
- Associe les fichiers `.map` à cette appli.
- Au double‑clic :
  - Valide la carte
  - Sauvegarde la carte actuelle
  - Remplace la carte de travail et envoie `hot_reload`
  - Écrit dans `%APPDATA%\DDNet\maps\ddnet_control.log`
- Idéal pour itérer rapidement en créant des cartes.

## 🚀 Utilisation rapide
1) Vérifier/déplacer `myServerconfig.cfg`
2) Associer les `.map` à cet EXE (recommandé)
   - Clic droit sur un `.map` → Ouvrir avec → Choisir une autre application → Plus d’applications → Rechercher une autre application sur ce PC → `ddnet_control.exe`
   - Cocher « Toujours utiliser cette application… »
3) Double‑cliquer un `.map` (ex. `%APPDATA%\DDNet\maps\mapsfortest\anymap.map`)
4) Consulter les journaux : `%APPDATA%\DDNet\maps\ddnet_control.log`

## 📁 Où placer myServerconfig.cfg
- Pour trouver facilement le dossier `data` de DDNet :
  1) Clic droit sur le raccourci DDNet (barre des tâches/Démarrer/Bureau) → Ouvrir l’emplacement du fichier
  2) Dans le dossier ouvert, aller dans `ddnet` (là où se trouve `DDNet.exe`)
  3) Ouvrir `data` → copier `myServerconfig.cfg` dedans
- Emplacements courants (exemples) :
  - Steam par défaut : `C:\Program Files (x86)\Steam\steamapps\common\DDraceNetwork\ddnet\data`
  - Autre bibliothèque Steam : `<VotreBibliothèqueSteam>\steamapps\common\DDraceNetwork\ddnet\data`
  - Hors Steam/portable : dossier `data` à côté de `DDNet.exe`

## 🧰 Dépannage
- La fenêtre clignote et se ferme → le chemin n’a pas été transmis. Refaire l’association (étape 2) et redémarrer l’Explorateur.
- N’apparaît pas dans « Ouvrir avec » → Utiliser « Rechercher une autre application sur ce PC », choisir `ddnet_control.exe`, cocher « Toujours utiliser… ».
- Icône inchangée → Redémarrer l’Explorateur Windows (cache d’icônes).
- Pas de hot‑reload → Vérifier serveur `127.0.0.1:8303` et RCON; voir le journal.
- Retirer l’association → `registry\remove_map_association_current_user.bat`

## 📂 Contenu
- `ddnet_control.exe`
- `ddnet_loader.ico`
- `myServerconfig.cfg`
- `registry/`
  - `setup_map_association_current_user.bat`
  - `remove_map_association_current_user.bat`