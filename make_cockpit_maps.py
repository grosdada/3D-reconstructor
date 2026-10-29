"""Deterministic, editable instrument graphics; no generative image editing."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import math, random

OUT=Path(__file__).resolve().parent/'output/cockpit-photo-modulaire-v1/maps'
OUT.mkdir(parents=True,exist_ok=True)
font_path=Path('C:/Windows/Fonts/consola.ttf')
def font(n): return ImageFont.truetype(str(font_path),n)
for k in range(6):
    rng=random.Random(310+k)
    im=Image.new('RGB',(512,384),(3,15,5)); d=ImageDraw.Draw(im)
    green=(93,195,65); muted=(29,65,25); bright=(143,223,105)
    for x in range(24,490,32): d.line((x,40,x,354),fill=muted)
    for y in range(42,358,24): d.line((24,y,488,y),fill=muted)
    d.text((26,14),['NAVIGATION / VECTOR','LIFE SUPPORT / O2','POWER DISTRIBUTION','ATTITUDE / ALIGN','SYSTEMS TELEMETRY','SURVEY / RADAR'][k],font=font(15),fill=bright)
    if k%3==0:
        for r in [36,72,108,140]: d.ellipse((256-r,205-r,256+r,205+r),outline=green,width=2)
        d.line((256,48,256,348),fill=green,width=1); d.line((100,205,412,205),fill=green)
        for j in range(11):
            x=rng.randint(150,360); y=rng.randint(100,300); d.rectangle((x,y,x+3,y+3),fill=bright)
        d.line((256,205,350,110),fill=bright,width=2)
    elif k%3==1:
        for j in range(7):
            y=60+j*40
            d.text((30,y),f'{j+1:02d}  '+['CABIN','RESERVE','COOLANT','FILTER','PRESS','THERMAL','FUEL'][j],font=font(14),fill=green)
            d.rectangle((165,y,465,y+13),outline=green)
            d.rectangle((167,y+2,167+rng.randint(160,270),y+11),fill=green)
            d.text((410,y+17),f'{rng.randint(85,99)}.2',font=font(12),fill=bright)
    else:
        for j in range(5):
            y=78+j*53
            points=[(26+i,y+math.sin(i*.05+j)*rng.uniform(3,16)) for i in range(455)]
            d.line(points,fill=green,width=2)
            d.text((30,y+15),f'BUS {j+1} / STABLE',font=font(11),fill=bright)
    d.text((26,363),'ONLINE   06:42:17     AUTO / MONITOR',font=font(12),fill=green)
    for y in range(0,384,3): d.line((0,y,511,y),fill=(5,19,7),width=1)
    im.save(OUT/f'crt-{k+1:02d}.png')

for k in range(4):
    rng=random.Random(92+k); im=Image.new('RGB',(768,512),(170,170,158)); d=ImageDraw.Draw(im)
    d.rectangle((8,8,759,503),outline=(98,100,96),width=3)
    for col in range(5):
        x=25+col*148
        d.text((x,22),['SYSTEM','POWER','AIRLOCK','CONTROL','AUX'][col],font=font(15),fill=(53,58,55))
        for row in range(9):
            y=61+row*47
            d.text((x,y-4),f'{k+1}{col+1}-{row+1:02d}',font=font(11),fill=(59,62,58))
            for j in range(3):
                xx=x+44+j*24; color=rng.choice([(54,61,55),(115,45,32),(187,180,153),(90,91,82)])
                d.rectangle((xx,y,xx+13,y+11),fill=color,outline=(70,72,65),width=1)
                d.line((xx+2,y+2,xx+11,y+2),fill=(201,203,188),width=1)
    im.save(OUT/f'panel-{k+1:02d}.png')

im=Image.new('RGB',(1024,768),(170,176,169)); d=ImageDraw.Draw(im)
d.rectangle((20,20,1003,747),outline=(115,123,116),width=3)
for x in range(65,1000,65): d.line((x,40,x,730),fill=(153,159,153))
for y in range(65,740,50): d.line((40,y,985,y),fill=(153,159,153))
for i in range(7):
    x=85+i*125
    d.rectangle((x,170,x+80,590),outline=(105,117,107),width=2)
    d.line((x+40,100,x+40,660),fill=(110,123,113),width=2)
    for j in range(4): d.rectangle((x+12,210+j*75,x+68,246+j*75),outline=(96,112,102),width=2)
d.text((60,45),'FLIGHT SYSTEMS / OPERATIONS TABLE',font=font(24),fill=(95,109,100))
d.text((60,690),'VEHICLE CONFIGURATION  /  REV 07',font=font(17),fill=(95,109,100))
im.save(OUT/'table-schematic.png')
print('12 instrument maps saved',OUT)
