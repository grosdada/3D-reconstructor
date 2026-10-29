import bpy,sys,json,time,ast,hashlib,array
from pathlib import Path
from mathutils import Vector
R=Path(__file__).parent;O=R/'output/ville-brutaliste-v4-mobilier';sys.path.insert(0,str(R));import pano_atelier
from pano_atelier.city_optimize import metrics
# Reuse the previous pass's fingerprint helpers, without running its scene mutations.
tree=ast.parse((R/'validate_city_opposite.py').read_text(encoding='utf8'))
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef)],type_ignores=[]),'validation_helpers','exec'))
bpy.ops.wm.open_mainfile(filepath=str(R/'output/ville-brutaliste-v3-vis-a-vis/ville-brutaliste-vis-a-vis.blend'));bpy.context.view_layer.update();before=snapshot(bpy.context.scene)
t=time.perf_counter();bpy.ops.wm.open_mainfile(filepath=str(O/'ville-brutaliste-mobilier.blend'));bpy.context.view_layer.update();load_seconds=time.perf_counter()-t
sc=bpy.context.scene;after=snapshot(sc);diff=[(category,name) for category in before for name,value in before[category].items() if after[category].get(name)!=value];assert not diff,diff
pano_atelier.register();assert not bpy.ops.pa.dress_city.poll()
sc.pa_city.output=str(O);sc.pa_city.asset_root=r'K:\Connector-Blender\Blender-asset-lib-VDB';sc.pa_city.ring_fog_density=.045
# Verify the new control drives both rings, while leaving the foreground haze intact.
base=bpy.data.materials['VIS · atmosphere urbaine continue'].node_tree.nodes['Brume continue'].inputs['Density'].default_value
sc.pa_city.ring_fog_density=.02
rings=[o for o in sc.objects if o.get('pa_ring_fog')];assert len(rings)==2
assert sorted(round(o.active_material.node_tree.nodes['Densite anneau'].outputs[0].default_value,5) for o in rings)==[.02,.03111]
assert base==bpy.data.materials['VIS · atmosphere urbaine continue'].node_tree.nodes['Brume continue'].inputs['Density'].default_value
sc.pa_city.ring_fog_density=.045
# Move + rotate an assembly and check its children and UV data, with neighbours fixed.
root=next(o for o in sc.objects if o.get('pa_street_sign'));children=list(root.children_recursive);saved=root.matrix_basis.copy();oldworld=root.matrix_world.copy();matrices={o.name:o.matrix_world.copy() for o in sc.objects if not o.hide_viewport}
uvs={o.name:vec_digest(o.data.uv_layers.active.data,'uv',len(o.data.loops)*2) for o in children if o.type=='MESH' and o.data.uv_layers.active}
root.location.x+=3;root.location.y+=2;root.rotation_euler.z+=.3;bpy.context.view_layer.update();delta=root.matrix_world@oldworld.inverted()
for o in sc.objects:
 if o.name not in matrices:continue
 expected=delta@matrices[o.name] if o in children or o==root else matrices[o.name]
 assert max(abs(o.matrix_world[i][j]-expected[i][j]) for i in range(4) for j in range(4))<.0002,o.name
assert uvs=={o.name:vec_digest(o.data.uv_layers.active.data,'uv',len(o.data.loops)*2) for o in children if o.type=='MESH' and o.data.uv_layers.active}
root.matrix_basis=saved;bpy.context.view_layer.update()
missing=[im.name for im in bpy.data.images if im.source=='FILE' and not im.packed_file and not Path(bpy.path.abspath(im.filepath)).is_file()];assert not missing,missing
linked=[d.name for seq in (bpy.data.objects,bpy.data.meshes,bpy.data.materials,bpy.data.node_groups,bpy.data.images) for d in seq if d.library and d.users];assert not linked,linked
furniture=[o for o in sc.objects if o.get('pa_street_furniture')];assert len({o.data.as_pointer() for o in furniture})==6
report={'addon':list(pano_atelier.bl_info['version']),'preserved_v3_objects':len(before['objects']),'preserved_geometry_materials_transforms':not diff,'load_and_update_seconds':load_seconds,'metrics':metrics(sc),'movable_sign_children_and_uvs':True,'neighbours_unchanged':True,'furniture_objects':len(furniture),'furniture_shared_meshes':6,'missing_images':missing,'used_linked_data':linked,'ring_control_test':True,'foreground_haze_unchanged':True,'duplicate_recipe_disabled':True}
(O/'validation.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf8');print('V4_VALIDATED',json.dumps(report),flush=True)
sc.camera=next(o for o in sc.objects if o.type=='CAMERA' and o.name.startswith('CAM_09'));sc.render.resolution_x=2200;sc.render.resolution_y=1210;sc.render.resolution_percentage=100;sc.cycles.samples=48;sc.cycles.use_denoising=True;sc.cycles.device='GPU';sc.render.image_settings.file_format='PNG';sc.render.image_settings.color_mode='RGB'
for screen in bpy.data.screens:
 for a in screen.areas:
  if a.type=='VIEW_3D':a.spaces.active.shading.type='SOLID';a.spaces.active.region_3d.view_perspective='CAMERA';a.spaces.active.clip_end=2000
sc['pa_dressing_report']=(O/'build-report.json').read_text(encoding='utf8')
bpy.ops.wm.save_as_mainfile(filepath=str(O/'ville-brutaliste-mobilier.blend'),compress=True)
p=bpy.context.preferences.addons['cycles'].preferences;p.compute_device_type='OPTIX';p.get_devices()
for d in p.devices:d.use=d.type!='CPU'
sc.render.use_persistent_data=True;jobs=[]
for i in (9,10,12,13,14):
 sc.camera=next(o for o in sc.objects if o.type=='CAMERA' and o.name.startswith('CAM_%02d'%i));sc.render.resolution_x=2200 if i==9 else 1800;sc.render.resolution_y=1210 if i==9 else 990
 sc.render.filepath=str(O/('CAM_%02d.png'%i));t=time.perf_counter();bpy.ops.render.render(write_still=True)
 jobs.append({'camera':sc.camera.name,'file':sc.render.filepath,'seconds':time.perf_counter()-t});print('V4_RENDER',i,flush=True)
(O/'renders.json').write_text(json.dumps(jobs,indent=2,ensure_ascii=False),encoding='utf8')
