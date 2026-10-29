from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).parent;O=R/'output/ville-brutaliste-v2';V1=R/'output/ville-brutaliste-v1'
items=[(V1/'reference-A1.png','REFERENCE A1'),(V1/'CAM_01.png','V1 — AVANT'),(O/'CAM_01.png','V2 — GEOMETRIE, PATINE, LUMIERE'),(O/'CAM_04.png','V2 — FACADE RAPPROCHEE'),(O/'CAM_02.png','V2 — CONTRE-ANGLE'),(O/'CAM_08.png','V2 — VOITURES DE LA BIBLIOTHEQUE')]
W,H=960,630;canvas=Image.new('RGB',(W*3,H*2),(22,26,24));d=ImageDraw.Draw(canvas);font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',23)
for i,(path,label) in enumerate(items):
 im=Image.open(path).convert('RGB');im.thumbnail((944,572));x=(i%3)*W+(W-im.width)//2;y=(i//3)*H+48+(572-im.height)//2;canvas.paste(im,(x,y));d.text(((i%3)*W+16,(i//3)*H+12),label,font=font,fill=(219,227,217))
canvas.save(O/'montage-ville-V2.jpg',quality=94)
print(O/'montage-ville-V2.jpg')
