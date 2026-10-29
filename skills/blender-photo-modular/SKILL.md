---
name: blender-photo-modular
description: Reconstruire un décor Blender modulaire à partir d'une photo ou d'un panorama, avec géométrie éditable, matériaux et éclairage guidés par la référence. Utiliser pour la reconstruction d'environnements, pas pour un simple effet de profondeur sur une photo.
---

# Décor photo vers Blender modulaire

Commencer par la référence visible. Construire une scène crédible en volume, puis étendre le hors champ quand cette partie est satisfaisante. Une entrée panoramique étend la couverture à reconstruire ; elle ne dispense pas de modéliser les ouvertures, les objets et leurs côtés.

## Décisions essentielles

- Examiner la photo avant de choisir une bibliothèque ou une forme de pièce. Une salle générique, même texturée avec la référence, n'est pas une reconstruction fidèle.
- Identifier les éléments et les plans de profondeur, les silhouettes importantes, l'horizon et les sources lumineuses. Séparer les observations des hypothèses. La focale et l'échelle restent des estimations si aucune mesure n'est fournie.
- Interpréter les artefacts de génération comme les détails fonctionnels les plus plausibles. Ne pas reproduire un meuble fusionné, une ouverture impossible ou une commande difforme. Conserver les choix d'interprétation dans le manifeste.
- Modéliser les détails qui produisent silhouette, occlusion ou ombre : cadres, ébrasements, profondeur des portes, caissons, pieds, accoudoirs. Réserver les maps aux motifs fins qui ne changent pas le volume.
- Chaque assemblage a un parent déplaçable et des enfants éditables. Préserver les pivots fonctionnels, notamment les charnières. Les coordonnées de texture doivent suivre les objets déplacés.
- Utiliser le camera mapping là où il aide la fidélité. Il ne remplace pas une géométrie erronée et ne doit pas reporter des silhouettes de sièges sur le sol. Préférer des UV locales ou un bake pour livrer des modules mobiles.
- Pour les vitrages, créer de vraies ouvertures, des cadres épais, des joints, puis une vitre distincte en retrait. Vérifier visuellement la transmission. Les reflets de lumières d'appoint peuvent occulter le fond même si le shader est transparent.
- Les maps d'écran peuvent être des graphiques instrumentaux déterministes ; les brancher sur l'émission avec intensité réglable. Les lumières pratiques doivent avoir une source physique plausible. Documenter les éventuelles lumières d'appoint.

## Boucle de travail

Produire une version indépendante du blend. Régler la caméra par plusieurs repères répartis dans l'image, puis modéliser architecture et mobilier. Rendre tôt depuis la caméra de référence. Corriger d'abord les proportions et les occultations, ensuite les matériaux et la lumière. Vérifier après correction depuis un point de vue latéral et une vue rapprochée.

Avant livraison, vérifier : objets et parents, pivots, UV et images embarquées, matériau de verre, ouvertures, nombre de triangles de base et évalués avec modificateurs. Déplacer temporairement un module et vérifier que ses enfants suivent sans que les modules voisins se déplacent ; restaurer la scène. Un rendu réussi ne prouve pas à lui seul l'éditabilité.

Livrer le blend, un aperçu réellement rendu, les scripts et maps nécessaires pour reproduire la scène, un manifeste des hypothèses et limites. Ne pas présenter une reconstruction spécifique comme une automatisation universelle. Un second décor différent sert à tester la transférabilité.

## Travail vers un add-on

Conserver séparément les données de référence, calibration, plans, modules, matériaux, éclairage et contrôles. Un changement de paramètre d'un module ne doit pas recréer silencieusement toute la scène. Les étapes IA doivent produire des propositions de données éditables, pas seulement des images.

Pour une réparation générative, lier chaque image à sa caméra, son masque, sa signature de géométrie et sa zone autorisée. Réinjecter uniquement les régions visées. Ne pas confondre génération d'une nouvelle vue et validation de cohérence 3D. La génération API dans Blender et la génération via les outils de la conversation sont deux modes distincts.

Lire [references/cockpit-case.md](references/cockpit-case.md) pour le cas cockpit déjà construit, ses fichiers reproductibles, les défauts observés et les contrôles. Les valeurs de caméra et les dimensions de ce cas ne sont pas des valeurs par défaut pour d'autres photos.

Lire aussi [references/multi-scene-lessons.md](references/multi-scene-lessons.md) pour les retours tour, sas, ville et station-service : procédural, projections rapprochées, optimisation, végétation, brouillard et intérieur. Le dossier de transmission général est [docs/TRANSMISSION-CLAUDE.html](../../docs/TRANSMISSION-CLAUDE.html).
