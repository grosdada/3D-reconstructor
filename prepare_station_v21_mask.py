"""An explicit authorization mask; generated proposal is composited in Blender."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFilter
import json
O=Path(__file__).parent/'output/station-sas-v2.1/textures'
im=Image.new('L',(1254,1254),0);d=ImageDraw.Draw(im)
polygons=[[(0,832),(255,703),(255,790),(0,921)],[(999,703),(1253,832),(1253,921),(999,790)]]
for p in polygons:d.polygon(p,fill=255)
im=im.filter(ImageFilter.GaussianBlur(5));im.save(O/'masque-faux-joints.png')
(O/'repair-manifest.json').write_text(json.dumps({'source':'../../station-sas-v2/textures/avant-albedo-v2.png','proposal':'avant-sans-faux-joints-proposition.png','mask':'masque-faux-joints.png','camera':'PROJ_avant','polygons_top_left_pixels':polygons,'feather_px':5,'scope':'Only the two false lower side-wall seams; source retained outside mask. Original depth and coverage gates retained.'},indent=2),encoding='utf8')
