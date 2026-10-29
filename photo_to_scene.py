"""Photo(s) → editable Blender scene without the interface.

blender --background --factory-startup --python photo_to_scene.py -- photo.jpg [autre.jpg …] --out sortie/
    [--quality DRAFT|STANDARD|FINAL] [--depth profondeur.npy] [--fov 60] [--moge-python python.exe]
    [--views 6] [--iterations 2] [--backend LOCAL|API --endpoint URL --image-model M --vision-model M]

The API key, when needed, is read from the PANO_ATELIER_API_KEY environment variable
and kept in memory only. Prints the phase statuses and the final score /20.
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path
from concurrent.futures import Future

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import pano_atelier
from pano_atelier import photo_pipeline, providers


def main(argv):
    p=argparse.ArgumentParser(prog='photo_to_scene')
    p.add_argument('photos',nargs='+'); p.add_argument('--out',default='photo-3d')
    p.add_argument('--quality',default='STANDARD',choices=list(photo_pipeline.QUALITY)); p.add_argument('--depth',default='')
    p.add_argument('--fov',type=float,default=60.); p.add_argument('--moge-python',default='')
    p.add_argument('--views',type=int,default=6); p.add_argument('--iterations',type=int,default=2)
    p.add_argument('--backend',default='LOCAL',choices=('LOCAL','API')); p.add_argument('--max-requests',type=int,default=12)
    p.add_argument('--endpoint',default='https://api.openai.com/v1'); p.add_argument('--image-model',default='gpt-image-1'); p.add_argument('--vision-model',default='gpt-4.1-mini')
    a=p.parse_args(argv)
    if a.backend=='API':
        providers.check_endpoint(a.endpoint); providers.set_key(a.endpoint,os.environ.get('PANO_ATELIER_API_KEY',''))
    folder=Path(a.out)/(time.strftime('%Y%m%d-%H%M%S')+'-cli')
    config=dict(photos=a.photos,backend=a.backend,quality=a.quality,depth=a.depth,fov=a.fov,views=a.views,iterations=a.iterations,
        refine_albedo=True,max_requests=a.max_requests,judge=True,endpoint=a.endpoint,image_model=a.image_model,vision_model=a.vision_model,moge_python=a.moge_python)
    start=time.time(); job=photo_pipeline.run(config,folder,lambda e:print('  ',json.dumps(e,ensure_ascii=False,default=str)) if 'phase' in e and e.get('state')!='running' else None)
    value=None
    while True:
        try:
            if isinstance(value,Future):
                try: result=value.result()
                except Exception as e: value=job.throw(e); continue
                value=job.send(result)
            else: value=job.send(None)
        except StopIteration: break
        if isinstance(value,str): print(f'[{time.time()-start:6.1f} s] {value}',flush=True)
    score=json.loads((folder/'score.json').read_text(encoding='utf-8'))
    print(f"NOTE {score['total']:.2f}/20 · {folder}")
    return 0


if __name__=='__main__':
    argv=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:]
    sys.exit(main(argv))
