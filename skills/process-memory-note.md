# Processus cockpit photo vers décor Blender modulaire

Demande explicite de l'utilisateur le 25 octobre 2026 : mémoriser tout le processus et en tirer un skill set en vue d'un add-on.

Projet : C:/Users/pc/Documents/Codex/Codex-Blender/pano_atelier.
Processus maintenu dans PROCESS-PHOTO-MODULAIRE.md ; skill source dans skills/blender-photo-modular/SKILL.md ; construction reproductible build_photo_cockpit.py et make_cockpit_maps.py ; sortie output/cockpit-photo-modulaire-v1/cockpit-photo-modulaire.blend. Lire scene-report.json et validation.json avant de reprendre l'état ou les chiffres.

Ordre de travail confirmé : photo fournie -> reconstruire le visible avec vrais volumes modulaires, détails structurants, matériaux et lumière proches de la référence -> inventer le hors champ après. Le camera mapping est facultatif et ne remplace pas la modélisation. Les artefacts d'image générative sont interprétés comme des détails fonctionnels plausibles, jamais reproduits littéralement. Fenêtres transparentes en retrait avec cadres en relief ; fond spatial sur un vrai cyclorama demi-circulaire ; petites maps d'écrans avec émission. Chaque assemblage doit être déplaçable, avec pivots locaux et textures attachées à l'objet.

Le maillage de profondeur dense et le template hexagonal générique des essais précédents ne satisfaisaient pas cette intention. La construction actuelle emploie des repères et plans définis manuellement ; ne pas la présenter comme une reconstruction automatique universelle. Prochaine épreuve : une seconde photo différente. L'intégration API doit rester distincte des générations GPT Image réalisées via cette conversation.
