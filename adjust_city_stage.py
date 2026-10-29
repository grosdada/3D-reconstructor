import bpy,sys
from pathlib import Path
R=Path(__file__).parent;O=R/'output/ville-brutaliste-v1';sys.path.insert(0,str(R))
from pano_atelier.station_procedural import node
bpy.ops.wm.open_mainfile(filepath=str(O/'ville-brutaliste-geometrie.blend'));sc=bpy.context.scene
for o in sc.objects:
 if o.type=='CAMERA':o.data.clip_end=1500;o.data.clip_start=.15
for name,loc,factor in [('BG · tour sombre',(-130,52,0),84/96),('BG · tour claire',(-100,77,0),77/90),('BG · tour droite',(38,85,0),78/88),('BG · lointain gauche',(-160,140,0),1),('BG · lointain droite',(75,140,0),95/105)]:
 o=bpy.data.objects[name];o.location=loc;o.scale.z=factor
wt=sc.world.node_tree;sky=node(wt,'ShaderNodeBackground','Ciel visible pale');sky.inputs['Color'].default_value=(.76,.82,.57,1);sky.inputs['Strength'].default_value=1.8;path=node(wt,'ShaderNodeLightPath','Ciel / ambiance');mx=node(wt,'ShaderNodeMixShader','Ciel visible et eclairage diffus');wt.links.new(path.outputs['Is Camera Ray'],mx.inputs[0]);wt.links.new(wt.nodes['Background'].outputs[0],mx.inputs[1]);wt.links.new(sky.outputs[0],mx.inputs[2]);wt.links.new(mx.outputs[0],wt.nodes['World Output'].inputs[0])
# Localize nested library dependencies, then pack: no K: requirement for the delivered blend.
for _ in range(4):
 for seq in (bpy.data.objects,bpy.data.meshes,bpy.data.materials,bpy.data.node_groups,bpy.data.images):
  for x in list(seq):
   if x.library:
    try:x.make_local()
    except RuntimeError:pass
for im in bpy.data.images:
 if im.source=='FILE' and not im.packed_file:
  try:im.pack()
  except RuntimeError:pass
bpy.context.view_layer.update();bpy.ops.wm.save_as_mainfile(filepath=str(O/'ville-brutaliste-geometrie.blend'));print('CITY_CAMERA_FIXED',flush=True)
p=bpy.context.preferences.addons['cycles'].preferences;p.compute_device_type='OPTIX';p.get_devices()
for d in p.devices:d.use=d.type!='CPU'
sc.cycles.device='GPU';sc.cycles.samples=12;sc.render.resolution_percentage=65;sc.render.filepath=str(O/'A1-preview-corrected.png');bpy.ops.render.render(write_still=True);print('CITY_PREVIEW_FIXED_DONE',flush=True)
