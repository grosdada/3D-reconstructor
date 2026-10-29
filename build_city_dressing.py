import bpy,sys,json,time
from pathlib import Path
R=Path(__file__).parent;O=R/'output/ville-brutaliste-v4-mobilier';O.mkdir(exist_ok=True);sys.path.insert(0,str(R))
from pano_atelier.city_dressing import build
from pano_atelier.city_optimize import metrics
bpy.ops.wm.open_mainfile(filepath=str(R/'output/ville-brutaliste-v3-vis-a-vis/ville-brutaliste-vis-a-vis.blend'));sc=bpy.context.scene
print('LOADED_V3',flush=True)
before=metrics(sc);print('BASE_METRICS',before,flush=True)
report=build(sc,Path(r'K:\Connector-Blender\Blender-asset-lib-VDB'));report['before']=before;report['after']=metrics(sc)
sc.name='Ville A1 · V4 · mobilier et Ring Fog';sc['pa_output']=str(O)
bpy.ops.file.pack_all();sc.camera=next(o for o in sc.objects if o.type=='CAMERA' and o.name.startswith('CAM_09'))
sc.render.resolution_x=2200;sc.render.resolution_y=1210;sc.render.resolution_percentage=100;sc.cycles.samples=48;sc.cycles.use_denoising=True;sc.cycles.device='GPU'
bpy.ops.wm.save_as_mainfile(filepath=str(O/'ville-brutaliste-mobilier.blend'),compress=True)
(O/'build-report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf8')
p=bpy.context.preferences.addons['cycles'].preferences;p.compute_device_type='OPTIX';p.get_devices()
for d in p.devices:d.use=d.type!='CPU'
sc.render.use_persistent_data=True;sc.cycles.samples=24;sc.render.resolution_x=1200;sc.render.resolution_y=660
for i in (9,10,12,14):
 sc.camera=next(o for o in sc.objects if o.type=='CAMERA' and o.name.startswith('CAM_%02d'%i));sc.render.filepath=str(O/('preview-%02d.png'%i));bpy.ops.render.render(write_still=True);print('DRESSING_PREVIEW',i,flush=True)
print('DRESSING_DONE',json.dumps(report),flush=True)
