import bpy,sys,json,shutil
from pathlib import Path
R=Path(__file__).parent;O=R/'output/gas-station-exterior-v1';O.mkdir(exist_ok=True);sys.path.insert(0,str(R))
from pano_atelier.gas_station import build
bpy.ops.wm.read_factory_settings(use_empty=True);sc=bpy.context.scene;sc.name='Station abandonnee · exterieur'
report=build(sc);sc['pa_output']=str(O)
shutil.copy2(r'C:\Users\pc\Downloads\035-gas-station_grid_v2.jpg',O/'reference.jpg')
(O/'scene-report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf8')
sc.cycles.device='GPU';bpy.ops.wm.save_as_mainfile(filepath=str(O/'station-exterieur-base.blend'),compress=True)
p=bpy.context.preferences.addons['cycles'].preferences;p.compute_device_type='OPTIX';p.get_devices()
for d in p.devices:d.use=d.type!='CPU'
sc.cycles.samples=24;sc.render.resolution_percentage=70;sc.render.use_persistent_data=True
for i in (1,2,3):
 sc.camera=next(o for o in sc.objects if o.type=='CAMERA' and o.name.startswith('CAM_%02d'%i));sc.render.filepath=str(O/('preview-%02d.png'%i));bpy.ops.render.render(write_still=True);print('GAS_PREVIEW',i,flush=True)
