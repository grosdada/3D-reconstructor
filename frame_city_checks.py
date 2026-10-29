import bpy
from pathlib import Path
from mathutils import Vector
R=Path(__file__).parent;O=R/'output/ville-brutaliste-v1';bpy.ops.wm.open_mainfile(filepath=str(O/'ville-brutaliste-A1.blend'));sc=bpy.context.scene
jobs=[]
for prefix,loc,target,lens in [('CAM_05',(106,-115,51),(0,16,38),35),('CAM_06',(-44,60,14),(3,13,35),21)]:
 cam=next(o for o in sc.objects if o.type=='CAMERA' and o.name.startswith(prefix));cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.lens=lens;jobs.append((cam,prefix))
bpy.context.view_layer.update();bpy.ops.wm.save_as_mainfile(filepath=str(O/'ville-brutaliste-A1.blend'))
p=bpy.context.preferences.addons['cycles'].preferences;p.compute_device_type='OPTIX';p.get_devices()
for d in p.devices:d.use=d.type!='CPU'
sc.cycles.device='GPU';sc.cycles.samples=32;sc.cycles.use_denoising=True;sc.render.use_persistent_data=True;sc.render.resolution_percentage=100;sc.render.resolution_x=1600;sc.render.resolution_y=1000
for cam,prefix in jobs:
 sc.camera=cam;sc.render.filepath=str(O/(prefix+'.png'));bpy.ops.render.render(write_still=True);print('CITY_FRAMING_RENDER',prefix,flush=True)
