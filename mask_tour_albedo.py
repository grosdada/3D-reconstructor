"""Rasterize feathered semantic guards; generated images themselves remain untouched."""
from pathlib import Path
import numpy as np,cv2
from PIL import Image
out=Path(__file__).parent/'output/tour-belvedere-v2'
for name in ['avant','droite','arriere','gauche','dessus','detail-facade']:
    im=np.asarray(Image.open(out/(name+'-classes.png')).convert('RGB')).astype(np.int16)
    result=np.zeros(im.shape[:2],np.float32)
    for rgb in [(255,0,0),(0,255,0),(0,0,255),(255,255,0),(255,0,255),(0,255,255),(188,0,0),(0,188,0)]:
        mask=(np.max(np.abs(im-np.array(rgb)),axis=2)<16).astype('uint8')
        # Thin modelled seams are already separate geometry; avoid pristine halos along them.
        mask=cv2.morphologyEx(mask,cv2.MORPH_CLOSE,np.ones((5,5),np.uint8))
        d=cv2.distanceTransform(mask,cv2.DIST_L2,5)
        safe=np.clip((d-1.5)/3.5,0,1)
        result=np.maximum(result,safe)
    Image.fromarray((result*255).astype('uint8')).save(out/(name+'-protection.png'))
print('TOUR_MASKS_DONE')
