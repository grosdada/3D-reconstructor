import bpy,sys,json
from pathlib import Path
R=Path(__file__).parent;O=R/'output/station-sas-v1'
bpy.ops.wm.open_mainfile(filepath=str(O/'station-sas-modulaire-texturee-v1.blend'));sc=bpy.context.scene
p=bpy.context.preferences.addons['cycles'].preferences;p.compute_device_type='OPTIX';p.get_devices()
for d in p.devices:d.use=d.type!='CPU'
sc.cycles.device='GPU';sc.cycles.samples=32;sc.cycles.use_denoising=True;sc.render.use_persistent_data=True;sc.render.resolution_percentage=100
cams=sorted([o for o in sc.objects if o.type=='CAMERA' and o.name.startswith('CAM_')],key=lambda o:o.name)
if '--quick' in sys.argv:cams=cams[:3];sc.cycles.samples=24
jobs=[]
for cam in cams:
    sc.camera=cam;w=cam.get('pa_resolution_x',1440);h=cam.get('pa_resolution_y',960)
    if '--quick' in sys.argv:h=int(h*1000/w);w=1000
    sc.render.resolution_x=w;sc.render.resolution_y=h;name=cam.name.split(' · ')[0]+('-preview' if '--quick' in sys.argv else '')
    sc.render.filepath=str(O/(name+'.png'));bpy.ops.render.render(write_still=True);jobs.append({'camera':cam.name,'file':name+'.png','size':[w,h]});print('STATION_RENDER',name,flush=True)
(O/('renders-preview.json' if '--quick' in sys.argv else 'renders.json')).write_text(json.dumps(jobs,ensure_ascii=False,indent=2),encoding='utf8');print('STATION_RENDERS_DONE',flush=True)
