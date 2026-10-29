import bpy,sys,json
from pathlib import Path
R=Path(__file__).parent;O=R/'output/tour-belvedere-v4'
bpy.ops.wm.open_mainfile(filepath=str(O/'tour-belvedere-herbe-hdri-v4.blend'))
sc=bpy.context.scene;p=bpy.context.preferences.addons['cycles'].preferences;p.compute_device_type='OPTIX';p.get_devices()
for d in p.devices:d.use=d.type!='CPU'
sc.cycles.device='GPU';sc.cycles.samples=48;sc.cycles.use_denoising=True;sc.render.use_persistent_data=True;sc.render.resolution_percentage=100
jobs=[('CAM_02 · ensemble frontal','01-ensemble-hdri',1440,960),('CAM_06 · facade est','02-contact-batiment',1440,960),('CAM_08 · pied rapproche','03-terrain-herbe',1200,1200),('CAM_14 · panorama 360','04-panorama-hdri',2400,1200)]
if '--all-cameras' in sys.argv:
    jobs=[(c.name,c.name.split(' · ')[0],int(c.get('pa_resolution_x',1440)),int(c.get('pa_resolution_y',960))) for c in sorted(sc.objects,key=lambda o:o.name) if c.type=='CAMERA' and c.name.startswith('CAM_')]
    jobs=[(c,n,min(w,1440),int(h*min(w,1440)/w)) for c,n,w,h in jobs]
if '--quick' in sys.argv:
    sc.cycles.samples=20;jobs=[(c,n+'-preview',960,int(h*960/w)) for c,n,w,h in jobs[:3]]
for cam,name,w,h in jobs:
    sc.camera=bpy.data.objects[cam];sc.render.resolution_x=w;sc.render.resolution_y=h;sc.render.filepath=str(O/(name+'.png'));bpy.ops.render.render(write_still=True);print('V4_RENDER',name,flush=True)
(O/('renders-preview.json' if '--quick' in sys.argv else 'renders.json')).write_text(json.dumps(jobs,ensure_ascii=False,indent=2),encoding='utf8')
print('V4_RENDERS_DONE',flush=True)
