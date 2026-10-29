from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json,zipfile,ast
R=Path(__file__).parent;O=R/'output/ville-brutaliste-v4-mobilier'
items=[('CAM_09.png','V4 — PARVIS ET VIS-A-VIS'),('CAM_10.png','AVENUE — FONDS DANS LA BRUME'),('CAM_14.png','MOBILIER — VUE AU NIVEAU DE LA RUE'),('CAM_13.png','RETOUR VERS A1 — AUTRE RIVE')]
W,H=1100,665;canvas=Image.new('RGB',(W*2,H*2),(22,26,24));d=ImageDraw.Draw(canvas);font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',24)
for i,(name,label) in enumerate(items):
 im=Image.open(O/name).convert('RGB');im.thumbnail((1080,600));x=(i%2)*W+(W-im.width)//2;y=(i//2)*H+50+(600-im.height)//2;canvas.paste(im,(x,y));d.text(((i%2)*W+16,(i//2)*H+14),label,font=font,fill=(219,227,217))
canvas.save(O/'montage-mobilier-brume.jpg',quality=94)
with zipfile.ZipFile(R/'dist/pano_atelier-0.5.3.zip') as z:
 names=z.namelist();assert len(names)==25
 for name in names:
  assert name.endswith(('.py','.toml')) and '/' not in name
  if name.endswith('.py'):ast.parse(z.read(name).decode('utf8'))
 assert 'city_dressing.py' in names
(O/'package-validation.json').write_text(json.dumps({'version':'0.5.3','files':names,'python_syntax_valid':True,'code_only_no_assets':True},indent=2),encoding='utf8')
print(O/'montage-mobilier-brume.jpg')
