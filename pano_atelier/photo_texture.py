"""Camera planning, texel projection and stitching. Pure numpy, no bpy.

Views are dicts: matrix (4x4 world-from-camera, Blender convention), fov
(horizontal, degrees), image (H,W,3 linear), depth (H,W axial, 0 = empty),
priority (photos > generated views) and optional mask (H,W, 1 = usable).
"""
import math
import numpy as np
from . import photo_util as U


def project(points,matrix,fov,w,h):
    """World points → pixel coordinates (top-left, pixel centres at i+.5) and axial depth."""
    m=np.asarray(matrix,np.float64); p=(np.asarray(points,np.float64)-m[:3,3])@m[:3,:3]
    z=-p[:,2]; t=math.tan(math.radians(fov)/2); zz=np.maximum(z,1e-9)
    return (p[:,0]/zz/t*.5+.5)*w,(.5-p[:,1]/zz/(t*h/w)*.5)*h,z


def bilinear(image,x,y):
    a=np.asarray(image,np.float32); h,w=a.shape[:2]
    x=np.clip(np.asarray(x)-.5,0,w-1); y=np.clip(np.asarray(y)-.5,0,h-1)
    x0=np.floor(x).astype(int); y0=np.floor(y).astype(int); x1=np.minimum(x0+1,w-1); y1=np.minimum(y0+1,h-1)
    fx=x-x0; fy=y-y0
    if a.ndim==3: fx=fx[:,None]; fy=fy[:,None]
    return (a[y0,x0]*(1-fx)+a[y0,x1]*fx)*(1-fy)+(a[y1,x0]*(1-fx)+a[y1,x1]*fx)*fy


def nearest(image,x,y):
    a=np.asarray(image); h,w=a.shape[:2]
    return a[np.clip(np.asarray(y).astype(int),0,h-1),np.clip(np.asarray(x).astype(int),0,w-1)]


def frame_fade(x,y,w,h,margin=.06):
    e=np.minimum(np.minimum(x/w,1-x/w),np.minimum(y/h,1-y/h))
    return np.clip(e/margin,0,1)


def silhouette_fade(depth,radius=6,jump=.03):
    """1 far from depth discontinuities, 0 on them: protects projected silhouettes."""
    d=np.asarray(depth,np.float32); edge=np.zeros(d.shape,bool)
    def jumps(a,b): return (abs(a-b)>jump*np.maximum(np.minimum(a,b),1e-3))|((a>0)!=(b>0))
    j=jumps(d[:,1:],d[:,:-1]); edge[:,1:]|=j; edge[:,:-1]|=j
    j=jumps(d[1:],d[:-1]); edge[1:]|=j; edge[:-1]|=j
    return U.distance_to(edge,radius)/radius


# ---------------------------------------------------------------- planning

def look_at(position,target,up=(0,0,1.)):
    p=np.asarray(position,np.float64); f=np.asarray(target,np.float64)-p; f/=np.linalg.norm(f)
    x=np.cross(f,up)
    if np.linalg.norm(x)<1e-6: x=np.cross(f,(0,1.,0))
    x/=np.linalg.norm(x); y=np.cross(x,f)
    m=np.eye(4); m[:3,0]=x; m[:3,1]=y; m[:3,2]=-f; m[:3,3]=p
    return m


def candidate_poses(reference,radius=.6,yaws=8,pitches=(0.,-28.),targets=()):
    """Eye-height positions around the reference camera, a ring of headings and
    explicit look-at views towards under-covered surface clusters."""
    ref=np.asarray(reference,np.float64); o=ref[:3,3]
    fwd=-ref[:3,2]; heading=math.atan2(fwd[1],fwd[0])
    positions=[o]+[o+radius*np.array((math.cos(heading+a),math.sin(heading+a),0)) for a in (0,math.pi/2,math.pi,1.5*math.pi)]
    poses=[]
    for p in positions:
        for i in range(yaws):
            a=heading+2*math.pi*i/yaws
            for pitch in pitches:
                pr=math.radians(pitch)
                d=np.array((math.cos(a)*math.cos(pr),math.sin(a)*math.cos(pr),math.sin(pr)))
                poses.append(look_at(p,p+d))
    for p in positions:
        for t in targets: poses.append(look_at(p,t))
    return poses


def view_quality(points,normals,matrix,fov,w,h,visible,reference_distance=2.):
    """Texel quality ~ incidence × resolution × frame fade, zero when hidden."""
    x,y,z=project(points,matrix,fov,w,h)
    inside=(z>.05)&(x>=0)&(x<w)&(y>=0)&(y<h)
    to_cam=np.asarray(matrix)[:3,3]-points; dist=np.linalg.norm(to_cam,axis=1)
    cos=np.einsum('ij,ij->i',normals,to_cam)/np.maximum(dist,1e-9)
    res=np.minimum(1,reference_distance/np.maximum(dist,1e-6))
    return np.where(inside&visible,np.clip(cos,0,1)*res*frame_fade(x,y,w,h),0)


def plan(quality,area,forced=(),max_views=6,min_gain=.01):
    """Greedy view selection on quality-weighted coverage gain (Trompe-style).

    quality: (C, S). forced candidates are kept first (the real photos).
    Returns selected indices and per-step gains as fractions of the total area.
    """
    Q=np.asarray(quality,np.float64); a=np.asarray(area,np.float64); total=max(a.sum(),1e-12)
    current=np.zeros(Q.shape[1]); chosen=[]; gains=[]
    for i in forced:
        gains.append(float((a*np.maximum(Q[i]-current,0)).sum()/total)); current=np.maximum(current,Q[i]); chosen.append(int(i))
    while len(chosen)<max_views:
        gain=(a*np.maximum(Q-current,0)).sum(1)/total; gain[chosen]=-1
        best=int(np.argmax(gain))
        if gain[best]<min_gain: break
        chosen.append(best); gains.append(float(gain[best])); current=np.maximum(current,Q[best])
    return chosen,gains,float((a*current).sum()/total)


def under_covered_targets(points,quality,area,count=4,threshold=.15,seed=3):
    """Centroids of poorly observed samples (k-means on positions)."""
    m=quality<threshold
    if m.sum()<count: return []
    p=points[m]; w=area[m]; rng=np.random.default_rng(seed)
    c=p[rng.choice(len(p),count,replace=False)]
    for _ in range(12):
        k=np.argmin(((p[:,None]-c[None])**2).sum(-1),1)
        for j in range(count):
            if np.any(k==j): c[j]=np.average(p[k==j],axis=0,weights=w[k==j])
    return [c[j] for j in range(count) if np.any(k==j)]


# ---------------------------------------------------------------- atlas

def rasterize(uv,positions,normals,size):
    """Per-texel world position / normal for one UV atlas.

    uv: (T,3,2) in Blender UV space (v up). positions, normals: (T,3,3).
    Returns P (S,S,3), N (S,S,3), mask (S,S) with top-left image origin.
    """
    S=int(size); P=np.zeros((S,S,3),np.float32); N=np.zeros((S,S,3),np.float32); M=np.zeros((S,S),bool)
    uv=np.asarray(uv,np.float64); pos=np.asarray(positions,np.float64); nrm=np.asarray(normals,np.float64)
    pts=np.stack((uv[...,0]*S,(1-uv[...,1])*S),-1)
    for t in range(len(pts)):
        a,b,c=pts[t]
        x0=max(0,int(math.floor(min(a[0],b[0],c[0])))); x1=min(S,int(math.ceil(max(a[0],b[0],c[0]))))
        y0=max(0,int(math.floor(min(a[1],b[1],c[1])))); y1=min(S,int(math.ceil(max(a[1],b[1],c[1]))))
        if x1<=x0 or y1<=y0: continue
        basis=np.array((b-a,c-a)).T; det=np.linalg.det(basis)
        if abs(det)<1e-12: continue
        xx,yy=np.meshgrid(np.arange(x0,x1)+.5,np.arange(y0,y1)+.5)
        q=np.stack((xx.ravel(),yy.ravel()),-1)-a
        bc=q@np.linalg.inv(basis).T; wts=np.column_stack((1-bc.sum(1),bc))
        inside=np.all(wts>=-1e-4,axis=1)
        if not inside.any(): continue
        wts=wts[inside]; ix=xx.ravel()[inside].astype(int); iy=yy.ravel()[inside].astype(int)
        P[iy,ix]=wts@pos[t]; n=wts@nrm[t]; N[iy,ix]=n/np.maximum(np.linalg.norm(n,axis=1,keepdims=True),1e-9); M[iy,ix]=True
    return P,N,M


def match_gain(reference,other,mask,limits=(.7,1.4)):
    """Per-channel colour gain making `other` agree with `reference` on an overlap."""
    if mask.sum()<32: return np.ones(3,np.float32)
    r=np.asarray(reference)[mask]; o=np.asarray(other)[mask]
    g=np.median(r,0)/np.maximum(np.median(o,0),1e-4)
    return np.clip(g,*limits).astype(np.float32)


def blend(P,N,M,views,sharpness=4.,normal_power=2.,tolerance=(.02,.02)):
    """Depth-tested, incidence-weighted multiview projection into one atlas.

    Returns colour (S,S,3), coverage (S,S), per-view stitch weights (V,S,S) and
    the applied colour gains. Outside every view's mask nothing is written.
    """
    S=M.shape[0]; pts=P[M]; nrm=N[M]; n=len(pts)
    weights=[]; colours=[]
    for v in views:
        img=v['image']; h,w=img.shape[:2]
        x,y,z=project(pts,v['matrix'],v['fov'],w,h)
        inside=(z>.02)&(x>=0)&(x<w)&(y>=0)&(y<h)
        seen=nearest(v['depth'],x,y)
        vis=inside&(seen>0)&(abs(seen-z)<tolerance[0]+tolerance[1]*z)
        to_cam=np.asarray(v['matrix'])[:3,3]-pts; dist=np.linalg.norm(to_cam,axis=1)
        cos=np.clip(np.einsum('ij,ij->i',nrm,to_cam)/np.maximum(dist,1e-9),0,1)
        wgt=vis*cos**normal_power*frame_fade(x,y,w,h)*v.get('priority',1.)
        if v.get('fade') is not None: wgt=wgt*nearest(v['fade'],x,y)
        if v.get('mask') is not None: wgt=wgt*nearest(v['mask'],x,y)
        weights.append(wgt.astype(np.float32)); colours.append(bilinear(img,x,y)[:,:3].astype(np.float32))
    W=np.array(weights) if weights else np.zeros((0,n),np.float32)
    gains=[np.ones(3,np.float32) for _ in views]
    if len(views)>1:
        acc=colours[0]*(W[0]>0)[:,None]; accw=(W[0]>.15)
        for k in range(1,len(views)):
            overlap=accw&(W[k]>.15)
            gains[k]=match_gain(acc,colours[k],overlap)
            colours[k]=colours[k]*gains[k]
            fresh=(W[k]>.15)&~accw; acc[fresh]=colours[k][fresh]; accw|=fresh
    Ws=W**sharpness; total=Ws.sum(0)
    colour=np.zeros((n,3),np.float32)
    for k in range(len(views)): colour+=Ws[k][:,None]*colours[k]
    colour=colour/np.maximum(total,1e-12)[:,None]
    covered=total>0
    out=np.zeros((S,S,3),np.float32); cov=np.zeros((S,S),np.float32)
    prio=np.array([max(v.get('priority',1.),1e-6) for v in views])[:,None]
    out[M]=np.where(covered[:,None],colour,0); cov[M]=(W/prio).max(0) if len(views) else 0  # observation quality, priority aside
    stitch=np.zeros((len(views),S,S),np.float32)
    for k in range(len(views)): stitch[k][M]=Ws[k]/np.maximum(total,1e-12)
    return out,cov,stitch,gains


def finish_atlas(colour,coverage,fallback,min_coverage=.08):
    """Known texels kept; uncovered ones take the fallback colour, then push-pull."""
    c=np.asarray(colour,np.float32).copy(); known=np.asarray(coverage)>min_coverage
    if not known.any():
        c[:]=np.asarray(fallback,np.float32)[:3]; return c
    return U.push_pull(c,known.astype(np.float32))


# ---------------------------------------------------------------- albedo

def delight(photo,strength=.6,sigma=.035,guide=None,labels=None):
    """Approximate albedo from a photo (linear RGB).

    With a guide (e.g. an albedo returned by an image model, roughly aligned),
    only its low frequencies are trusted: albedo = photo × blur(guide)/blur(photo).
    Pixel-exact detail always comes from the photo, so small shifts introduced
    by a generator cannot duplicate edges. Without a guide, large-scale shading
    is partially divided out (retinex-like). Result is an estimate, not a measure.
    """
    p=np.asarray(photo,np.float32)[...,:3]; h,w=p.shape[:2]; s=max(1.,sigma*max(h,w))
    smooth=(lambda x:U.blur(x,s)) if labels is None else (lambda x:U.segment_blur(x,labels,s))
    if guide is not None:
        g=U.resize(np.asarray(guide,np.float32)[...,:3],w,h)
        ratio=smooth(g)/np.maximum(smooth(p),1e-4)
        a=p*np.clip(ratio,.2,5)
    else:
        L=U.luminance(p); S=smooth(L); S=S/max(float(np.median(S)),1e-4)
        a=p/np.maximum(S,.05)[...,None]**strength
    # Soften clipped highlights: they are mostly specular, not paint.
    lum=U.luminance(a); hi=float(np.percentile(lum,99.5))
    if hi>.9: a=a*np.where(lum>.9,(.9+(lum-.9)*.3)/np.maximum(lum,1e-4),1)[...,None]
    med=float(np.median(U.luminance(a)))
    a=a*(.42/max(med,1e-4))
    return np.clip(a,.01,.95).astype(np.float32)


def refine(atlas,P,M,view,ratio,strength=1.,limits=(.6,1.6)):
    """Analysis by synthesis: multiply the albedo of texels seen by the photo by the
    photo/render ratio (lighting stays physical; only residual colour moves)."""
    a=np.asarray(atlas,np.float32).copy(); pts=P[M]
    h,w=ratio.shape[:2]
    x,y,z=project(pts,view['matrix'],view['fov'],w,h)
    inside=(z>.02)&(x>=0)&(x<w)&(y>=0)&(y<h)
    seen=nearest(view['depth'],x,y)
    vis=inside&(seen>0)&(abs(seen-z)<.02+.02*z)
    wgt=vis*frame_fade(x,y,w,h)*(nearest(view['fade'],x,y) if view.get('fade') is not None else 1)
    r=np.clip(bilinear(ratio,x,y),*limits)
    k=(1+np.clip(wgt*strength,0,1)[:,None]*(r-1))
    a[M]=np.clip(a[M]*k,.005,.95)
    return a


def local_inpaint(image,mask,labels=None):
    """Deterministic fill for LOCAL mode (no network): push-pull from the rim.

    With labels (object ids), each surface is filled only from its own known
    pixels, so colours never bleed from one object onto another.
    """
    img=np.asarray(image,np.float32)[...,:3]; m=np.asarray(mask)>.5
    if labels is None:
        filled=U.push_pull(img,(~m).astype(np.float32))
    else:
        lab=np.asarray(labels); filled=U.push_pull(img,(~m).astype(np.float32))
        for l in np.unique(lab[m]):
            region=lab==l; known=region&~m
            if not known.any(): continue
            own=U.push_pull(img,known.astype(np.float32))
            filled[region]=own[region]
    soft=U.blur(m.astype(np.float32),2)
    return img*(1-soft[...,None])+filled*soft[...,None]


def compose_masked(original,generated,mask):
    """Outside the mask, the original pixels are kept exactly."""
    o=np.asarray(original,np.float32); g=np.asarray(generated,np.float32); m=np.clip(np.asarray(mask,np.float32),0,1)
    out=o*(1-m[...,None])+g*m[...,None]
    out[m<=0]=o[m<=0]
    return out
