"""Build and audit the user's supplied image; does not generate or retouch it."""
import sys
import json
import shutil
import hashlib
from pathlib import Path
import bpy
import numpy as np
from mathutils import Matrix
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import pano_atelier
from pano_atelier import engine,pipeline
pano_atelier.register()
OUT=ROOT/'output'/'cockpit'; OUT.mkdir(parents=True,exist_ok=True)
source=Path(r'C:\Users\pc\Downloads\022-cockpit-hexagonal-minimal_base.webp')
copy=OUT/source.name
shutil.copy2(source,copy)
depth_folder=OUT/'moge'/source.stem
meta=json.loads((depth_folder/'metadata.json').read_text())
scene=bpy.data.scenes.new('Cockpit — Pano Atelier')
bpy.context.window.scene=scene
obj=engine.build(scene,copy,depth_folder/'depth.npy',fov=meta['fov_degrees'],resolution=512,edge=.15)
settings=scene.pa_settings
settings.image=str(copy); settings.depth=str(depth_folder/'depth.npy'); settings.fov=meta['fov_degrees']
settings.output=str(OUT/'inspections'); settings.radius=.25; settings.width=256; settings.backend='AUDIT'
settings.moge_python=str(ROOT/'.venv'/'Scripts'/'python.exe')
cfg=dict(backend='AUDIT',radius=.25,width=192,fov=meta['fov_degrees'],vision=False,max_requests=1,max_patches=1,
    endpoint='',image_model='',vision_model='',prompt='')
for status in pipeline.run(scene,cfg,OUT/'initial-audit'): print(status,flush=True)
scene['pa_last_folder']=str(OUT/'initial-audit')
surface=engine.Surface(scene)
for name,offset in [('origine',(0,0,0)),('droite',(0.25,0,0)),('avance',(0,0,-.25))]:
    shot=engine.scan(surface,engine.base_matrix() @ Matrix.Translation(offset),meta['fov_degrees'],640,360)
    engine.save_scan(OUT/name,shot)
    print(name, int(shot['masks']['holes'].sum()),flush=True)
scene.frame_set(1)
scene.render.engine='CYCLES'; scene.cycles.samples=16
scene.render.resolution_x=1280; scene.render.resolution_y=720; scene.render.resolution_percentage=100
scene.view_settings.view_transform='Standard'
scene.pa_settings.status='Cockpit reconstruit. Parcours ±25 cm audité, sans génération API.'
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.show_region_ui=True
            area.spaces.active.overlay.show_overlays=False
            area.spaces.active.shading.type='MATERIAL'
            area.spaces.active.region_3d.view_perspective='CAMERA'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'cockpit.blend'))
report={'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
    'copy_sha256':hashlib.sha256(copy.read_bytes()).hexdigest(),'vertices':len(obj.data.vertices),
    'triangles':len(obj.data.polygons),'fov_estimated':meta['fov_degrees'],'depth_model':meta['model'],
    'depth_min':float(np.min(np.load(depth_folder/'depth.npy')[np.load(depth_folder/'depth.npy')>0])),
    'depth_max':float(np.max(np.load(depth_folder/'depth.npy'))),'api_calls':0,'texture_modified':False,
    'status':'reconstructed_and_audited_not_completed_360'}
(OUT/'build-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report),flush=True)
