"""Runs in the user's isolated ML Python, never inside Blender's Python."""
import argparse
import os
from pathlib import Path
import sys

parser=argparse.ArgumentParser()
parser.add_argument('--image',required=True)
parser.add_argument('--output',required=True)
parser.add_argument('--fov',type=float,default=70)
parser.add_argument('--panorama',action='store_true')
args=parser.parse_args()
os.environ.setdefault('HF_HOME',str(Path(sys.prefix)/'model-cache'))
os.environ.setdefault('OPENCV_IO_ENABLE_OPENEXR','1')

if args.panorama:
    import subprocess
    subprocess.run([sys.executable,'-m','moge.scripts.infer_panorama','--input',args.image,
        '--output',args.output,'--maps','--resize','1024'],check=True)
else:
    import json
    import numpy as np
    import torch
    from PIL import Image
    from moge.model.v2 import MoGeModel
    out=Path(args.output)/Path(args.image).stem; out.mkdir(parents=True,exist_ok=True)
    image=Image.open(args.image).convert('RGB')
    image.thumbnail((1024,1024))
    array=np.asarray(image).copy()
    device='cuda' if torch.cuda.is_available() else 'cpu'
    model=MoGeModel.from_pretrained('Ruicheng/moge-2-vitb-normal').to(device).eval()
    tensor=torch.tensor(array/255,dtype=torch.float32,device=device).permute(2,0,1)
    with torch.inference_mode(): result=model.infer(tensor,fov_x=args.fov if args.fov>0 else None,resolution_level=7)
    depth=result['depth'].cpu().numpy().astype(np.float32)
    valid=result['mask'].cpu().numpy()
    depth[~valid]=0
    np.save(out/'depth.npy',depth)
    image.save(out/'source.png')
    intrinsics=result['intrinsics'].cpu().numpy()
    fov=float(np.degrees(2*np.arctan(.5/intrinsics[0,0])))
    (out/'metadata.json').write_text(json.dumps({'model':'Ruicheng/moge-2-vitb-normal','fov_degrees':fov,
        'device':device,'depth':'axial','scale':'estimated metric; not measured','valid_fraction':float(valid.mean())},indent=2))
    print('DEPTH_READY',out/'depth.npy')
