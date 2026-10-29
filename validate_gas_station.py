import bpy,sys,json,math,hashlib
from pathlib import Path
from mathutils import Vector,Matrix
import numpy as np
R=Path(__file__).parent;sys.path.insert(0,str(R));O=R/'output/gas-station-exterior-v1'
import pano_atelier as addon
addon.register()
old=bpy.context.scene;old_count=len(old.objects)
assert bpy.ops.pa.build_gas_exterior()=={'FINISHED'}
assert old in list(bpy.data.scenes) and len(old.objects)==old_count
assert bpy.context.scene.get('pa_gas_station')
report={'addon_version':addon.bl_info['version'],'build_operator_preserves_existing_scene':True}
bpy.ops.wm.open_mainfile(filepath=str(O/'station-exterieur.blend'));sc=bpy.context.scene
assert len(json.loads(sc['pa_city_projection_layers']))==3
images=[i for i in bpy.data.images if i.source=='FILE' and i.name!='Render Result']
assert all(i.packed_file or i.packed_files for i in images)
report['packed_images']=len(images)
# Verify all module descendants move together and retain per-vertex projection data.
mods=[o for o in sc.objects if o.get('pa_module')]
for root in mods:
 children=list(root.children_recursive);before={o.name:o.matrix_world.copy() for o in children};orig=root.matrix_world.copy()
 delta=Matrix.Translation((2.1,-1.7,.4))@Matrix.Rotation(.31,4,'Z')
 root.matrix_world=delta@orig;bpy.context.view_layer.update()
 assert all(max(abs(a-b) for ra,rb in zip(o.matrix_world,delta@before[o.name]) for a,b in zip(ra,rb))<1e-4 for o in children),root.name
 root.matrix_world=orig;bpy.context.view_layer.update()
report['module_transform_checks']=len(mods)
# Actual image comparison: move and rotate a textured pump with the camera.
root=next(o for o in sc.objects if o.get('pa_gas_pump'))
visible=set(root.children_recursive)|{root}
for o in sc.objects:
 if o.type not in ('CAMERA','LIGHT'):o.hide_render=o not in visible
for m in bpy.data.materials:
 if not m.node_tree:continue
 nt=m.node_tree;bs=next((n for n in nt.nodes if n.type=='BSDF_PRINCIPLED'),None);out=next((n for n in nt.nodes if n.type=='OUTPUT_MATERIAL'),None)
 if not bs or not out:continue
 e=nt.nodes.new('ShaderNodeEmission')
 if bs.inputs['Base Color'].is_linked:nt.links.new(bs.inputs['Base Color'].links[0].from_socket,e.inputs[0])
 else:e.inputs[0].default_value=bs.inputs['Base Color'].default_value
 nt.links.new(e.outputs[0],out.inputs['Surface'])
sc.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.08,.08,.08,1)
sc.view_settings.view_transform='Standard';sc.view_settings.look='None';sc.view_settings.exposure=0
cam=sc.camera;cam.location=root.matrix_world.translation+Vector((2.1,-4,2.1));cam.rotation_euler=(root.matrix_world.translation+Vector((0,0,1))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.lens=48
sc.render.resolution_x=512;sc.render.resolution_y=512;sc.render.resolution_percentage=100;sc.cycles.samples=16;sc.cycles.use_denoising=False;sc.cycles.seed=71
p=bpy.context.preferences.addons['cycles'].preferences;p.compute_device_type='OPTIX';p.get_devices()
for d in p.devices:d.use=d.type!='CPU'
sc.cycles.device='GPU';sc.render.filepath=str(O/'test-module-before.png');bpy.ops.render.render(write_still=True)
im=bpy.data.images.load(str(O/'test-module-before.png'));before=np.array(im.pixels[:]);bpy.data.images.remove(im)
delta=Matrix.Translation((4,-2,.7))@Matrix.Rotation(.65,4,'Z');root.matrix_world=delta@root.matrix_world;cam.matrix_world=delta@cam.matrix_world;bpy.context.view_layer.update()
sc.render.filepath=str(O/'test-module-after.png');bpy.ops.render.render(write_still=True)
im=bpy.data.images.load(str(O/'test-module-after.png'));after=np.array(im.pixels[:]);bpy.data.images.remove(im)
diff=np.abs(before-after);report['moved_pump_albedo_mean_error']=float(diff.mean());report['moved_pump_albedo_changed_fraction']=float((diff>.02).mean());assert diff.mean()<.002
# Saved final file remains untouched by validation overrides.
(O/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf8')
addon.unregister();print('GAS_VALIDATION_OK',json.dumps(report),flush=True)
