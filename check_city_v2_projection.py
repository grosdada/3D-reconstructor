import bpy,json,numpy as np
from pathlib import Path
R=Path(__file__).parent;O=R/'output/ville-brutaliste-v2';bpy.ops.wm.open_mainfile(filepath=str(O/'ville-brutaliste-V2.blend'));sc=bpy.context.scene
for o in sc.objects:
 if o.get('pa_noncolliding'):o.hide_render=True
for n in sc.world.node_tree.nodes:
 if n.type=='BACKGROUND':n.inputs['Color'].default_value=(0,0,0,1)
for m in bpy.data.materials:
 if not m.node_tree:continue
 t=m.node_tree;out=next((n for n in t.nodes if n.type=='OUTPUT_MATERIAL' and n.is_active_output),None)
 if not out:continue
 e=t.nodes.new('ShaderNodeEmission');e.inputs[0].default_value=(0,0,0,1);gr=next((n for n in t.nodes if n.type=='GROUP' and n.node_tree and n.outputs.get('Coverage') and n.outputs['Coverage'].is_linked and any(l.to_node.type=='MATH' and l.to_node.outputs[0].is_linked for l in n.outputs['Coverage'].links)),None)
 if gr:t.links.new(gr.outputs['Coverage'],e.inputs[0])
 t.links.new(e.outputs[0],out.inputs['Surface'])
sc.render.resolution_x=720;sc.render.resolution_y=400;sc.render.resolution_percentage=100;sc.cycles.device='CPU';sc.render.threads_mode='FIXED';sc.render.threads=12;sc.cycles.samples=1;sc.cycles.use_denoising=False;sc.view_settings.view_transform='Standard';sc.view_settings.look='None';sc.view_settings.exposure=0;sc.render.filepath=str(O/'projection/coverage-check.png');bpy.ops.render.render(write_still=True)
im=bpy.data.images.load(sc.render.filepath);px=np.asarray(im.pixels[:]).reshape(-1,4)[:,0];r={'max_coverage':float(px.max()),'pixels_above_0_1':int((px>.1).sum()),'total_pixels':len(px)}
assert r['pixels_above_0_1']>1000,r
(O/'projection/coverage-check.json').write_text(json.dumps(r,indent=2),encoding='utf8');print('CITY_PROJECTION_VISIBLE',r,flush=True)
