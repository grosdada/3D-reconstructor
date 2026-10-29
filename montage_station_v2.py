import json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).parent;O=R/'output/station-sas-v2';jobs=json.loads((O/'renders.json').read_text(encoding='utf8'))
W=1920;cw=616;ch=430;gap=18;top=106
im=Image.new('RGB',(W,top+3*(ch+gap)+18),'#151a1c');d=ImageDraw.Draw(im);title=ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf',34);font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',23)
d.text((20,18),'STATION / SAS CIRCULAIRES — V2',font=title,fill='#f4eee1');d.text((22,65),'Cablage en volume · assemblages varies · patine locale · eclairage par cabine',font=font,fill='#b5b8b2')
for i,job in enumerate(jobs):
    x=18+(i%3)*(cw+gap);y=top+(i//3)*(ch+gap);d.rounded_rectangle((x,y,x+cw,y+ch),6,fill='#283033');pic=Image.open(O/job['file']).convert('RGB');pic.thumbnail((cw-12,ch-48),Image.Resampling.LANCZOS);im.paste(pic,(x+(cw-pic.width)//2,y+6+(ch-48-pic.height)//2));d.text((x+12,y+ch-34),job['camera'].replace(' · ',' — '),font=font,fill='#e5e5da')
im.save(O/'montage-9-cameras-v2.jpg',quality=95)
pair=Image.new('RGB',(1920,704),'#151a1c');d=ImageDraw.Draw(pair)
for i,folder in enumerate((R/'output/station-sas-v1',O)):
    pic=Image.open(folder/'CAM_01.png').convert('RGB');pic.thumbnail((948,632),Image.Resampling.LANCZOS);pair.paste(pic,(i*960+6,58));d.text((i*960+18,12),'V1' if i==0 else 'V2 · cables, patine et lumiere',font=title,fill='#f4eee1')
pair.save(O/'comparaison-v1-v2.jpg',quality=95)
print('MONTAGE_V2_DONE')
