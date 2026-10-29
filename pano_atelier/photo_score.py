"""Fidelity score /20 between the reference photo and the final render. Pure numpy.

The score is an objective for iterations, not a perceptual truth: human ratings
(0–20) are logged next to the sub-scores so the weights can be refitted.
"""
import json
import math
import numpy as np
from . import photo_util as U

WEIGHTS={'structure':.30,'colour':.25,'edges':.15,'detail':.15,'light':.15}
LABELS={'structure':'Structure (SSIM)','colour':'Couleur (ΔE)','edges':'Contours','detail':'Détail / grain','light':'Lumière'}


def prepare(image,size=384):
    a=np.clip(np.asarray(image,np.float32)[...,:3],0,1); h,w=a.shape[:2]
    if max(h,w)>size: a=U.resize(a,max(8,round(w*size/max(h,w))),max(8,round(h*size/max(h,w))))
    return a


def ssim(x,y,sigma=1.5):
    C1,C2=.01**2,.03**2
    mx=U.blur(x,sigma); my=U.blur(y,sigma)
    sxx=U.blur(x*x,sigma)-mx*mx; syy=U.blur(y*y,sigma)-my*my; sxy=U.blur(x*y,sigma)-mx*my
    return ((2*mx*my+C1)*(2*sxy+C2))/((mx*mx+my*my+C1)*(sxx+syy+C2))


def multiscale_ssim(x,y):
    total=0.
    for weight in (.4,.35,.25):
        total+=weight*float(np.clip(ssim(x,y),0,1).mean())
        if min(x.shape)<32: break
        x=U.resize(x,x.shape[1]//2,x.shape[0]//2); y=U.resize(y,y.shape[1]//2,y.shape[0]//2)
    return total


def lab(srgb):
    c=U.srgb_to_linear(srgb)
    M=np.array(((.4124,.3576,.1805),(.2126,.7152,.0722),(.0193,.1192,.9505)),np.float32)
    xyz=c@M.T/np.array((.95047,1.,1.08883),np.float32)
    f=np.where(xyz>.008856,np.cbrt(np.maximum(xyz,0)),7.787*xyz+16/116)
    return np.stack((116*f[...,1]-16,500*(f[...,0]-f[...,1]),200*(f[...,1]-f[...,2])),-1)


def delta_e(a,b):
    return np.linalg.norm(lab(U.blur(a,1))-lab(U.blur(b,1)),axis=-1)


def edges(gray,reference=None,q=85):
    g=U.gradient_magnitude(U.blur(gray,1))
    t=np.percentile(g if reference is None else reference,q)
    return g>max(t,1e-4),g


def edge_f1(x,y,tolerance=2):
    ey,gy=edges(y); ex,_=edges(x,reference=gy)
    if not ey.any(): return 1. if not ex.any() else 0.
    p=(ex&U.dilate(ey,tolerance)).sum()/max(ex.sum(),1); r=(ey&U.dilate(ex,tolerance)).sum()/max(ey.sum(),1)
    return float(2*p*r/max(p+r,1e-9))


def detail_similarity(x,y,tiles=12):
    hx=x-U.blur(x,1.5); hy=y-U.blur(y,1.5); h,w=x.shape; logs=[]
    for i in range(tiles):
        for j in range(tiles):
            sl=(slice(i*h//tiles,(i+1)*h//tiles),slice(j*w//tiles,(j+1)*w//tiles))
            logs.append(abs(math.log((hx[sl].std()+.004)/(hy[sl].std()+.004))))
    return float(math.exp(-np.mean(logs)))


def light_similarity(x,y):
    s=max(2.,.04*max(x.shape)); lx=U.blur(x,s).ravel(); ly=U.blur(y,s).ravel()
    r=float(np.corrcoef(lx,ly)[0,1]) if lx.std()>1e-6 and ly.std()>1e-6 else (1. if abs(lx.mean()-ly.mean())<.02 else 0.)
    hx,_=np.histogram(x,64,(0,1)); hy,_=np.histogram(y,64,(0,1))
    emd=float(np.abs(np.cumsum(hx/max(hx.sum(),1))-np.cumsum(hy/max(hy.sum(),1))).mean())
    return .5*max(r,0)+.5*(1-min(1,4*emd))


def score(photo,render,weights=None):
    """Both images display-referred sRGB in [0,1]. Returns total /20 and sub-scores in [0,1]."""
    p=prepare(photo); r=prepare(render)
    if r.shape!=p.shape: r=U.resize(r,p.shape[1],p.shape[0])
    lp=U.luminance(p); lr=U.luminance(r)
    de=delta_e(r,p)
    subs={'structure':multiscale_ssim(lr,lp),'colour':float(math.exp(-float(de.mean())/12)),
          'edges':edge_f1(lr,lp),'detail':detail_similarity(lr,lp),'light':light_similarity(lr,lp)}
    wts=dict(WEIGHTS if weights is None else weights); total_w=sum(wts.values())
    total=20*sum(wts[k]*subs[k] for k in subs)/max(total_w,1e-9)
    return dict(total=round(float(total),2),subscores={k:round(v,4) for k,v in subs.items()},
                weights=wts,mean_delta_e=round(float(de.mean()),2))


def combine(metric,judge=None,judge_weight=.3):
    if judge is None: return metric
    return round((1-judge_weight)*metric+judge_weight*float(np.clip(judge,0,20)),2)


def heatmap(photo,render):
    """Side by side: photo | render | ΔE map (dark = identical, yellow ≥ 20)."""
    p=prepare(photo,640); r=U.resize(prepare(render,640),p.shape[1],p.shape[0])
    d=np.clip(delta_e(r,p)/20,0,1)
    heat=np.stack((np.clip(d*2,0,1),np.clip(d*2-.6,0,1)*.9+d*.1,np.clip(.35-d,0,.35)),-1)
    gap=np.ones((p.shape[0],6,3),np.float32)
    return np.concatenate((p,gap,r,gap,heat),1)


def fit_weights(records,prior=WEIGHTS,strength=10.):
    """Refit sub-score weights from human ratings (non-negative least squares).

    records: [{'subscores': {...}, 'human': 0..20}]. With few ratings the result
    stays close to the prior weights (shrinkage by count/(count+strength)).
    """
    keys=list(prior); rows=[r for r in records if isinstance(r.get('human'),(int,float)) and all(k in r.get('subscores',{}) for k in keys)]
    if not rows: return dict(prior)
    S=np.array([[r['subscores'][k] for k in keys] for r in rows],np.float64); y=np.array([r['human']/20 for r in rows])
    w=np.array([prior[k] for k in keys],np.float64)
    lr=1/max(np.linalg.norm(S,2)**2,1e-9)
    for _ in range(2000):  # projected gradient NNLS
        w=np.maximum(w-lr*S.T@(S@w-y),0)
    if w.sum()<=1e-9: return dict(prior)
    w=w/w.sum(); alpha=len(rows)/(len(rows)+strength)
    mixed={k:float((1-alpha)*prior[k]+alpha*w[i]) for i,k in enumerate(keys)}
    s=sum(mixed.values()); return {k:v/s for k,v in mixed.items()}


def read_ratings(path):
    out=[]
    try:
        with open(path,encoding='utf-8') as f:
            for line in f:
                line=line.strip()
                if line:
                    try: out.append(json.loads(line))
                    except ValueError: pass
    except OSError: pass
    return out
