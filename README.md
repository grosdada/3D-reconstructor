# 3D Reconstructor / Pano Atelier

Prototype Blender **0.7.0** pour reconstruire une scène éditable depuis une ou plusieurs photos, construire des décors modulaires depuis des références, combiner matériaux procéduraux et projections d’albédo, inspecter des vues et réparer des raccords sous masque.

**Commencer par [le dossier de transmission HTML](docs/TRANSMISSION-CLAUDE.html)** : autonome, illustré et lisible hors ligne. Sur GitHub, télécharger le fichier brut puis l’ouvrir dans un navigateur ; GitHub affiche le code HTML, pas la page rendue.

[Brief pour Claude](CLAUDE.md) · [Skill Blender](skills/blender-photo-modular/SKILL.md) · [Processus détaillé](PROCESS-PHOTO-MODULAIRE.md) · [Références et ressources tierces](THIRD_PARTY.md)

## Nouveau en 0.7.0 · Photo → Scène 3D

Panneau **Vue 3D → barre latérale → Pano Atelier → Photo → Scène 3D** : ajouter une ou plusieurs photos (la première est la référence), choisir *Locales* ou *Modèle API*, puis **GÉNÉRER**. Une nouvelle scène est créée ; la scène ouverte n’est jamais modifiée.

| Phase | Ce qui est produit |
|---|---|
| 1 · Camera mapping | Profondeur (fichier, MoGe, sinon diorama sol + fond), caméra de référence, maillage brut projeté depuis la photo : version rough fidèle à la spatialité. |
| 2 · Modélisation | Gravité et orientation Manhattan, plans RANSAC redressés (sol, murs, plafond prolongés derrière les occultants), vraies ouvertures avec jambages, cadres et vitrages, objets fermés (relief débruité, dos poussé le long des rayons, posés au sol), fond lointain. Corrige les étirements et trous du camera mapping. |
| 3 · Texturing multivues | Albédo de la photo (délumination guidée par segments, ou par l’API), atlas UV par module, caméras de texturing placées par gain de couverture glouton (inspiré de Trompe), vues manquantes générées par l’API (ou remplissage local par objet), projection avec test de profondeur, fondus de cadre et de silhouette, harmonisation des couleurs ; **masques de raccord** écrits par module et par vue. |
| 4 · Matériaux | Famille par module (indice de la vision, rôle géométrique, statistiques de texture) → Principled physique ; rugosité estimée sur les reflets de la photo. Albédo seulement dans Base Color. |
| 5 · Procédural | Groupe de détail (grain, bois, brossé, tissage, feuillage) qui apparaît quand un pixel devient plus fin qu’un texel de l’atlas : pas de flou en gros plan, coordonnées locales qui suivent le module. |
| 6 · Lumière & effets | Lumières candidates (soleils, fenêtres, plafonnier, remplissage, sources visibles) rendues une à une puis intensités et teintes résolues par moindres carrés non négatifs face à la photo ; ciel, brume (modèle de Koschmieder sur le canal sombre), glow, vignettage, grain et étalonnage global ; compositeur reproduit dans Blender 5. |
| 7 · Note /20 | Structure (SSIM multi-échelle), couleur (ΔE), contours, détail, lumière ; itérations d’amélioration (albédo par comparaison photo / rendu, réajustement du look) conservées seulement si la note monte ; avis optionnel d’un juge IA. Votre note /20 est journalisée et réajuste les poids de la note automatique. |

Sur la pièce synthétique de test (640 × 480, 4 cœurs CPU, qualité Standard, mode local) : **18,3 / 20** en environ trois minutes, contre 18,0 pour la simple projection de la photo sur la profondeur ; la scène reste cohérente hors axe. Sur une première photo réelle (intérieur de voiture-restaurant, MoGe sur CPU, mode local) : **16,7 / 20** en 8 minutes 30, contre 16,4 pour la projection brute ; meubles en vrais volumes, mais les surfaces vues en rasance depuis la photo restent peu crédibles hors axe. Une seule photo réelle ne fait pas une mesure générale, et le chemin API payant n’a été testé qu’avec un serveur simulé.

Sans interface : `blender --background --factory-startup --python photo_to_scene.py -- photo.jpg [autres…] --out sortie/ [--depth profondeur.npy] [--moge-python …] [--quality DRAFT|STANDARD|FINAL]`. Les photos supplémentaires sont alignées par SIFT + PnP dans le Python MoGe (OpenCV requis) ; sans lui, elles servent de références de matières pour l’API.

## Ce qui est réellement disponible

- Recettes supervisées : cockpit, tour, sas, ville brutaliste et station-service avec intérieur.
- Modules éditables, caméras nommées, navigation, guides couleur/profondeur/masques et projection multivue.
- Matériaux procéduraux et mélange réglable avec les détails projetés ; protections des vitrages et des silhouettes.
- Inspection, retouches locales de test et adaptateur API image/vision avec clé en mémoire de session.

Ce n’est pas une reconstruction universelle « une photo → scène parfaite ». Les recettes contiennent des choix artistiques et des dimensions propres aux références. Les images GPT des décors ont été générées via la conversation, puis importées. Le parcours API payant complet dans Blender reste à valider ; les tests réseau utilisent un serveur local simulé.

## Installer le code courant

Blender déclaré minimum 4.2 ; contrôles effectués sur **Blender 5.2.1 LTS**, Windows. La compatibilité de tous les modules avec chaque version intermédiaire n’est pas garantie.

```sh
python package.py
```

Installer le ZIP produit `dist/pano_atelier-0.7.0.zip` depuis les préférences de Blender, puis ouvrir **Vue 3D → barre latérale → Pano Atelier**. Aucune dépendance Python externe n’est requise pour enregistrer l’add-on ; les fonctions optionnelles de profondeur nécessitent un environnement MoGe séparé.

## Tests locaux sans API payante

```sh
blender --background --factory-startup --python-exit-code 1 --python tests_blender.py
blender --background --factory-startup --python-exit-code 1 --python tests_modular_blender.py
blender --background --factory-startup --python-exit-code 1 --python tests_photo_blender.py
python tests_photo.py            # algorithmes photo → scène, sans Blender
python tests_photo_worker.py     # alignement multi-photos, nécessite OpenCV
```

Les scripts créent leurs fixtures dans `test-output/`. Voir `docs/evidence/publication-checks.json` pour les tests de cette livraison. Les contrôles de scènes nommées dans `validate_*` peuvent exiger leurs `.blend`, guides et bibliothèques locales ; ils ne sont pas tous exécutables sur un clone vide.

## Organisation

| Emplacement | Rôle |
|---|---|
| `pano_atelier/` | Code installable de l’extension et manifeste |
| `pano_atelier/photo_*.py` | Photo → scène : géométrie, texturing, look, note (numpy pur), scène Blender, pipeline, interface, worker MoGe/OpenCV |
| `photo_to_scene.py`, `photo_fixtures.py` | Ligne de commande et pièce analytique de test |
| `package.py` | ZIP par liste explicite de sources ; aucun asset |
| `tests_blender.py`, `tests_modular_blender.py` | Tests sur fixtures indépendantes |
| `build_*`, `prepare_*`, `render_*`, `validate_*` | Recettes de production et contrôles historiques |
| `skills/blender-photo-modular/` | Méthode réutilisable et retours d’expérience |
| `docs/TRANSMISSION-CLAUDE.html` | Synthèse illustrée, état, limites, Trompe et plan proposé |
| `docs/evidence/` | Rapports techniques légers, provenance et contrôles |

## Données volontairement absentes

Aucune modélisation, `.blend`, `.glb`, atlas de production, HDRI, poids de modèle, bibliothèque commerciale ou clé API n’est publiée. `output/`, `dist/`, `.venv/`, `.cache/` et `vendor/` restent locaux. Le HTML ne contient que des illustrations réduites de rendus.

Les scripts historiques peuvent contenir les chemins de bibliothèques du poste de production et dépendent souvent de versions précédentes des scènes. Ces chemins ne donnent pas accès aux assets ; les adapter avant exécution. Les lanceurs VBS présupposent une installation Windows de Blender et les fichiers locaux correspondants.

## Références

[Trompe / Patch](https://github.com/patch-gg/trompe) est une inspiration étudiée, **pas une dépendance intégrée**. L’analyse est liée à la révision `fd81fe467b1e29659597109f14bcf4e7054afa7f`. GPT Image est envisagé comme fournisseur interchangeable ; aucune égalité de qualité, coût ou vitesse avec les modèles de Trompe n’est démontrée.

Le manifeste déclare le code de l’extension sous GPL-3.0-or-later. Les bibliothèques et marques tierces gardent leurs droits propres ; voir `THIRD_PARTY.md`. Les anciens états sont conservés dans `docs/historique/README-prototype-0.3.md` et `ETAT-DU-PROTOTYPE.md` : ne pas les confondre avec l’état courant.
