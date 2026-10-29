import sys
import json
from pathlib import Path
import bpy
import numpy as np
from mathutils import Matrix,Vector
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import pano_atelier
from pano_atelier import structural,engine
pano_atelier.register()
OUT=ROOT/'output'/'cockpit-lowpoly-v1'
bpy.ops.wm.open_mainfile(filepath=str(OUT/'cockpit-lowpoly-guide.blend'))
scene=bpy.context.scene
report=structural.project_atlas(scene,OUT/'generated-atlas-v1.png',OUT/'projection')
print(json.dumps(report),flush=True)
surface=engine.Surface(scene)
checks=[]
for origin in [(0,0,1.6),(.7,0,1.6),(-.7,0,1.6),(0,.7,1.6),(0,-.7,1.6)]:
    for name,matrix in structural.cameras(origin):
        shot=engine.scan(surface,matrix,90,128,128)
        checks.append({'origin':origin,'view':name,'holes':int((shot['ids']<0).sum())})
scene.render.engine='CYCLES'; scene.cycles.samples=1
scene.view_settings.view_transform='Standard'
scene.render.resolution_x=960; scene.render.resolution_y=540; scene.render.resolution_percentage=100
cam=bpy.data.objects.new('PA Preview',bpy.data.cameras.new('PA Preview'))
engine.collection(scene).objects.link(cam); scene.camera=cam
cam.data.sensor_fit='HORIZONTAL'; cam.data.angle=np.radians(90); cam.data.clip_start=.02
poses=structural.cameras()
for name,matrix in [('front',poses[0][1]),('back',poses[2][1]),
                    ('move-right',Matrix.Translation((.65,0,0))@poses[0][1]),
                    ('look-left',poses[3][1])]:
    cam.matrix_world=matrix; scene.render.filepath=str(OUT/('preview-'+name+'.png'))
    bpy.ops.render.render(write_still=True,scene=scene.name)
cam.matrix_world=poses[0][1]
scene.pa_settings.radius=1.; scene.pa_settings.status='404 triangles · projections GPT Image · raccords à affiner'
scene.pa_settings.output=str(OUT/'inspections'); scene.pa_settings.extend_geometry=False
scene.pa_settings.image=str(OUT/'generated-atlas-v1.png')
scene.pa_settings.projection_atlas=str(OUT/'generated-atlas-v1.png')
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.show_region_ui=True
            area.spaces.active.overlay.show_overlays=False
            area.spaces.active.shading.type='MATERIAL'
            area.spaces.active.region_3d.view_perspective='CAMERA'
for obj in scene.objects: obj.select_set(False)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'cockpit-lowpoly-v1.blend'))
(OUT/'navigation-checks.json').write_text(json.dumps(checks,indent=2))
print('NAVIGATION: %d views, %d missing rays'%(len(checks),sum(x['holes'] for x in checks)),flush=True)
