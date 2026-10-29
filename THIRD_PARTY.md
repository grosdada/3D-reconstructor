# Références et ressources tierces

## Trompe

Projet de Patch : https://github.com/patch-gg/trompe

Révision étudiée le 29 octobre 2026 : `fd81fe467b1e29659597109f14bcf4e7054afa7f`.
Le dépôt déclare Apache-2.0 ; marque et éléments d'identité Patch en sont exclus. Ce dépôt ne contient pas de copie de son code ni de ses assets. Le document de transmission cite les modules étudiés et propose des adaptations indépendantes. En cas de reprise de code, conserver les mentions requises et documenter la provenance.

## Profondeur et reconstruction

- MoGe : https://github.com/microsoft/MoGe — dépendance optionnelle à installer séparément ; `vendor/` et poids de modèles non publiés.
- Texture Diffusion : https://github.com/Shaamallow/texture-diffusion
- Text2Room : https://github.com/lukasHoel/text2room
- DreamScene360 : https://github.com/ShijieZhou-UCLA/DreamScene360

Les trois derniers sont des références historiques, non des intégrations validées de ce dépôt. Examiner leurs licences respectives avant toute réutilisation.

## Bibliothèques utilisateur

botaniq, KitBash, Elements-decor, SKetch-Fab et Trash-Kit ont servi sur le poste de production. Aucun maillage, atlas, matériau de bibliothèque ou HDRI commercial n'est distribué ici. Les scripts conservent parfois les noms et chemins d'origine : adapter aux ressources de l'utilisateur. Les peintures procédurales développées dans le code sont des implémentations indépendantes.

Les illustrations du HTML sont des aperçus de rendus des scènes de travail, pas des fichiers d'assets ni des textures réutilisables. Elles documentent les essais ; leur présence ne concède aucun droit sur les bibliothèques tierces. Les photos sources et captures d'interface de l'utilisateur ne sont pas publiées.

## API image

GPT Image est un service distant distinct de cet add-on. Référence technique consultée : https://developers.openai.com/api/docs/guides/image-generation . Les modèles, formats, prix et limites doivent être vérifiés lors de l'intégration. Les identifiants de modèles par défaut du prototype ne sont pas une recommandation de version actuelle.
