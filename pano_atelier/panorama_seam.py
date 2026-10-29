"""Lossless wrap preparation and explicitly masked seam reintegration.

No image service is invoked here. Arrays are top-down H x W x C.
The original outside the authorized band remains byte-identical.
"""
import numpy as np

def prepare(source, width_fraction=.20, feather_fraction=.025):
    a=np.asarray(source)
    if a.ndim!=3 or a.shape[1]<8:raise ValueError('Image RGB/RGBA requise')
    if not 0<width_fraction<.5 or not 0<=feather_fraction<width_fraction/2:raise ValueError('Largeur de masque invalide')
    w=a.shape[1];shift=w//2;center=shift
    distance=np.abs(np.arange(w,dtype=float)-center)
    half=w*width_fraction/2;feather=max(1,w*feather_fraction)
    mask=np.clip((half-distance)/feather,0,1)
    return np.roll(a,shift,axis=1),np.broadcast_to(mask[None,:],a.shape[:2]).copy(),shift

def reintegrate(source, edited_rolled, mask, shift):
    a=np.asarray(source);b=np.asarray(edited_rolled);m=np.asarray(mask,dtype=float)
    if b.shape!=a.shape or m.shape!=a.shape[:2]:raise ValueError('Dimensions source/correction/masque incompatibles')
    if not np.isfinite(m).all() or m.min()<0 or m.max()>1:raise ValueError('Masque hors [0,1]')
    rolled=np.roll(a,shift,axis=1)
    out=rolled.astype(float)*(1-m[:,:,None])+b.astype(float)*m[:,:,None]
    if np.issubdtype(a.dtype,np.integer):out=np.rint(out)
    return np.roll(out.astype(a.dtype),-shift,axis=1)
