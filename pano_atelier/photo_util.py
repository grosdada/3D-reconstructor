"""Small numpy image helpers shared by the photo pipeline. No bpy.

Arrays are top-left origin, H x W (x C). Colours are scene-linear unless named srgb.
"""
import math
import numpy as np


def srgb_to_linear(c):
    c=np.asarray(c,np.float32)
    return np.where(c<=.04045,c/12.92,((np.maximum(c,0)+.055)/1.055)**2.4).astype(np.float32)


def linear_to_srgb(c):
    c=np.clip(np.asarray(c,np.float32),0,None)
    return np.where(c<=.0031308,c*12.92,1.055*np.power(c,1/2.4)-.055).astype(np.float32)


def luminance(rgb):
    rgb=np.asarray(rgb,np.float32)
    return rgb[...,0]*.2126+rgb[...,1]*.7152+rgb[...,2]*.0722


def _box(a,r,axis):
    if r<1: return a
    n=a.shape[axis]
    pad=[(0,0)]*a.ndim; pad[axis]=(r+1,r)
    c=np.cumsum(np.pad(a,pad,mode='edge'),axis=axis,dtype=np.float64)
    hi=np.take(c,np.arange(2*r+1,2*r+1+n),axis=axis); lo=np.take(c,np.arange(0,n),axis=axis)
    return ((hi-lo)/(2*r+1)).astype(np.float32)


def blur(a,sigma):
    """Gaussian approximation by three box passes, edge clamped."""
    a=np.asarray(a,np.float32)
    if sigma<=.3: return a.copy()
    r=max(1,int(round(math.sqrt(12*sigma*sigma/3+1)-1)//2))
    for _ in range(3):
        a=_box(_box(a,r,0),r,1)
    return a


def resize(a,w,h):
    """Bilinear resize with box prefilter when shrinking."""
    a=np.asarray(a,np.float32); H,W=a.shape[:2]
    if (W,H)==(w,h): return a.copy()
    f=max(W/w,H/h)
    if f>1.5: a=blur(a,.5*f)
    ys=np.clip((np.arange(h)+.5)*H/h-.5,0,H-1); xs=np.clip((np.arange(w)+.5)*W/w-.5,0,W-1)
    y0=np.floor(ys).astype(int); x0=np.floor(xs).astype(int); y1=np.minimum(y0+1,H-1); x1=np.minimum(x0+1,W-1)
    fy=(ys-y0)[:,None]; fx=(xs-x0)[None,:]
    if a.ndim==3: fy=fy[...,None]; fx=fx[...,None]
    top=a[y0][:,x0]*(1-fx)+a[y0][:,x1]*fx; bottom=a[y1][:,x0]*(1-fx)+a[y1][:,x1]*fx
    return (top*(1-fy)+bottom*fy).astype(np.float32)


def nearest(a,w,h):
    a=np.asarray(a); H,W=a.shape[:2]
    yy=np.minimum(((np.arange(h)+.5)*H/h).astype(int),H-1); xx=np.minimum(((np.arange(w)+.5)*W/w).astype(int),W-1)
    return a[yy[:,None],xx[None,:]]


def dilate(mask,radius=1):
    m=np.asarray(mask,bool).copy()
    for _ in range(int(radius)):
        p=np.pad(m,1)
        m=p[1:-1,1:-1]|p[:-2,1:-1]|p[2:,1:-1]|p[1:-1,:-2]|p[1:-1,2:]
    return m


def erode(mask,radius=1):
    return ~dilate(~np.asarray(mask,bool),radius)


def distance_to(mask,limit):
    """Approximate city-block distance to True pixels, saturated at limit."""
    m=np.asarray(mask,bool); d=np.full(m.shape,float(limit),np.float32); front=m.copy(); d[m]=0
    for i in range(1,int(limit)):
        nxt=dilate(front,1); d[nxt&~front]=i; front=nxt
        if front.all(): break
    return d


def label(mask,right=None,down=None):
    """Connected components on a 4-grid. right/down optionally forbid links (H,W-1)/(H-1,W).

    Min-label propagation with pointer jumping; returns int32 labels, -1 outside mask.
    """
    m=np.asarray(mask,bool); h,w=m.shape
    lab=np.where(m,np.arange(h*w).reshape(h,w),h*w).astype(np.int64)
    r=m[:,1:]&m[:,:-1]; d=m[1:]&m[:-1]
    if right is not None: r&=right
    if down is not None: d&=down
    big=h*w
    for _ in range(4*(h+w)):
        old=lab.copy()
        lab[:,1:]=np.minimum(lab[:,1:],np.where(r,old[:,:-1],big)); lab[:,:-1]=np.minimum(lab[:,:-1],np.where(r,old[:,1:],big))
        lab[1:]=np.minimum(lab[1:],np.where(d,old[:-1],big)); lab[:-1]=np.minimum(lab[:-1],np.where(d,old[1:],big))
        flat=lab.ravel(); inside=flat<big
        flat[inside]=flat[flat[inside]]  # pointer jumping towards each root
        lab=flat.reshape(h,w)
        if np.array_equal(old,lab): break
    out=np.full((h,w),-1,np.int32)
    roots=np.unique(lab[m])
    out[m]=np.searchsorted(roots,lab[m])
    return out


def push_pull(color,weight):
    """Fill weight==0 texels from a mip pyramid; known texels stay byte-identical."""
    c=np.asarray(color,np.float32); w=np.asarray(weight,np.float32)>0
    if w.all() or not w.any(): return c.copy()
    levels=[(np.where(w[...,None],c,0),w.astype(np.float32))]
    while min(levels[-1][1].shape)>1:
        a,k=levels[-1]; h,wd=k.shape; h2=(h+1)//2*2; w2=(wd+1)//2*2
        a=np.pad(a,((0,h2-h),(0,w2-wd),(0,0))); k=np.pad(k,((0,h2-h),(0,w2-wd)))
        s=a[0::2,0::2]+a[1::2,0::2]+a[0::2,1::2]+a[1::2,1::2]
        n=k[0::2,0::2]+k[1::2,0::2]+k[0::2,1::2]+k[1::2,1::2]
        levels.append((s,n))
    fill=levels[-1][0]/np.maximum(levels[-1][1],1e-8)[...,None]
    for a,k in reversed(levels[:-1]):
        up=np.repeat(np.repeat(fill,2,0),2,1)[:k.shape[0],:k.shape[1]]
        mean=a/np.maximum(k,1e-8)[...,None]
        fill=np.where((k>0)[...,None],mean,up)
    out=c.copy(); out[~w]=fill[~w]
    return out


def gradient_magnitude(gray):
    g=np.asarray(gray,np.float32)
    gx=np.zeros_like(g); gy=np.zeros_like(g)
    gx[:,1:-1]=(g[:,2:]-g[:,:-2])*.5; gy[1:-1]=(g[2:]-g[:-2])*.5
    return np.hypot(gx,gy)


def masked_blur(a,mask,sigma):
    """Normalized convolution: blur only over mask pixels (no leakage across it)."""
    a=np.asarray(a,np.float32); m=np.asarray(mask,np.float32)
    mm=m[...,None] if a.ndim==3 else m
    return blur(a*mm,sigma)/np.maximum(blur(mm,sigma),1e-6)


def segment_blur(a,labels,sigma):
    """Blur within each label region independently (edge-aware large-scale estimate)."""
    a=np.asarray(a,np.float32); lab=np.asarray(labels); out=blur(a,sigma)
    for l in np.unique(lab):
        if l<0: continue
        m=lab==l
        if m.sum()<4: continue
        out[m]=masked_blur(a,m,sigma)[m]
    return out
