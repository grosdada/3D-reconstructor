"""Incremental jobs. Generator yields status or a Future; bpy stays on main thread."""
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as np
import bpy
from . import core, engine, providers

POOL=ThreadPoolExecutor(max_workers=1,thread_name_prefix='PanoAtelier')


def infer_depth(python,image,output,panorama,fov):
    if not python or not Path(python).is_file():
        raise ValueError('Configurer un Python avec MoGe installé, ou fournir une profondeur NPY/EXR.')
    command=[python,str(Path(__file__).with_name('depth_worker.py')),'--image',image,'--output',str(output),'--fov',str(fov)]
    if panorama: command+=['--panorama']
    completed=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=900,
        creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if completed.returncode:
        # This subprocess handles no credentials. Keep local diagnostics for setup errors.
        Path(output).mkdir(parents=True,exist_ok=True)
        (Path(output)/'moge-error.txt').write_bytes(completed.stdout[-32000:])
        raise RuntimeError('MoGe a échoué. Consulter moge-error.txt dans le dossier de sortie.')
    folder=Path(output)/Path(image).stem
    path=folder/('depth.exr' if panorama else 'depth.npy')
    if not path.exists(): raise RuntimeError('MoGe n’a pas produit de profondeur.')
    return str(path)


def run(scene,config,folder):
    folder=Path(folder); folder.mkdir(parents=True,exist_ok=True)
    report={'version':'0.1.0','status':'running','backend':config['backend'], 'requests':0,
        'accepted':0,'rejected':0,'views':[], 'limitations':['Generated geometry is experimental and inferred, not measured.',
        'Semantic quality is not guaranteed by geometric/pixel checks.']}
    patches=json.loads(scene.get('pa_patch_history','[]')); calls=0; accepted=0
    def persist():
        report['requests']=calls; report['accepted']=accepted
        (folder/'report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    try:
        objects=engine.owned(scene)
        if not objects: raise ValueError('Aucun décor Pano Atelier dans cette scène.')
        cam,poses=engine.create_path(scene,objects[0],config['radius'])
        report['camera']=cam.name
        holdouts=[(m,h) for m,h in poses if h]
        baseline=[]
        yield 'Mesure des vues de contrôle indépendantes…'
        surface=engine.Surface(scene)
        for i,(matrix,_) in enumerate(holdouts):
            shot=engine.scan(surface,matrix,config['fov'],config['width'],round(config['width']*9/16))
            baseline.append(shot)
            engine.save_scan(folder/f'control-{i:02d}-before',shot)
        seen=set()
        for index,(matrix,holdout) in enumerate(poses):
            if holdout: continue
            cam.matrix_world=matrix
            yield f'Inspection {index+1}/{len(poses)-len(holdouts)}…'
            surface=engine.Surface(scene)
            # Avoid traversing a known surface between origin and inspection position.
            root=engine.base_matrix().translation
            delta=matrix.translation-root
            if delta.length>.001:
                hit,normal,face,dist=surface.tree.ray_cast(root,delta.normalized(),delta.length+.05)
                if face is not None:
                    report['views'].append({'index':index,'status':'blocked_camera_collision'}); persist(); continue
            shot=engine.scan(surface,matrix,config['fov'],config['width'],round(config['width']*9/16))
            work=folder/f'view-{index:03d}'; engine.save_scan(work,shot)
            view={'index':index,'holes':int(shot['masks']['holes'].sum()),'candidates':int(shot['masks']['texture'].sum()),'status':'inspected'}
            report['views'].append(view); persist()
            mask=shot['masks']['texture'].copy()
            extend=(not scene.get('pa_structural') and config['backend']=='API' and config.get('extend_geometry',False)
                and bool(config.get('moge_python')) and shot['masks']['holes'].sum()>=16)
            if config['backend']=='API' and config['vision']:
                if calls>=config['max_requests']:
                    report['status']='request_limit'; view['status']='inspected_request_limit'; continue
                calls+=1; persist()
                defects=yield POOL.submit(providers.inspect_image,config['endpoint'],providers.get_key(config['endpoint']),config['vision_model'],work/'view.png')
                (work/'vision.json').write_text(json.dumps(defects,indent=2),encoding='utf-8')
                # Semantic model chooses texture regions, geometric hit test limits their scope.
                mask=core.boxes_mask(defects,mask.shape) & (shot['ids']>=0)
                view['semantic_defects']=len(defects)
            elif config['backend']=='AUDIT':
                continue
            if not np.any(mask) and not extend: view['status']='no_texture_candidate'; continue
            # Track triangle IDs already repaired rather than repeating across nearby views.
            for face in seen: mask[shot['ids']==face]=False
            if not np.any(mask) and not extend: view['status']='already_processed'; continue
            if accepted>=config['max_patches']:
                report['status']='patch_limit'; view['status']='inspected_patch_limit'; continue
            alpha=core.feather(mask,2)*(shot['ids']>=0)
            engine.write_image(work/'mask-editable.png',alpha,True)
            edit_alpha=np.maximum(alpha,shot['masks']['holes'].astype(np.float32)) if extend else alpha
            # Images/edit API: transparent = edit, opaque = preserve.
            api_mask=np.ones((*alpha.shape,4),np.float32); api_mask[...,3]=1-edit_alpha
            engine.write_image(work/'mask-api.png',api_mask,True)
            if config['backend']=='LOCAL':
                yield 'Réparation locale de test (sans IA)…'
                generated=core.local_fill(shot['rgb'],alpha)
                engine.write_image(work/'generated.png',generated)
            else:
                if calls>=config['max_requests']:
                    report['status']='request_limit'; view['status']='inspected_request_limit'; continue
                calls+=1; persist()
                yield 'Génération du raccord via l’API…'
                # Letterbox to a supported square. Crop back, never stretch a provider's aspect.
                canvas=np.ones((1024,1024,4),np.float32); canvas[...,:3]=.1
                ch=round(1024*shot['rgb'].shape[0]/shot['rgb'].shape[1]); top=(1024-ch)//2
                canvas[top:top+ch]=engine.resize(shot['rgb'],1024,ch)
                full_mask=np.ones((1024,1024,4),np.float32)
                full_mask[top:top+ch]=engine.resize(api_mask,1024,ch)
                engine.write_image(work/'api-view.png',canvas)
                engine.write_image(work/'api-mask.png',full_mask,True)
                output=yield POOL.submit(providers.edit_image,config['endpoint'],providers.get_key(config['endpoint']),
                    config['image_model'],work/'api-view.png',work/'api-mask.png',work/'generated.png',
                    'Repair only masked texture seams or damaged texture; complete masked missing surfaces consistently with the visible scene. Preserve scene layout, perspective, existing objects, materials and lighting. '
                    'Continue surrounding surface details naturally. Do not add objects, text or borders. '+config['prompt'])
                raw=engine.load_pixels(output)
                if raw.shape[0]!=raw.shape[1]: raise ValueError('Réponse API non carrée : impossible de garantir la projection.')
                generated=engine.resize(raw,1024,1024)[top:top+ch]
            new_depth=None
            if extend:
                yield 'Estimation et alignement de la surface révélée…'
                # Match the camera aspect before depth inference; provider output may differ.
                engine.write_image(work/'generated-camera.png',engine.resize(generated,shot['depth'].shape[1],shot['depth'].shape[0]))
                new_depth=yield POOL.submit(infer_depth,config['moge_python'],str(work/'generated-camera.png'),work/'depth-generated',False,config['fov'])
            yield 'Reprojection et vérification…'
            patch=engine.bake_patch(surface,shot,generated,alpha,work)
            # Always roll back a candidate on any exception in evaluation.
            keep=False
            try:
                if new_depth:
                    added,alignment=engine.add_missing_surface(scene,shot,str(work/'generated-camera.png'),new_depth,work/'geometry')
                    patch['added_objects']=[added.name]; view['depth_alignment']=alignment
                after=engine.scan(engine.Surface(scene),matrix,config['fov'],config['width'],round(config['width']*9/16))
                before_error=core.boundary_error(shot['rgb'],alpha); after_error=core.boundary_error(after['rgb'],alpha)
                view.update(texels=patch['texels'],boundary_before=before_error,boundary_after=after_error)
                keep=(patch['texels']>0 or bool(patch.get('added_objects'))) and after_error<=before_error*1.15+.008
                if new_depth:
                    remaining=int(after['masks']['holes'].sum()); view['holes_after']=remaining
                    keep=keep and remaining<view['holes']
                # Independent viewpoints: detect large new colour discontinuities.
                for base,(control_matrix,_) in zip(baseline,holdouts):
                    control=engine.scan(engine.Surface(scene),control_matrix,config['fov'],max(64,config['width']//2),round(max(64,config['width']//2)*9/16))
                    old=engine.resize(base['rgb'],control['rgb'].shape[1],control['rgb'].shape[0])
                    before_grad=np.mean(abs(np.diff(old[...,:3],axis=1)))
                    after_grad=np.mean(abs(np.diff(control['rgb'][...,:3],axis=1)))
                    if after_grad>before_grad*1.8+.015: keep=False
                engine.save_scan(work/'after',after)
            finally:
                if not keep: engine.restore(patch)
            if keep:
                patches.append(patch); accepted+=1
                seen.update(int(i) for i in np.unique(shot['ids'][mask]) if i>=0)
                scene['pa_patch_history']=json.dumps(patches)
                view['status']='accepted_heuristic'
            else:
                report['rejected']+=1; view['status']='rejected'
                seen.update(int(i) for i in np.unique(shot['ids'][mask]) if i>=0)
            persist()
        yield 'Contrôle final du parcours…'
        surface=engine.Surface(scene)
        for i,(matrix,_) in enumerate(holdouts):
            final=engine.scan(surface,matrix,config['fov'],config['width'],round(config['width']*9/16))
            engine.save_scan(folder/f'control-{i:02d}-after',final)
        if report['status']=='running':
            report['status']='review_required' if any(v.get('holes',0)>0 for v in report['views']) else 'completed_with_heuristic_checks'
        report['validation']='Geometry and pixel heuristics only; no claim of semantic or human validation.'
        persist()
        scene.frame_set(1)
        scene['pa_last_report']=str(folder/'report.json')
        yield f'Terminé : {accepted} correction(s), {calls} appel(s). Rapport enregistré.'
    except GeneratorExit:
        report['status']='cancelled'; persist(); raise
    except Exception as e:
        report['status']='failed'; report['error_type']=type(e).__name__; persist(); raise
