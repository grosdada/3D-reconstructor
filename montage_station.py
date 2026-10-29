import json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).parent;O=R/'output/station-sas-v1';jobs=json.loads((O/'renders.json').read_text(encoding='utf8'))
W=1920;cw=616;ch=430;gap=18;top=106
im=Image.new('RGB',(W,top+3*(ch+gap)+18),'#151a1c');d=ImageDraw.Draw(im);title=ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf',34);font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',23)
d.text((20,18),'STATION / SAS CIRCULAIRES — V1',font=title,fill='#f4eee1');d.text((22,65),'Geometrie modulaire · assets KitBash · albedos GPT multivues · eclairage physique',font=font,fill='#b5b8b2')
for i,job in enumerate(jobs):
    x=18+(i%3)*(cw+gap);y=top+(i//3)*(ch+gap);d.rounded_rectangle((x,y,x+cw,y+ch),6,fill='#283033');pic=Image.open(O/job['file']).convert('RGB');pic.thumbnail((cw-12,ch-48),Image.Resampling.LANCZOS);im.paste(pic,(x+(cw-pic.width)//2,y+6+(ch-48-pic.height)//2));d.text((x+12,y+ch-34),job['camera'].replace(' · ',' — '),font=font,fill='#e5e5da')
im.save(O/'montage-9-cameras.jpg',quality=94)
pan=Image.open(O/'CAM_08.png');w,h=pan.size;crop_h=w//3;pan.crop((0,(h-crop_h)//2,w,(h+crop_h)//2)).save(O/'panorama-bande-360.png')
print('STATION_MONTAGE_DONE',O/'montage-9-cameras.jpg')
