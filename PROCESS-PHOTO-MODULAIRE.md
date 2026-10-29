# Reconstruction de décor à partir d'une photo

## Intention validée avec l'utilisateur — 25 octobre 2026

La photo dicte la scène. Modéliser d'abord les volumes visibles avec leurs détails structurants, leurs matériaux et leur éclairage. Chaque élément doit être déplaçable. Le camera mapping est un outil de fidélité visuelle facultatif ; il ne doit pas remplacer une fenêtre, une porte, un siège ou un meuble par une surface grossière. Étendre ensuite les parties hors champ, en cohérence avec la reconstruction visible. Une entrée 360 change la couverture à reconstruire, pas cette exigence de volume.

Interpréter les artefacts de génération d'image selon leur fonction probable : bouton, articulation, coffret, grille, document, etc. Ne pas reproduire les objets fusionnés ou les perspectives impossibles comme des défauts de géométrie. Noter les interprétations artistiques.

## Étapes et données à conserver pour l'add-on

1. **Référence** : chemin, dimensions, empreinte, type perspective/panorama, annotation des principaux contours. Garder l'original. Ne pas écraser une scène ouverte.
2. **Lecture du décor** : architecture, ouvertures, mobilier, accessoires, sources lumineuses. Distinguer les éléments visibles, déduits et inventés. Les répétitions deviennent des familles de modules.
3. **Caméra** : estimer focale, horizon, hauteur, orientation ; mettre en correspondance plusieurs repères. Une image ne donne pas une échelle absolue. Conserver ces hypothèses dans le manifeste.
4. **Géométrie** : murs, encadrements, embrasures, vitrage séparé, volumes fermés de meubles, détails qui changent la silhouette et l'ombre. Les détails minuscules peuvent rester dans les maps. Éviter les géométries reconstruites par profondeur dense pour ce type de décor léger et éditable.
5. **Modules** : collection par fonction, parent nommé par assemblage, pièces enfants séparées, pivots locaux. Le parent de porte est à sa charnière. Les transformations ne doivent pas modifier la projection des textures.
6. **Textures** : UV attachées aux objets pour les détails, maps d'écrans distinctes branchées sur émission, matériaux physiques pour la peinture, le verre, le vinyle, le métal. Conserver les fichiers de maps et les embarquer dans le blend. Un résultat de GPT Image ne constitue pas une reconstruction géométrique.
7. **Éclairage** : sources motivées par la photo, dimensions et puissance séparées ; choisir les paramètres de gestion des couleurs avant le réglage final. Vérifier les reflets du verre et les hautes lumières des écrans. Ne pas compenser une mauvaise géométrie avec une texture de silhouette.
8. **Contrôle** : rendu caméra de référence, comparaison aux repères, puis décalage latéral et vue de détail. Compter séparément les triangles de base et ceux produits par les modificateurs. Vérifier les maps embarquées, les pivots, l'indépendance des modules et les vraies ouvertures.
9. **Extension** : après validation du visible, construire le hors champ ; générer les textures manquantes sous contrainte de géométrie. Le parcours caméra sert à déceler les manques et raccords. L'inpainting sous masque doit préserver la géométrie et les régions hors masque.

## Étude cockpit courante

- Script reproductible : `build_photo_cockpit.py`.
- Maps instrumentales procédurales : `make_cockpit_maps.py`, petites PNG séparées.
- Sortie : `output/cockpit-photo-modulaire-v1/`.
- Fond spatial : GPT Image intégré, prompt et provenance dans `maps/generation.json`. Application en UV sur un vrai demi-cylindre de 180° ; retour supérieur séparé pour les vitrages de toit.
- Repères de fenêtres et consoles annotés manuellement dans le script. Géométrie construite par intersection de rayons de la caméra estimée avec des plans architecturaux.
- Cette méthode n'est pas une estimation automatique de plans universelle. Le cockpit est un cas de calibration ; une seconde photo doit tester la transférabilité sans réutiliser les proportions du cockpit.
- Interprétations : panneaux de commande lisibles, touches et leviers plausibles, porte à charnières, sièges assemblés, dossiers et accoudoirs, lampadaire de table, schéma de table. Les détails fins ne sont pas des copies exactes des motifs ambigus de la photo.
- Première revue : table trop grande, reflets de softbox trop présents, ambiance trop blanche ; correction par repères de table, réduction de la contribution spéculaire des lumières d'appoint et baisse d'exposition. Ne pas qualifier un rendu de fidèle avant inspection.
- Revue hors axe : les sièges croisaient les caissons malgré une vue de référence acceptable. Contrôle BVH des surfaces évaluées, recherche locale d'un placement libre, puis correction des coordonnées. `find_chair_clearance.py` conserve cette recherche et `verify_photo_cockpit.py` vérifie les intersections, les déplacements de modules, les vitrages et les textures. La vérification des intersections n'est pas un solveur de navigation ou de collision universel.
- Source conservée dans la sortie sous `reference.webp`, SHA-256 `8637ee2d78dfad7ae7d7b20a99bd030966a125cb4293e34f5ea49de0c0494eab`.

## Extraction vers l'add-on

Séparer : `reference` (photo et repères), `calibration`, `layout` (plans et dimensions), `module_library`, `materials`, `lighting`, `inspection`, `repair` et `export`. La bibliothèque ne doit pas imposer une salle hexagonale à toute image. Un manifeste de scène doit permettre de reconstruire un module sans écraser les modifications faites aux autres. Prévoir un mode proposition/édition des hypothèses et une vue de comparaison caméra.

L'intégration API souhaitée reste une étape distincte : clé saisissable, jamais dans les fichiers partagés ; demandes et coûts visibles ; résultat généré attaché à une vue, un masque et une signature de géométrie. Ne pas présenter les outils GPT Image de cette conversation comme une API déjà disponible dans Blender.

## Passe V2 — texture et extension arrière, 26 octobre 2026

L'utilisateur a approuvé la base et demandé de retrouver la patine d'une nouvelle référence, puis d'inventer le décor derrière la caméra. Sortie indépendante : `output/cockpit-photo-modulaire-v2/cockpit-patine-360.blend`. Script `style_extend_cockpit.py`, contrôles `check_cockpit_v2.py`, rendus `render_cockpit_v2.py`.

Trois générations GPT Image intégré conservées dans `maps/`, avec prompts dans `maps/generation.json` : peinture ivoire, résine de sol et atlas de quatre plaques instrumentales. Demander des albédos sans perspective, ombre portée ni reflet de lampe pour les surfaces ; appliquer les reflets en 3D. Utiliser des coordonnées objet locales pour les matériaux répétables et des UV pour les plaques. L'atlas est sélectionné par échelle/décalage UV dans le shader. Le générateur n'ayant pas produit des maps physiques mesurées, la rugosité et le microrelief sont des réglages artistiques dérivés.

La première passe était trop claire et le sol trop granuleux : correction de l'exposition, mélange du sol avec une base greige et réduction de l'amplitude du bump. Le microrelief peut disperser les reflets même si la valeur de rugosité semble faible.

Le nouvel arrière comprend postes de communication/systèmes, consoles latérales, rangements, sas à hublot réel, vestibule fermé et verrières. Les raccords se fondent sur les extrémités mondiales des fenêtres existantes. Un second demi-cyclorama complète l'espace derrière.

Les rendus et les rayons ont révélé des jours aux raccords : hauteur de frise insuffisante, discontinuité de pente entre deux baies, raccord de toit inversé sur le côté gauche, joints sans fond et jonction entre anciens/nouveaux cadres. Correction par géométrie de frise, montants et traverse, en gardant les points du modèle initial. Ne pas masquer un trou avec une image spatiale.

Après corrections : 72 modules, 12 978 triangles de base, 80 454 triangles évalués ; empreinte identique pour la géométrie/transformation des objets V1. Le test de couverture lance 5 400 rayons depuis cinq positions centrales ; ce contrôle échantillonné ne remplace pas un système de collision complet. Vérifier également visuellement l'avant, l'arrière, la diagonale, le raccord et le panorama.

La dernière revue panoramique a révélé des traverses de raccord qui dépassaient dans les coins supérieurs du cadrage original. Reprendre exactement le profil extérieur de l'ancien toit et diviser le raccord en deux panneaux vitrés par côté, plutôt que relier les extrémités par une seule droite. La fermeture géométrique et la discrétion du raccord dans l'image sont deux vérifications distinctes.

## Passe V3 — usure et lumière moins uniforme, 26 octobre 2026

Retour utilisateur : la V2 reste trop propre ; augmenter la brillance/usure du sol, la patine des consoles et les différences d'éclairage sans perdre la mobilité des éléments. `patine_cockpit_v3.py` charge la V2, ajoute des couches procédurales sur les albédos GPT Image existants et produit `output/cockpit-photo-modulaire-v3/cockpit-usure-lumiere.blend`.

Séparer les matériaux de mobilier de ceux de l'architecture avant d'accentuer la salissure. Utiliser une faible occlusion locale pour les creux et des variations de surface en coordonnées objet locales ; ne pas lier ces variations à un Empty mondial. La première prévisualisation avait de grandes taches nuageuses : augmenter la fréquence spatiale du masque et réduire son amplitude évite l'aspect béton/marbre. Les rayures contribuent à la couleur, à la rugosité et à un bump fin.

Le sol combine zones polies, micro-rayures mates et vernis. Une brillance accrue ne suffit pas si les sources sont toutes invisibles aux rayons glossy : autoriser les petites sources pratiques à se refléter, tout en gardant les grandes sources d'appoint masquées. Réduire le remplissage frontal, varier puissance et température des plafonniers, et inspecter avant/arrière pour conserver la lisibilité.

Empreintes avant/après de tous les meshes V2 (géométrie, matrices et parents), test de déplacement et contrôle des coordonnées locales. Aucune géométrie supplémentaire ; les contrôles et rendus partagés prennent maintenant le dossier du blend chargé comme sortie.

## Correction décisive — projection d'albédo multivues, 26 octobre 2026

L'utilisateur préfère la V2 : la V3 a un aspect trop procédural. Un premier essai de photo GPT globale projetée en émission répondait mal à son intention. Sa correction explicite est de ne projeter que l'albédo, sans lumière/ombre/reflet photographié, puis de répéter depuis plusieurs points de vue, réparer les raccords et régler les matériaux physiques pour approcher l'image GPT. La front projection concerne textures et détails peints, pas les volumes ni la lumière. Cette instruction remplace l'hypothèse de projection d'une beauty complète.

Sortie actuelle : `output/cockpit-albedo-multivues-test/cockpit-albedo-multivues.blend`. Six vues carrées à 15,5 mm, positions légèrement décalées et orientations avant/droite/arrière/gauche/plafond/sol. `prepare_albedo_views.py` produit vues éclairées, base color non éclairée et profondeur. GPT reçoit la base color comme cible géométrique, la vue éclairée seulement pour comprendre les surfaces, et une référence pour les matières. Les prompts demandent explicitement aucune ombre, occlusion ambiante ou réflexion. Le résultat reste un albédo estimé, pas une décomposition physique exacte.

`build_albedo_multiview.py` projette les couleurs dans le Base Color du Principled, jamais en émission. Vitrage, métal, CRT et instrumentation restent indépendants. Poids de chaque vue = visibilité par profondeur × fondu de cadre × cosinus d'incidence à la puissance 4. Le mélange normalisé est limité par la couverture réelle. Les réglages de rugosité, vernis et microrelief dérivent des marques colorées avec une faible amplitude et restent artistiques.

La première intégration montrait des grilles et lignes dupliquées : GPT déplace légèrement les motifs et les silhouettes. `make_projection_masks.py` rend les classes de matériaux originales ; `feather_projection_masks.py` fabrique séparément des masques de protection des contours et détails géométriques. Les albédos GPT ne sont pas retouchés par ce calcul. Le facteur de couverture doit être le rapport des poids protégés aux poids avant protection, pas une amplification arbitraire qui annulerait le fondu du masque.

Pour suivre les modules sans artefacts sur les chanfreins : stocker position et normale de référence APRÈS les modificateurs, avec matrices d'objet figées. Un petit Geometry Nodes par objet ne modifie pas la géométrie. Les entrées personnalisées d'un NodesModifier par id-properties ont échoué dans Blender 5.2 ; les constantes sont donc inscrites dans une copie du groupe de coordonnées. Vérifier explicitement translations ET rotations de modules, ainsi que les voisins.

Une trajectoire d'inspection est enregistrée sur `CAM_TRAJET_INSPECTION` (frames 1–241). `render_albedo_checks.py` rend vues avant/arrière/raccord, déplacement de 40 cm, relighting réel, panorama et masque de couverture/recouvrement. Ce premier cycle protège les défauts et conserve la V2 dans les zones cachées ; il ne prouve pas la perfection de tous les raccords. Les petites réparations sous masque peuvent ensuite viser les zones résiduelles sans refaire l'ensemble.

## Pipeline automatique photo → scène, 0.7.0 — 29 octobre 2026

Demande : une interface simple (une ou plusieurs photos, un gros bouton Générer) qui mêle camera mapping et vraie modélisation pour reproduire une photo, en sept phases, avec une note /20 servant d’objectif d’amélioration. Code : `pano_atelier/photo_*.py`, interface `photo_workflow.py`, ligne de commande `photo_to_scene.py`.

Ordre retenu et raisons :

1. **Camera mapping brut** : profondeur sur la caméra de la photo. Il fixe la spatialité et sert d’étalon (« projection brute » notée elle aussi). Il n’est jamais livré comme résultat : sa collection est masquée après la phase 2.
2. **Modélisation** : la profondeur est relue comme une pièce. Gravité depuis le sol ou le plafond, lacet Manhattan, plans RANSAC redressés à moins de 8° des axes, murs prolongés jusqu’au sol, au plafond et aux angles voisins (le mur caché derrière un meuble existe). Les pixels plus profonds que le mur dans son rectangle deviennent des ouvertures construites explicitement (cellules de dalle, jambages et linteaux, sans booléen), avec cadre et vitrage séparé. Le reste devient des objets fermés : relief lissé le long des rayons (la silhouette reste exacte depuis la photo), côtés le long du contour, dos poussé selon les rayons sans traverser les murs, base ramenée au sol si l’écart est inférieur à 25 cm. Le lointain et le ciel vont sur une carte de fond.
3. **Texturing** : délumination de la photo par segments (le flou d’éclairage ne traverse pas les bords d’objets) ou, en mode API, guidée par l’albédo renvoyé dont seules les basses fréquences sont conservées (aucun contour dédoublé si le générateur décale un motif). Atlas UV par module. Les caméras de texturing sont choisies par gain de couverture pondéré par la qualité (incidence, distance, fondu de cadre, visibilité BVH). Chaque vue générée ne remplace que son masque ; le remplissage local se fait objet par objet (rendu d’identifiants). Les masques de raccord sont écrits par module et par vue.
4. **Matériaux** : familles physiques, rugosité d’après les reflets de la photo. Albédo uniquement en Base Color.
5. **Procédural** : détail métrique en coordonnées objet, activé selon le rapport entre la taille du texel et l’empreinte du pixel (distance × angle pixel de la caméra).
6. **Lumière** : un rendu par lumière candidate, puis intensités et teintes résolues par NNLS face à la photo. Les sources d’appoint sont invisibles à la caméra, aux reflets et à la transmission : sinon leur disque apparaît dans le vitrage (constaté sur la fixture). L’exposition résiduelle est appliquée aux lumières, pas au post-traitement, pour que la plaque photo du fond reste intacte.
7. **Note et amélioration** : sous-notes structure, couleur, contours, détail et lumière. Chaque itération corrige l’albédo des surfaces vues par la photo (rapport de luminance restreint aux surfaces modélisées, teinte amortie) et réajuste le look ; elle est annulée si la note baisse.

Erreurs rencontrées et décisions :

- Une régression pixel à pixel pour l’étalonnage écrase le contraste (régression vers la moyenne) : rendu délavé. Remplacée par une matrice de gains bornée ajustée sur des images floutées, puis une correspondance d’histogramme.
- Des courbes par canal créent des anneaux colorés sur les dégradés ; une courbe unique sur la luminance sans pente bornée crée des lignes de niveau. Retenu : courbe de luminance appliquée en rapport, pente limitée entre 0,6 et 1,8.
- Le nœud Render Layers d’un compositeur créé par script pointe sur la scène de contexte : il faut fixer `rl.scene`. Les rendus internes désactivent le compositeur.
- Un driver vers `scene.camera.data.angle` n’est pas résolu par le depsgraph : il faut cibler directement la donnée caméra.
- Une seconde génération dans la même session renomme les objets (`.001`) : tout est indexé par le nom réel de l’objet.

Résultat mesuré sur la pièce analytique 640 × 480 (`photo_fixtures.py`, mode local, Standard, 4 cœurs CPU) : 18,3/20 en environ 3 minutes, contre 18,0 pour la projection brute. La scène reste cohérente hors axe ; le flanc de l’objet, inventé par le remplissage local, reste la zone la plus faible. Aucune photo réelle n’a encore été évaluée, et le chemin API n’est validé qu’avec un serveur simulé.
