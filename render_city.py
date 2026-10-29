import bpy,json,sys
from pathlib import Path
R=Path(__file__).parent;O=R/'output/ville-brutaliste-v1';bpy.ops.wm.open_mainfile(filepath=str(O/'ville-brutaliste-A1.blend'));sc=bpy.context.scene
p=bpy.context.preferences.addons['cycles'].preferences;p.compute_device_type='OPTIX';p.get_devices()
for d in p.devices:d.use=d.type!='CPU'
sc.cycles.device='GPU';sc.cycles.samples=48;sc.cycles.use_denoising=True;sc.render.use_persistent_data=True;sc.render.resolution_percentage=100
cams=sorted([o for o in sc.objects if o.type=='CAMERA' and o.name.startswith('CAM_')],key=lambda o:o.name)
jobs=[]
for i in (0,1,3,4,5):
 cam=cams[i];sc.camera=cam;sc.cycles.samples=32
 sc.render.resolution_x=1800 if i==0 else 1600;sc.render.resolution_y=1000
 sc.render.filepath=str(O/('CAM_%02d.png'%(i+1)));bpy.ops.render.render(write_still=True);jobs.append({'camera':cam.name,'image':sc.render.filepath});print('CITY_RENDER_DONE',cam.name,flush=True)
 if '--hero' in sys.argv:break
(O/'renders.json').write_text(json.dumps(jobs,ensure_ascii=False,indent=2),encoding='utf8');print('CITY_RENDERS_DONE',flush=True)
