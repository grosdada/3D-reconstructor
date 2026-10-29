from PIL import Image,ImageDraw,ImageFont,ImageOps
from pathlib import Path
import json
R=Path(__file__).parent;O=R/'output/tour-belvedere-v4'
jobs=json.loads((O/'renders.json').read_text(encoding='utf8'))
assert len(jobs)==15
font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',23)
small=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',20)
title=ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf',34)
W=1920;gap=18;cw=616;ch=420;top=110
im=Image.new('RGB',(W,top+5*(ch+gap)+18),'#13191b');d=ImageDraw.Draw(im)
d.text((22,18),'TOUR BELVÉDÈRE  /  V4',font=title,fill='#edf2ed')
d.text((24,66),'15 caméras · herbe botaniq instanciée · ciel HDRI Pure-sky · rendus Blender',font=small,fill='#aebbb7')
for i,(cam,name,w,h) in enumerate(jobs):
    x=18+(i%3)*(cw+gap);y=top+(i//3)*(ch+gap)
    d.rounded_rectangle((x,y,x+cw,y+ch),radius=6,fill='#242d30')
    pic=Image.open(O/(name+'.png')).convert('RGB');pic.thumbnail((cw-12,ch-48),Image.Resampling.LANCZOS)
    im.paste(pic,(x+(cw-pic.width)//2,y+6+(ch-48-pic.height)//2))
    d.text((x+12,y+ch-34),cam.replace(' · ','  —  '),font=font,fill='#e0e9e4')
im.save(O/'montage-15-cameras-v4.jpg',quality=94)
print(O/'montage-15-cameras-v4.jpg')
