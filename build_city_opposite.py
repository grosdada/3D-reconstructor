import bpy,sys,json,hashlib
from pathlib import Path
R=Path(__file__).parent;O=R/'output/ville-brutaliste-v3-vis-a-vis';O.mkdir(exist_ok=True);sys.path.insert(0,str(R))
from pano_atelier.city_opposite import build
bpy.ops.wm.open_mainfile(filepath=str(R/'output/ville-brutaliste-v2/ville-brutaliste-V2.blend'));sc=bpy.context.scene
baseline={o.name:{'matrix':[list(r) for r in o.matrix_world],'data':o.data.name if o.data else None} for o in sc.objects}
r=build(sc);sc.name='Ville A1 · V3 · vis-a-vis';sc['pa_output']=str(O);sc.cycles.device='GPU';sc.cycles.samples=48;sc.render.filepath=str(O/'rendu-utilisateur.png')
(O/'build-report.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf8');(O/'baseline-v2.json').write_text(json.dumps(baseline,ensure_ascii=False),encoding='utf8')
bpy.ops.wm.save_as_mainfile(filepath=str(O/'ville-brutaliste-vis-a-vis.blend'),compress=True)
p=bpy.context.preferences.addons['cycles'].preferences;p.compute_device_type='OPTIX';p.get_devices()
for d in p.devices:d.use=d.type!='CPU'
sc.cycles.samples=24;sc.render.resolution_percentage=65;sc.render.filepath=str(O/'preview-vis-a-vis.png');bpy.ops.render.render(write_still=True);print('OPPOSITE_PREVIEW_READY',json.dumps(r),flush=True)
