import bpy,sys,json,time,math,hashlib
from pathlib import Path
from mathutils import Vector
R=Path(__file__).parent;O=R/'output/ville-brutaliste-v2';sys.path.insert(0,str(R));import pano_atelier
from pano_atelier.city_optimize import metrics
times={}
for version,path in [('v1',R/'output/ville-brutaliste-v1/ville-brutaliste-A1.blend'),('v2',O/'ville-brutaliste-V2.blend')]:
 t=time.perf_counter();bpy.ops.wm.open_mainfile(filepath=str(path));bpy.context.view_layer.update();times[version]=time.perf_counter()-t
pano_atelier.register();sc=bpy.context.scene
assert bpy.types.Operator.bl_rna_get_subclass_py('PA_OT_optimize_city')
assert not bpy.ops.pa.optimize_city.poll()
assert not bpy.ops.pa.project_city_details.poll()
root=bpy.data.objects['A1 · tour mince perforee'];children=list(root.children_recursive);old=root.matrix_basis.copy();before={o.name:o.matrix_world.copy() for o in sc.objects};root_world=root.matrix_world.copy()
def signature(me,attr):
 return hashlib.sha256(b''.join(__import__('struct').pack('fff',*v.vector) for v in me.attributes[attr].data)).hexdigest()
projected=next(o for o in children if o.type=='MESH' and o.get('pa_city_project'))
attrs={n:signature(projected.data,n) for n in ('PA_CityRest','PA_CityNormal','PA_CityRest_02','PA_CityNormal_02','PA_SourceLocal','PA_BuildingLocal')}
root.location.x+=5;root.rotation_euler.z+=.25;bpy.context.view_layer.update();delta=root.matrix_world@root_world.inverted()
for o in children:
 expected=delta@before[o.name]
 assert max(abs(o.matrix_world[i][j]-expected[i][j]) for i in range(4) for j in range(4))<.0002,o.name
for o in sc.objects:
 if o not in children and o!=root:assert max(abs(o.matrix_world[i][j]-before[o.name][i][j]) for i in range(4) for j in range(4))<.0002,o.name
assert attrs=={n:signature(projected.data,n) for n in attrs}
root.matrix_basis=old;bpy.context.view_layer.update()
missing=[];images=[]
for im in bpy.data.images:
 if im.source=='FILE':
  images.append({'name':im.name,'size':list(im.size),'packed':bool(im.packed_file)})
  if not im.packed_file and not Path(bpy.path.abspath(im.filepath)).is_file():missing.append(im.name)
assert not missing,missing
linked=[d.name for seq in (bpy.data.objects,bpy.data.meshes,bpy.data.materials,bpy.data.node_groups,bpy.data.images) for d in seq if d.library and d.users]
assert not linked,linked
cars=[o for o in sc.objects if o.get('pa_asset_model')];assert len(cars)==13
assert len({o.data.as_pointer() for o in cars})==3
contacts=[min((o.matrix_world@Vector(p)).z for p in o.bound_box) for o in cars];assert all(-.01<z<.03 for z in contacts),contacts
for m in bpy.data.materials:
 if m.get('pa_projection_strength'):
  bs=m.node_tree.nodes.get('Principled BSDF');assert not bs.inputs['Emission Color'].is_linked
  assert not bs.inputs['Roughness'].links[0].from_node.type=='TEX_IMAGE'
report={'addon_version':list(pano_atelier.bl_info['version']),'metrics':metrics(sc),'file_load_and_update_seconds':times,'building_move_rotate_test':True,'other_buildings_unchanged':True,'material_coordinates_stable':True,'projection_coordinates_stable':True,'cars':len(cars),'shared_car_meshes':3,'car_ground_z_range':[min(contacts),max(contacts)],'images':images,'missing_images':missing,'used_linked_data':linked,'projection_base_color_only':True,'optimized_operator_repeat_disabled':True}
report['projection_layers']=json.loads(sc['pa_city_projection_layers']);assert len(report['projection_layers'])==2
assert report['metrics']['objects']<250
(O/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('CITY_V2_VALIDATION_OK',json.dumps({k:v for k,v in report.items() if k!='images'}),flush=True)
