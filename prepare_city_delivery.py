import bpy,json
from pathlib import Path
R=Path(__file__).parent;O=R/'output/ville-brutaliste-v1';bpy.ops.wm.open_mainfile(filepath=str(O/'ville-brutaliste-A1.blend'));sc=bpy.context.scene
sc.cycles.device='GPU';sc.render.filepath=str(O/'rendu-utilisateur.png')
for o in sc.objects:
 if o.type=='CAMERA' and o.name.startswith(('CAM_02','CAM_04','CAM_05','CAM_06')):o['pa_resolution_x']=1600;o['pa_resolution_y']=1000
for screen in bpy.data.screens:
 for a in screen.areas:
  if a.type=='VIEW_3D':a.spaces.active.clip_end=2000;a.spaces.active.region_3d.view_perspective='CAMERA'
bpy.ops.wm.save_as_mainfile(filepath=str(O/'ville-brutaliste-A1.blend'));print('CITY_DELIVERY_SAVED',flush=True)
