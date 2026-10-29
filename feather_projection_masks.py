"""Generate a scalar protection mask from rendered geometry labels (not an edit to GPT images)."""
from pathlib import Path
import numpy as np
import cv2
from PIL import Image,ImageFilter
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'output/cockpit-albedo-multivues-test'
for name in ['avant','arriere','droite','gauche','plafond','sol']:
    a=np.asarray(Image.open(OUT/(name+'-classes.png')).convert('RGB'))
    result=np.zeros(a.shape[:2],dtype=np.float32)
    for rgb in [(255,0,0),(0,255,0),(0,0,255),(255,255,0)]:
        mask=np.max(np.abs(a.astype(np.int16)-np.array(rgb)),axis=2)<24
        distance=cv2.distanceTransform(mask.astype('uint8'),cv2.DIST_L2,5)
        radius=50 if name=='plafond' else 36
        safe=np.clip((distance-radius)/14,0,1)*255
        result=np.maximum(result,safe)
    Image.fromarray(result.clip(0,255).astype('uint8')).save(OUT/(name+'-protection.png'))
print('PROTECTION_MASKS_DONE')
