import bpy,sys
from pathlib import Path
R=Path(__file__).parent;O=R/'output/ville-brutaliste-v3-vis-a-vis';sys.path.insert(0,str(R));import pano_atelier
bpy.ops.wm.open_mainfile(filepath=str(O/'ville-brutaliste-vis-a-vis.blend'));pano_atelier.register();sc=bpy.context.scene
sc.pa_city.output=str(O);sc.pa_city.projection_scope='OPPOSITE';sc.pa_city.append_projection=True;sc.pa_city.projection_folder=str(O/'projection-12');sc.pa_city.projection_strength=.67
sc.pa_city.fog_density=.0072
sc['pa_city_haze_note']='Original and local fog volumes retained but hidden; one large continuous envelope avoids seams between local volume boxes in reverse shots.'
sc.camera=next(o for o in sc.objects if o.type=='CAMERA' and o.name.startswith('CAM_09'))
for screen in bpy.data.screens:
 for a in screen.areas:
  if a.type=='VIEW_3D':a.spaces.active.region_3d.view_perspective='CAMERA';a.spaces.active.shading.type='SOLID';a.spaces.active.clip_end=2000
bpy.ops.wm.save_as_mainfile(filepath=str(O/'ville-brutaliste-vis-a-vis.blend'),compress=True)
print('OPPOSITE_UI_READY',flush=True)
