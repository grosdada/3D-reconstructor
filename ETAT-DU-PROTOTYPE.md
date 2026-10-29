# État au 25 octobre 2026

## Troisième itération : raccords séparés par objet

- Fichier courant : `output/cockpit-lowpoly-v2/cockpit-lowpoly-v2.blend`.
- 764 triangles, 964 sommets, 206 panneaux/volumes distincts.
- Fenêtres : cadres trapézoïdaux et tableaux en profondeur, vitrage reculé de 22 cm.
- Portes : vantaux épais entrouverts, jambages, linteaux, seuils, espaces fermés derrière.
- Accoudoirs et pieds ajoutés aux sièges. Pas de modélisation des boutons.
- Nettoyage GPT Image du fond sous masque, sans silhouettes du mobilier.
- Six vues GPT Image pour le mobilier, appliquées uniquement à ses surfaces visibles.
- Sélection des projections par angle/distance, correction des diagonales de quads.
- Projection verticale unique sur le sol pour éviter les raccords entre faces du cube.
- Empreinte géométrie/UV identique avant et après les retouches ; aucun polygone ajouté par celles-ci.
- Panneau de retouche : nouveau masque des objets sélectionnés, imposé à la reprojection.
- Comparatifs : `check-center.png`, `check-left.png`, `check-right.png`, `check-forward.png`.
- Architecture : `clay-door.png`, `clay-window.png`. Déplacement : `navigation.mp4`.
- Limites : d'autres raccords restent visibles sur les consoles, portes et fenêtres ;
  les images projetées ne remplacent pas des matériaux physiques, notamment les reflets.
- Les versions v1 et l'étude de profondeur restent intactes. Aucun push.

## Deuxième itération : structure low-poly et GPT Image ici

- Nouvelle scène : `output/cockpit-lowpoly-v1/cockpit-lowpoly-v1.blend`.
- 372 sommets, 208 faces, **404 triangles** en 66 volumes/panneaux éditables.
- Gabarit architectural explicite de cockpit hexagonal, pas reconstruction IA universelle.
- Six vues générées avec l'outil GPT Image de cette conversation, guidées par
  les rendus Blender et la photo d'origine. Aucun appel au compte API de l'utilisateur.
- Textures uniquement issues de projections de caméras fixes, calculées par texel
  dans les UV. Aucun déplacement ni subdivision généré par les textures.
- 30 vues de contrôle (six directions depuis cinq positions) : aucun rayon sans
  géométrie. Cela vérifie la fermeture visuelle, pas la cohérence des textures.
- Limites observées : changements de silhouettes dans la génération, raccords
  imparfaits entre vues et déformations autour du mobilier après déplacement.
- Le rapport distingue projections visibles et projections de secours sur faces
  cachées. Les dessous/arrière du mobilier restent largement non observés.
- Nouveau cycle dans l'add-on : gabarit → export des vues → génération ici → import
  et projection. Le mode structure interdit l'ajout de maillage dense par MoGe.
- Tests : suite enrichie d'un contrôle de fermeture, budget de triangles et retouche
  masquée/annulation de l'atlas partagé. Voir `test-output/tests.json`.
- Le lanceur sélectionne cette nouvelle scène ; l'ancienne reste disponible.
- État : **itération de travail, raccords à affiner**, pas décor fini.

## Premier décor réel : cockpit

Source : `022-cockpit-hexagonal-minimal_base.webp`, fournie par l'utilisateur.
Original préservé ; la copie locale a la même empreinte SHA-256.

- Profondeur calculée localement par MoGe-2 ViT-B sur RTX 5090.
- Champ horizontal estimé : 97,23°, sans mesure photographique de référence.
- Maillage : 146 944 sommets, 288 881 triangles.
- Texture d'origine embarquée dans `output/cockpit/cockpit.blend`.
- Parcours d'inspection : sept positions, amplitude 25 cm dans l'échelle estimée.
- Une position indépendante réservée au contrôle.
- Aucune génération API et aucune modification de la texture de la photo.
- État : reconstruction partielle inspectée, **pas un environnement 360° terminé**.

Les discontinuités de profondeur sont coupées pour éviter de transformer les
contours des consoles en grandes surfaces étirées. Cela laisse des fentes, y
compris depuis la vue d'origine, et des trous plus larges après déplacement.
Ces trous figurent dans les masques géométriques. Les zones derrière la caméra
ne sont pas connues. Les vitres et étoiles compliquent l'estimation de profondeur.

## Vérifications

15 tests automatisés réussis sous Blender 5.2.1, dans `test-output/tests.json`.
Le ZIP a aussi passé la validation officielle du manifeste d'extension Blender.
Scènes de test distinctes des anciens projets. Les appels API sont simulés par
un serveur HTTP local ; le fournisseur réel n'a pas été appelé faute de clé
saisie dans l'add-on. La voie MoGe perspective a été exécutée sur le cockpit.

Le lanceur VBS a ouvert la fenêtre `cockpit.blend` avec Blender 5.2.1. La capture
Computer Use n'a pas abouti (délai d'autorisation, puis `FrameArrived timed out`). Les gestes
de navigation et la disposition effective du panneau restent donc à confirmer
visuellement dans cette fenêtre, malgré l'enregistrement des opérateurs testé.

## À activer pour la génération

Dans les préférences de l'add-on, choisir l'URL et les modèles compatibles, puis
saisir la clé dans le champ masqué. Elle reste en mémoire de session. Le mode
API permet la vision et les corrections ; l'option de surfaces cachées ajoute
la reconstruction MoGe après génération. Son alignement/retour arrière est
testé sur une scène contrôlée, pas encore validé avec un générateur réel.

ComfyUI natif, Gaussian Splatting, soudure topologique des surfaces ajoutées et
validation sémantique après réparation restent des travaux ultérieurs.
