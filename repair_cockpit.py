"""Controlled GPT Image masked repair iteration. Run with -- prepare/background/furniture/check."""
import sys
import json
from pathlib import Path
import bpy
import numpy as np
from mathutils import Matrix,Vector
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import pano_atelier
from pano_atelier import engine,structural,core
pano_atelier.register()
OUT=ROOT/'output'/'cockpit-lowpoly-v2'; OUT.mkdir(parents=True,exist_ok=True)
OLD=ROOT/'output'/'cockpit-lowpoly-v1'
MODE=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'prepare'

def furniture(obj):
    return obj.name.startswith(('PA Seat','PA Central'))

def stats(scene):
    objects=engine.owned(scene); count=0
    for obj in objects: obj.data.calc_loop_triangles(); count+=len(obj.data.loop_triangles)
    return dict(triangles=count,objects=len(objects),vertices=sum(len(o.data.vertices) for o in objects),signature=engine.geometry_signature(scene))

def render(scene,cam,path,engine_name='CYCLES',size=(768,432),samples=1):
    scene.camera=cam; scene.render.engine=engine_name
    scene.cycles.samples=samples; scene.view_settings.view_transform='Standard'
    scene.render.resolution_x=size[0]; scene.render.resolution_y=size[1]; scene.render.resolution_percentage=100
    scene.render.filepath=str(path)
    bpy.ops.render.render(write_still=True,scene=scene.name)

def camera(scene):
    data=bpy.data.cameras.new('PA Repair camera'); obj=bpy.data.objects.new('PA Repair camera',data)
    engine.collection(scene).objects.link(obj); data.sensor_fit='HORIZONTAL'; data.angle=np.radians(90); data.clip_start=.02
    return obj

def furniture_cameras():
    origins=[(-1.,0,1.6),(0,0,1.6),(1.,0,1.6),(-1.,4.7,1.6),(0,4.7,1.6),(1.,4.7,1.6)]
    poses=[]
    for origin in origins:
        target=Vector((0,2.65,1.0)); matrix=(target-Vector(origin)).to_track_quat('-Z','Y').to_matrix().to_4x4()
        matrix.translation=Vector(origin); poses.append(matrix)
    return poses

if MODE=='prepare':
    # The mask surrounds the furniture in the original generated cubemap.
    # It deliberately includes its old projected shadows/halos on the floor.
    mask=np.zeros((1024,1536),np.float32)
    for x0,y0,x1,y1 in [(100,225,390,470),(0,225,115,410),(385,220,512,425),
                         (512,220,590,405),(405,745,512,970)]: mask[y0:y1,x0:x1]=1
    engine.write_image(OUT/'background-mask.png',mask,True)
    scene=bpy.data.scenes.new('Cockpit — volume et raccords v2'); bpy.context.window.scene=scene
    structural.build(scene,OUT/'structure',architecture=True)
    structural.export_guides(scene,OUT/'architecture-guides')
    (OUT/'geometry-before.json').write_text(json.dumps(stats(scene),indent=2))
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'architecture.blend'))
    print(json.dumps(stats(scene)),flush=True)

elif MODE=='background':
    bpy.ops.wm.open_mainfile(filepath=str(OUT/'architecture.blend')); scene=bpy.context.scene
    # Hard mask enforcement before projection: generation cannot edit outside it.
    original=engine.load_pixels(OLD/'generated-atlas-v1.png')
    generated=engine.load_pixels(OUT/'background-generated.png')
    generated=engine.resize(generated,original.shape[1],original.shape[0])
    mask=engine.load_pixels(OUT/'background-mask.png',True)[...,0]
    mask=core.feather(mask>.5,8)*(mask>.5)
    combined=original.copy(); combined[...,:3]=original[...,:3]*(1-mask[...,None])+generated[...,:3]*mask[...,None]
    engine.write_image(OUT/'background-masked.png',combined)
    hidden=[o for o in engine.owned(scene) if furniture(o)]
    for obj in hidden: obj.hide_render=True
    report=structural.project_atlas(scene,OUT/'background-masked.png',OUT/'background-projection')
    for obj in hidden: obj.hide_render=False
    # A flat lit clay material on foreground only is the geometry constraint for
    # GPT Image. It is replaced entirely by projected generated photographs.
    original_mats={}
    mat=bpy.data.materials.new('PA Furniture guide only'); mat.diffuse_color=(.44,.44,.40,1); mat.use_nodes=True
    bsdf=mat.node_tree.nodes.get('Principled BSDF'); bsdf.inputs['Base Color'].default_value=(.5,.49,.44,1); bsdf.inputs['Roughness'].default_value=.65
    for obj in hidden:
        original_mats[obj.name]=obj.data.materials[0]; obj.data.materials[0]=mat
    world=scene.world or bpy.data.worlds.new('PA Guide world'); scene.world=world; world.use_nodes=True
    world.node_tree.nodes.get('Background').inputs['Color'].default_value=(.8,.8,.8,1)
    world.node_tree.nodes.get('Background').inputs['Strength'].default_value=.8
    cam=camera(scene); atlas=np.ones((1024,1536,4),np.float32); masks=np.zeros((1024,1536),np.float32)
    poses=furniture_cameras(); manifest=[]
    for i,matrix in enumerate(poses):
        cam.matrix_world=matrix; path=OUT/('furniture-guide-%d.png'%i)
        render(scene,cam,path,size=(512,512),samples=16)
        atlas[i//3*512:(i//3+1)*512,i%3*512:(i%3+1)*512]=engine.load_pixels(path)
    for obj in hidden: obj.data.materials[0]=original_mats[obj.name]
    surface=engine.Surface(scene)
    for i,matrix in enumerate(poses):
        shot=engine.scan(surface,matrix,90,512,512)
        tids=[j for j,r in enumerate(surface.records) if furniture(r[0])]
        mask=np.isin(shot['ids'],tids)
        engine.write_image(OUT/('furniture-mask-%d.png'%i),mask.astype(np.float32),True)
        masks[i//3*512:(i//3+1)*512,i%3*512:(i%3+1)*512]=mask
        manifest.append({'matrix':[list(r) for r in matrix],'fov':90,'tile':[i%3,i//3]})
    engine.write_image(OUT/'furniture-guide-atlas.png',atlas)
    engine.write_image(OUT/'furniture-mask-atlas.png',masks,True)
    (OUT/'furniture-cameras.json').write_text(json.dumps(manifest,indent=2))
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'background-clean.blend'))
    print(json.dumps(report),flush=True)

elif MODE=='furniture':
    bpy.ops.wm.open_mainfile(filepath=str(OUT/'background-clean.blend')); scene=bpy.context.scene
    atlas=engine.load_pixels(OUT/'furniture-generated.png')
    if abs(atlas.shape[1]/atlas.shape[0]-1.5)>.01: raise ValueError('Expected 3x2 atlas')
    h,w=atlas.shape[:2]
    patches=[]
    scores=np.zeros((scene['pa_atlas_size'],scene['pa_atlas_size']),np.float32)
    # Side views first; center front last anchors the principal view.
    for i in (3,5,4,0,2,1):
        matrix=furniture_cameras()[i]; surface=engine.Surface(scene)
        shot=engine.scan(surface,matrix,90,512,512)
        tids=[j for j,r in enumerate(surface.records) if furniture(r[0])]
        mask=np.isin(shot['ids'],tids).astype(np.float32)
        tile=atlas[round(i//3*h/2):round((i//3+1)*h/2),round(i%3*w/3):round((i%3+1)*w/3)]
        patch=engine.bake_patch(surface,shot,tile,mask,OUT/('furniture-patch-%d'%i),score_buffer=scores); patches.append(patch)
        print('Furniture camera %d: %d texels'%(i,patch['texels']),flush=True)
    scene['pa_patch_history']=json.dumps(patches)
    # A single overhead fixed projector on the planar floor removes cubemap
    # exposure/tile boundaries. It reuses GPT Image's clean down-facing image.
    all_objects=engine.owned(scene); hidden=[o for o in all_objects if not o.name.startswith('PA Floor')]
    for obj in hidden: obj.hide_render=True
    surface=engine.Surface(scene)
    matrix=structural.cameras((0,1.6,6.0))[-1][1]
    shot=engine.scan(surface,matrix,90,768,768)
    clean=engine.load_pixels(OUT/'background-generated.png')
    ch,cw=clean.shape[:2]; floor=clean[ch//2:,cw*2//3:]
    patch=engine.bake_patch(surface,shot,floor,(shot['ids']>=0).astype(float),OUT/'floor-patch')
    for obj in hidden: obj.hide_render=False
    patches.append(patch); scene['pa_patch_history']=json.dumps(patches)
    (OUT/'geometry-after.json').write_text(json.dumps(stats(scene),indent=2))
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'cockpit-lowpoly-v2.blend'))

elif MODE=='check':
    bpy.ops.wm.open_mainfile(filepath=str(OUT/'cockpit-lowpoly-v2.blend')); scene=bpy.context.scene
    cam=camera(scene)
    for label,origin in [('center',(0,0,1.6)),('left',(-.9,0,1.6)),('right',(.9,0,1.6)),('forward',(0,.85,1.6))]:
        cam.matrix_world=structural.cameras(origin)[0][1]
        render(scene,cam,OUT/('check-'+label+'.png'))
    # Close geometry views verify the new modeled recesses and opening.
    for label,origin,target in [('door',(0,4.2,1.6),(0,6.,1.5)),('window',(3.6,2.0,1.6),(4.8,2.5,2.))]:
        cam.matrix_world=(Vector(target)-Vector(origin)).to_track_quat('-Z','Y').to_matrix().to_4x4(); cam.location=origin
        render(scene,cam,OUT/('clay-'+label+'.png'),'BLENDER_WORKBENCH')
    cam.matrix_world=structural.cameras()[0][1]; scene.render.engine='CYCLES'
    scene.pa_settings.radius=1.; scene.pa_settings.status='Raccords mobilier v2 · fenêtres et portes en volume'
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=='VIEW_3D':
                area.spaces.active.show_region_ui=True; area.spaces.active.overlay.show_overlays=False
                area.spaces.active.shading.type='MATERIAL'; area.spaces.active.region_3d.view_perspective='CAMERA'
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'cockpit-lowpoly-v2.blend'))

elif MODE=='video':
    bpy.ops.wm.open_mainfile(filepath=str(OUT/'cockpit-lowpoly-v2.blend')); scene=bpy.context.scene
    cam=camera(scene); frames=OUT/'motion'; frames.mkdir(exist_ok=True)
    for i in range(36):
        x=-.85+1.7*i/35
        cam.matrix_world=structural.cameras((x,.12*np.sin(i*np.pi/35),1.6))[0][1]
        render(scene,cam,frames/('frame-%03d.png'%i))
        print('Navigation frame %d/36'%(i+1),flush=True)
    cam.matrix_world=structural.cameras()[0][1]
    # A delivered scene is a new baseline; retain the construction history on disk.
    (OUT/'repair-history.json').write_text(scene.get('pa_patch_history','[]'))
    scene['pa_patch_history']='[]'
    before=json.loads((OUT/'geometry-before.json').read_text()); after=stats(scene)
    assert before['signature']==after['signature']
    report={'geometry':after,'geometry_unchanged_during_texture_repairs':True,
        'furniture_views':6,'masked_background_generation':True,'mask_scope':'visible selected-object surfaces',
        'motion_range_x_m':[-.85,.85],'motion_frames':36,
        'limits':'Floor highlights remain baked; other architectural projection seams are still visible. No claim of perfect arbitrary-distance navigation.'}
    (OUT/'repair-report.json').write_text(json.dumps(report,indent=2))
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'cockpit-lowpoly-v2.blend'))
