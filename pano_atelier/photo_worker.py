"""Depth for every photo (MoGe) and poses of extra photos (OpenCV SIFT + PnP).

Runs in the user's isolated ML Python, never inside Blender's Python.
Writes <output>/results.json; camera matrices use Blender's convention
(X right, Y up, looking down -Z) and are expressed in the first photo's camera frame.
"""
import argparse
import json
import math
import os
import sys
from pathlib import Path
import numpy as np


def moge(image_path, output, fov):
    import torch
    from PIL import Image
    from moge.model.v2 import MoGeModel
    image = Image.open(image_path).convert('RGB'); image.thumbnail((1024, 1024))
    array = np.asarray(image).copy()
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    global MODEL
    if MODEL is None: MODEL = MoGeModel.from_pretrained('Ruicheng/moge-2-vitb-normal').to(device).eval()
    tensor = torch.tensor(array/255, dtype=torch.float32, device=device).permute(2, 0, 1)
    with torch.inference_mode(): result = MODEL.infer(tensor, fov_x=fov if fov > 0 else None, resolution_level=7)
    depth = result['depth'].cpu().numpy().astype(np.float32)
    valid = result['mask'].cpu().numpy()
    depth[~valid] = 0
    intrinsics = result['intrinsics'].cpu().numpy()
    fov_x = float(np.degrees(2*np.arctan(.5/intrinsics[0, 0])))
    return depth, fov_x, array


MODEL = None


def gray(array):
    a = np.asarray(array, np.float32)
    if a.ndim == 3: a = a[..., :3] @ np.array((.299, .587, .114), np.float32)
    if a.max() <= 1.001: a = a*255
    return np.clip(a, 0, 255).astype(np.uint8)


def focal(width, fov):
    return width/2/math.tan(math.radians(fov)/2)


def align(ref_gray, ref_depth, ref_fov, img_gray, img_fov, max_features=6000):
    """Pose of a second photo in the reference camera frame, from 2D-3D matches."""
    import cv2
    h, w = ref_depth.shape
    if ref_gray.shape != ref_depth.shape: ref_gray = cv2.resize(ref_gray, (w, h), interpolation=cv2.INTER_AREA)
    sift = cv2.SIFT_create(max_features)
    k1, d1 = sift.detectAndCompute(ref_gray, None); k2, d2 = sift.detectAndCompute(img_gray, None)
    if d1 is None or d2 is None: return None
    pairs = cv2.BFMatcher().knnMatch(d1, d2, k=2)
    good = [p[0] for p in pairs if len(p) == 2 and p[0].distance < .75*p[1].distance]
    f1 = focal(w, ref_fov); obj = []; pts = []
    for m in good:
        u, v = k1[m.queryIdx].pt; z = float(ref_depth[min(h-1, int(round(v))), min(w-1, int(round(u)))])
        if z <= 0: continue
        obj.append(((u-(w-1)/2)/f1*z, (v-(h-1)/2)/f1*z, z)); pts.append(k2[m.trainIdx].pt)
    if len(obj) < 12: return None
    H2, W2 = img_gray.shape[:2]; f2 = focal(W2, img_fov)
    K = np.array(((f2, 0, (W2-1)/2), (0, f2, (H2-1)/2), (0, 0, 1)), np.float64)
    ok, rvec, tvec, inliers = cv2.solvePnPRansac(np.array(obj, np.float64), np.array(pts, np.float64), K, None,
        reprojectionError=4., iterationsCount=3000, confidence=.999, flags=cv2.SOLVEPNP_EPNP)
    if not ok or inliers is None or len(inliers) < 10: return None
    idx = inliers.ravel()
    rvec, tvec = cv2.solvePnPRefineLM(np.array(obj, np.float64)[idx], np.array(pts, np.float64)[idx], K, None, rvec, tvec)
    R, _ = cv2.Rodrigues(rvec)
    F = np.diag((1., -1., -1.))  # OpenCV (y down, +z forward) <-> Blender camera axes
    M = np.eye(4); M[:3, :3] = F@R.T@F; M[:3, 3] = F@(-R.T@tvec.ravel())
    return {'matrix': M.tolist(), 'inliers': int(len(idx)), 'matches': len(obj)}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--images', nargs='+', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--fov', type=float, default=0)
    parser.add_argument('--depths', nargs='*', help='Precomputed axial depth .npy per image (skips MoGe)')
    parser.add_argument('--fovs', nargs='*', type=float)
    args = parser.parse_args(argv)
    os.environ.setdefault('HF_HOME', str(Path(sys.prefix)/'model-cache'))
    out = Path(args.output); out.mkdir(parents=True, exist_ok=True)
    photos = []; arrays = []
    for i, path in enumerate(args.images):
        if args.depths:
            from PIL import Image
            depth = np.load(args.depths[i]).astype(np.float32); fov = args.fovs[i]
            array = np.asarray(Image.open(path).convert('RGB').resize(depth.shape[::-1]))
        else:
            depth, fov, array = moge(path, out, args.fov)
        np.save(out/f'depth-{i:02d}.npy', depth)
        photos.append({'image': str(path), 'depth': str(out/f'depth-{i:02d}.npy'), 'fov': fov,
                       'width': int(depth.shape[1]), 'height': int(depth.shape[0]), 'valid_fraction': float((depth > 0).mean())})
        arrays.append(array)
    poses = {}
    for i in range(1, len(photos)):
        try:
            pose = align(gray(arrays[0]), np.load(photos[0]['depth']), photos[0]['fov'], gray(arrays[i]), photos[i]['fov'])
        except ImportError:
            pose = None; photos[i]['note'] = 'OpenCV absent : photo utilisée comme référence de matières seulement.'
        if pose: poses[str(i)] = pose
    (out/'results.json').write_text(json.dumps({'photos': photos, 'poses': poses,
        'model': None if args.depths else 'Ruicheng/moge-2-vitb-normal', 'scale': 'estimated metric; not measured'}, indent=2))
    print('PHOTOS_READY', out/'results.json')


if __name__ == '__main__':
    main()
