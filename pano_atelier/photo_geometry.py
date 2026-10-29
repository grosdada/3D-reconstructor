"""Photo → editable modules. Pure numpy, no bpy.

Camera frame (Blender): X right, Y up, -Z forward; depth is axial (distance along -Z).
World frame: Z up, metres, camera at (0, 0, height) looking roughly +Y.
The result is a proposal of modules (architecture slabs with real openings, closed
object shells, backdrop) derived from one depth map; it is not a measured survey.
"""
import math
import numpy as np
from . import photo_util as U

AXES=np.array([(1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)],np.float64)


def camera_rays(w,h,fov):
    t=math.tan(math.radians(fov)/2)
    x,y=np.meshgrid((np.arange(w)+.5)/w,(np.arange(h)+.5)/h)
    return np.stack(((2*x-1)*t,(1-2*y)*t*h/w,-np.ones_like(x)),-1)


def camera_points(depth,fov):
    depth=np.asarray(depth,np.float32)
    return camera_rays(depth.shape[1],depth.shape[0],fov)*depth[...,None]


def continuity(depth,edge=.06):
    """Links between 4-neighbours that do not cross a depth discontinuity."""
    d=np.asarray(depth,np.float32); ok=d>0
    def link(a,b,va,vb): return va&vb&(abs(a-b)<=edge*np.minimum(a,b)+1e-6)
    return link(d[:,1:],d[:,:-1],ok[:,1:],ok[:,:-1]),link(d[1:],d[:-1],ok[1:],ok[:-1])


def point_normals(points,depth,edge=.06):
    p=np.asarray(points,np.float64); h,w=p.shape[:2]
    right,down=continuity(depth,edge)
    dx=np.zeros_like(p); dy=np.zeros_like(p)
    dx[:,1:-1]=p[:,2:]-p[:,:-2]; dy[1:-1]=p[2:]-p[:-2]
    n=np.cross(dy,dx); norm=np.linalg.norm(n,axis=-1)
    ok=np.zeros((h,w),bool)
    ok[1:-1,1:-1]=(right[1:-1,1:]&right[1:-1,:-1]&down[1:,1:-1]&down[:-1,1:-1])
    ok&=norm>1e-12
    n=n/np.maximum(norm,1e-12)[...,None]
    flip=np.sum(n*p,-1)>0  # normals face the camera at the origin
    n[flip]*=-1
    return n,ok


def prior_depth(h,w,fov,horizon=.5,height=1.6,far=40.,boxes=()):
    """Ground plane + backdrop diorama when no depth model is available.

    Optional boxes (normalized, top-left) become vertical cards standing where
    their lower edge meets the ground, in the spirit of photo pop-up methods.
    """
    t=math.tan(math.radians(fov)/2)
    rays=camera_rays(w,h,fov)
    # Horizon below/above image centre is modelled as a camera pitch.
    pitch=math.atan((horizon-.5)*2*t*h/w)
    c,s=math.cos(pitch),math.sin(pitch)
    ry=rays[...,1]*c-rays[...,2]*s  # vertical component in a level frame, rays have z=-1
    depth=np.where(ry<-1e-6,height/np.maximum(-ry,1e-6),far)
    depth=np.minimum(depth,far).astype(np.float32)
    for box in boxes:
        x0,y0,x1,y1=box
        if not (0<=x0<x1<=1 and 0<=y0<y1<=1): continue
        bx=min(w-1,max(0,int((x0+x1)/2*w))); by=min(h-1,max(0,int(y1*h)-1))
        d=float(depth[by,bx])
        if d>=far*.999: continue
        depth[int(y0*h):int(math.ceil(y1*h)),int(x0*w):int(math.ceil(x1*w))]=d
    return depth


def fit_plane(points):
    p=np.asarray(points,np.float64)
    c=p.mean(0); _,_,vt=np.linalg.svd(p-c,full_matrices=False)
    return vt[2],c


def ransac_plane(P,N,candidates,rng,iterations=160,angle=20.,tol=(.012,.012),allowed=None):
    """Point + normal hypotheses; returns (normal, centre, inlier mask) or None."""
    idx=np.flatnonzero(candidates)
    if len(idx)<16: return None
    dist=np.linalg.norm(P,axis=-1); cos=math.cos(math.radians(angle))
    threshold=tol[0]+tol[1]*dist
    best=None; best_count=0
    pool=allowed if allowed is not None else np.ones(len(P),bool)
    for i in rng.choice(idx,size=min(iterations,len(idx)),replace=False):
        n=N[i]; c=P[i]
        inl=pool&(abs((P-c)@n)<threshold)&((N@n)>cos)
        k=int(inl.sum())
        if k>best_count: best_count=k; best=(n,c,inl)
    if best is None: return None
    n,c,inl=best
    for _ in range(2):
        sample=np.flatnonzero(inl)
        if len(sample)<8: return None
        if len(sample)>20000: sample=rng.choice(sample,20000,replace=False)
        n,c=fit_plane(P[sample])
        if n@N[sample].mean(0)<0: n=-n
        inl=pool&(abs((P-c)@n)<threshold)&((N@n)>cos)
    return n,c,inl


def frame_from_up(up,forward=(0,0,-1)):
    """Camera→world rotation: world Z = up, world +Y = forward projected on the ground."""
    z=np.asarray(up,np.float64); z/=np.linalg.norm(z)
    f=np.asarray(forward,np.float64); y=f-z*(f@z)
    if np.linalg.norm(y)<1e-6: y=np.array((0,1.,0))-z*z[1]
    y/=np.linalg.norm(y); x=np.cross(y,z)
    return np.stack((x,y,z))  # rows: world axes in camera coordinates


def estimate_frame(P,N,valid,rng,min_fraction=.03):
    """Gravity from the floor (or ceiling) plane; level camera when neither is reliable."""
    up0=np.array((0,1.,0)); total=max(1,int(valid.sum()))
    tries=[('floor',(N@up0>math.cos(math.radians(35)))&(P@up0<-.2)&valid,1),
           ('ceiling',(N@up0<-math.cos(math.radians(35)))&(P@up0>.2)&valid,-1)]
    for name,cand,sign in tries:
        found=ransac_plane(P,N,cand,rng,angle=15)
        if found is None: continue
        n,c,inl=found
        if inl.sum()<min_fraction*total: continue
        up=n*sign
        height=float(-(c@n)*sign) if name=='floor' else None
        return dict(rotation=frame_from_up(up),height=height,source=name)
    return dict(rotation=frame_from_up(up0),height=None,source='level_camera_assumption')


def manhattan_yaw(Nw,mask):
    """Dominant wall orientation modulo 90°, in radians within (-45°, 45°]."""
    m=mask&(abs(Nw[:,2])<math.sin(math.radians(20)))
    if m.sum()<32: return 0.
    a=np.arctan2(Nw[m,1],Nw[m,0])*4
    yaw=math.atan2(np.sin(a).mean(),np.cos(a).mean())/4
    return float(yaw)


def rotation_z(angle):
    c,s=math.cos(angle),math.sin(angle)
    return np.array(((c,-s,0),(s,c,0),(0,0,1.)))


def snap_normal(n,degrees=8.):
    dots=AXES@n; i=int(np.argmax(dots))
    return AXES[i].copy() if dots[i]>math.cos(math.radians(degrees)) else n/np.linalg.norm(n)


def plane_basis(n):
    n=np.asarray(n,np.float64)
    if abs(n[2])>.9:  # horizontal plane: world axes
        u=np.array((1.,0,0)); v=np.cross(n,u); return u/np.linalg.norm(u),v/np.linalg.norm(v)
    u=np.cross((0,0,1.),n); u/=np.linalg.norm(u); v=np.cross(n,u)
    return u,v


def slab(origin,u,v,n,rect,thickness,holes=()):
    """Closed slab on a plane rectangle with real rectangular openings.

    The front face lies on the plane, facing n; thickness extrudes along -n.
    Openings produce explicit jambs, sills and lintels (no boolean).
    """
    u=np.asarray(u,np.float64); v=np.asarray(v,np.float64); n=np.asarray(n,np.float64); o=np.asarray(origin,np.float64)
    if np.cross(u,v)@n<0: v=-v; rect=(rect[0],-rect[3],rect[2],-rect[1]); holes=[(a0,-b1,a1,-b0) for a0,b0,a1,b1 in holes]
    u0,v0,u1,v1=rect
    holes=[(max(u0,a0),max(v0,b0),min(u1,a1),min(v1,b1)) for a0,b0,a1,b1 in holes]
    holes=[h for h in holes if h[2]-h[0]>1e-3 and h[3]-h[1]>1e-3]
    us=sorted({u0,u1,*[x for h in holes for x in (h[0],h[2])]}); vs=sorted({v0,v1,*[y for h in holes for y in (h[1],h[3])]})
    nu,nv=len(us)-1,len(vs)-1
    occupied=np.ones((nu,nv),bool)
    for i in range(nu):
        for j in range(nv):
            cu=(us[i]+us[i+1])/2; cv=(vs[j]+vs[j+1])/2
            occupied[i,j]=not any(a0<cu<a1 and b0<cv<b1 for a0,b0,a1,b1 in holes)
    verts=[]; index={}
    def vid(i,j,layer):
        key=(i,j,layer)
        if key not in index:
            index[key]=len(verts); verts.append(o+u*us[i]+v*vs[j]-n*thickness*layer)
        return index[key]
    faces=[]
    def cell(i,j): return 0<=i<nu and 0<=j<nv and occupied[i,j]
    for i in range(nu):
        for j in range(nv):
            if not occupied[i,j]: continue
            faces.append((vid(i,j,0),vid(i+1,j,0),vid(i+1,j+1,0),vid(i,j+1,0)))
            faces.append((vid(i,j+1,1),vid(i+1,j+1,1),vid(i+1,j,1),vid(i,j,1)))
            if not cell(i-1,j): faces.append((vid(i,j,0),vid(i,j+1,0),vid(i,j+1,1),vid(i,j,1)))
            if not cell(i+1,j): faces.append((vid(i+1,j+1,0),vid(i+1,j,0),vid(i+1,j,1),vid(i+1,j+1,1)))
            if not cell(i,j-1): faces.append((vid(i,j,0),vid(i,j,1),vid(i+1,j,1),vid(i+1,j,0)))
            if not cell(i,j+1): faces.append((vid(i,j+1,0),vid(i+1,j+1,0),vid(i+1,j+1,1),vid(i,j+1,1)))
    return np.array(verts),faces


def box(center,size,yaw=0.):
    R=rotation_z(yaw); c=np.asarray(center,np.float64); sx,sy,sz=(s/2 for s in size)
    return slab(c+R@(-sx,-sy,sz),R[:,0],R[:,1],R[:,2],(0,0,2*sx,2*sy),2*sz)


def shell(points,mask,right,down,origin,thickness,limits=(),floor=None,smooth=3):
    """Closed object volume: visible relief, sides along the silhouette, back face.

    The back is pushed along the viewing rays, so the silhouette is exact from the
    photo while the object gains a plausible thickness. limits: (n, k) planes
    n·x = k (room surfaces) that the back must not cross.
    """
    P=np.asarray(points,np.float64).copy(); m=np.asarray(mask,bool); h,w=m.shape
    r=right&m[:,1:]&m[:,:-1]; d=down&m[1:]&m[:-1]
    origin=np.asarray(origin,np.float64)
    ray=P-origin; dist=np.linalg.norm(ray,axis=-1); ray/=np.maximum(dist,1e-9)[...,None]
    for _ in range(smooth):  # denoise the relief along rays only: silhouette unchanged
        acc=dist.copy(); cnt=np.ones_like(dist)
        acc[:,1:]+=np.where(r,dist[:,:-1],0); cnt[:,1:]+=r; acc[:,:-1]+=np.where(r,dist[:,1:],0); cnt[:,:-1]+=r
        acc[1:]+=np.where(d,dist[:-1],0); cnt[1:]+=d; acc[:-1]+=np.where(d,dist[1:],0); cnt[:-1]+=d
        dist=np.where(m,.5*dist+.5*acc/cnt,dist)
    P=origin+ray*dist[...,None]
    tris=[]; ys,xs=np.nonzero(m)
    for y in range(max(0,ys.min()),min(h-1,ys.max()+1)):
        for x in range(max(0,xs.min()),min(w-1,xs.max()+1)):
            if not (r[y,x] and r[y+1,x] and d[y,x] and d[y,x+1]): continue
            a,b,c,e=y*w+x,y*w+x+1,(y+1)*w+x+1,(y+1)*w+x
            tris.append((a,e,c)); tris.append((a,c,b))
    if not tris: return None
    used=np.unique(np.array(tris)); remap=-np.ones(h*w,np.int64); remap[used]=np.arange(len(used))
    front=P.reshape(-1,3)[used]; rays=ray.reshape(-1,3)[used]
    depth=np.full(len(used),float(thickness))
    for n,k in limits:
        n=np.asarray(n,np.float64); den=rays@n
        s=(k-front@n)/np.where(abs(den)>1e-9,den,1e-9)
        hit=(den<-1e-6)&(s>0)
        depth=np.where(hit,np.minimum(depth,np.maximum(s-.02,.01)),depth)
    back=front+rays*depth[:,None]
    if floor is not None:
        verts=np.concatenate((front,back))
        low=verts[:,2].min(); gap=low-floor
        if 0<gap<=.25:  # objects close to the floor rest on it instead of floating
            k=np.clip(1-(verts[:,2]-low)/.3,0,1); verts[:,2]-=gap*k
        front,back=verts[:len(front)],verts[len(front):]
        back[:,2]=np.maximum(back[:,2],floor)
    tris=remap[np.array(tris)]; n=len(front)
    edges={}
    for t in tris:
        for a,b in ((t[0],t[1]),(t[1],t[2]),(t[2],t[0])):
            key=(min(a,b),max(a,b)); edges[key]=edges.get(key,0)+1
    faces=[tuple(int(i) for i in t) for t in tris]
    faces+=[(int(t[2])+n,int(t[1])+n,int(t[0])+n) for t in tris]
    for t in tris:
        for a,b in ((t[0],t[1]),(t[1],t[2]),(t[2],t[0])):
            if edges[(min(a,b),max(a,b))]==1: faces.append((int(b),int(a),int(a)+n,int(b)+n))
    return np.concatenate((front,back)),faces


def components(mask,right,down,min_pixels):
    lab=U.label(mask,right,down)
    counts=np.bincount(lab[lab>=0].ravel()) if (lab>=0).any() else np.zeros(0,int)
    return [lab==i for i in np.flatnonzero(counts>=min_pixels)]


def element_for(mask,elements,w,h):
    """Vision element whose box contains most of the component, if any."""
    ys,xs=np.nonzero(mask)
    if not len(xs): return None
    best=None; score=.3
    for e in elements:
        x0,y0,x1,y1=e['box']
        inside=((xs+.5)/w>=x0)&((xs+.5)/w<=x1)&((ys+.5)/h>=y0)&((ys+.5)/h<=y1)
        f=float(inside.mean())
        if f>score: score=f; best=e
    return best


def analyse(depth,fov,valid=None,elements=(),width=192,seed=7,max_planes=10,edge=.06):
    """Depth map → camera pose, architecture planes, openings and object shells.

    Returns a JSON-friendly dict (numpy arrays for vertices). All thresholds are
    relative to depth; they are proposals to inspect, not physical measurements.
    """
    rng=np.random.default_rng(seed)
    depth=np.asarray(depth,np.float32); H0,W0=depth.shape
    w=min(width,W0); h=max(8,round(w*H0/W0))
    d=U.nearest(depth,w,h).astype(np.float32)
    ok=d>0
    if valid is not None: ok&=U.nearest(np.asarray(valid,bool),w,h)
    d=np.where(ok,d,0)
    if ok.sum()<64: raise ValueError('Profondeur insuffisante pour modéliser la scène.')
    Pc=camera_points(d,fov); Nc,nok=point_normals(Pc,d,edge); nok&=ok
    right,down=continuity(d,edge)
    flatP=Pc.reshape(-1,3).astype(np.float64); flatN=Nc.reshape(-1,3); flatok=nok.ravel()
    frame=estimate_frame(flatP,flatN,flatok,rng)
    R=frame['rotation']
    Pw=flatP@R.T; Nw=flatN@R.T
    yaw=manhattan_yaw(Nw,flatok)
    Rz=rotation_z(-yaw); R=Rz@R; Pw=Pw@Rz.T; Nw=Nw@Rz.T
    height=frame['height'] or 1.6
    Pw[:,2]+=height; cam=np.array((0,0,height))
    total=int(flatok.sum())
    # Sequential plane extraction in the gravity-aligned frame.
    planes=[]; free=flatok.copy()
    for _ in range(max_planes):
        found=ransac_plane(Pw-cam,Nw,free,rng,allowed=free)
        if found is None: break
        n,c,inl=found
        if inl.sum()<max(48,.015*total): break
        n=snap_normal(n); c=c+cam
        k=float(np.median(Pw[inl]@n))
        planes.append(dict(normal=n,k=k,mask=inl)); free&=~inl
    floor=ceiling=None; walls=[]
    for p in planes:
        n=p['normal']
        if n[2]>.95 and p['k']<height-.3 and (floor is None or p['k']<floor['k']): floor=p
        elif n[2]<-.95 and -p['k']>height+.3 and (ceiling is None or -p['k']>-ceiling['k']): ceiling=p
    room_h=(-ceiling['k']-floor['k']) if floor and ceiling else 2.5
    for p in planes:
        n=p['normal']; pts=Pw[p['mask']]; zspan=np.percentile(pts[:,2],98)-np.percentile(pts[:,2],2)
        # A wall spans a good part of the storey and stays near; box faces and far scenery do not.
        if abs(n[2])<.1 and zspan>max(1.,.45*room_h) and abs(cam@n-p['k'])<30: walls.append(p)
    for p in planes:
        p['kind']='floor' if p is floor else 'ceiling' if p is ceiling else 'wall' if any(p is q for q in walls) else 'surface'
    floor_z=float(floor['k']) if floor else None
    ceil_z=float(-ceiling['k']) if ceiling else None
    rays=camera_rays(w,h,fov).reshape(-1,3)@R.T; rays/=np.linalg.norm(rays,axis=-1,keepdims=True)
    dist=np.linalg.norm(Pw-cam,axis=-1)
    modules=[]; owner=np.full(h*w,-1,np.int32)
    def add(module,pixels=None):
        modules.append(module)
        if pixels is not None: owner[pixels&(owner<0)]=len(modules)-1
        return module
    arch=[p for p in planes if p['kind']!='surface']
    # Wall extents, corner closing and openings.
    for p in walls:
        n=p['normal']; u,v=plane_basis(n); pts=Pw[p['mask']]
        uu=pts@u; a0,a1=np.percentile(uu,(.5,99.5))
        bottom=floor_z if floor_z is not None else float(np.percentile(pts[:,2],1))
        top=ceil_z if ceil_z is not None else max(float(np.percentile(pts[:,2],99.5)),bottom+2.6)
        p.update(u=u,v=v,rect=[float(a0),bottom,float(a1),top])
    for p in walls:
        for q in walls:
            if q is p or abs(p['normal']@q['normal'])>.2: continue
            # Vertical intersection line of the two wall planes.
            A=np.array((p['normal'][:2],q['normal'][:2])); b=np.array((p['k'],q['k']))
            try: xy=np.linalg.solve(A,b)
            except np.linalg.LinAlgError: continue
            s=float(np.array((*xy,0))@p['u'])
            if p['rect'][0]-1<s<p['rect'][0]+.5: p['rect'][0]=min(p['rect'][0],s)
            if p['rect'][2]-.5<s<p['rect'][2]+1: p['rect'][2]=max(p['rect'][2],s)
    window_labels={'window','fenetre','fenêtre'}
    for i,p in enumerate(walls):
        n,u,v=p['normal'],p['u'],p['v']; a0,b0,a1,b1=p['rect']
        den=rays@n; t=(p['k']-cam@n)/np.where(abs(den)>1e-9,den,1e-9)
        X=cam+rays*t[:,None]; uu=X@u; zz=X[:,2]
        inside=(t>0)&(uu>a0+.03)&(uu<a1-.03)&(zz>b0+.03)&(zz<b1-.03)
        behind=inside&((~ok.ravel())|(dist>t+.12+.02*t))
        holes=[]
        for comp in components(behind.reshape(h,w),None,None,12):
            cu=uu[comp.ravel()]; cz=zz[comp.ravel()]
            h0,h1=np.percentile(cu,(2,98)); z0,z1=np.percentile(cz,(2,98))
            if h1-h0<.25 or z1-z0<.25: continue
            if h0<a0+.08 or h1>a1-.08: continue  # wall end, not an opening
            z0=b0 if z0<b0+.12 else z0; z1=min(z1,b1-.08)
            el=element_for(comp,elements,w,h)
            kind='door' if z0<=b0+1e-6 else 'window'
            if el and el.get('kind') in ('window','door'): kind=el['kind']
            elif el and str(el.get('label','')).lower() in window_labels: kind='window'
            holes.append((float(h0),float(z0),float(h1),float(z1),kind))
        p['openings']=holes
        thick=.18
        verts,faces=slab(n*p['k'],u,(0,0,1.),n,(a0,b0,a1,b1),thick,[x[:4] for x in holes])
        add(dict(name='Mur %02d'%(i+1),kind='wall',group='Architecture',vertices=verts,faces=faces,
            pivot=np.array((*(n*p['k']+u*(a0+a1)/2)[:2],b0)),bevel=0,normal=n.tolist()),p['mask'])
        for j,(h0,z0,h1,z1,kind) in enumerate(holes):
            frame_d=.06; inset=thick*.5
            base=n*(p['k']-inset)
            parts=[((h0,z0),(h0+frame_d,z1)),((h1-frame_d,z0),(h1,z1)),((h0+frame_d,z1-frame_d),(h1-frame_d,z1))]
            if kind=='window': parts.append(((h0+frame_d,z0),(h1-frame_d,z0+frame_d)))
            fv=[];ff=[]
            for (c0,r0),(c1,r1) in parts:
                vv,f2=slab(base+n*.03,u,(0,0,1.),n,(c0,r0,c1,r1),.08)
                ff+=[tuple(x+len(fv) for x in f) for f in f2]; fv+=list(vv)
            add(dict(name='Cadre %s %02d-%02d'%('fenêtre' if kind=='window' else 'porte',i+1,j+1),kind='frame',group='Ouvertures',
                vertices=np.array(fv),faces=ff,pivot=np.array((*(base+u*(h0+h1)/2)[:2],z0)),bevel=.003,opening=kind))
            if kind=='window':
                gv,gf=slab(base-n*.01,u,(0,0,1.),n,(h0+frame_d,z0+frame_d,h1-frame_d,z1-frame_d),.006)
                add(dict(name='Vitrage %02d-%02d'%(i+1,j+1),kind='glass',group='Ouvertures',vertices=gv,faces=gf,
                    pivot=np.array((*(base+u*(h0+h1)/2)[:2],z0))))
    # Floor / ceiling cover the observed area and the wall footprints.
    for p,name in ((floor,'Sol'),(ceiling,'Plafond')):
        if p is None: continue
        pts=Pw[p['mask']][:,:2]
        ext=[pts]+[np.array([(p2['u']*p2['rect'][0]+p2['normal']*p2['k'])[:2],(p2['u']*p2['rect'][2]+p2['normal']*p2['k'])[:2]]) for p2 in walls]
        xy=np.concatenate(ext); lo=np.percentile(xy,.5,axis=0)-.05; hi=np.percentile(xy,99.5,axis=0)+.05
        lo=np.maximum(lo,cam[:2]-60); hi=np.minimum(hi,cam[:2]+60)
        n=p['normal']; z=p['k']*n[2]
        if name=='Sol':
            verts,faces=slab((0,0,z),(1.,0,0),(0,1.,0),(0,0,1.),(lo[0],lo[1],hi[0],hi[1]),.12)
        else:
            verts,faces=slab((0,0,z),(1.,0,0),(0,-1.,0),(0,0,-1.),(lo[0],-hi[1],hi[0],-lo[1]),.12)
        add(dict(name=name,kind=p['kind'],group='Architecture',vertices=verts,faces=faces,
            pivot=np.array(((lo[0]+hi[0])/2,(lo[1]+hi[1])/2,z)),bevel=0),p['mask'])
    # Objects: everything valid that the room planes do not explain.
    taken=np.zeros(h*w,bool)
    for p in arch: taken|=p['mask']
    holes=U.label(~ok)  # invalid regions touching the top border = sky
    top_ids=[int(i) for i in np.unique(holes[0]) if i>=0]
    sky=np.isin(holes,top_ids) if top_ids else np.zeros((h,w),bool)
    far=float(np.percentile(dist[ok.ravel()],99)) if ok.any() else 30.
    room=[p for p in arch]
    limits=[(p['normal'],p['k']) for p in room]  # backs stay on the camera side of room surfaces
    rest=(ok.ravel()&~taken).reshape(h,w)
    backdrop_d=max(far*1.15,8.)
    distant=(dist.reshape(h,w)>max(35.,far*.9))&rest
    rest&=~distant
    objects=components(rest,right,down,max(10,int(.0015*h*w)))
    P3=Pw.reshape(h,w,3)
    for k,m in enumerate(objects):
        pts=P3[m]; xy=pts[:,:2]
        width_h=float(np.ptp(xy@np.array((1,0)))+np.ptp(xy@np.array((0,1))))/2
        tall=float(np.ptp(pts[:,2]))
        thickness=float(np.clip(.6*min(max(width_h,.05),max(tall,.05)),.04,1.5))
        el=element_for(m,elements,w,h)
        res=shell(P3,m,right,down,cam,thickness,limits,floor_z)
        if res is None: continue
        verts,faces=res
        if np.ptp(verts[:len(verts)//2],axis=0).max()<.15: continue  # slivers along plane joints
        low=verts[:,2].min(); centre=verts.mean(0)
        label=el.get('label') if el else None
        add(dict(name=(label or 'Objet')[:40].capitalize()+' %02d'%(k+1),kind='object',group='Objets',vertices=verts,faces=faces,
            pivot=np.array((centre[0],centre[1],low)),bevel=0,label=label,material_hint=(el or {}).get('material'),
            thickness=thickness),m.ravel())
    # A distant card keeps sky and far scenery visible behind everything.
    t=math.tan(math.radians(fov)/2)
    corners=np.array([((-1)*t,(1)*t*h/w,-1),(t,t*h/w,-1),(t,-t*h/w,-1),(-t,-t*h/w,-1)])*backdrop_d*1.02
    back=corners@R.T+cam
    add(dict(name='Fond lointain',kind='backdrop',group='Fond',vertices=back,faces=[(0,3,2,1)],
        pivot=back.mean(0),bevel=0),(sky|distant).ravel())
    camera=np.eye(4); camera[:3,:3]=R; camera[:3,3]=cam
    report=dict(gravity=frame['source'],camera_height=float(height),manhattan_yaw_deg=math.degrees(yaw),
        planes=[dict(kind=p['kind'],normal=[float(x) for x in p['normal']],k=p['k'],pixels=int(p['mask'].sum())) for p in planes],
        walls=len(walls),openings=sum(len(p.get('openings',[])) for p in walls),objects=sum(1 for m in modules if m['kind']=='object'),
        floor=floor_z,ceiling=ceil_z,backdrop_distance=backdrop_d,analysis_size=[w,h],
        sky_fraction=float(sky.mean()),unexplained_fraction=float(((owner<0)&ok.ravel()).mean()))
    return dict(camera=camera,fov=float(fov),modules=modules,owner=owner.reshape(h,w),sky=sky,report=report,
                normals=Nw.reshape(h,w,3).astype(np.float32),valid=nok)
