# Leçons complémentaires — tour, sas, ville, station-service

État de transmission : 29 octobre 2026, add-on 0.6.1. Voir le document HTML `../../../docs/TRANSMISSION-CLAUDE.html` pour les illustrations et les liens vers le code.

## Matériaux et projection

Préférer le procédural pour les grandes surfaces vues de près : grain, humidité au pied, coulures, écaillage discontinu, roughness et microrelief. Une carte d'ensemble agrandie ne crée pas les détails absents. Ajouter une projection rapprochée si un détail unique exige des pixels supplémentaires ; vérifier le budget de texels selon distance, focale et taille à l'écran.

Éviter les grandes nappes de bruit contrasté qui donnent un aspect marbré. Respecter la logique de l'usure : creux, rives, pieds et arêtes. Le motif antidérapant peut être un shader ; une encoche visible en silhouette doit être modélisée. Les masques Bevel/AO de Cycles nécessitent une stratégie de bake pour un moteur de jeu.

Ne pas éliminer brutalement une projection déjà approuvée. Comparer le procédural pur et un mélange conservant les détails peints. Les groupes de coordonnées de référence sont figés à chaque projection ; une seconde couche après déplacement doit avoir ses propres attributs sans écraser les premiers.

## Géométrie et performances

Des milliers de petits objets peuvent ralentir le chargement davantage qu'un nombre raisonnable de triangles. Regrouper par bâtiment et matériau, conserver un parent fonctionnel. Partager maillages et matériaux pour voitures, végétation, débris et mobilier ; ne pas réaliser inutilement les instances. Distinguer triangles uniques, triangles évalués et coût virtuel des instances.

Le regroupement doit préserver coordonnées et UV. Un booléen sur une somme de boîtes de murs peut retirer une façade sans rapport : pour les ouvertures structurantes de recettes paramétriques, produire explicitement les jambages et linteaux et contrôler les vues extérieures après création de l'intérieur.

## Lecture du terrain et atmosphère

Corriger le contact bâtiment/sol avant d'ajouter de l'herbe. Exclure les points de scatter des chaussées et vérifier la marge de débordement des brins. Réduire la densité du viewport sans changer celle du rendu. Utiliser plusieurs essences pour les fonds, et contrôler tous les angles.

La brume de premier plan reste légère ; des anneaux lointains plus denses permettent de lire des silhouettes et de masquer la fin du décor. Fondre les limites des volumes. Un fond brumeux ne transforme pas un quartier limité en monde infini.

## Intérieur

Interpréter un plan fonctionnel à partir des vues, avec vraies ouvertures, vitrage séparé, portes sur charnières, circulation et mobilier indépendants. Conserver la lumière motivée par les fenêtres et les appliques, documenter les renforts Area. Une fenêtre transmissive peut sembler opaque à cause de roughness, réflexions ou d'un fond opaque placé derrière.

## Contrôle et traçabilité

Conserver avant/après, scripts, prompts, masques, caméras, signatures et rapports. Vérifier au moins : vue source, hors axe, proche, arrière, toit ; transformations de modules ; voisins ; images embarquées ; profondeur et contours ; vraie géométrie d'ouverture. Un rayon central ne certifie pas la navigation entière. Les tests API simulés ne certifient pas le fournisseur réel.

## Inspirations à expérimenter

Trompe suggère un planificateur de vues sur surfaces accessibles, une qualité par texel, des passes dédiées aux toits et trous, puis une correction colorimétrique locale aux raccords. Ce n'est pas encore intégré. Garder les pixels connus de manière déterministe hors du masque, même si le modèle image modifie davantage. GPT Image est un fournisseur possible, sans preuve d'équivalence aux modèles de Trompe sur ce benchmark.
