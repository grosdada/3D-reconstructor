"""Materials, procedural recipes, lighting and lens/atmosphere look. Pure numpy.

Every estimate here is a starting point derived from one photo; the scene keeps
editable physical parameters (lights, Principled inputs, haze density, glare).
"""
import math
import numpy as np
from . import photo_util as U

# Principled starting points per material family; procedural = recipe for close-up detail.
MATERIALS={
    'plaster':dict(roughness=.82,specular=.35,procedural='grain',bump=.0004),
    'paint':dict(roughness=.55,specular=.5,procedural='grain',bump=.0002),
    'concrete':dict(roughness=.85,specular=.4,procedural='grain',bump=.0008),
    'stone':dict(roughness=.72,specular=.45,procedural='grain',bump=.001),
    'brick':dict(roughness=.86,specular=.35,procedural='brick',bump=.0015),
    'tile':dict(roughness=.22,specular=.6,coat=.3,procedural='tiles',bump=.0006),
    'wood':dict(roughness=.5,specular=.45,procedural='wood',bump=.0004),
    'metal':dict(roughness=.35,metallic=1.,specular=.5,procedural='brushed',bump=.0001),
    'fabric':dict(roughness=.95,sheen=.6,specular=.25,procedural='weave',bump=.0003),
    'leather':dict(roughness=.55,specular=.45,coat=.1,procedural='grain',bump=.0003),
    'plastic':dict(roughness=.4,specular=.5,procedural='grain',bump=.0001),
    'ceramic':dict(roughness=.15,specular=.6,coat=.5,procedural='none',bump=0.),
    'glass':dict(roughness=.02,transmission=1.,ior=1.45,procedural='none',bump=0.),
    'foliage':dict(roughness=.6,specular=.4,procedural='foliage',bump=.001),
    'asphalt':dict(roughness=.9,specular=.35,procedural='grain',bump=.0012),
    'soil':dict(roughness=.95,specular=.3,procedural='grain',bump=.0015),
    'water':dict(roughness=.03,specular=.5,ior=1.33,procedural='none',bump=0.),
    'screen':dict(roughness=.1,specular=.5,emission=1.,procedural='none',bump=0.),
}


# ---------------------------------------------------------------- surfaces

def hue_saturation(rgb):
    c=np.asarray(rgb,np.float32); mx=c.max(-1); mn=c.min(-1); d=mx-mn
    s=np.where(mx>1e-6,d/np.maximum(mx,1e-6),0)
    r,g,b=c[...,0],c[...,1],c[...,2]; dd=np.maximum(d,1e-6)
    h=np.where(mx==r,((g-b)/dd)%6,np.where(mx==g,(b-r)/dd+2,(r-g)/dd+4))/6
    return np.where(d>1e-6,h,0),s


def texture_stats(albedo,mask=None,texel_m=.005):
    """Colour, contrast, scale, orientation and periodicity of a texture patch."""
    a=np.asarray(albedo,np.float32)[...,:3]; m=np.ones(a.shape[:2],bool) if mask is None else np.asarray(mask,bool)
    if m.sum()<16: return dict(mean=[.5,.5,.5],contrast=0.,saturation=0.,hue=0.,wavelength_m=.05,anisotropy=0.,angle=0.,
                               periodic=0.,period_m=0.,detail=.02,texel_m=texel_m)
    mean=a[m].mean(0); L=U.luminance(a); mu=float(L[m].mean())
    contrast=float(L[m].std()/max(mu,1e-4))
    hue,sat=hue_saturation(a); s=float(sat[m].mean())
    ang=hue[m]*2*math.pi; wts=sat[m]
    h=float((math.atan2((np.sin(ang)*wts).sum(),(np.cos(ang)*wts).sum())/(2*math.pi))%1)
    ys,xs=np.nonzero(m); crop=L[ys.min():ys.max()+1,xs.min():xs.max()+1].copy()
    cm=m[ys.min():ys.max()+1,xs.min():xs.max()+1]; crop[~cm]=mu; crop=crop-mu
    n=min(256,min(crop.shape)); n=max(8,n); scale_px=max(1.,max(crop.shape)/n)
    crop=U.resize(crop,n,n) if min(crop.shape)>=8 else np.pad(crop,((0,max(0,8-crop.shape[0])),(0,max(0,8-crop.shape[1]))))[:8,:8]
    win=np.outer(np.hanning(crop.shape[0]),np.hanning(crop.shape[1]))
    F=np.fft.fft2(crop*win); power=np.abs(F)**2
    fy=np.fft.fftfreq(crop.shape[0]); fx=np.fft.fftfreq(crop.shape[1])
    radius=np.hypot(*np.meshgrid(fy,fx,indexing='ij'))
    bins=np.linspace(1/crop.shape[0],.5,24); prof=[]
    for lo,hi in zip(bins[:-1],bins[1:]):
        sel=(radius>=lo)&(radius<hi); prof.append(power[sel].mean() if sel.any() else 0)
    prof=np.array(prof); centres=(bins[:-1]+bins[1:])/2
    peak=centres[int(np.argmax(prof*centres))] if prof.any() else .1
    wavelength=float(scale_px/peak*texel_m)
    hf=(radius>.25)&(radius<=.5); total=power[radius>0].sum()
    detail=float(math.sqrt(power[hf].sum()/max(total,1e-12))*contrast)
    gy,gx=np.gradient(crop)
    J=np.array(((np.sum(gx*gx),np.sum(gx*gy)),(np.sum(gx*gy),np.sum(gy*gy))))
    ev,evec=np.linalg.eigh(J)
    aniso=float((ev[1]-ev[0])/max(ev[1]+ev[0],1e-12))
    angle=float(math.degrees(math.atan2(evec[1,1],evec[0,1]))+90)%180  # stripe direction
    ac=np.real(np.fft.ifft2(power)); ac/=max(ac[0,0],1e-12)
    ac=np.fft.fftshift(ac); cy,cx=np.array(ac.shape)//2
    yy,xx=np.mgrid[:ac.shape[0],:ac.shape[1]]; r=np.hypot(yy-cy,xx-cx)
    ring=(r>3)&(r<min(cy,cx)*.8)
    periodic=float(ac[ring].max()) if ring.any() else 0.
    period=float(r[ring][np.argmax(ac[ring])]*scale_px*texel_m) if ring.any() else 0.
    return dict(mean=[float(x) for x in mean],contrast=contrast,saturation=s,hue=h,wavelength_m=wavelength,
                anisotropy=aniso,angle=angle,periodic=periodic,period_m=period,detail=detail,texel_m=texel_m)


def classify(stats,kind='object',hint=None):
    """Material family: explicit hint (vision) first, then geometric role and statistics."""
    if hint:
        h=str(hint).lower()
        for name in MATERIALS:
            if name in h: return name
        for words,name in ((('enduit','platre','plâtre'),'plaster'),(('peint',),'paint'),(('béton','beton'),'concrete'),
                           (('bois','parquet','oak','pine'),'wood'),(('métal','metal','steel','acier','alu'),'metal'),
                           (('tissu','cloth','textile','velvet'),'fabric'),(('verre','vitre'),'glass'),(('carrel','tiles'),'tile'),
                           (('brique',),'brick'),(('pierre','marble','marbre','granite'),'stone'),(('herbe','grass','leaf','plant','tree'),'foliage')):
            if any(w in h for w in words): return name
    if kind=='glass': return 'glass'
    if kind=='frame': return 'paint'
    hue=stats['hue']*360; sat=stats['saturation']; c=stats['contrast']
    warm=(15<hue<50) and sat>.25
    if 70<hue<170 and sat>.25 and c>.15: return 'foliage'
    if stats['anisotropy']>.3 and warm: return 'wood'  # planks are periodic too: grain direction wins
    if stats['periodic']>.35:
        if kind in ('floor','ceiling'): return 'tile'
        if (hue<25 or hue>340) and sat>.3: return 'brick'
    if kind=='floor':
        if warm: return 'wood'
        return 'concrete' if c>.08 else 'tile'
    if kind in ('wall','ceiling'):
        return 'concrete' if sat<.12 and c>.09 else 'plaster'
    if sat<.1 and c>.25: return 'metal'
    if c<.06 and sat>.2: return 'fabric'
    return 'paint'


def recipe(stats,family):
    """Procedural detail parameters (metres) taking over below the atlas resolution."""
    base=MATERIALS.get(family,MATERIALS['paint'])
    kind=base['procedural']
    if kind=='grain' and stats['anisotropy']>.45: kind='brushed' if family=='metal' else kind
    texel=max(stats.get('texel_m',.005),1e-4)
    return dict(type=kind,scale_m=float(np.clip(stats['wavelength_m'],.002,2.)),
        detail_scale_m=float(np.clip(texel*2,.0005,.05)),amplitude=float(np.clip(stats['contrast'],.02,.35)),
        detail=float(np.clip(stats['detail']*1.5,.015,.25)),angle=stats['angle'],
        period_m=float(np.clip(stats['period_m'],.02,1.5)) if stats['periodic']>.35 else 0.,
        bump=base.get('bump',.0003),texel_m=texel)


def highlight_roughness(photo,mask,base=.5):
    """Sharp, bright specular peaks on a region suggest a glossier surface."""
    L=U.luminance(photo); m=np.asarray(mask,bool)
    if m.sum()<64: return base
    local=U.blur(L,6); peaks=(L>local*1.6)&(L>np.percentile(L[m],90))&m
    frac=peaks.sum()/m.sum()
    return float(np.clip(base-frac*6,.08,.95))


# ---------------------------------------------------------------- light

def fit_directional(normals,values,weights=None):
    """L ≈ ambient + n·v by weighted least squares over planar surfaces.

    Returns direction towards the light, directional/ambient ratio and fit quality.
    """
    n=np.asarray(normals,np.float64); y=np.asarray(values,np.float64)
    w=np.ones(len(y)) if weights is None else np.asarray(weights,np.float64)
    if len(y)<4: return None
    X=np.column_stack((np.ones(len(y)),n)); W=np.sqrt(w)[:,None]
    sol,*_=np.linalg.lstsq(X*W,y*W[:,0],rcond=None)
    c0,v=sol[0],sol[1:]; strength=float(np.linalg.norm(v))
    if c0<=1e-6 or strength<1e-6: return None
    pred=X@sol; r2=1-np.sum(w*(y-pred)**2)/max(np.sum(w*(y-np.average(y,weights=w))**2),1e-12)
    d=v/strength
    if d[2]<math.sin(math.radians(5)):  # keep the key light above the horizon
        d=np.array((d[0],d[1],0.)); d=d/max(np.linalg.norm(d),1e-9)*math.cos(math.radians(5)); d[2]=math.sin(math.radians(5))
    return dict(direction=[float(x) for x in d],ratio=strength/c0,ambient=float(c0),r2=float(r2))


def sky_colours(photo,sky):
    m=np.asarray(sky,bool)
    if m.mean()<.01: return None
    ys=np.nonzero(m)[0]; top=m&(np.arange(m.shape[0])[:,None]<np.percentile(ys,35))
    bottom=m&(np.arange(m.shape[0])[:,None]>np.percentile(ys,65))
    p=np.asarray(photo,np.float32)[...,:3]
    return dict(zenith=[float(x) for x in p[top].mean(0)] if top.any() else [float(x) for x in p[m].mean(0)],
                horizon=[float(x) for x in p[bottom].mean(0)] if bottom.any() else [float(x) for x in p[m].mean(0)])


def light_sources(photo,depth,threshold=.92,contrast=1.5,max_count=6):
    """Small clipped blobs much brighter than their surroundings = practical lights.

    A bright wall is not a lamp: the blob must stand out from its ring by `contrast`.
    """
    p=np.asarray(photo,np.float32)[...,:3]; L=U.luminance(p); h,w=L.shape
    hot=L>threshold
    if not hot.any() or hot.mean()>.08: return []
    lab=U.label(hot); out=[]
    counts=np.bincount(lab[lab>=0].ravel())
    for i in np.argsort(counts)[::-1][:max_count]:
        m=lab==i; n=int(m.sum())
        if n<3 or n>.02*h*w: continue
        ys,xs=np.nonzero(m); ring=U.dilate(m,max(3,int(math.sqrt(n))))&~U.dilate(m,1)
        if not ring.any() or L[m].mean()<contrast*np.median(L[ring]): continue
        d=np.asarray(depth)[ring]; d=d[d>0]
        out.append(dict(x=float(xs.mean()+.5)/w,y=float(ys.mean()+.5)/h,pixels=n,
            colour=[float(x) for x in p[m].mean(0)],depth=float(np.median(d)) if len(d) else 0.))
    return out


# ---------------------------------------------------------------- atmosphere & lens

def min_filter(a,r):
    out=np.asarray(a,np.float32).copy(); h,w=out.shape
    p=np.pad(out,((r,r),(0,0)),mode='edge'); out=np.min([p[i:i+h] for i in range(2*r+1)],0)
    p=np.pad(out,((0,0),(r,r)),mode='edge'); return np.min([p[:,i:i+w] for i in range(2*r+1)],0)


def fit_haze(photo,distance,valid,sky=None,min_range=6.):
    """Koschmieder model I = J·t + A·(1−t), t = exp(−β·d), from the dark channel.

    Per distance bin, the low percentile of the dark channel ≈ a·(1−exp(−β·d));
    a and β are fitted jointly. β is reported 0 when the photo gives no reliable
    evidence (short depth range, poor fit), which is the usual interior case.
    """
    p=np.asarray(photo,np.float32)[...,:3]; d=np.asarray(distance,np.float32); ok=np.asarray(valid,bool)&(d>0)
    dark=min_filter(p.min(-1),3)
    if sky is not None and np.asarray(sky).mean()>.01: A=np.median(p[np.asarray(sky,bool)],0)
    else:
        k=max(1,int(dark.size*.001)); idx=np.argsort(dark.ravel())[-k:]; A=p.reshape(-1,3)[idx].mean(0)
    direction=np.clip(A,.02,None)/max(float(np.clip(A,.02,None).min()),1e-3)
    none=dict(beta=0.,airlight=[float(x) for x in np.clip(A,.05,1.)],confidence=0.)
    if ok.sum()<200: return none
    dv=d[ok]; lo,hi=np.percentile(dv,(5,95))
    if hi-lo<min_range: return none
    edges=np.quantile(dv,np.linspace(0,1,13)); X=[];Y=[]
    for a,b in zip(edges[:-1],edges[1:]):
        sel=ok&(d>=a)&(d<=b)
        if sel.sum()<20: continue
        X.append(float(np.median(d[sel]))); Y.append(float(np.percentile(dark[sel],5)))
    X=np.array(X); Y=np.array(Y)
    if len(X)<5 or np.std(Y)<1e-4: return none
    best=None
    for beta in np.geomspace(5e-4,.25,90):
        f=1-np.exp(-beta*X); a=float(Y@f/max(f@f,1e-12)); res=float(((Y-a*f)**2).sum())
        if best is None or res<best[0]: best=(res,beta,a)
    res,beta,a=best
    r2=1-res/max(float(((Y-Y.mean())**2).sum()),1e-12)
    if r2<.6 or not (.05<=a<=1.2) or np.corrcoef(X,Y)[0,1]<.6: return dict(none,confidence=float(max(r2,0)))
    return dict(beta=float(np.clip(beta,0,.2)),airlight=[float(x) for x in np.clip(direction*a,.02,1.5)],confidence=float(r2))


def fit_glow(photo,threshold=.8):
    """Halo energy around highlights → bloom threshold, strength and radius."""
    p=np.asarray(photo,np.float32)[...,:3]; L=U.luminance(p); h,w=L.shape
    hot=L>threshold
    if hot.mean()<.0003 or hot.mean()>.2: return dict(threshold=threshold,strength=0.,radius=.01)
    R=max(4,int(.06*max(h,w)))
    dist=U.distance_to(hot,R)
    far=(dist>=R*.75)&(dist<R); bg=float(np.median(L[far])) if far.any() else float(np.median(L))
    radii=np.arange(1,int(R*.75)); excess=[]
    for r in radii:
        sel=dist==r; excess.append(max(float(L[sel].mean())-bg,0) if sel.any() else 0)
    excess=np.array(excess); peak=float(L[hot].mean())-bg
    if peak<=1e-4 or excess.max()<=1e-4: return dict(threshold=threshold,strength=0.,radius=.01)
    pos=excess>excess.max()*.05
    rr=radii[pos]; ee=np.log(excess[pos])
    sigma=float(-1/np.polyfit(rr,ee,1)[0]) if len(rr)>=3 and np.polyfit(rr,ee,1)[0]<0 else R/4
    strength=float(np.clip(excess[0]/peak,0,1))
    return dict(threshold=threshold,strength=strength,radius=float(np.clip(sigma/max(h,w),.002,.08)))


def noise_sigma(srgb):
    """Immerkær fast noise estimate on the luminance, in sRGB units."""
    g=U.luminance(np.asarray(srgb,np.float32)[...,:3])
    k=(g[:-2,:-2]-2*g[:-2,1:-1]+g[:-2,2:]-2*g[1:-1,:-2]+4*g[1:-1,1:-1]-2*g[1:-1,2:]+g[2:,:-2]-2*g[2:,1:-1]+g[2:,2:])
    return float(math.sqrt(math.pi/2)*np.abs(k).mean()/6)


def radial(h,w):
    y,x=np.mgrid[:h,:w]; return np.hypot((x+.5)/w-.5,(y+.5)/h-.5)/math.hypot(.5,.5)


def fit_vignette(ratio,valid):
    """ratio ≈ c·(1 − k·r²) with r the normalised distance to the image centre."""
    r=radial(*ratio.shape)[valid]**2; y=np.asarray(ratio)[valid]
    if len(y)<100: return 0.
    A=np.column_stack((np.ones_like(r),r)); (c,b),*_=np.linalg.lstsq(A,y,rcond=None)
    return float(np.clip(-b/max(c,1e-6),0,.6))


def fit_grade(render,photo,mask,blur_px=4.,strength=.85,points=24):
    """Global grade: bounded colour matrix + per-channel histogram matching.

    The matrix is fitted on blurred images (misalignment-tolerant) with near-diagonal
    gains; tone curves match the photo's per-channel distribution instead of a
    pixel regression, which would pull contrast towards the mean (washed-out look).
    """
    r=np.asarray(render,np.float32)[...,:3]; p=np.asarray(photo,np.float32)[...,:3]; m=np.asarray(mask,bool)
    m=m&(U.luminance(p)<.92)&(U.luminance(r)>1e-4)
    identity=dict(matrix=np.eye(3).tolist(),offset=[0.,0.,0.],curves=None)
    if m.sum()<200: return identity
    rb=U.blur(r,blur_px); pb=U.blur(p,blur_px)
    X=rb[m].astype(np.float64); Y=pb[m].astype(np.float64)
    M=np.eye(3)
    for c in range(3):
        # Ridge towards identity: diagonal gain plus small cross-talk.
        lam=np.array((.5,.5,.5))*len(Y)*float(np.mean(X**2)); lam[c]*=.02
        A=X.T@X+np.diag(lam); b=X.T@Y[:,c]+lam*np.eye(3)[c]
        row=np.linalg.solve(A,b)
        row[c]=np.clip(row[c],.5,2.); off=np.delete(np.arange(3),c); row[off]=np.clip(row[off],-.12,.12)
        M[c]=row
    # One smooth tone curve on luminance, applied as a ratio: no per-channel kinks,
    # hence no coloured iso-luminance rings on smooth gradients.
    pred=U.linear_to_srgb(U.luminance(np.clip(r[m]@M.T,0,None))); target=U.linear_to_srgb(U.luminance(p[m]))
    qs=np.linspace(0,1,points+1)
    xs=np.maximum.accumulate(np.quantile(pred,qs)); ys=np.quantile(target,qs)
    keep=np.concatenate(([True],np.diff(xs)>1e-3)); xs=xs[keep]; ys=ys[keep]
    if len(ys)>4: ys=np.convolve(np.pad(ys,2,mode='edge'),np.ones(5)/5,'valid')
    xs=np.concatenate(([0.],xs,[1.])); ys=np.concatenate(([0.],ys,[max(ys[-1],min(1.,ys[-1]+1-xs[-1]))]))
    # Bounded slopes: a flat segment would posterize smooth gradients into contour rings.
    target=ys.copy(); slope=np.clip(np.diff(ys)/np.maximum(np.diff(xs),1e-6),.6,1.8)
    ys=np.concatenate(([0.],np.cumsum(slope*np.diff(xs)))); mid=len(xs)//2
    ys=np.maximum.accumulate(np.clip(ys+target[mid]-ys[mid],0,1))  # anchored on the median tone
    ys=strength*ys+(1-strength)*xs
    return dict(matrix=M.tolist(),offset=[0.,0.,0.],tone=[[float(x) for x in xs],[float(y) for y in ys]],curves=None)


def bloom(x,threshold,strength,radius):
    if strength<=0: return x
    h,w=x.shape[:2]; hi=np.maximum(x-threshold,0); glow=np.zeros_like(x)
    for k,f in ((.5,.5),(1.,.3),(2.,.2)):
        glow+=f*U.blur(hi,max(.5,radius*max(h,w)*k))
    return x+strength*glow


def apply_look(render,depth,look,seed=11):
    """Scene-linear render → display sRGB with exposure, haze, bloom, vignette, grade, grain."""
    x=np.asarray(render,np.float32)[...,:3].copy(); h,w=x.shape[:2]
    x*=2**look.get('exposure',0.)
    beta=look.get('haze_beta',0.)
    if beta>0 and depth is not None:
        d=np.asarray(depth,np.float32)
        # Pixels without modelled depth show the photo plate / sky, which already carry the haze.
        t=np.where(d>0,np.exp(-beta*np.maximum(d,0)),1.)[...,None]; A=np.asarray(look.get('airlight',(.7,.75,.8)),np.float32)
        x=x*t+A*(1-t)*look.get('airlight_gain',1.)
    x=bloom(x,look.get('glow_threshold',.8),look.get('glow_strength',0.),look.get('glow_radius',.01))
    k=look.get('vignette',0.)
    if k>0: x*=(1-k*radial(h,w)**2)[...,None]
    g=look.get('grade')
    if g:
        M=np.asarray(g['matrix'],np.float32); x=np.clip(x@M.T+np.asarray(g['offset'],np.float32),0,None)
    s=U.linear_to_srgb(x)
    if g and g.get('tone'):
        xs,ys=g['tone']; L=U.linear_to_srgb(U.luminance(x)); k=np.interp(L,xs,ys)/np.maximum(L,1e-4)
        s=U.linear_to_srgb(U.srgb_to_linear(np.clip(s,0,1))*U.srgb_to_linear(np.clip(L*k,0,1))[...,None]/np.maximum(U.srgb_to_linear(L),1e-6)[...,None])
    if g and g.get('curves'):
        for c,(xs,ys) in enumerate(g['curves']): s[...,c]=np.interp(s[...,c],xs,ys)
    sigma=look.get('grain',0.)
    if sigma>0: s=s+np.random.default_rng(seed).normal(0,sigma,s.shape[:2])[...,None]
    return np.clip(s,0,1).astype(np.float32)


def fit_look(render,depth,photo,mask,base=None):
    """Fit exposure, vignette and grade of a render onto the photo (all linear).

    Haze, glow and grain come from the photo analysis (base); this only measures
    what is left once those are applied, so the grade stays a global correction.
    """
    look=dict(exposure=0.,haze_beta=0.,airlight=[.7,.75,.8],glow_threshold=.8,glow_strength=0.,glow_radius=.01,vignette=0.,grade=None,grain=0.)
    look.update(base or {}); look['grade']=None; look['vignette']=0.; look['exposure']=0.
    p=np.asarray(photo,np.float32)[...,:3]; m=np.asarray(mask,bool)
    def lum_ratio(img):
        lr=U.luminance(U.srgb_to_linear(img)); lp=U.luminance(p); ok=m&(lr>1e-4)&(lp>1e-4)&(lp<.9)
        return lp,lr,ok
    lp,lr,ok=lum_ratio(apply_look(render,depth,look))
    if ok.sum()>100: look['exposure']=float(np.clip(math.log2(np.median(lp[ok]/lr[ok])),-8,8))
    lp,lr,ok=lum_ratio(apply_look(render,depth,look))
    if ok.sum()>100:
        look['vignette']=fit_vignette(U.blur(np.where(ok,lp/np.maximum(lr,1e-4),1),3),ok)
        if look['vignette']>0:
            lp,lr,ok=lum_ratio(apply_look(render,depth,look))
            if ok.sum()>100: look['exposure']+=float(np.clip(math.log2(np.median(lp[ok]/lr[ok])),-2,2))
    pre=U.srgb_to_linear(apply_look(render,depth,dict(look,grain=0.)))
    look['grade']=fit_grade(pre,p,m)
    return look


def nnls(A,b,iterations=3000):
    """Non-negative least squares by projected gradient (small problems)."""
    A=np.asarray(A,np.float64); b=np.asarray(b,np.float64)
    AtA=A.T@A; Atb=A.T@b; L=max(np.linalg.eigvalsh(AtA).max(),1e-12)
    x=np.maximum(np.linalg.lstsq(A,b,rcond=None)[0],0)
    for _ in range(iterations):
        x=np.maximum(x-(AtA@x-Atb)/L,0)
    return x


def fit_lights(basis,baseline,target,mask,colour_range=(.6,1.4)):
    """Light intensities and tints from one render per candidate light.

    Rendering is linear in light power: photo ≈ baseline + Σ w_k·basis_k. Weights
    come from luminance NNLS; each light's tint from per-channel ratios, bounded.
    Returns weights (K,), colours (K,3) and the relative residual.
    """
    B=np.asarray(basis,np.float32)-np.asarray(baseline,np.float32)[None]
    m=np.asarray(mask,bool); t=np.asarray(target,np.float32)[m]
    X=np.maximum(B[:,m],0)  # (K,N,3)
    if not len(X) or m.sum()<50: return np.zeros(len(B)),np.ones((len(B),3)),1.
    lum=lambda a:a[...,0]*.2126+a[...,1]*.7152+a[...,2]*.0722
    w=nnls(lum(X).T,lum(t))
    colours=np.ones((len(B),3))
    for c in range(3):
        wc=nnls(X[...,c].T,t[:,c])
        colours[:,c]=np.where(w>1e-9,np.clip(wc/np.maximum(w,1e-12),*colour_range),1)
    colours/=np.maximum(colours.max(1,keepdims=True),1e-9)
    w=w/np.maximum(lum(colours),1e-3)  # a tint must not change the fitted luminance
    pred=np.einsum('k,knc->nc',w,X*colours[:,None,:])
    residual=float(np.linalg.norm(pred-t)/max(np.linalg.norm(t),1e-9))
    return w,colours,residual
