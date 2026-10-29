import bpy,sys,json,hashlib
from pathlib import Path
R=Path(__file__).parent;sys.path.insert(0,str(R));O=R/'output/gas-station-v2';O.mkdir(exist_ok=True)
from pano_atelier import gas_weather,gas_interior,gas_details
from pano_atelier.city_optimize import metrics
source=R/'output/gas-station-exterior-v1/station-exterieur.blend';digest=hashlib.sha256(source.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(source));sc=bpy.context.scene
groups,pure,changed=gas_weather.install(sc)
interior=gas_interior.build(sc,pure[0],pure[1])
dressing=gas_details.dress(sc,Path(r'K:\Connector-Blender\Blender-asset-lib-VDB\Trash-kit\TrashKit.blend'))
sc['pa_output']=str(O);sc['pa_gas_phase']='V2 - procedural white/blue paint, Trash-Kit dressing, dirty roofs, reference-inspired corridor and service rooms.'
sc['pa_gas_v2']=True
# Independent image-free material library, suitable for the user's Asset Browser.
bpy.data.libraries.write(str(O/'Peintures-procedurales.blend'),set(pure),fake_user=True,compress=True)
p=bpy.context.preferences.addons['cycles'].preferences;p.compute_device_type='OPTIX';p.get_devices()
for d in p.devices:d.use=d.type!='CPU'
sc.cycles.device='GPU';sc.cycles.samples=64;sc.cycles.use_denoising=True;sc.render.resolution_x=1800;sc.render.resolution_y=1200;sc.render.resolution_percentage=100
sc.camera=next(o for o in sc.objects if o.type=='CAMERA' and o.name.startswith('CAM_01'))
for im in bpy.data.images:
 if im.source=='FILE' and not im.packed_file:
  try:im.pack()
  except RuntimeError:pass
report={'source':str(source),'source_sha256':digest,'materials':changed,'interior':interior,'dressing':dressing,'metrics':metrics(sc),'pure_materials':[m.name for m in pure]}
bpy.ops.wm.save_as_mainfile(filepath=str(O/'station-v2-exterieur-interieur.blend'),compress=True)
assert hashlib.sha256(source.read_bytes()).hexdigest()==digest
(O/'scene-report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf8')
sc.cycles.samples=24;sc.render.resolution_percentage=65;sc.render.use_persistent_data=True
for i in (1,4,7,8,9,10):
 sc.camera=next(o for o in sc.objects if o.type=='CAMERA' and o.name.startswith('CAM_%02d'%i));sc.render.filepath=str(O/('preview-%02d.png'%i));bpy.ops.render.render(write_still=True);print('V2_PREVIEW',i,flush=True)
