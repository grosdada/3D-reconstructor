from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).parent;O=R/'output/ville-brutaliste-v3-vis-a-vis'
items=[('CAM_09.png','VIS-A-VIS — DEPUIS LE PARVIS'),('CAM_10.png','AVENUE — LES DEUX RIVES'),('CAM_11.png','LOGGIAS — DETAIL DU BETON'),('CAM_12.png','RUE TRANSVERSALE — COTE COUR')]
W,H=1100,665;canvas=Image.new('RGB',(W*2,H*2),(22,26,24));d=ImageDraw.Draw(canvas);font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',24)
for i,(name,label) in enumerate(items):
 im=Image.open(O/name).convert('RGB');im.thumbnail((1080,600));x=(i%2)*W+(W-im.width)//2;y=(i//2)*H+50+(600-im.height)//2;canvas.paste(im,(x,y));d.text(((i%2)*W+16,(i//2)*H+14),label,font=font,fill=(219,227,217))
canvas.save(O/'montage-vis-a-vis.jpg',quality=94)
print(O/'montage-vis-a-vis.jpg')
