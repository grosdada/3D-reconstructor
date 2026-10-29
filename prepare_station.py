import json,shutil,importlib.util
from pathlib import Path
import numpy as np
from PIL import Image
R=Path(__file__).parent;O=R/'output/station-sas-v1';O.mkdir(parents=True,exist_ok=True)
(O/'reference').mkdir(exist_ok=True);(O/'textures').mkdir(exist_ok=True)
src=Path(r'C:\Users\pc\AppData\Local\Temp\codex-clipboard-1c891685-5e69-450d-aae4-67857c53dd51.png')
shutil.copy2(src,O/'reference/original.png')
spec=importlib.util.spec_from_file_location('seam',R/'pano_atelier/panorama_seam.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
a=np.array(Image.open(src).convert('RGB'));rolled,mask,shift=m.prepare(a,.44,.035)
Image.fromarray(rolled).save(O/'reference/seam-centered.png');Image.fromarray(np.uint8(mask*255)).save(O/'reference/seam-mask.png')
(O/'reference/seam-job.json').write_text(json.dumps({'source_size':list(a.shape[1::-1]),'shift':shift,'band_fraction':.44,'feather_fraction':.035,'interpretation':'Panorama horizontal 360 presume, bande verticale incomplete 3:1; pas une sphere 2:1. Le sas aux deux extremites doit devenir un passage arriere unique.'},indent=2),encoding='utf8')
print(O)
