import bpy,json,sys
from pathlib import Path
R=Path(__file__).parent;O=R/'output/ville-brutaliste-v1';G=O/'projection';G.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(O/'ville-brutaliste-geometrie.blend'));sc=bpy.context.scene
p=bpy.context.preferences.addons['cycles'].preferences;p.compute_device_type='OPTIX';p.get_devices()
for d in p.devices:d.use=d.type!='CPU'
sc.cycles.device='GPU';sc.cycles.samples=2;sc.cycles.use_denoising=False;sc.render.use_persistent_data=True;sc.render.resolution_percentage=100;sc.render.resolution_x=1800;sc.render.resolution_y=1000
if '--cpu' in sys.argv:sc.cycles.device='CPU';sc.render.threads_mode='FIXED';sc.render.threads=12
for o in sc.objects:
 if o.get('pa_noncolliding'):o.hide_render=True
# Make inherited Botaniq dependencies local before manipulating guide shaders.
for _ in range(4):
 for seq in (bpy.data.objects,bpy.data.meshes,bpy.data.materials,bpy.data.node_groups,bpy.data.images):
  for x in list(seq):
   if x.library:
    try:x.make_local()
    except RuntimeError:pass
sc.view_settings.view_transform='Standard';sc.view_settings.look='None';sc.view_settings.exposure=0
eligible={s.material for o in sc.objects if o.get('pa_city_project') for s in o.material_slots if s.material}
temps={}
for m in bpy.data.materials:
 if not m.node_tree:continue
 nt=m.node_tree;bs=next((n for n in nt.nodes if n.type=='BSDF_PRINCIPLED'),None);out=next((n for n in nt.nodes if n.type=='OUTPUT_MATERIAL' and n.is_active_output),None)
 if not bs or not out:continue
 e=nt.nodes.new('ShaderNodeEmission')
 if bs.inputs['Base Color'].is_linked:nt.links.new(bs.inputs['Base Color'].links[0].from_socket,e.inputs[0])
 else:e.inputs[0].default_value=bs.inputs['Base Color'].default_value
 nt.links.new(e.outputs[0],out.inputs['Surface']);temps[m]=e
sc.render.filepath=str(G/'guide-albedo.png');bpy.ops.render.render(write_still=True)
for m,e in temps.items():
 for l in list(e.inputs[0].links):m.node_tree.links.remove(l)
 v=1 if m in eligible else 0;e.inputs[0].default_value=(v,v,v,1)
for n in sc.world.node_tree.nodes:
 if n.type=='BACKGROUND':n.inputs['Color'].default_value=(0,0,0,1)
sc.render.filepath=str(G/'guide-mask.png');bpy.ops.render.render(write_still=True)
dm=bpy.data.materials.new('TEMP_CITY_DEPTH');dm.use_nodes=True;nt=dm.node_tree;nt.nodes.clear();tc=nt.nodes.new('ShaderNodeTexCoord');tc.object=sc.camera;sep=nt.nodes.new('ShaderNodeSeparateXYZ');nt.links.new(tc.outputs['Object'],sep.inputs[0]);mu=nt.nodes.new('ShaderNodeMath');mu.operation='MULTIPLY';mu.inputs[1].default_value=-1;nt.links.new(sep.outputs['Z'],mu.inputs[0]);e=nt.nodes.new('ShaderNodeEmission');nt.links.new(mu.outputs[0],e.inputs[0]);out=nt.nodes.new('ShaderNodeOutputMaterial');nt.links.new(e.outputs[0],out.inputs['Surface']);sc.view_layers[0].material_override=dm
sc.render.image_settings.file_format='OPEN_EXR';sc.render.image_settings.color_depth='32';sc.cycles.samples=1;sc.render.filter_size=.1;sc.render.filepath=str(G/'guide-depth.exr');bpy.ops.render.render(write_still=True)
cam=sc.camera;(G/'projection.json').write_text(json.dumps({'camera':cam.name,'matrix':[list(r) for r in cam.matrix_world],'frame':[list(v) for v in cam.data.view_frame(scene=sc)],'size':[1800,1000]}),encoding='utf8');print('CITY_GUIDES_DONE',flush=True)
