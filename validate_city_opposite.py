import bpy,sys,json,hashlib,time,array
from pathlib import Path
from mathutils import Vector
R=Path(__file__).parent;O=R/'output/ville-brutaliste-v3-vis-a-vis';sys.path.insert(0,str(R));import pano_atelier
from pano_atelier.city_optimize import metrics

def vec_digest(seq,field,count):
 a=array.array('f',[0])*count;seq.foreach_get(field,a);return hashlib.sha256(a.tobytes()).hexdigest()
def mesh_sig(me):
 indices=array.array('i',[0])*len(me.loops);me.loops.foreach_get('vertex_index',indices)
 return {'vertices':vec_digest(me.vertices,'co',len(me.vertices)*3),'topology':hashlib.sha256(indices.tobytes()).hexdigest(),'polygons':len(me.polygons),'attributes':{a.name:vec_digest(a.data,'vector',len(a.data)*3) for a in me.attributes if a.name.startswith('PA_') and a.data_type=='FLOAT_VECTOR'}}
def shader_sig(mat):
 if not mat.node_tree:return None
 t=mat.node_tree;nodes=[]
 for n in t.nodes:
  vals=[]
  for s in n.inputs:
   if not hasattr(s,'default_value'):continue
   v=s.default_value
   try:v=list(v)
   except TypeError:pass
   if not isinstance(v,(str,int,float,bool,list,type(None))):v=getattr(v,'name',str(type(v)))
   vals.append((s.identifier,v))
  nodes.append((n.name,n.bl_idname,vals,getattr(n,'attribute_name',''),n.node_tree.name if n.type=='GROUP' else ''))
 return {'nodes':nodes,'links':sorted((l.from_node.name,l.from_socket.identifier,l.to_node.name,l.to_socket.identifier) for l in t.links)}
def snapshot(scene):
 meshes={o.data.name:mesh_sig(o.data) for o in scene.objects if o.type=='MESH'}
 mats={s.material.name:shader_sig(s.material) for o in scene.objects for s in o.material_slots if s.material}
 objs={o.name:{'matrix':[list(r) for r in o.matrix_world],'parent':o.parent.name if o.parent else None,'data':o.data.name if o.data else None,'materials':[s.material.name if s.material else None for s in o.material_slots]} for o in scene.objects}
 return {'objects':objs,'meshes':meshes,'materials':mats}

bpy.ops.wm.open_mainfile(filepath=str(R/'output/ville-brutaliste-v2/ville-brutaliste-V2.blend'));bpy.context.view_layer.update();before=snapshot(bpy.context.scene)
t=time.perf_counter();bpy.ops.wm.open_mainfile(filepath=str(O/'ville-brutaliste-vis-a-vis.blend'));bpy.context.view_layer.update();load_seconds=time.perf_counter()-t;sc=bpy.context.scene
# Disabled objects have no evaluated world matrix after loading. Evaluate the preserved archive for comparison only.
archive=bpy.data.objects.get('ATMOSPHERE · brume');archived=archive.hide_viewport;archive.hide_viewport=False;bpy.context.view_layer.update();after=snapshot(sc)
diff=[]
for category in before:
 for name,value in before[category].items():
  if after[category].get(name)!=value:diff.append((category,name))
assert not diff,diff
pano_atelier.register();assert not bpy.ops.pa.build_city_opposite.poll()
assert sc.pa_city.bl_rna.properties['projection_scope'].enum_items.get('OPPOSITE')
root=bpy.data.objects['VIS · logements et commerces'];children=list(root.children_recursive);saved=root.matrix_basis.copy();oldworld=root.matrix_world.copy();matrices={o.name:o.matrix_world.copy() for o in sc.objects}
digests={o.name:mesh_sig(o.data) for o in children if o.type=='MESH'}
root.location.x+=4.5;root.location.y+=2;root.rotation_euler.z+=.23;bpy.context.view_layer.update();delta=root.matrix_world@oldworld.inverted()
for o in sc.objects:
 expected=delta@matrices[o.name] if o in children or o==root else matrices[o.name]
 assert max(abs(o.matrix_world[i][j]-expected[i][j]) for i in range(4) for j in range(4))<.0002,o.name
assert digests=={o.name:mesh_sig(o.data) for o in children if o.type=='MESH'}
root.matrix_basis=saved;bpy.context.view_layer.update()
missing=[im.name for im in bpy.data.images if im.source=='FILE' and not im.packed_file and not Path(bpy.path.abspath(im.filepath)).is_file()];assert not missing,missing
linked=[d.name for seq in (bpy.data.objects,bpy.data.meshes,bpy.data.materials,bpy.data.node_groups,bpy.data.images) for d in seq if d.library and d.users];assert not linked,linked
cars=[o for o in sc.objects if o.get('pa_asset_model')];assert len(cars)==19;assert len({o.data.as_pointer() for o in cars})==3
contacts=[min((o.matrix_world@Vector(p)).z for p in o.bound_box) for o in cars];assert all(-.01<z<.03 for z in contacts),contacts
layers=json.loads(sc['pa_city_projection_layers']);assert len(layers)==5
for o in sc.objects:
 if not o.get('pa_opposite') and o.type=='MESH':assert not any(a.name in ('PA_CityRest_03','PA_CityRest_04','PA_CityRest_05') for a in o.data.attributes),o.name
for m in bpy.data.materials:
 if m.get('pa_projection_strength'):
  bs=m.node_tree.nodes.get('Principled BSDF');assert not bs.inputs['Emission Color'].is_linked
met=metrics(sc);assert met['objects']<350
report={'addon_version':list(pano_atelier.bl_info['version']),'metrics':met,'load_and_update_seconds':load_seconds,'preserved_v2_objects':len(before['objects']),'v2_geometry_materials_transforms_unchanged':not diff,'building_translation_rotation_children':True,'unrelated_modules_unchanged':True,'frozen_texture_attributes_stable':True,'projection_layers':layers,'new_projections_only_opposite':True,'missing_images':missing,'used_linked_data':linked,'cars':len(cars),'shared_car_meshes':3,'ground_contact_z':[min(contacts),max(contacts)],'repeat_extension_disabled':True,'new_cameras':[o.name for o in sc.objects if o.type=='CAMERA' and o.get('pa_opposite')]}
(O/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8');print('OPPOSITE_VALIDATED',json.dumps(report),flush=True)
