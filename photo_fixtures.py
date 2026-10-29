"""Analytic photo fixtures for the photo → scene tests. Pure numpy, no bpy.

A small room seen by a slightly pitched camera: floor, three walls, a ceiling,
a window looking at a distant garden plane and a coloured box on the floor.
"""
import math
import numpy as np

ROOM=dict(x0=-2.2,x1=2.6,back=5.,height=2.7,window=(-.6,1.,.8,2.),box=((.1,2.6,0.),(.9,3.4,.8)),far=60.)


def camera(height=1.5,pitch=-6.,yaw=4.):
    p,y=math.radians(pitch),math.radians(yaw)
    # Camera looks +Y with Z up, then pitch about X and yaw about Z.
    base=np.array(((1,0,0),(0,0,1),(0,-1,0)),np.float64).T  # columns: cam X,Y,Z in world
    rx=np.array(((1,0,0),(0,math.cos(p),-math.sin(p)),(0,math.sin(p),math.cos(p))))
    rz=np.array(((math.cos(y),-math.sin(y),0),(math.sin(y),math.cos(y),0),(0,0,1)))
    m=np.eye(4); m[:3,:3]=rz@rx@base; m[:3,3]=(0,0,height)
    return m


def render(w=160,h=120,fov=70.,matrix=None,room=ROOM,noise=0.,seed=0,textured=False):
    """Return (srgb image HxWx3, axial depth HxW, world positions, labels)."""
    m=camera() if matrix is None else matrix
    t=math.tan(math.radians(fov)/2)
    x,y=np.meshgrid((np.arange(w)+.5)/w,(np.arange(h)+.5)/h)
    rc=np.stack(((2*x-1)*t,(1-2*y)*t*h/w,-np.ones_like(x)),-1)
    rw=rc@m[:3,:3].T; o=m[:3,3]
    best=np.full((h,w),np.inf); lab=np.full((h,w),-1)
    def plane(axis,value,label,keep=None):
        nonlocal best
        den=rw[...,axis]; s=(value-o[axis])/np.where(abs(den)>1e-9,den,1e-9)
        p=o+rw*s[...,None]; ok=(s>1e-4)&(s<best)
        if keep is not None: ok&=keep(p)
        best=np.where(ok,s,best); lab[ok]=label
    r=room; wx0,wz0,wx1,wz1=r['window']
    plane(2,0.,0,lambda p:(p[...,0]>r['x0'])&(p[...,0]<r['x1'])&(p[...,1]<r['back']))
    plane(2,r['height'],1,lambda p:(p[...,0]>r['x0'])&(p[...,0]<r['x1'])&(p[...,1]<r['back']))
    plane(1,r['back'],2,lambda p:~((p[...,0]>wx0)&(p[...,0]<wx1)&(p[...,2]>wz0)&(p[...,2]<wz1)))
    plane(0,r['x0'],3,lambda p:p[...,1]<r['back']); plane(0,r['x1'],4,lambda p:p[...,1]<r['back'])
    plane(1,r['far'],5)
    (bx0,by0,bz0),(bx1,by1,bz1)=r['box']
    lo=np.array((bx0,by0,bz0)); hi=np.array((bx1,by1,bz1))
    with np.errstate(divide='ignore',invalid='ignore'):
        t0=(lo-o)/rw; t1=(hi-o)/rw
    tn=np.nanmax(np.minimum(t0,t1),-1); tf=np.nanmin(np.maximum(t0,t1),-1)
    hit=(tn<=tf)&(tn>1e-4)&(tn<best)
    best=np.where(hit,tn,best); lab[hit]=6
    pos=o+rw*best[...,None]
    colors=np.array([(.55,.38,.22),(.86,.85,.82),(.80,.76,.68),(.72,.70,.64),(.74,.72,.66),(.35,.55,.30),(.70,.12,.08)])
    img=colors[np.maximum(lab,0)].copy()
    floor=lab==0
    plank=(np.floor(pos[...,0]/.18)%2==0)
    img[floor&plank]*=.82
    grain=.5+.5*np.sin(pos[...,1]*40+np.floor(pos[...,0]/.18)*1.7)
    img[floor]*=(.9+.1*grain[floor])[:,None]
    if textured:  # world-anchored random cells: stable features for multi-photo matching
        for k,(scale,amp) in enumerate(((3.,.35),(7.,.25),(17.,.2))):
            cell=np.floor(pos*scale+k*.37)
            hsh=np.sin(cell@np.array((12.9898,78.233,37.719))+k)*43758.5453
            img*=(1-amp+amp*(hsh-np.floor(hsh)))[...,None]
    # Simple lambert shading from a window-side sun, so the photo has light.
    n=np.zeros_like(pos); n[lab==0]=(0,0,1); n[lab==1]=(0,0,-1); n[lab==2]=(0,-1,0); n[lab==3]=(1,0,0); n[lab==4]=(-1,0,0); n[lab==5]=(0,-1,0)
    eps=1e-3
    for axis,val,nv in ((0,bx0,(-1,0,0)),(0,bx1,(1,0,0)),(1,by0,(0,-1,0)),(1,by1,(0,1,0)),(2,bz1,(0,0,1))):
        n[(lab==6)&(abs(pos[...,axis]-val)<eps*10)]=nv
    sun=np.array((.35,-.55,.76)); sun/=np.linalg.norm(sun)
    shade=.45+.55*np.clip(n@sun,0,1)
    img*=shade[...,None]
    if noise:
        img+=np.random.default_rng(seed).normal(0,noise,img.shape)
    depth=(best*1.0).astype(np.float32)  # rc has z=-1, so the ray parameter is axial depth
    depth[~np.isfinite(depth)]=0
    srgb=np.clip(img,0,1)**(1/2.2)
    return srgb.astype(np.float32),depth,pos,lab
