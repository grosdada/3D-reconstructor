"""Isolated Blender worker: export neutral albedo, eligibility and camera Z.

Run on a saved scene in background. Never save the temporary shader overrides.
Sequential passes retain the already accepted projection in the albedo guide.
"""
import bpy,json,sys
from pathlib import Path
R=Path(__file__).parent;O=R/'output/gas-station-exterior-v1'
shot=sys.argv[-1] if sys.argv[-1] in ('01','02','03','05') else '01'
G=O/('projection-'+shot);G.mkdir(exist_ok=True)
source=O/'station-exterieur-textures.blend'
if shot=='01' or not source.exists():source=O/'station-exterieur-base.blend'
bpy.ops.wm.open_mainfile(filepath=str(source));sc=bpy.context.scene
sc.camera=next(o for o in sc.objects if o.type=='CAMERA' and o.name.startswith('CAM_'+shot))
if shot=='05':
 from mathutils import Vector
 sc.camera.location=(-20,18,3.2);sc.camera.rotation_euler=(Vector((-1,2,2.6))-sc.camera.location).to_track_quat('-Z','Y').to_euler();bpy.context.view_layer.update()
p=bpy.context.preferences.addons['cycles'].preferences;p.compute_device_type='OPTIX';p.get_devices()
for d in p.devices:d.use=d.type!='CPU'
sc.cycles.device='GPU';sc.cycles.samples=4;sc.cycles.use_denoising=False
sc.render.resolution_percentage=100;sc.render.resolution_x=1536;sc.render.resolution_y=1024
sc.render.image_settings.file_format='PNG';sc.render.image_settings.color_mode='RGBA'
for o in sc.objects:
 if o.get('pa_noncolliding'):o.hide_render=True
sc.view_settings.view_transform='Standard';sc.view_settings.look='None';sc.view_settings.exposure=0
sc.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.16,.20,.22,1)
sc.world.node_tree.nodes['Background'].inputs['Strength'].default_value=1
for m in list(bpy.data.materials):
 if not m.node_tree:continue
 nt=m.node_tree;bs=next((n for n in nt.nodes if n.type=='BSDF_PRINCIPLED'),None);out=next((n for n in nt.nodes if n.type=='OUTPUT_MATERIAL' and n.is_active_output),None)
 if not bs or not out:continue
 e=nt.nodes.new('ShaderNodeEmission')
 if bs.inputs['Base Color'].is_linked:nt.links.new(bs.inputs['Base Color'].links[0].from_socket,e.inputs[0])
 else:e.inputs[0].default_value=bs.inputs['Base Color'].default_value
 nt.links.new(e.outputs[0],out.inputs['Surface'])
sc.render.filepath=str(G/'guide-albedo.png');bpy.ops.render.render(write_still=True)
def flat(name,color):
 m=bpy.data.materials.new(name);m.use_nodes=True;nt=m.node_tree;nt.nodes.clear();e=nt.nodes.new('ShaderNodeEmission');e.inputs[0].default_value=(*color,1);out=nt.nodes.new('ShaderNodeOutputMaterial');nt.links.new(e.outputs[0],out.inputs['Surface']);return m
yes=flat('TEMP eligible',(1,1,1));no=flat('TEMP protected',(0,0,0))
for o in sc.objects:
 if o.type not in ('MESH','CURVE','FONT'):continue
 m=yes if o.get('pa_city_project') else no
 for slot in o.material_slots:slot.link='OBJECT';slot.material=m
sc.world.node_tree.nodes['Background'].inputs['Color'].default_value=(0,0,0,1)
sc.render.filepath=str(G/'guide-mask.png');bpy.ops.render.render(write_still=True)
dm=flat('TEMP camera depth',(0,0,0));nt=dm.node_tree;e=next(n for n in nt.nodes if n.type=='EMISSION')
tc=nt.nodes.new('ShaderNodeTexCoord');tc.object=sc.camera;sep=nt.nodes.new('ShaderNodeSeparateXYZ');nt.links.new(tc.outputs['Object'],sep.inputs[0]);mu=nt.nodes.new('ShaderNodeMath');mu.operation='MULTIPLY';mu.inputs[1].default_value=-1;nt.links.new(sep.outputs['Z'],mu.inputs[0]);nt.links.new(mu.outputs[0],e.inputs[0]);sc.view_layers[0].material_override=dm
sc.render.image_settings.file_format='OPEN_EXR';sc.render.image_settings.color_depth='32';sc.cycles.samples=1;sc.render.filter_size=.1;sc.render.filepath=str(G/'guide-depth.exr');bpy.ops.render.render(write_still=True)
cam=sc.camera;(G/'projection.json').write_text(json.dumps({'camera':cam.name,'matrix':[list(r) for r in cam.matrix_world],'frame':[list(v) for v in cam.data.view_frame(scene=sc)],'size':[1536,1024],'source':str(source),'albedo_only':True,'preserves_prior_projection':shot!='01'},indent=2),encoding='utf8')
print('GAS_GUIDES_DONE',shot,flush=True)
