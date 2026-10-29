import bpy,sys,json,hashlib,math
from pathlib import Path
from mathutils import Vector,Matrix
from bpy_extras.object_utils import world_to_camera_view
R=Path(__file__).parent;O=R/'output/ville-brutaliste-v1';sys.path.insert(0,str(R));import pano_atelier
bpy.ops.wm.open_mainfile(filepath=str(O/'ville-brutaliste-A1.blend'));pano_atelier.register();sc=bpy.context.scene
assert bpy.types.Operator.bl_rna_get_subclass_py('PA_OT_build_brutalist_city')
assert not bpy.ops.pa.project_city_details.poll()
root=bpy.data.objects['A1 · tour mince perforee'];children=list(root.children_recursive)
before={o.name:o.matrix_world.copy() for o in sc.objects};old=root.matrix_basis.copy();beforeworld=root.matrix_world.copy()
target=next(o for o in children if o.type=='MESH' and 'PA_CityRest' in o.data.attributes)
attributes=[tuple(e.vector) for e in target.data.attributes['PA_CityRest'].data]
root.location.x+=3.25;root.rotation_euler.z+=math.radians(12);bpy.context.view_layer.update();delta=root.matrix_world@beforeworld.inverted()
for o in children:
 expect=delta@before[o.name]
 assert max(abs(a-b) for a,b in zip(sum((list(r) for r in o.matrix_world),[]),sum((list(r) for r in expect),[])))<.001,o.name
assert attributes==[tuple(e.vector) for e in target.data.attributes['PA_CityRest'].data]
assert all(o.matrix_world==before[o.name] for o in sc.objects if o not in children and o!=root)
root.matrix_basis=old;bpy.context.view_layer.update()
images=[];missing=[]
for im in bpy.data.images:
 if im.source=='FILE':
  images.append({'name':im.name,'size':list(im.size),'packed':bool(im.packed_file),'linked':bool(im.library)})
  if not im.packed_file and not Path(bpy.path.abspath(im.filepath)).is_file():missing.append(im.name)
assert not missing
linked=[]
for seq in (bpy.data.objects,bpy.data.meshes,bpy.data.materials,bpy.data.node_groups,bpy.data.images):
 linked += [x.name for x in seq if x.library and x.users>0]
assert not linked,linked
for m in bpy.data.materials:
 if m.get('pa_projection_strength'):
  bs=m.node_tree.nodes.get('Principled BSDF');assert not bs.inputs['Emission Color'].is_linked
  assert not bs.inputs['Normal'].links[0].from_node.type=='TEX_IMAGE'
oldfog=sc.pa_city.fog_density;sc.pa_city.fog_density=.006;assert abs(bpy.data.materials['VILLE · brume atmospherique'].node_tree.nodes['Brume · faible devant dense derriere'].inputs['To Max'].default_value-.006)<1e-7;sc.pa_city.fog_density=oldfog
unique={o.data.name:o.data for o in sc.objects if o.type=='MESH'}
base=sum(sum(len(p.vertices)-2 for p in me.polygons) for me in unique.values())
dg=bpy.context.evaluated_depsgraph_get();evaluated=0
for o in sc.objects:
 if o.type=='MESH' and not o.hide_render:
  e=o.evaluated_get(dg);me=e.to_mesh();evaluated+=sum(len(p.vertices)-2 for p in me.polygons);e.to_mesh_clear()
# The view frustum encloses the central roof, unlike the initial inherited clip range.
anchor=root.matrix_world@Vector((0,0,70));uv=world_to_camera_view(sc,sc.camera,anchor);assert 0<uv.x<1 and 0<uv.y<1 and uv.z<sc.camera.data.clip_end
wheel_contacts=[]
for o in sc.objects:
 if o.type=='EMPTY' and o.name.startswith('VEHICULE · voiture'):
  wheels=[c for c in o.children if c.name.startswith('Roue')]
  wheel_contacts.extend([min((c.matrix_world@Vector(co)).z for co in c.bound_box) for c in wheels])
assert all(abs(z)<.02 for z in wheel_contacts)
cams=[o for o in sc.objects if o.type=='CAMERA' and o.name.startswith('CAM_')];assert len(cams)==7
report={'addon_version':list(pano_atelier.bl_info['version']),'objects':len(sc.objects),'module_roots':sum(bool(o.get('pa_module')) for o in sc.objects),'unique_base_triangles':base,'evaluated_mesh_triangles':evaluated,'cameras':[c.name for c in cams],'images':images,'missing_images':missing,'used_linked_dependencies':linked,'module_translation_rotation_test':True,'children_follow':True,'neighbors_unchanged':True,'projection_rest_coordinates_stable':True,'no_projected_emission':True,'fog_control_works':True,'wheel_contacts_m':[min(wheel_contacts),max(wheel_contacts)],'hero_in_frustum':True,'limitations':['A1 interpreted geometry, not surveyed reconstruction.','Single view albedo detail projection; other angles rely on procedural surfaces.','Exterior district; interiors not furnished.','Back and side blocks are inferred.']}
(O/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8');print('CITY_VALIDATION_OK',base,evaluated,flush=True)
