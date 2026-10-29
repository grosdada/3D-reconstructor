# Pano Atelier — prototype Blender 0.3

## Raccords du mobilier et architecture en volume

Le lanceur ouvre `output/cockpit-lowpoly-v2/cockpit-lowpoly-v2.blend`.
Il respecte désormais les préférences enregistrées de souris et de clavier :
il ne démarre plus avec le profil usine. Le réglage Alt se trouve dans Préférences
> Entrée > Souris > Émuler une souris à 3 boutons.
Le gabarit comporte désormais 764 triangles : douze fenêtres trapézoïdales avec
cadres et retraits de 22 cm, deux portes de 9 cm d'épaisseur entrouvertes avec
embrasures et espace derrière, ainsi que les volumes des consoles, sièges et socle.
Les écrans/boutons et détails fins restent dans les textures projetées.

Pour corriger les anciennes silhouettes fantômes, GPT Image a produit un fond
nettoyé sous masque, puis six vues du mobilier guidées par sa géométrie. Les
masques issus des surfaces visibles empêchent de reporter un siège sur le sol.
Les projections sur le mobilier privilégient l'angle de vue et la distance ; le
sol reçoit une seule projection verticale de l'image générée pour supprimer les
raccords de cube. Les 764 triangles et les UV restent identiques pendant la retouche.

Dans **Retouche manuelle**, cocher **Masquer uniquement les objets sélectionnés**
avant la capture pour cibler le mobilier. Le masque et l'application de la correction
restent limités à ces objets même si le générateur modifie le reste de l'image.
Le retour arrière peut recharger la texture précédente depuis son fichier local.
Conserver les dossiers de résultats pour cette restauration après réouverture.

Les rendus et `navigation.mp4` montrent l'essai sur une translation de -85 à +85 cm.
Des défauts de projection subsistent ailleurs dans l'architecture ; les reflets
du sol sont photographiques et restent figés. Ce n'est pas une validation de tous
les déplacements possibles. Le fichier livré est une nouvelle base ; l'historique
de fabrication et les versions précédentes restent dans leurs dossiers.

Générations : outil GPT Image de la conversation, sans appel à la clé API de
l'utilisateur. Prompts : `output/cockpit-lowpoly-v2/background-prompt.txt` et
`furniture-prompt.txt`. Masques, guides et photos générées sont dans le même dossier.

## Atelier low-poly avec GPT Image

La première version low-poly à 404 triangles reste dans
`output/cockpit-lowpoly-v1/cockpit-lowpoly-v1.blend`. Le gabarit actuel à
**764 triangles** ajoute les volumes architecturaux décrits plus haut.
La reconstruction dense précédente est également conservée.
Le gabarit est dessiné pour ce cockpit ; ce n'est pas une reconnaissance automatique
de l'architecture d'une image quelconque.

Dans le panneau, **Créer le cockpit low-poly (gabarit)** crée une scène séparée.
**Exporter les six vues pour GPT Image** produit `guide-atlas.png` et les matrices
des caméras. Ordre exact : avant / droite / arrière, puis gauche / haut / bas.
Les six vues carrées ont un champ de 90°. Utiliser cet atlas et la photo source
comme références dans GPT Image ici, en conservant les silhouettes et les cadrages.
La génération intégrée à cette conversation n'est pas un service appelé par Blender.

Importer l'image obtenue dans **Atlas généré 3 × 2**, puis **Projeter les six vues
sur le décor**. La projection est calculée pour chaque texel de surface et conservée
dans un atlas UV de 4096² ; elle reste fixe lorsque la caméra de navigation bouge.
Les images sont embarquées dans le `.blend`. Le retour arrière restaure les textures.
Les corrections du parcours gardent la structure low-poly et ne lancent pas MoGe.

Limites constatées sur cet essai : GPT Image a modifié certaines silhouettes ; les
vues générées ne se raccordent pas parfaitement. Les faces cachées depuis le point
de génération reçoivent une projection de secours, identifiée dans le rapport et
la carte de couverture, à réparer depuis d'autres positions. La part de couverture
est une proportion de texels UV (incluant dessous/arrière du mobilier), pas de
pixels visibles ni de surface physique. La navigation est donc un essai à affiner.

La photo originale est ici une référence pour GPT Image ; les textures de cette
itération sont les vues générées, pas une reproduction photographique exacte.
Prompt conservé dans `output/cockpit-lowpoly-v1/generation-prompt.txt`.

Un add-on local pour reconstruire un décor depuis une image et une profondeur,
inspecter un parcours de caméra, proposer des masques, puis reprojeter des
corrections dans les textures. Le projet et ses résultats restent dans ce dossier.

## Démarrer

Double-cliquer **Ouvrir-Pano-Atelier.vbs**. Le lanceur ouvre le cockpit de test
s'il existe, sinon l'ancienne étude de profondeur ou la démonstration synthétique, avec l'add-on chargé pour cette
session. Il ne modifie pas les préférences globales de Blender.

Installation permanente : Blender > Préférences > Add-ons > menu > Installer
depuis le disque, puis choisir `dist/pano_atelier-0.3.0.zip`.
Ouvrir la barre latérale de la Vue 3D avec **N**, onglet **Pano Atelier**.

## Parcours utilisateur

1. Choisir une image. Fournir une profondeur `.npy` ou `.exr`, ou configurer le
   Python MoGe dans les préférences. Le Python préparé pour ce poste est
   `.venv/Scripts/python.exe` dans ce dossier.
2. Choisir perspective ou panorama 360° équirectangulaire 2:1. Une image large
   ordinaire n'est pas automatiquement un panorama. Le champ de vision peut
   être estimé par MoGe ou fourni manuellement.
3. Cliquer **Reconstruire dans une nouvelle scène**. La scène précédente reste
   intacte. Les textures sont projetées sur le maillage et embarquées dans le blend.
4. Régler l'amplitude du déplacement et lancer **Explorer et traiter le parcours**.
   Les positions déplacées et les vues de contrôle sont calculées automatiquement.
5. Examiner les images de diagnostic et `report.json`. Orange : candidats texture ;
   rose : rayons sans surface. Un diagnostic géométrique ne prouve pas un défaut
   sémantique : les contours réels peuvent être des faux positifs.
6. **Explorer à la souris** : glisser pour regarder, molette pour avancer/reculer,
   Maj + glisser pour se déplacer latéralement/verticalement, Échap pour sortir.
   Le déplacement est limité au rayon choisi et évite les surfaces détectées.

## Modes

- **Inspection seule** : aucune requête réseau, aucune retouche.
- **Réparation locale de test** : diffusion déterministe des couleurs, sans IA.
  Utile pour tester les raccords synthétiques, pas pour reconstruire les détails
  des consoles d'un cockpit. Ne pas confondre ce mode avec de l'inpainting génératif.
- **IA via API** : endpoint compatible `/chat/completions` pour l'analyse visuelle
  et `/images/edits` pour la génération. Réponse PNG `b64_json` requise.
  Les noms des modèles et l'URL sont configurables. Les valeurs initiales sont
  des exemples OpenAI ; leur disponibilité dépend du compte.

La clé est saisie dans un champ masqué et conservée uniquement en mémoire du
processus. Elle n'est ni dans le blend, ni dans les préférences, ni dans les
rapports. Il faut la ressaisir après fermeture. Aucun coffre persistant n'est
implémenté dans cette version. Les redirections réseau sont refusées ; HTTPS
est requis hors boucle locale. Les erreurs HTTP n'exposent pas les corps de réponse.

Le mode API envoie les vues de la scène et les masques au fournisseur configuré.
Le plafond est un **nombre d'appels**, pas une garantie de coût en euros. Les
requêtes vision et image sont comptées avant envoi, y compris si elles échouent.
Échap arrête les étapes suivantes ; un appel déjà envoyé peut encore finir et
être facturé. Aucune génération payante n'est exécutée pour les tests automatisés.

## Réparation et reconstruction

Les corrections sont reprojetées dans les UV. Un contrôle de visibilité par
triangle empêche de peindre les surfaces cachées derrière un objet. Les pixels
hors masque restent protégés, même si le générateur réécrit l'image entière.
Le rendu envoyé est centré dans un carré puis recadré au retour, pour préserver
la perspective. Les textures d'origine et les versions successives sont conservées.
**Retirer la dernière correction** restaure la version précédente.

L'option **Compléter les surfaces cachées** nécessite l'API ET MoGe. Une nouvelle
profondeur est estimée depuis la vue complétée, puis alignée sur le recouvrement
déjà connu. Le prototype exige au moins 15 % de pixels d'ancrage, au moins 64
pixels, et une dispersion relative médiane des rapports d'échelle <= 20 %.
Les ajouts restent des surfaces séparées ; une topologie parfaitement soudée
n'est pas garantie. Les contrôles exigent une réduction des trous de la vue et
limitent les ruptures de couleur dans les vues de contrôle. Ils ne valident pas
la vraisemblance du contenu généré.

La validation actuelle est géométrique et photométrique. Le modèle de vision
sélectionne des zones à réparer mais ne constitue pas encore un juge après
chaque génération. Il faut revoir les résultats. Les limites et les refus sont
enregistrés, sans affirmer qu'un environnement est intégralement validé.

## Retouche manuelle

Placer la caméra, cliquer **Capturer la caméra et créer son masque**, puis
**Peindre le masque dans Blender**. Blanc = corriger, noir = protéger.
Enregistrer le masque dans l'éditeur d'images. Choisir l'image corrigée puis
**Appliquer l'image dans le masque**. La caméra capturée est réutilisée ; si la
géométrie ou les UV ont changé entre-temps, il faut refaire la capture.

## Profondeur

NPY : tableau flottant H x W, origine en haut à gauche, zéro = invalide.
Perspective : distance le long de l'axe caméra (pas une distance radiale).
Panorama : distance radiale. Pour EXR, le premier canal est utilisé en Non-Color.
Une profondeur inverse ou une image de visualisation colorée doit être convertie
avant import. Le réglage d'échelle ne convertit pas une disparité en profondeur.
MoGe produit une estimation, pas un relevé métrique certifié.

## État des intégrations

- Maillages Blender et projection UV : implémentés.
- MoGe perspective v2 : worker séparé, modèle `Ruicheng/moge-2-vitb-normal`.
- Panorama : import profondeur radiale ; worker MoGe panorama expérimental.
- API image et vision : connecteur implémenté, tests via serveur local simulé.
- ComfyUI natif : pas encore de connecteur de workflow ; utiliser un serveur
  compatible avec le contrat API ou le cycle export/import manuel.
- Gaussian Splatting : pas inclus dans cette première version.
- Pas de génération à chaque frame : le parcours est inspecté par positions clés.
  Les surfaces fines, reflets, transparences et miroirs restent des cas difficiles.

## Vérifier et distribuer

`blender --background --factory-startup --python-exit-code 1 --python tests_blender.py`

Les tests couvrent profondeur, panorama, trous révélés, reprojection, retour
arrière, géométrie ajoutée, plafond API, contrat HTTP et absence de clé dans le
blend. Les images et rapports sont dans `test-output/`.

`python package.py` produit un ZIP avec une liste explicite de fichiers autorisés.
Ni photo, ni modèle, ni environnement Python, ni clé ne sont inclus dans le ZIP.

## Références et dépendances

- [MoGe](https://github.com/microsoft/MoGe) : code MIT, composants DINOv2 Apache 2.0.
  Le checkout local est conservé dans `vendor/MoGe` avec sa licence.
- [Texture Diffusion](https://github.com/Shaamallow/texture-diffusion),
  [Text2Room](https://github.com/lukasHoel/text2room) et
  [DreamScene360](https://github.com/ShijieZhou-UCLA/DreamScene360) : références
  d'architecture ; aucun de leur code n'a été copié dans l'add-on.
- [API images OpenAI](https://developers.openai.com/api/reference/resources/images).

Code propre de l'add-on : GPL-3.0-or-later. Les modèles et dépendances conservent
leurs licences respectives. Les images de l'utilisateur restent hors distribution.
