from PIL import Image,ImageDraw,ImageFont
from pathlib import Path
import json
R=Path(__file__).parent;O=R/'output/ville-brutaliste-v1'
jobs=json.loads((O/'renders.json').read_text(encoding='utf8'));assert len(jobs)==5
canvas=Image.new('RGB',(2400,1030),(23,28,26));d=ImageDraw.Draw(canvas);font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',23)
items=[('reference-A1.png','Reference A1'),('CAM_01.png','Reconstruction 3D - vue A1'),('CAM_02.png','Contre-angle'),('CAM_04.png','Facade rapprochee'),('CAM_05.png','Quartier et skyline'),('CAM_06.png','Arriere interprete')]
for k,(file,title) in enumerate(items):
 im=Image.open(O/file).convert('RGB');im.thumbnail((788,460));col=k%3;row=k//3;x=col*800+(800-im.width)//2;y=row*515+43+(460-im.height)//2;canvas.paste(im,(x,y));d.text((col*800+15,row*515+9),title,font=font,fill=(224,229,217))
canvas.save(O/'montage-ville-A1.jpg',quality=95)
print(O/'montage-ville-A1.jpg')
