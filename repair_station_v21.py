import bpy,sys,json,hashlib
from pathlib import Path
R=Path(__file__).parent;O=R/'output/station-sas-v2.1';sys.path.insert(0,str(R));import pano_atelier
from pano_atelier import station_surface_repairs as repair
bpy.ops.wm.open_mainfile(filepath=str(R/'output/station-sas-v2/station-sas-modulaire-texturee-v2.blend'));pano_atelier.register();sc=bpy.context.scene
def fingerprint():
    return hashlib.sha256(str([(o.name,o.parent.name if o.parent else '',tuple(tuple(r) for r in o.matrix_world),[(tuple(v.co)) for v in o.data.vertices] if o.type=='MESH' else None) for o in sorted(sc.objects,key=lambda o:o.name) if not o.get('pa_atmosphere')]).encode()).hexdigest()
before=fingerprint();report={}
report['repair']=repair.patch_projection(sc,'avant',O/'textures/avant-sans-faux-joints-proposition.png',O/'textures/masque-faux-joints.png')
report['floor']=repair.floor_relief(sc)
report['atmosphere']=repair.depth_haze(sc)
assert fingerprint()==before;report['existing_geometry_parents_transforms_unchanged']=True
sc.name='Station · V2.1 raccord plaques atmosphere';sc.pa_modular.output=str(O);sc.pa_settings.output=str(O);sc['pa_output']=str(O)
sc.render.resolution_x=1800;sc.render.resolution_y=1200;sc.cycles.samples=64
(O/'repair-report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf8')
bpy.ops.wm.save_as_mainfile(filepath=str(O/'station-sas-modulaire-texturee-v2.1.blend'));print('STATION_V21_SAVED',flush=True)
