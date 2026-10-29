# 3D Reconstructor / Pano Atelier

Prototype Blender **0.6.1** pour construire des décors modulaires depuis des références, combiner matériaux procéduraux et projections d’albédo, inspecter des vues et réparer des raccords sous masque.

**Commencer par [le dossier de transmission HTML](docs/TRANSMISSION-CLAUDE.html)** : autonome, illustré et lisible hors ligne. Sur GitHub, télécharger le fichier brut puis l’ouvrir dans un navigateur ; GitHub affiche le code HTML, pas la page rendue.

[Brief pour Claude](CLAUDE.md) · [Skill Blender](skills/blender-photo-modular/SKILL.md) · [Processus détaillé](PROCESS-PHOTO-MODULAIRE.md) · [Références et ressources tierces](THIRD_PARTY.md)

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

Installer le ZIP produit `dist/pano_atelier-0.6.1.zip` depuis les préférences de Blender, puis ouvrir **Vue 3D → barre latérale → Pano Atelier**. Aucune dépendance Python externe n’est requise pour enregistrer l’add-on ; les fonctions optionnelles de profondeur nécessitent un environnement MoGe séparé.

## Tests locaux sans API payante

```sh
blender --background --factory-startup --python-exit-code 1 --python tests_blender.py
blender --background --factory-startup --python-exit-code 1 --python tests_modular_blender.py
```

Les scripts créent leurs fixtures dans `test-output/`. Voir `docs/evidence/publication-checks.json` pour les tests de cette livraison. Les contrôles de scènes nommées dans `validate_*` peuvent exiger leurs `.blend`, guides et bibliothèques locales ; ils ne sont pas tous exécutables sur un clone vide.

## Organisation

| Emplacement | Rôle |
|---|---|
| `pano_atelier/` | Code installable de l’extension et manifeste |
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
