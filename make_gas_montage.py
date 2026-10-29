from PIL import Image,ImageDraw,ImageFont
from pathlib import Path
O=Path(__file__).parent/'output/gas-station-exterior-v1';tile=(800,533);pad=18;bar=42
im=Image.new('RGB',(pad+3*(800+pad),pad+2*(533+bar+pad)),(22,28,31));d=ImageDraw.Draw(im);f=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',23)
labels=['01 / Façade principale','02 / Sous l’auvent','03 / Côté technique','04 / Toiture et implantation','05 / Arrière et annexe','06 / Vue intermédiaire']
for k in range(6):
 x=pad+(k%3)*(800+pad);y=pad+(k//3)*(533+bar+pad)
 p=Image.open(O/('render-%02d.png'%(k+1))).convert('RGB');p.thumbnail(tile,Image.Resampling.LANCZOS);im.paste(p,(x,y));d.text((x+8,y+542),labels[k],font=f,fill=(215,229,232))
im.save(O/'montage-exterieur.jpg',quality=93)
