import bpy,sys,json
from pathlib import Path
R=Path(__file__).parent;O=R/'output/station-sas-v2'
bpy.ops.wm.open_mainfile(filepath=str(O/'station-sas-modulaire-texturee-v2.blend'));sc=bpy.context.scene
p=bpy.context.preferences.addons['cycles'].preferences;p.compute_device_type='OPTIX';p.get_devices()
for d in p.devices:d.use=d.type!='CPU'
sc.cycles.device='GPU';sc.cycles.samples=40;sc.cycles.use_denoising=True;sc.render.use_persistent_data=True;sc.render.resolution_percentage=100
cams=sorted([o for o in sc.objects if o.type=='CAMERA' and o.name.startswith('CAM_')],key=lambda o:o.name)
quick='--quick' in sys.argv
if quick:cams=[cams[0],cams[4],cams[5]];sc.cycles.samples=24
jobs=[]
for cam in cams:
    sc.camera=cam;w=cam.get('pa_resolution_x',1440);h=cam.get('pa_resolution_y',960)
    if quick:h=int(h*1100/w);w=1100
    else:h=int(h*1800/w);w=1800 if cam.data.type!='PANO' else 3000;h=h if cam.data.type!='PANO' else 1500
    sc.render.resolution_x=w;sc.render.resolution_y=h;name=cam.name.split(' · ')[0]+('-preview' if quick else '')
    sc.render.filepath=str(O/(name+'.png'));bpy.ops.render.render(write_still=True);jobs.append({'camera':cam.name,'file':name+'.png','size':[w,h]});print('V2_RENDER',name,flush=True)
(O/('renders-preview.json' if quick else 'renders.json')).write_text(json.dumps(jobs,ensure_ascii=False,indent=2),encoding='utf8');print('V2_RENDERS_DONE',flush=True)
