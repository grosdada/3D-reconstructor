# Étude cockpit — 25 octobre 2026

Projet : `C:/Users/pc/Documents/Codex/Codex-Blender/pano_atelier`.
Référence : `C:/Users/pc/Downloads/022-cockpit-hexagonal-minimal_base.webp`, 1456 × 816.

Lire le journal complet `PROCESS-PHOTO-MODULAIRE.md` dans le projet. Le script `build_photo_cockpit.py` reconstruit une scène indépendante ; `make_cockpit_maps.py` produit les graphiques instrumentaux. Les sorties sont dans `output/cockpit-photo-modulaire-v1/`. Le rapport `scene-report.json` et le rapport de validation, lorsqu'il est présent, décrivent le résultat réel : les consulter avant de reprendre des chiffres.

## Ce qui a changé dans l'approche

Le premier maillage issu d'une profondeur monoculaire était lourd et déformait la photo. Un template hexagonal très léger a ensuite permis du camera mapping et des masques, mais ne reconstruisait pas suffisamment l'architecture originale. L'utilisateur a précisé l'ordre : photo, modélisation fidèle du visible et de sa lumière, puis invention du hors champ. Ne pas reprendre le template comme géométrie source sans revoir les proportions.

## Construction du cas

- Repères manuels des fenêtres, consoles et table ; intersection des rayons caméra avec des plans. Calibration estimée à 650 pixels de focale pour 1456 pixels de large, caméra à 1,6 m et inclinaison de 4° vers le bas. Ces valeurs ne sont pas une mesure physique du lieu.
- Cadres extrudés, joints, vitres distinctes, embrasure de porte, caissons fermés, petits chanfreins non destructifs, sièges par pièces.
- Ivoire satiné, vinyle gris olive, porte brun tabac, écrans CRT verts avec PNG propres et émission. Les instruments sont des interprétations fonctionnelles et non des copies exactes des signes ambigus de l'image.
- Cyclorama réel en demi-cercle à 180°, rayon 18 m, UV sur une image spatiale créée avec l'outil GPT Image intégré. Retour supérieur séparé pour le toit. Le prompt et la provenance sont dans `maps/generation.json`.
- La V1 ne construit pas encore le verso ; voir la passe V2 ci-dessous pour son extension inventée.

## Corrections déjà motivées par des rendus

La table initiale était trop grande : dériver son plateau des intersections des rayons avec son plan et vérifier aussi le pied. L'éclairage initial était trop blanc : réduire l'énergie/exposition et corriger les valeurs de peinture. De grands disques de lumière se reflétaient dans les vitres : vérifier la visibilité glossy/transmission des sources d'appoint dans Cycles, pas seulement `specular_factor`.

Les origines sont recentrées sans déplacer les sommets dans le monde. Mettre à jour le dependency graph entre les changements de pivots des enfants et la capture de leurs matrices monde pour recentrer les parents. Conserver la charnière de porte explicitement.

Le rendu hors axe a révélé des intersections siège/console et siège/bureau invisibles ou ambiguës depuis la caméra de référence. `verify_photo_cockpit.py` vérifie les intersections des surfaces évaluées avec BVH ; `find_chair_clearance.py` a permis une recherche de position proche sans intersection. Contrôler également les contenances et les zones de circulation quand elles deviennent pertinentes : le test d'intersection de surfaces seul ne constitue pas un système de collision complet.

## Passe V2 : patine et arrière inventé — 26 octobre 2026

Sortie indépendante `output/cockpit-photo-modulaire-v2/cockpit-patine-360.blend`. Construction `style_extend_cockpit.py`, validation `check_cockpit_v2.py`, rendus `render_cockpit_v2.py`. La géométrie et les transformations des objets V1 restent identiques par empreinte ; les nouvelles pièces restent séparées.

Trois textures GPT Image intégré : peinture ivoire patinée, sol greige usé, atlas de quatre plaques d'instrumentation. Prompts et référence dans `maps/generation.json`. Demander un albédo sans perspective ni reflet lumineux ; produire les reflets dans Blender. Coordonnées objet locales pour les surfaces, UV pour les plaques, images embarquées. La rugosité et le bump sont dérivés artistiquement, pas des maps PBR mesurées. Réduire le bump avant de pousser la brillance si le sol semble granuleux.

L'arrière comprend un sas à hublot transparent et charnière, un vestibule fermé, quatre consoles, des rangements, des verrières et un second cyclorama de 180°. Il s'agit d'une invention cohérente, pas d'une reconstruction d'une zone photographiée. Raccorder murs et toit sur les coordonnées mondiales et le profil exact de l'avant existant. Une seule traverse droite peut dépasser dans le cadrage si l'ancien toit comporte plusieurs segments.

Contrôles : déplacer un module avec ses enfants et textures ; vérifier les voisins ; lancer des rayons vers l'enveloppe en excluant le cyclorama ; inspecter aussi les rendus avant, arrière, oblique, raccord et panorama. Les 5 400 rayons de ce cas ne garantissent ni une étanchéité topologique universelle ni les collisions pendant toute navigation. Les chiffres courants sont dans `scene-report.json` et les résultats dans `validation.json`.

## Passe V3 : retour utilisateur sur la propreté

L'utilisateur demande davantage de brillance/usure au sol, de patine sur les consoles et une lumière moins uniforme. `patine_cockpit_v3.py` ajoute des couches procédurales sur les albédos V2 et sauvegarde une V3 distincte. Séparer les matériaux du mobilier de ceux de l'architecture pour ne pas salir tous les objets pareil. Les coordonnées d'usure doivent rester locales. Un masque de bruit trop large et contrasté produit un aspect marbré ; réduire son amplitude et affiner son échelle avant validation.

La brillance du sol dépend aussi des sources visibles aux rayons glossy. Autoriser les petites lumières pratiques à se refléter, sans réintroduire les grands disques des sources d'appoint dans les vitrages. Réduire le remplissage frontal et varier les puissances/températures des plafonniers. Vérifier les rendus avant et arrière, l'empreinte géométrie/matrices/parents, les images embarquées et un déplacement de module. Les contrôles et rendus partagés choisissent maintenant le dossier du blend ouvert.

## Instruction prioritaire suivante : albédo multivues

L'utilisateur préfère la V2 à la V3, trop procédurale. Il a corrigé le premier essai de projection GPT : projeter uniquement l'albédo et les détails de texture, pas une beauty avec lumière/ombres/reflets figés. Répéter depuis plusieurs angles, traiter les raccords par mélange ou masques, puis régler les matériaux physiques pour approcher la photo GPT. Respecter cette correction pour les prochains essais.

Cas réalisé : `output/cockpit-albedo-multivues-test/`. Scripts : `prepare_albedo_views.py`, `make_projection_masks.py`, `feather_projection_masks.py`, `build_albedo_multiview.py`, `render_albedo_checks.py`. Six albédos GPT guidés par de vraies vues base color et géométrie ; prompts conservés. Les images générées ne constituent pas des albédos physiquement mesurés et peuvent garder des contrastes résiduels.

Projeter en Base Color du Principled, garder verre/CRT/métaux indépendants ; visibilité par profondeur, poids angulaires, fondus des recouvrements. Les légers déplacements de motifs par GPT créent des grilles dédoublées : protéger les contours et détails déjà modélisés via des masques sémantiques, conserver la V2 là où la projection est risquée. Un rapport poids protégés/poids initiaux préserve le fondu des protections. Positions/normales de référence après chanfreins dans Geometry Nodes ; matrices figées dans le groupe par objet, pas un projecteur mondial mobile. Contrôler déplacement ET rotation des modules, un changement de lumière et des vues intermédiaires.

## Limite de généralisation

Les repères, les plans et les interprétations ont été définis artistiquement pour cette image. Un add-on doit permettre leur édition et leur remplacement, puis proposer leur estimation. La fabrication de cette scène ne valide pas une reconstruction automatique depuis n'importe quelle photo. Le second test demandé par l'utilisateur reste à faire sur une autre référence.
