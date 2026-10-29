"""Actual camera renders for mapped surfaces and full forest surround."""
import bpy,json,sys
from pathlib import Path
R=Path(__file__).parent;O=R/'output/tour-belvedere-v3'
bpy.ops.wm.open_mainfile(filepath=str(O/'tour-belvedere-foret-360-v3.blend'))
sc=bpy.context.scene
p=bpy.context.preferences.addons['cycles'].preferences;p.compute_device_type='OPTIX';p.get_devices()
for d in p.devices:d.use=d.type!='CPU'
sc.cycles.device='GPU';sc.cycles.samples=48;sc.cycles.use_denoising=True;sc.render.use_persistent_data=True;sc.render.resolution_percentage=100
jobs=[('CAM_02 · ensemble frontal','01-ensemble-foret',1440,960),('CAM_07 · arriere annexe','02-facade-arriere',1440,960),('CAM_06 · facade est','03-facade-est',1440,960),('CAM_08 · pied rapproche','04-pied-mappe',1200,1200),('CAM_14 · panorama 360','05-panorama-360',2400,1200),('CAM_15 · ensemble foret','06-ceinture-aerienne',1440,960),('CAM_01 · reference portrait','07-reference',1000,1200),('CAM_09 · face ouest','08-facade-ouest',1440,960)]
if '--quick' in sys.argv:
    jobs=jobs[:2]+jobs[4:6];sc.cycles.samples=24
    jobs=[(cam,name+'-preview',min(w,1200),int(h*min(w,1200)/w)) for cam,name,w,h in jobs]
for camera,name,w,h in jobs:
    sc.camera=bpy.data.objects[camera];sc.render.resolution_x=w;sc.render.resolution_y=h;sc.render.filepath=str(O/(name+'.png'))
    bpy.ops.render.render(write_still=True);print('V3_RENDER',name,flush=True)
(O/('renders-preview.json' if '--quick' in sys.argv else 'renders.json')).write_text(json.dumps(jobs,ensure_ascii=False,indent=2),encoding='utf8')
print('V3_RENDERS_DONE',flush=True)
