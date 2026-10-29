"""Local HDRI contact sheets for lighting selection; originals stay unchanged."""
from pathlib import Path
import os
os.environ['OPENCV_IO_ENABLE_OPENEXR']='1'
import cv2,numpy as np
from PIL import Image,ImageDraw
R=Path(__file__).parent;O=R/'output/tour-belvedere-v4';O.mkdir(exist_ok=True)
A=Path(r'K:\Connector-Blender\HDR\HDRI-Haven\Pure-sky')
names=['kloofendal_38d_partly_cloudy_puresky_4k.exr','kloppenheim_02_puresky_4k.exr','kloppenheim_05_puresky_4k.exr','mpumalanga_veld_puresky_4k.exr','quarry_01_puresky_4k.exr','qwantani_puresky_4k.exr','table_mountain_1_puresky_4k.exr','table_mountain_2_puresky_4k.exr']
sheet=Image.new('RGB',(1200,700),(25,25,25));d=ImageDraw.Draw(sheet)
for i,name in enumerate(names):
    src=cv2.imread(str(A/name),cv2.IMREAD_UNCHANGED)
    if src is None:continue
    im=cv2.cvtColor(cv2.resize(src,(600,150)),cv2.COLOR_BGR2RGB)
    light=np.percentile(im[:75],65);im=np.power(np.clip(im*(.35/max(float(light),.0001)),0,1),1/2.2)
    thumb=Image.fromarray((im*255).astype('uint8'));x=(i%2)*600;y=(i//2)*175;sheet.paste(thumb,(x,y));d.text((x+8,y+153),name,fill='white')
sheet.save(O/'hdri-puresky-candidates.jpg')
print('HDRI_PREVIEWS_DONE')
