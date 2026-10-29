"""Multi-photo alignment of the external worker (needs OpenCV, not MoGe):
python tests_photo_worker.py   (in an environment with opencv-python and numpy)
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import photo_fixtures as F


class WorkerAlignmentTests(unittest.TestCase):
    def test_second_photo_pose_from_sift_and_pnp(self):
        try: import cv2  # noqa: F401
        except ImportError: self.skipTest('OpenCV absent')
        from PIL import Image
        tmp=Path(tempfile.mkdtemp())
        m1=F.camera(); m2=F.camera(yaw=14.,pitch=-3.); m2[:3,3]+=(.35,.2,0)
        paths=[];depths=[]
        for i,m in enumerate((m1,m2)):
            img,depth,_,_=F.render(480,360,matrix=m,textured=True)
            Image.fromarray((img*255).astype(np.uint8)).save(tmp/f'p{i}.png'); np.save(tmp/f'd{i}.npy',depth)
            paths.append(str(tmp/f'p{i}.png')); depths.append(str(tmp/f'd{i}.npy'))
        subprocess.run([sys.executable,str(ROOT/'pano_atelier'/'photo_worker.py'),'--images',*paths,'--output',str(tmp/'out'),
                        '--depths',*depths,'--fovs','70','70'],check=True,capture_output=True)
        result=json.loads((tmp/'out'/'results.json').read_text())
        self.assertIn('1',result['poses'])
        rel=np.array(result['poses']['1']['matrix'])
        truth=np.linalg.inv(m1)@m2  # photo 2 camera in the photo 1 camera frame
        self.assertLess(np.linalg.norm(rel[:3,3]-truth[:3,3]),.05)
        angle=np.degrees(np.arccos(np.clip((np.trace(rel[:3,:3].T@truth[:3,:3])-1)/2,-1,1)))
        self.assertLess(angle,1.)


if __name__=='__main__':
    unittest.main()
