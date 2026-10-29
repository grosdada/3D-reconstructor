import bpy,json,time
from pathlib import Path
from mathutils import Vector
R=Path(__file__).parent;O=R/'output/ville-brutaliste-v3-vis-a-vis'
bpy.ops.wm.open_mainfile(filepath=str(O/'ville-brutaliste-vis-a-vis.blend'));sc=bpy.context.scene
# Reframe the inspection view to clear the lamp post. Its texture projector stays frozen.
cam=next(o for o in sc.objects if o.type=='CAMERA' and o.name.startswith('CAM_11'))
cam.location=(-1,-48,4.5);cam.rotation_euler=(Vector((-18,-64,12))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.lens=32
sc.camera=next(o for o in sc.objects if o.type=='CAMERA' and o.name.startswith('CAM_09'))
sc.render.resolution_x=2200;sc.render.resolution_y=1210;sc.render.resolution_percentage=100
sc.cycles.device='GPU';sc.cycles.use_denoising=True;sc.cycles.samples=48
bpy.ops.wm.save_as_mainfile(filepath=str(O/'ville-brutaliste-vis-a-vis.blend'),compress=True)
p=bpy.context.preferences.addons['cycles'].preferences;p.compute_device_type='OPTIX';p.get_devices()
for d in p.devices:d.use=d.type!='CPU'
sc.render.use_persistent_data=True;sc.render.image_settings.file_format='PNG';sc.render.image_settings.color_mode='RGB';jobs=[]
for i in (9,10,11,12,13):
 sc.camera=next(o for o in sc.objects if o.type=='CAMERA' and o.name.startswith('CAM_%02d'%i))
 sc.render.resolution_x=2200 if i==9 else 1800;sc.render.resolution_y=1210 if i==9 else 990
 sc.render.filepath=str(O/('CAM_%02d.png'%i));t=time.perf_counter();bpy.ops.render.render(write_still=True)
 jobs.append({'camera':sc.camera.name,'file':sc.render.filepath,'seconds':time.perf_counter()-t});print('V3_RENDER',json.dumps(jobs[-1]),flush=True)
(O/'renders.json').write_text(json.dumps(jobs,ensure_ascii=False,indent=2),encoding='utf8')
print('ALL_OPPOSITE_RENDERS_DONE',flush=True)
