import json,shutil,importlib.util
from pathlib import Path
import numpy as np
from PIL import Image
R=Path(__file__).parent;O=R/'output/station-sas-v1/reference'
g=Path(r'C:\Users\pc\.codex\generated_images\01a17406-ed7d-7373-a427-fec1090b0a33\exec-5dcbb7b5-3e66-4df5-a85f-a5e7aa8e1f7a.png')
shutil.copy2(g,O/'seam-gpt-proposal.png')
spec=importlib.util.spec_from_file_location('seam',R/'pano_atelier/panorama_seam.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
a=np.array(Image.open(O/'original.png').convert('RGB'));rolled,mask,shift=m.prepare(a,.44,.035)
b=np.array(Image.open(g).convert('RGB').resize((a.shape[1],a.shape[0]),Image.Resampling.LANCZOS))
c=m.reintegrate(a,b,mask,shift);Image.fromarray(c).save(O/'panorama-stitched.png')
allowed=np.roll(mask,-shift,axis=1)>0;assert np.array_equal(c[~allowed],a[~allowed])
report={'unchanged_outside_mask':True,'original_seam_MAE':float(np.abs(a[:,0].astype(float)-a[:,-1]).mean()),'repaired_seam_MAE':float(np.abs(c[:,0].astype(float)-c[:,-1]).mean()),'generator':'GPT Image built-in','proposal':g.name,'mask':'seam-mask.png','roll_pixels':shift,'note':'Visual repair of duplicated hatch. Error metric measures boundary color continuity only, not 3D validity.'}
(O/'seam-validation.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(report)
