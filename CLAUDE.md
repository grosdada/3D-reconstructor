# Transmission pour revue — Pano Atelier 0.6.1

Lire en premier `docs/TRANSMISSION-CLAUDE.html` : document autonome en français, illustré, contenant l'état, l'architecture, les essais, les erreurs, les limites, Trompe et les priorités de revue.

Puis lire `skills/blender-photo-modular/SKILL.md`, ses références et `PROCESS-PHOTO-MODULAIRE.md`. Le manifeste d'extension et `bl_info` indiquent 0.6.1. Le README historique et `ETAT-DU-PROTOTYPE.md` racontent les premières itérations, pas l'état courant.

## Invariants

- Modéliser les vraies silhouettes et ouvertures avant de texturer. Un siège peint sur un mur n'est pas un objet 3D.
- Modules déplaçables, pivots fonctionnels, textures attachées aux objets. Tester translation ET rotation, voisins inchangés.
- Albedo généré uniquement dans Base Color ; pas de beauty GPT en émission. Verre, métal, écrans et lumière physiques indépendants.
- Procédural pour grain, roughness, patine générale ; projection pour détails spécifiques. Faible bump et échelle métrique.
- Préserver les versions validées. Les tests ne doivent jamais enregistrer leurs overrides dans les scènes de production.
- Aucune clé, donnée privée, bibliothèque commerciale ou modélisation dans Git. Les images de ce dossier sont uniquement des aperçus de rendus.
- Ne pas annoncer une reconstruction automatique universelle : les scènes actuelles sont des recettes supervisées.

## État et tests

Noyau : `tests_blender.py` (fixtures locales et faux serveur HTTP, aucun appel payant). Multivues : `tests_modular_blender.py`. Exécution : `blender --background --factory-startup --python-exit-code 1 --python <script.py>`.

Les recettes et contrôles de scènes réelles ont souvent besoin de fichiers dans `output/` et de bibliothèques sur le poste d'origine ; ces dépendances ne sont pas distribuées. Ne pas lancer tous les scripts à l'aveugle. `docs/evidence/` conserve une sélection de rapports techniques, avec provenance et statut historique.

L'adaptateur `providers.py` est testé avec une API simulée. Les images GPT des décors ont été générées dans la conversation puis importées. Le parcours API Blender payant complet n'est pas validé. Les défauts identifiés dans le HTML sont des points de revue, pas des corrections déjà implémentées.

## Demande de revue suggérée

Évaluer architecture, invariants de projection, budget mémoire, portabilité, séparation recettes/moteur, reprise transactionnelle et contrats fournisseurs. Proposer un plan progressif pour adapter la planification et la correction de raccords de Trompe à Blender, avec GPT Image comme fournisseur interchangeable. Commencer par une scène fixture minuscule et des tests hors masque ; ne pas refondre toutes les recettes ni appeler une API payante sans instruction.
