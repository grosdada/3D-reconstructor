from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json
R=Path(__file__).parent;O=R/'output/station-sas-v2.1'
font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',23);title=ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf',29)
im=Image.new('RGB',(1600,680),'#151a1c');d=ImageDraw.Draw(im)
d.text((20,14),'V2.1 · raccord corrige et plaques antiderapantes',font=title,fill='#f4eee1')
for i,(folder,label) in enumerate(((R/'output/station-sas-v2','Avant'),(O,'Joint corrige'))):
    pic=Image.open(folder/'CAM_01.png').convert('RGB').crop((0,750,310,1080)).resize((390,415),Image.Resampling.LANCZOS)
    im.paste(pic,(15+i*405,150));d.text((20+i*405,100),label,font=title,fill='#f4eee1')
pic=Image.open(O/'detail-sol.png').convert('RGB');pic.thumbnail((755,580),Image.Resampling.LANCZOS);im.paste(pic,(830,100));d.text((835,64),'Relief de normale · sans polygones en plus',font=font,fill='#deded6')
d.text((20,617),'Vraie geometrie conservee · retouche limitee au masque · patine legere',font=font,fill='#b9bcb5');im.save(O/'details-corrections.jpg',quality=95)
if (O/'renders.json').exists():
    jobs=json.loads((O/'renders.json').read_text(encoding='utf8'));W=1920;cw=616;ch=430;gap=18;top=106
    montage=Image.new('RGB',(W,top+3*(ch+gap)+18),'#151a1c');d=ImageDraw.Draw(montage)
    d.text((20,18),'STATION / V2.1 — RACCORD, PLAQUES ET ATMOSPHERE',font=title,fill='#f4eee1')
    for i,job in enumerate(jobs):
        x=18+(i%3)*(cw+gap);y=top+(i//3)*(ch+gap);pic=Image.open(O/job['file']).convert('RGB');pic.thumbnail((cw-12,ch-48),Image.Resampling.LANCZOS);montage.paste(pic,(x+(cw-pic.width)//2,y+6+(ch-48-pic.height)//2));d.text((x+12,y+ch-34),job['camera'].replace(' · ',' — '),font=font,fill='#e5e5da')
    montage.save(O/'montage-9-cameras-v2.1.jpg',quality=95)
print('V21_MONTAGE_DONE')
