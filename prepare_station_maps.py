import json,shutil
from pathlib import Path
from PIL import Image
import numpy as np,cv2
R=Path(__file__).parent;O=R/'output/station-sas-v1';G=O/'projections';GEN=Path(r'C:\Users\pc\.codex\generated_images\01a17406-ed7d-7373-a427-fec1090b0a33')
sources=['exec-26a3de23-7621-49a1-b603-260be84850c1.png','exec-ed088ded-bfbb-41fc-969c-ae9339f1dbd3.png']
groups=[['avant','droite','arriere','gauche'],['plafond','sol','couloir','retour']];report=[]
for gi,(file,names) in enumerate(zip(sources,groups)):
    shutil.copy2(GEN/file,G/('gpt-atlas-%d.png'%gi));atlas=Image.open(GEN/file).convert('RGB');w,h=atlas.size
    for i,name in enumerate(names):
        tile=atlas.crop((i%2*w//2,i//2*h//2,(i%2+1)*w//2,(i//2+1)*h//2)).resize((1024,1024),Image.Resampling.LANCZOS);tile.save(G/(name+'-albedo.png'))
        base=np.array(Image.open(G/(name+'-basecolor.png')).convert('RGB'));eligible=np.array(Image.open(G/(name+'-eligible.png')).convert('L'))
        gray=cv2.cvtColor(cv2.GaussianBlur(base,(9,9),2),cv2.COLOR_RGB2GRAY);edges=cv2.Canny(gray,25,65);edges=cv2.dilate(edges,np.ones((9,9),np.uint8))
        mask=cv2.erode(eligible,np.ones((5,5),np.uint8));mask[edges>0]=0;mask=cv2.GaussianBlur(mask,(5,5),.8)
        Image.fromarray(mask).save(G/(name+'-protection.png'));report.append({'view':name,'authorized_fraction':float((mask>128).mean()),'source':file,'tile':i})
(G/'map-preparation.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(report)
