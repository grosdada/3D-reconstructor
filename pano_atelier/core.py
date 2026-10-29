"""Geometry and mask utilities. Coordinates: Blender camera, looking down -Z.

Image arrays use top-left origin; Blender pixels are converted at the boundary.
Depth is axial for perspective, radial for an equirectangular panorama.
"""
import math
import numpy as np


def grid_mesh(depth, fov=70.0, panorama=False, edge_limit=0.15):
    depth = np.asarray(depth, dtype=np.float32)
    h, w = depth.shape
    if h < 3 or w < 3:
        raise ValueError('La profondeur doit mesurer au moins 3 x 3 pixels.')
    u, v = np.meshgrid(np.linspace(0, 1, w), np.linspace(0, 1, h))
    if panorama:
        lon, lat = (u - .5) * 2 * np.pi, (.5 - v) * np.pi
        rays = np.stack((np.sin(lon)*np.cos(lat), np.sin(lat), -np.cos(lon)*np.cos(lat)), -1)
    else:
        t = math.tan(math.radians(fov)/2)
        rays = np.stack(((u*2-1)*t, (1-v*2)*t*h/w, -np.ones_like(u)), -1)
    valid = np.isfinite(depth) & (depth > 0)
    points = rays * np.where(valid, depth, 0)[..., None]
    faces = []
    for y in range(h-1):
        for x in range(w-1):
            ids = [y*w+x, y*w+x+1, (y+1)*w+x+1, (y+1)*w+x]
            for tri in ((ids[0],ids[2],ids[1]), (ids[0],ids[3],ids[2])):
                d = depth.ravel()[list(tri)]
                if np.all(np.isfinite(d)) and min(d) > 0 and (max(d)-min(d))/min(d) <= edge_limit:
                    faces.append(tri)
    return points.reshape(-1,3), faces, np.stack((u, 1-v), -1).reshape(-1,2)


def camera_rays(width, height, fov):
    t = math.tan(math.radians(fov)/2)
    x, y = np.meshgrid((np.arange(width)+.5)/width, (np.arange(height)+.5)/height)
    rays = np.stack(((2*x-1)*t, (1-2*y)*t*height/width, -np.ones_like(x)), -1)
    return rays / np.linalg.norm(rays, axis=-1, keepdims=True)


def expand(mask, radius=2):
    result = np.asarray(mask, dtype=bool).copy()
    for _ in range(radius):
        p = np.pad(result, 1)
        result = p[1:-1,1:-1] | p[:-2,1:-1] | p[2:,1:-1] | p[1:-1,:-2] | p[1:-1,2:]
    return result


def feather(mask, radius=2):
    mask = np.asarray(mask, dtype=bool)
    alpha = mask.astype(np.float32)
    front = mask
    for i in range(radius):
        nxt = expand(front, 1)
        alpha[nxt & ~front] = (radius-i)/(radius+1)
        front = nxt
    return alpha


def detect(rgb, depth, incidence, source_incidence, valid):
    """Conservative geometric candidates, not semantic AI diagnoses."""
    holes = ~valid
    stretch = valid & (source_incidence < .18) & (incidence > source_incidence*1.5)
    # Colour discontinuity on a locally continuous surface = candidate, not proof.
    dx = np.max(abs(rgb[:,1:,:3]-rgb[:,:-1,:3]), axis=-1)
    rel = abs(depth[:,1:]-depth[:,:-1]) / np.maximum(np.minimum(depth[:,1:],depth[:,:-1]), .001)
    seams = np.zeros(valid.shape, bool)
    seams[:,1:] = (dx > .32) & (rel < .015) & valid[:,1:] & valid[:,:-1]
    # Sky/background and genuinely missing surfaces cannot receive a texture patch.
    texture = expand(stretch | seams, 2) & valid
    return dict(holes=holes, stretch=stretch, seams=seams, texture=texture)


def boxes_mask(boxes, shape):
    """Strictly validate model output; normalized top-left coordinates only."""
    h,w = shape
    mask = np.zeros(shape, bool)
    for b in boxes[:64]:
        if b.get('kind') not in ('seam','texture'):
            continue
        xy = b.get('box', [])
        if len(xy)!=4 or not all(isinstance(n,(int,float)) and math.isfinite(n) and 0<=n<=1 for n in xy):
            continue
        x0,y0,x1,y1 = xy
        if x1<=x0 or y1<=y0:
            continue
        mask[int(y0*h):min(h,math.ceil(y1*h)),int(x0*w):min(w,math.ceil(x1*w))] = True
    return mask


def path_poses(radius=.35, panorama=False):
    offsets = [(0,0,0),(-radius,0,0),(radius,0,0),(0,0,-radius),(0,0,radius),(0,radius*.4,0),(0,-radius*.4,0)]
    # Holdout positions are deliberately absent from generation poses.
    poses = [(p,yaw,False) for p in offsets for yaw in ([0,90,180,270] if panorama else [0])]
    poses += [((radius*.45,radius*.2,-radius*.4),yaw,True) for yaw in ([45,135,225,315] if panorama else [0])]
    return poses


def boundary_error(rgb, mask):
    m = mask > .05
    values = []
    for axis in (0,1):
        a = np.diff(m.astype(np.int8), axis=axis)!=0
        d = np.mean(abs(np.diff(rgb[...,:3],axis=axis)),axis=-1)
        if np.any(a): values.append(float(np.mean(d[a])))
    return float(np.mean(values)) if values else 0.


def local_fill(rgb, mask, iterations=200):
    """Deterministic local colour diffusion for tests/small seams. NOT AI."""
    out = np.asarray(rgb,dtype=np.float32).copy()
    m = mask > .05
    if not np.any(~m): raise ValueError('Le masque couvre toute la vue.')
    out[m,:3] = np.mean(out[~m,:3],axis=0)
    for _ in range(iterations):
        p = np.pad(out,((1,1),(1,1),(0,0)),mode='edge')
        avg = (p[:-2,1:-1]+p[2:,1:-1]+p[1:-1,:-2]+p[1:-1,2:])/4
        out[m,:3] = avg[m,:3]
    return out


def align_missing_depth(predicted, reference, holes):
    """Align a new monocular estimate using already observed overlap.

    Refuse weak/inconsistent anchors; never infer scale solely from invented pixels.
    """
    predicted=np.asarray(predicted,np.float32)
    valid=np.isfinite(predicted)&(predicted>.01)
    overlap=valid & (reference>.01) & ~holes
    if int(overlap.sum())<max(64,int(reference.size*.15)):
        raise ValueError('Recouvrement insuffisant pour aligner la nouvelle géométrie.')
    ratios=reference[overlap]/predicted[overlap]
    scale=float(np.median(ratios))
    scatter=float(np.median(abs(ratios/scale-1)))
    if scatter>.2:
        raise ValueError('Profondeur générée incohérente avec les surfaces existantes.')
    result=predicted*scale
    result[~valid | ~holes]=0
    return result,{'scale':scale,'relative_mad':scatter,'anchors':int(overlap.sum())}
