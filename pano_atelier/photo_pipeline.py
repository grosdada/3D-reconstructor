"""Photo(s) → editable Blender scene in seven phases, as an incremental job.

The generator yields status strings or Futures (numpy / network work runs in a
worker thread); every bpy call stays on the main thread. Each phase is timed and
recorded in manifest.json beside its artifacts. The reference camera reproduces
the photo; modules, materials and lights stay editable and physically lit.
"""
import hashlib
import json
import math
import subprocess
import time
from pathlib import Path
import numpy as np
import bpy
from mathutils import Matrix
from . import engine, providers, photo_geometry as G, photo_texture as T, photo_look as LOOK, photo_score as SCORE, photo_scene as SC, photo_util as U
from .pipeline import POOL

PHASES=(('camera','Camera mapping'),('model','Modélisation'),('texture','Texturing multivues'),('material','Matériaux'),
        ('procedural','Procédural'),('light','Lumière & effets'),('score','Note /20'))

QUALITY={
    'DRAFT':dict(analysis=192,density=128,atlas_max=512,view_size=384,samples=16,long=640,planner_samples=1200,rough=128,preview=320),
    'STANDARD':dict(analysis=384,density=256,atlas_max=1024,view_size=640,samples=48,long=1024,planner_samples=2500,rough=200,preview=480),
    'FINAL':dict(analysis=512,density=384,atlas_max=2048,view_size=1024,samples=128,long=1600,planner_samples=4000,rough=256,preview=640)}

ALBEDO_PROMPT=('Convert this photo into its albedo / base colour map: identical framing, perspective and edges, every object in place. '
    'Remove cast shadows, shading, ambient occlusion, reflections and highlights; flat even light. No new objects, no text.')
VIEW_PROMPT=('Render of a 3D scene: the masked areas have no texture yet. Paint only the masked areas as flat albedo (base colour) of the '
    'surfaces they cover, continuing the materials of the unmasked areas and of the reference photo. No shadows, lighting or reflections, '
    'no new objects, no text; keep perspective and edges.')


def sha256(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(1<<20),b''): h.update(block)
    return h.hexdigest()


def load_depth(path):
    if str(path).lower().endswith('.npy'):
        d=np.load(str(path),allow_pickle=False)
        if d.ndim!=2: raise ValueError('La profondeur NPY doit être un tableau H x W.')
        return d.astype(np.float32)
    return engine.load_pixels(path,True)[...,0]


def infer_photos(python,photos,output,fov):
    if not python or not Path(python).is_file():
        raise ValueError('Configurer un Python avec MoGe installé, ou fournir une profondeur.')
    command=[python,str(Path(__file__).with_name('photo_worker.py')),'--images',*map(str,photos),'--output',str(output),'--fov',str(fov)]
    done=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=3600,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if done.returncode:
        Path(output).mkdir(parents=True,exist_ok=True); (Path(output)/'photo-worker-error.txt').write_bytes(done.stdout[-32000:])
        raise RuntimeError('Le worker de profondeur a échoué. Consulter photo-worker-error.txt.')
    return json.loads((Path(output)/'results.json').read_text())


def letterbox(image,size):
    """Fit an image into a provider canvas without stretching; returns canvas and crop box."""
    W,H=size; h,w=image.shape[:2]; s=min(W/w,H/h); nw,nh=max(1,round(w*s)),max(1,round(h*s))
    top=(H-nh)//2; left=(W-nw)//2
    canvas=np.full((H,W,image.shape[2]),.1 if image.shape[2]==3 else 1.,np.float32)
    canvas[top:top+nh,left:left+nw]=U.resize(image,nw,nh)
    return canvas,(top,left,nh,nw)


def unletterbox(result,box,w,h):
    top,left,nh,nw=box
    return U.resize(result[top:top+nh,left:left+nw],w,h)


class Manifest:
    def __init__(self,folder,config):
        self.path=Path(folder)/'manifest.json'
        safe={k:v for k,v in config.items() if k not in ('key',)}
        self.data=dict(version='0.7.0',created=time.strftime('%Y-%m-%d %H:%M:%S'),config=safe,phases={},requests=0,
            limitations=['Proposition automatique depuis une image : échelle, dos des objets et hors champ sont estimés.',
                         'Les albédos sont des estimations ; la note /20 est un objectif d’itération, pas une validation humaine.'])
        self.save()
    def save(self):
        self.path.write_text(json.dumps(self.data,indent=2,ensure_ascii=False,default=lambda o:o.tolist() if hasattr(o,'tolist') else str(o)),encoding='utf-8')
    def set(self,**kw):
        self.data.update(kw); self.save()


def run(config,folder,progress=None):
    folder=Path(folder); folder.mkdir(parents=True,exist_ok=True)
    progress=progress or (lambda event:None)
    q=dict(QUALITY[config.get('quality','STANDARD')]); q.update(config.get('overrides') or {})
    man=Manifest(folder,config); state={'calls':0}
    budget=lambda: config.get('backend')=='API' and state['calls']<config.get('max_requests',12)
    key=lambda: providers.get_key(config.get('endpoint',''))
    current={'phase':None,'start':0.}
    def begin(key_):
        current.update(phase=key_,start=time.time())
        man.data['phases'][key_]={'state':'running'}; man.save(); progress({'phase':key_,'state':'running'})
    def end(note='',**extra):
        k=current['phase']; seconds=round(time.time()-current['start'],2)
        man.data['phases'][k]=dict(state='done',seconds=seconds,note=note,**extra); man.save()
        progress({'phase':k,'state':'done','seconds':seconds,'note':note}); current['phase']=None
    def api(fn,*args):
        state['calls']+=1; man.set(requests=state['calls'])
        return POOL.submit(fn,*args)
    try:
        photos=[Path(p) for p in config['photos'] if str(p).strip()]
        if not photos: raise ValueError('Ajouter au moins une photo.')
        for p in photos:
            if not p.is_file(): raise FileNotFoundError(p)
        inputs=[]
        for p in photos:
            rgba=engine.load_pixels(p); inputs.append(dict(path=str(p),sha256=sha256(p),width=int(rgba.shape[1]),height=int(rgba.shape[0])))
        man.set(inputs=inputs)
        refs=[]
        for i,p in enumerate(photos[1:4]):  # PNG copies: extra photos guide materials in generated views
            im=engine.load_pixels(p)[...,:3]; s2=min(1.,1024/max(im.shape[:2]))
            engine.write_image(folder/'inputs'/f'photo-{i+2:02d}.png',U.resize(im,max(8,round(im.shape[1]*s2)),max(8,round(im.shape[0]*s2))))
            refs.append(str(folder/'inputs'/f'photo-{i+2:02d}.png'))
        # ------------------------------------------------ 1 · camera mapping
        begin('camera'); yield 'Lecture de la photo de référence…'
        src=engine.load_pixels(photos[0])[...,:3]; H0,W0=src.shape[:2]; s=min(1.,q['long']/max(W0,H0))
        W,H=max(16,round(W0*s)),max(16,round(H0*s)); photo=U.resize(src,W,H); photo_srgb=U.linear_to_srgb(photo)
        analysis=None
        if budget() and config.get('vision',True):
            yield 'Lecture de la scène par le modèle de vision…'
            try:
                analysis=yield api(providers.analyze_scene,config['endpoint'],key(),config['vision_model'],[str(p) for p in photos[:4]])
                (folder/'analysis.json').write_text(json.dumps(analysis,indent=2,ensure_ascii=False),encoding='utf-8')
            except Exception as e: man.set(analysis_error=type(e).__name__)
        elements=analysis['elements'] if analysis else []
        fov=float(config.get('fov',60.)); poses={}; extra={}
        if config.get('depth'):
            depth=load_depth(config['depth']); depth_source='fichier'
        elif config.get('moge_python'):
            yield 'Profondeur et focale (MoGe)…'
            result=yield POOL.submit(infer_photos,config['moge_python'],photos,folder/'depth',0 if config.get('estimate_fov',True) else fov)
            depth=np.load(result['photos'][0]['depth']); fov=float(result['photos'][0]['fov']); depth_source='MoGe'
            poses={int(k):v for k,v in result.get('poses',{}).items()}
            extra={i:result['photos'][i] for i in poses}
        else:
            boxes=[e['box'] for e in elements if e['kind'] in ('furniture','object','vehicle','vegetation')]
            depth=G.prior_depth(H,W,fov,boxes=boxes); depth_source='diorama (sol + fond), sans modèle de profondeur'
        depth=U.nearest(depth,W,H).astype(np.float32); valid=depth>0
        yield 'Analyse de la spatialité (gravité, plans, volumes)…'
        structure=yield POOL.submit(G.analyse,depth,fov,valid,elements,q['analysis'])
        cam_m=structure['camera']
        scene=SC.new_scene('Photo 3D · '+photos[0].stem[:40],W,H); scene['pa_photo_run']=str(folder)
        progress({'scene':scene})
        root=SC.collection(scene,'Photo 3D')
        ref=SC.camera(scene,'Caméra photo',cam_m,fov,root,W,H); scene.camera=ref
        plate=SC.image('PA Photo · référence',photo,folder/'inputs'/'reference.png')
        rough_coll=SC.collection(scene,'1 · Camera mapping (brut)',root)
        yield 'Camera mapping brut…'
        SC.rough(scene,plate,depth,fov,cam_m,rough_coll,q['rough'])
        pw,ph=preview=(q['preview'],max(8,round(q['preview']*H/W)))
        img=SC.render(scene,ref,folder/'1-camera-mapping.exr',pw,ph,samples=1,denoise=False)
        rough_srgb=U.linear_to_srgb(img[...,:3]); engine.write_image(folder/'1-camera-mapping.png',img)
        rough_score=SCORE.score(photo_srgb,rough_srgb)
        end(f'profondeur : {depth_source}, champ {fov:.1f}°',depth=depth_source,fov=fov,reference_score=rough_score['total'])
        # ------------------------------------------------ 2 · modelling
        begin('model'); yield 'Modélisation des volumes…'
        model=SC.collection(scene,'2 · Modèle',root)
        objects=SC.build_modules(scene,structure,model)
        rough_coll.hide_render=True; rough_coll.hide_viewport=True
        albedo=T.delight(photo)
        ah,aw=structure['owner'].shape; small=U.resize(albedo,aw,ah)
        colours={}  # keyed by the real object name (Blender may suffix duplicates: « Mur 01.001 »)
        for ob in objects.values():
            sel=structure['owner']==ob['pa_photo_index']
            colours[ob.name]=np.median(small[sel],0) if sel.sum()>8 else np.median(small.reshape(-1,3),0)
            if ob['pa_photo_kind'] not in ('backdrop',):
                SC.assign(ob,SC.material('PA argile · '+ob.name,'glass' if ob['pa_photo_kind']=='glass' else 'paint',None,colours[ob.name]))
        textured=[o for o in objects.values() if o['pa_photo_kind'] in ('wall','floor','ceiling','object','frame')]
        backdrop=[o for o in objects.values() if o['pa_photo_kind']=='backdrop']
        glass=[o for o in objects.values() if o['pa_photo_kind']=='glass']
        yield 'Dépliage UV des modules…'
        SC.unwrap(scene,textured)
        SC.world(scene,ambient=(.6,.6,.6),strength=1.)
        img=SC.render(scene,ref,folder/'2-modele-argile.exr',pw,ph,samples=12)
        engine.write_image(folder/'2-modele-argile.png',img)
        rep=structure['report']
        (folder/'structure.json').write_text(json.dumps(dict(report=rep,modules=[{k:v for k,v in m.items() if k not in ('vertices','faces')}|
            {'vertices':len(m['vertices']),'faces':len(m['faces'])} for m in structure['modules']]),indent=2,ensure_ascii=False,default=lambda o:o.tolist()),encoding='utf-8')
        end(f"{rep['walls']} murs, {rep['openings']} ouvertures, {rep['objects']} objets",**{k:rep[k] for k in ('walls','openings','objects','gravity','camera_height')})
        # ------------------------------------------------ 3 · texturing
        begin('texture'); tex_dir=folder/'textures'; view_dir=folder/'vues'
        guide=None
        if budget() and config.get('api_albedo',True):
            yield 'Albédo de la photo via le modèle image…'
            try:
                size=providers.edit_size(W,H); canvas,box=letterbox(photo_srgb,size)
                engine.write_image(view_dir/'albedo-input.png',U.srgb_to_linear(canvas))
                mask=np.zeros((size[1],size[0],4),np.float32); engine.write_image(view_dir/'albedo-mask.png',mask,True)
                out=yield api(providers.edit_images,config['endpoint'],key(),config['image_model'],view_dir/'albedo-input.png',view_dir/'albedo-mask.png',[],view_dir/'albedo-api.png',ALBEDO_PROMPT,size)
                guide=unletterbox(engine.load_pixels(out)[...,:3],box,W,H)
            except Exception as e: man.set(albedo_api_error=type(e).__name__)
        labels=U.nearest(structure['owner'],W,H)
        albedo=T.delight(photo,guide=guide,labels=labels)
        engine.write_image(view_dir/'photo-albedo.png',albedo)
        occluders=textured+glass
        yield 'Profondeur de la caméra photo…'
        d0=SC.render_depth(scene,ref,view_dir/'photo-depth.exr',W,H,exclude=backdrop+glass)
        # The modelled silhouette is only as sharp as the analysis grid: fade the photo over that error.
        edge_px=max(6,int(round(3*W/aw)))
        views=[dict(name='photo',matrix=cam_m,fov=fov,image=albedo,depth=d0,priority=4.,fade=T.silhouette_fade(d0,edge_px))]
        for i,pose in poses.items():
            p=extra[i]; m=np.asarray(cam_m)@np.asarray(pose['matrix']); w,h=p['width'],p['height']
            cam=SC.camera(scene,'Photo %02d'%(i+1),m,p['fov'],root,w,h)
            dk=SC.render_depth(scene,cam,view_dir/f'photo-{i:02d}-depth.exr',w,h,exclude=backdrop+glass)
            im=U.resize(engine.load_pixels(photos[i])[...,:3],w,h)
            views.append(dict(name='photo %02d'%(i+1),matrix=m,fov=p['fov'],image=T.delight(im),depth=dk,priority=3.,fade=T.silhouette_fade(dk)))
        yield 'Atlas UV par module…'
        atlases={}
        for ob in textured:
            uv,pos,nrm=SC.triangles(scene,ob)
            area=float((np.linalg.norm(np.cross(pos[:,1]-pos[:,0],pos[:,2]-pos[:,0]),axis=1)/2).sum())
            size=int(min(q['atlas_max'],max(64,2**math.ceil(math.log2(max(8.,math.sqrt(area)*q['density']))))))
            P,N,M=yield POOL.submit(T.rasterize,uv,pos,nrm,size)
            atlases[ob.name]=dict(P=P,N=N,M=M,size=size,texel=math.sqrt(area/max(1,M.sum())),colour=None,coverage=None,image=None)
        def blend_all():
            for ob in textured:
                a=atlases[ob.name]
                col,cov,stitch,gains=yield POOL.submit(T.blend,a['P'],a['N'],a['M'],views)
                a.update(colour=T.finish_atlas(col,cov,colours[ob.name]),coverage=cov,stitch=stitch,gains=gains)
                a['image']=SC.replace_image(a['image'],'PA Atlas · '+ob.name,a['colour'],tex_dir/(ob.name+'.png'))
        yield 'Projection de la photo…'
        yield from blend_all()
        # Intelligent camera deployment: greedy coverage gain over candidate views.
        planned=[]
        if config.get('views',6)>len(views) and textured:
            yield 'Placement des caméras de texturing…'
            rng=np.random.default_rng(5)
            Ps,Ns,As,_=SC.samples(scene,textured,q['planner_samples'],rng)
            tree=SC.bvh(scene,occluders)
            vfov=75.; vs=q['view_size']
            photo_q=[T.view_quality(Ps,Ns,v['matrix'],v['fov'],v['image'].shape[1],v['image'].shape[0],
                     _visible(tree,v['matrix'],Ps,Ns,v['fov'],v['image'].shape[1],v['image'].shape[0])) for v in views]
            observed=np.max(photo_q,0) if photo_q else np.zeros(len(Ps))
            targets=T.under_covered_targets(Ps,observed,As)
            cands=[c for c in T.candidate_poses(cam_m,radius=config.get('radius',.6),targets=targets) if SC.free_position(tree,cam_m[:3,3],c[:3,3])]
            Q=np.array(photo_q+[T.view_quality(Ps,Ns,c,vfov,vs,vs,_visible(tree,c,Ps,Ns,vfov,vs,vs)) for c in cands])
            chosen,gains,coverage=T.plan(Q,As,forced=range(len(views)),max_views=config.get('views',6),min_gain=.01)
            planned=[(cands[i-len(views)],g) for i,g in zip(chosen,gains) if i>=len(views)]
            man.set(planner=dict(candidates=len(cands),selected=len(planned),coverage=coverage,gains=gains,photos_coverage=float((As*observed).sum()/As.sum())))
        guide_mats={ob:SC.emission_material('PA guide · '+ob.name,atlases[ob.name]['image']) for ob in textured}
        for k,(m,gain) in enumerate(planned):
            name='Vue texture %02d'%(k+1); cam=SC.camera(scene,name,m,75.,root,q['view_size'],q['view_size'])
            vs=q['view_size']
            yield f'{name} : guide et masque…'
            for ob in textured: guide_mats[ob].node_tree.nodes['Image Texture'].image=atlases[ob.name]['image']
            g=SC.render_with(scene,cam,view_dir/f'vue-{k+1:02d}-guide.exr',vs,vs,guide_mats)
            cover={}
            for ob in textured:
                a=atlases[ob.name]; c=np.clip(a['coverage']*4,0,1)
                a['cover_image']=SC.image('PA couverture · '+ob.name,c,tex_dir/(ob.name+'-couverture.png'),True)
                cover[ob]=SC.emission_material('PA couverture · '+ob.name,a['cover_image'])
            c=SC.render_with(scene,cam,view_dir/f'vue-{k+1:02d}-couverture.exr',vs,vs,cover)
            for mat in cover.values(): bpy.data.materials.remove(mat)
            surface=g[...,3]>.5
            need=surface&(c[...,0]<.5)
            dk=SC.render_depth(scene,cam,view_dir/f'vue-{k+1:02d}-depth.exr',vs,vs,exclude=backdrop+glass)
            if need.mean()<.01:
                man.data.setdefault('views',[]).append(dict(name=name,skipped='déjà couvert')); man.save(); continue
            mask=np.clip(U.blur(U.dilate(need,2).astype(np.float32),1.5),0,1)*surface
            base=g[...,:3]; ids=SC.render_ids(scene,cam,view_dir/f'vue-{k+1:02d}-ids.exr',vs,vs,textured)
            if budget():
                yield f'{name} : génération des textures manquantes (API)…'
                try:
                    size=(1024,1024); canvas,box=letterbox(U.linear_to_srgb(base),size)
                    engine.write_image(view_dir/f'vue-{k+1:02d}-api.png',U.srgb_to_linear(canvas))
                    am=np.ones((size[1],size[0],4),np.float32); mc,_=letterbox(mask[...,None],size); am[...,3]=1-mc[...,0]
                    engine.write_image(view_dir/f'vue-{k+1:02d}-api-mask.png',am,True)
                    out=yield api(providers.edit_images,config['endpoint'],key(),config['image_model'],view_dir/f'vue-{k+1:02d}-api.png',
                        view_dir/f'vue-{k+1:02d}-api-mask.png',[str(folder/'inputs'/'reference.png')]+refs[:2],view_dir/f'vue-{k+1:02d}-genere.png',VIEW_PROMPT,size)
                    generated=unletterbox(engine.load_pixels(out)[...,:3],box,vs,vs); source='API'
                except Exception as e:
                    generated=T.local_inpaint(base,mask,ids); source='local (API : %s)'%type(e).__name__
            else:
                generated=T.local_inpaint(base,mask,ids); source='local'
            out_img=T.compose_masked(base,generated,mask)
            engine.write_image(view_dir/f'vue-{k+1:02d}-albedo.png',out_img); engine.write_image(view_dir/f'vue-{k+1:02d}-masque.png',mask,True)
            views.append(dict(name=name,matrix=np.asarray(cam.matrix_world),fov=75.,image=out_img,depth=dk,priority=1.,fade=T.silhouette_fade(dk),mask=mask))
            man.data.setdefault('views',[]).append(dict(name=name,gain=gain,painted=float(need.mean()),source=source)); man.save()
            yield f'{name} : reprojection…'
            yield from blend_all()
        for mat in guide_mats.values(): bpy.data.materials.remove(mat)
        # Light-emitting regions of the photo (window glare, lamps, backlit screens) are
        # sources, not paint: their observed radiance becomes emission, their albedo dark.
        yield 'Sources lumineuses visibles (émission)…'
        emitters=0
        for ob in textured:
            a=atlases[ob.name]
            rad,cov,_,_=yield POOL.submit(T.blend,a['P'],a['N'],a['M'],[dict(views[0],image=photo)])
            glow_mask=np.clip((U.luminance(rad)-.6)/.3,0,1)*(cov>.05)
            if (glow_mask>.5).sum()<30: continue
            a['emission']=SC.image('PA émission · '+ob.name,rad*glow_mask[...,None],tex_dir/(ob.name+'-emission.png'))
            a['colour']=a['colour']*(1-.9*glow_mask[...,None])
            a['image']=SC.replace_image(a['image'],'PA Atlas · '+ob.name,a['colour'],tex_dir/(ob.name+'.png')); emitters+=1
        for ob in textured:  # stitch masks: share of each view in every texel
            a=atlases[ob.name]
            for k,v in enumerate(views):
                if a['stitch'][k].max()>0: engine.write_image(tex_dir/f"{ob.name}-raccord-{v['name'].replace(' ','-')}.png",a['stitch'][k],True)
        end(f"{len(views)} vues ({len(views)-len(planned)} photo), {len(textured)} atlas, {emitters} sources",views=[v['name'] for v in views],emitters=emitters)
        # ------------------------------------------------ 4 · materials
        begin('material'); yield 'Matériaux physiques…'
        small_photo=U.resize(photo,aw,ah)
        mats={}; report=[]
        pixel_m=2*math.tan(math.radians(fov)/2)/W
        for ob in textured:
            a=atlases[ob.name]; seen=(a['coverage']>.02)
            kind=ob['pa_photo_kind']
            # Statistics on the photo region of the module (a continuous image), not on
            # the atlas whose UV islands fake repetitive patterns; atlas as a fallback.
            region=U.erode(labels==ob['pa_photo_index'],2)
            if region.sum()>400: src,src_mask,texel=albedo,region,float(np.median(depth[region]))*pixel_m
            else: src,src_mask,texel=a['colour'],seen,a['texel']
            split=LOOK.split_materials(src,src_mask,texel,target=a['colour'],target_mask=a['M'])
            stats=split['main'] if split else LOOK.texture_stats(src,src_mask,texel)
            family=LOOK.classify(stats,kind,ob.get('pa_photo_hint'))
            trim=None
            if split:  # e.g. plaster panel with brass trims: one atlas, two physical materials
                trim_family=LOOK.classify_trim(split['trim'],split['main'],kind)
                if trim_family!=family:
                    trim=dict(family=trim_family,mask=SC.image('PA masque · '+ob.name,split['mask'],tex_dir/(ob.name+'-masque-matiere.png'),True))
            preset=LOOK.MATERIALS[family]; sel=structure['owner']==ob['pa_photo_index']
            rough=LOOK.highlight_roughness(small_photo,sel,preset['roughness']) if sel.sum()>64 else preset['roughness']
            rough=float(np.clip(rough,preset['roughness']*.5,min(1.,preset['roughness']*1.2)))  # highlights adjust, never redefine
            mat=SC.material('PA · '+ob.name,family,a['image'],stats['mean'],rough,trim=trim,emission=a.get('emission')); SC.assign(ob,mat)
            mats[ob.name]=(mat,stats,family); report.append(dict(object=ob.name,family=family,roughness=round(rough,3),
                metallic=preset.get('metallic',0.),contrast=round(stats['contrast'],3),wavelength_m=round(stats['wavelength_m'],4),
                secondary=dict(family=trim['family'],share=round(split['share'],3)) if trim else None))
        if glass:
            gm=SC.material('PA · verre','glass',colour=(1.,1.,1.))
            for ob in glass: SC.assign(ob,gm)
        for ob in backdrop:
            mw=np.array(ob.matrix_world); co=np.array([mw[:3,:3]@np.array(v.co)+mw[:3,3] for v in ob.data.vertices])
            x,y,_=T.project(co,cam_m,fov,W,H)
            layer=ob.data.uv_layers.new(name='Photo')
            for poly in ob.data.polygons:
                for li in poly.loop_indices:
                    vi=ob.data.loops[li].vertex_index; layer.data[li].uv=(x[vi]/W,1-y[vi]/H)
            SC.assign(ob,SC.emission_material('PA Fond · plaque photo',plate))
        (folder/'materiaux.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
        families=sorted({r['family'] for r in report}|{r['secondary']['family'] for r in report if r.get('secondary')})
        end(', '.join(families),families=families)
        # ------------------------------------------------ 5 · procedural
        begin('procedural'); yield 'Détail procédural de près…'
        pixel=SC.pixel_angle_group(scene,ref); rec=[]
        for name,(mat,stats,family) in mats.items():
            r=LOOK.recipe(dict(stats,texel_m=atlases[name]['texel']),family)  # detail takes over below the atlas texel
            if SC.add_detail(mat,r,pixel): rec.append(dict(material=mat.name,**r))
        (folder/'procedural.json').write_text(json.dumps(rec,indent=2,ensure_ascii=False),encoding='utf-8')
        end(f'{len(rec)} matières émulées',recipes=len(rec))
        # ------------------------------------------------ 6 · light & effects
        begin('light'); yield 'Estimation de la lumière…'; scene.view_layers[0].update()
        light_coll=SC.collection(scene,'3 · Lumières',root)
        sky_mask=U.nearest(structure['sky'],W,H)
        sky=LOOK.sky_colours(photo,sky_mask)
        exterior=(analysis or {}).get('scene')=='exterior' or bool(sky) or (rep['ceiling'] is None and rep['walls']<2)
        shading=U.luminance(small_photo)/np.maximum(U.luminance(U.resize(albedo,aw,ah)),.02)
        okn=structure['valid']&(structure['owner']>=0)
        idx=np.flatnonzero(okn.ravel()); idx=idx[np.random.default_rng(2).permutation(len(idx))[:6000]]
        key_fit=LOOK.fit_directional(structure['normals'].reshape(-1,3)[idx],shading.ravel()[idx]) if len(idx)>50 else None
        sun_dir=None
        if key_fit and key_fit['r2']>.3 and key_fit['ratio']>.2 and key_fit['direction'][2]>.17: sun_dir=np.array(key_fit['direction'])
        elif analysis and analysis.get('sun'):
            fwd=-np.asarray(cam_m)[:3,2]; head=math.atan2(fwd[1],fwd[0])-math.radians(analysis['sun']['azimuth_deg']); el=math.radians(analysis['sun']['elevation_deg'])
            sun_dir=np.array((math.cos(head)*math.cos(el),math.sin(head)*math.cos(el),math.sin(el)))
        mean=photo.reshape(-1,3).mean(0); cam_pos=np.asarray(cam_m)[:3,3]
        fwd=-np.asarray(cam_m)[:3,2]; fh=np.array((fwd[0],fwd[1],0.)); fh/=max(np.linalg.norm(fh),1e-9); head=math.atan2(fh[1],fh[0])
        def towards(azimuth,elevation):
            el=math.radians(elevation); return np.array((math.cos(azimuth)*math.cos(el),math.sin(azimuth)*math.cos(el),math.sin(el)))
        suns=[('Soleil estimé',sun_dir)] if sun_dir is not None else []
        if exterior:
            SC.world(scene,sky,ambient=mean,strength=1.)
            suns+=[('Soleil gauche',towards(head+2.,40)),('Soleil droite',towards(head-2.,40)),('Soleil contre-jour',towards(head,35)),('Soleil de face',towards(head+math.pi,45))]
        else:
            SC.world(scene,None,ambient=mean/max(mean.max(),1e-3)*.6,strength=.5)
            for ob in glass:  # window light enters through every modelled pane
                mw=ob.matrix_world; n=np.array(mw.to_3x3()@ob.data.polygons[0].normal); n/=np.linalg.norm(n)
                pts=np.array([np.array(mw@v.co) for v in ob.data.vertices])
                if np.dot(n,cam_pos-pts.mean(0))<0: n=-n
                width=float(np.linalg.norm(np.ptp(pts[:,:2],0))); height=float(np.ptp(pts[:,2]))
                SC.light(scene,light_coll,'Fenêtre · '+ob.name,'AREA',pts.mean(0)+n*.05,-n,energy=60*max(.2,width*height),
                         colour=tuple(np.clip(sky['horizon'] if sky else (1,1,1),0,1)),size=(max(width,.1),max(height,.1)),glossy=False)
                out=np.array((-n[0],-n[1],0.)); out/=max(np.linalg.norm(out),1e-9)
                suns.append(('Soleil par '+ob.name,towards(math.atan2(out[1],out[0]),35)))
            top=(rep['ceiling'] if rep['ceiling'] is not None else cam_pos[2]+1.2)-.05
            SC.light(scene,light_coll,'Plafonnier','AREA',(*(cam_pos[:2]+fh[:2]*2.5),top),(0,0,1.),energy=200,size=(1.5,1.5),glossy=False)
            SC.light(scene,light_coll,'Remplissage caméra','AREA',cam_pos-fh*.4,-fh,energy=80,size=(2.,1.5),glossy=False)
        for name,d in suns: SC.light(scene,light_coll,name,'SUN',cam_pos+np.asarray(d)*5,d,energy=3.,colour=(1,.97,.92))
        sources=LOOK.light_sources(photo,depth)
        rays=G.camera_rays(W,H,fov)
        for i,src_ in enumerate(sources):
            if src_['depth']<=0: continue
            px,py=min(W-1,int(src_['x']*W)),min(H-1,int(src_['y']*H))
            pc=rays[py,px]*src_['depth']*.97; pos=np.asarray(cam_m)[:3,:3]@pc+cam_pos
            col=np.array(src_['colour']); col=col/max(col.max(),1e-3)
            SC.light(scene,light_coll,'Source %02d'%(i+1),'POINT',pos,energy=25.,colour=tuple(col),size=(.05,.05))
        yield 'Calibration des lumières sur la photo (une passe par lumière)…'
        lw,lh=preview; lphoto=U.resize(photo,lw,lh); lsky=U.nearest(sky_mask,lw,lh); ld=U.nearest(d0,lw,lh)
        lmask=(ld>0)&~lsky&(U.luminance(lphoto)<.9)
        cands=[o for o in scene.objects if o.type=='LIGHT' and o.get('pa_photo_light')]
        energies={o.name:o.data.energy for o in cands}; bg=scene.world.node_tree.nodes['PA Ciel']; strength0=bg.inputs['Strength'].default_value
        def solo(active):
            for o in cands: o.data.energy=energies[o.name] if o is active else 0.
            bg.inputs['Strength'].default_value=strength0 if active=='world' else 0.
        bs=max(8,q['samples']//3); basis=[]
        solo(None); baseline=SC.render(scene,ref,folder/'lumieres'/'base.exr',lw,lh,samples=bs)[...,:3]
        for k,c in enumerate(cands+['world']):
            solo(c); basis.append(SC.render(scene,ref,folder/'lumieres'/f'lumiere-{k:02d}.exr',lw,lh,samples=bs)[...,:3])
        w,tints,residual=LOOK.fit_lights(basis,baseline,lphoto,lmask)
        share=w*np.array([U.luminance(b-baseline)[lmask].mean() for b in basis]); share=share/max(share.sum(),1e-9)
        kept=[]
        for o,wk,tint,sh in zip(cands,w,tints,share):
            if sh<.02: bpy.data.objects.remove(o,do_unlink=True); continue
            o.data.energy=energies[o.name]*float(wk); o.data.color=tuple(np.clip(np.array(o.data.color)*tint,0,1)); kept.append(dict(light=o.name,share=round(float(sh),3)))
        bg.inputs['Strength'].default_value=strength0*float(w[-1])
        if not scene.world.node_tree.nodes['PA Ciel'].inputs['Color'].is_linked:
            bg.inputs['Color'].default_value=(*np.clip(np.array(bg.inputs['Color'].default_value[:3])*tints[-1],0,1),1)
        man.set(lights=dict(kept=kept,world_share=round(float(share[-1]),3),residual=round(residual,4)))
        yield 'Rendu de référence…'
        render_lin=SC.render(scene,ref,folder/'6-rendu-brut.exr',W,H,samples=q['samples'])[...,:3]
        dfinal=SC.render_depth(scene,ref,folder/'6-profondeur.exr',W,H,exclude=backdrop)
        haze=LOOK.fit_haze(photo,dfinal,dfinal>0,sky_mask)
        if analysis and analysis['atmosphere'].get('haze',0)<.1 and haze['confidence']<.8: haze['beta']=0.
        glow=LOOK.fit_glow(photo)
        base=dict(haze_beta=haze['beta'],airlight=haze['airlight'],glow_threshold=glow['threshold'],glow_strength=glow['strength'],glow_radius=glow['radius'],
                  grain=max(0.,LOOK.noise_sigma(photo_srgb)-LOOK.noise_sigma(U.linear_to_srgb(render_lin))))
        mask=np.ones((H,W),bool)
        look=yield POOL.submit(LOOK.fit_look,render_lin,dfinal,photo,mask,base)
        if abs(look['exposure'])>.15:  # exposure belongs to the lights: the photo plate must stay untouched
            SC.scale_lights(scene,2**look['exposure'])
            yield 'Rendu de référence (exposition corrigée)…'
            render_lin=SC.render(scene,ref,folder/'6-rendu-brut.exr',W,H,samples=q['samples'])[...,:3]
            look=yield POOL.submit(LOOK.fit_look,render_lin,dfinal,photo,mask,base)
        compositor=SC.compositor(scene,look)
        (folder/'look.json').write_text(json.dumps(dict(look=look,haze=haze,glow=glow,key_light=key_fit,exterior=exterior,
            sources=sources,compositor=compositor),indent=2,ensure_ascii=False),encoding='utf-8')
        lights=sum(1 for o in scene.objects if o.type=='LIGHT')
        end(f"{lights} lumières, brume β={look['haze_beta']:.3f}, glow {look['glow_strength']:.2f}",lights=lights,exterior=exterior)
        # ------------------------------------------------ 7 · score
        begin('score'); yield 'Note de fidélité…'
        weights=config.get('weights')
        final=LOOK.apply_look(render_lin,dfinal,look)
        best=dict(score=SCORE.score(photo_srgb,final,weights),final=final,look=look,colours={n:a['colour'].copy() for n,a in atlases.items()})
        history=[dict(iteration=0,total=best['score']['total'])]
        for it in range(int(config.get('iterations',2)) if config.get('refine_albedo',True) else 0):
            yield f'Amélioration {it+1} : albédo par comparaison…'
            # Luminance ratio over modelled surfaces only (no leakage from the plate), plus a damped tint.
            surf=dfinal>0; fl=U.srgb_to_linear(best['final'])
            lum=U.masked_blur(U.luminance(photo),surf,1.5)/np.maximum(U.masked_blur(U.luminance(fl),surf,1.5),1e-3)
            tint=U.masked_blur(photo,surf,6.)/np.maximum(U.masked_blur(fl,surf,6.),1e-3)
            tint=tint/np.maximum(U.luminance(tint)[...,None],1e-3)
            ratio=np.where(surf[...,None],lum[...,None]*(1+.5*(np.clip(tint,.7,1.4)-1)),1.)
            for ob in textured:
                a=atlases[ob.name]
                a['colour']=yield POOL.submit(T.refine,best['colours'][ob.name],a['P'],a['M'],views[0],ratio,.85)
                a['image']=SC.replace_image(a['image'],'PA Atlas · '+ob.name,a['colour'],tex_dir/(ob.name+'.png'))
            render_it=SC.render(scene,ref,folder/f'7-iteration-{it+1}.exr',W,H,samples=q['samples'])[...,:3]
            look_it=yield POOL.submit(LOOK.fit_look,render_it,dfinal,photo,mask,base)
            final_it=LOOK.apply_look(render_it,dfinal,look_it); sc=SCORE.score(photo_srgb,final_it,weights)
            engine.write_image(folder/f'7-iteration-{it+1}.png',U.srgb_to_linear(final_it))
            history.append(dict(iteration=it+1,total=sc['total']))
            if sc['total']>best['score']['total']+.05:
                best=dict(score=sc,final=final_it,look=look_it,colours={n:a['colour'].copy() for n,a in atlases.items()})
            else:
                for ob in textured:
                    a=atlases[ob.name]; a['colour']=best['colours'][ob.name]
                    a['image']=SC.replace_image(a['image'],'PA Atlas · '+ob.name,a['colour'],tex_dir/(ob.name+'.png'))
                break
        if best['look'] is not look: SC.compositor(scene,best['look'])
        engine.write_image(folder/'final.png',U.srgb_to_linear(best['final']))
        engine.write_image(folder/'comparaison.png',U.srgb_to_linear(SCORE.heatmap(photo_srgb,best['final'])))
        result=dict(best['score'],camera_mapping_reference=rough_score['total'],history=history)
        if budget() and config.get('judge',True):
            yield 'Avis du juge IA…'
            try:
                verdict=yield api(providers.judge,config['endpoint'],key(),config['vision_model'],str(folder/'inputs'/'reference.png'),str(folder/'final.png'))
                result.update(judge=verdict,metric=result['total'],total=SCORE.combine(result['total'],verdict['score']))
            except Exception as e: result['judge_error']=type(e).__name__
        (folder/'score.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
        (folder/'look.json').write_text(json.dumps(dict(json.loads((folder/'look.json').read_text(encoding='utf-8')),final_look=best['look']),indent=2,ensure_ascii=False),encoding='utf-8')
        man.set(score=result)
        end(f"{result['total']:.1f} / 20",total=result['total'])
        progress({'score':result})
        scene.camera=ref; scene.render.resolution_x=W; scene.render.resolution_y=H
        SC.set_pixel_angle(scene,ref)
        scene.render.filepath=str(folder/'rendu-')
        for ob in textured: ob['pa_photo_movable']=True
        bpy.data.libraries.write(str(folder/'scene.blend'),{scene},fake_user=True,compress=True)
        man.set(status='completed',blend=str(folder/'scene.blend'))
        yield f"Terminé : {result['total']:.1f}/20 — scène « {scene.name} »."
    except GeneratorExit:
        man.set(status='cancelled'); raise
    except Exception as e:
        if current['phase']:
            man.data['phases'][current['phase']]=dict(state='failed',error=type(e).__name__,message=str(e)[:300]); progress({'phase':current['phase'],'state':'failed','note':str(e)[:120]})
        man.set(status='failed',error_type=type(e).__name__); raise


def _visible(tree,matrix,points,normals,fov,w,h):
    x,y,z=T.project(points,matrix,fov,w,h)
    cand=(z>.05)&(x>=0)&(x<w)&(y>=0)&(y<h)&(np.einsum('ij,ij->i',normals,np.asarray(matrix)[:3,3]-points)>0)
    out=np.zeros(len(points),bool)
    idx=np.flatnonzero(cand)
    if len(idx): out[idx]=SC.visible(tree,np.asarray(matrix)[:3,3],points[idx])
    return out

