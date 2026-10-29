import bpy,sys,json,zipfile,ast
from pathlib import Path
R=Path(__file__).parent;O=R/'output/station-sas-v2.2';sys.path.insert(0,str(R));import pano_atelier
bpy.ops.wm.open_mainfile(filepath=str(O/'station-sas-modulaire-texturee-v2.2.blend'));pano_atelier.register();sc=bpy.context.scene
assert pano_atelier.bl_info['version']==(0,4,3)
assert bpy.types.Operator.bl_rna_get_subclass_py('PA_OT_procedural_station')
assert not bpy.ops.pa.procedural_station.poll()
from pano_atelier.station_procedural import apply
count=len(sc.objects)
try:apply(sc)
except ValueError:pass
else:raise AssertionError('Second pass must be refused')
assert len(sc.objects)==count
m=bpy.data.materials['V2 · plaques de sol use fine'];b=m.node_tree.nodes['Normal · relief antiderapant fin'];old=sc.pa_modular.plate_relief_mm
sc.pa_modular.plate_relief_mm=.4;assert abs(b.inputs['Distance'].default_value-.0004)<1e-7;sc.pa_modular.plate_relief_mm=old
meshtris=sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in sc.objects if o.type=='MESH')
dg=bpy.context.evaluated_depsgraph_get();evaluated_plate_tris=0
for o in sc.objects:
 if o.get('pa_machined_plate'):
  e=o.evaluated_get(dg);me=e.to_mesh();evaluated_plate_tris+=sum(len(p.vertices)-2 for p in me.polygons);e.to_mesh_clear()
with zipfile.ZipFile(R/'dist/pano_atelier-0.4.3.zip') as z:
 assert len(z.namelist())==18
 for name in z.namelist():
  assert name.endswith(('.py','.toml'))
  if name.endswith('.py'):ast.parse(z.read(name).decode('utf8'))
report={'version':[0,4,3],'ui_operator_registered':True,'repeat_guard':True,'floor_control_works':True,'addon_package_source_only':True,'objects':count,'base_mesh_triangles_object_sum':meshtris,'evaluated_plate_triangles':evaluated_plate_tris,'images':len(bpy.data.images),'missing_file_images':[i.name for i in bpy.data.images if i.source=='FILE' and not i.packed_file and not Path(bpy.path.abspath(i.filepath)).exists()]}
assert not report['missing_file_images']
(O/'addon-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8');print('V22_VALIDATION_OK',json.dumps(report),flush=True)
