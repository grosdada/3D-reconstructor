import bpy,json
from pathlib import Path
R=Path(__file__).parent;O=R/'output/ville-brutaliste-v2'
bpy.ops.wm.open_mainfile(filepath=str(O/'ville-brutaliste-V2.blend'));sc=bpy.context.scene
bpy.data.objects['EXT · ilot 01'].location.x=99;bpy.data.objects['EXT · ilot 01'].location.y=-4
for m in bpy.data.materials:
 if not m.node_tree:continue
 nt=m.node_tree
 if nt.nodes.get('Patine · traces selectionnees'):nt.nodes['Patine · traces selectionnees'].inputs['To Max'].default_value=.30
 if nt.nodes.get('Patine · pluies minerales'):nt.nodes['Patine · pluies minerales'].inputs[1].default_value=(2.1,2.1,.55)
# Restore shared car meshes after batching: same normalized geometry and UVs for each model.
cars=sorted([o for o in sc.objects if o.type=='EMPTY' and o.name.startswith('VEHICULE ·')],key=lambda o:o.name);meshes={}
for i,r in enumerate(cars):
 o=next(c for c in r.children if c.type=='MESH')
 if i%3 not in meshes:meshes[i%3]=o.data
 else:o.data=meshes[i%3]
 o['pa_asset_model']=['Rover P6','Triumph Dolomite','Jaguar XJ-S'][i%3]
bpy.context.view_layer.update();bpy.ops.outliner.orphans_purge(do_local_ids=True,do_linked_ids=False,do_recursive=True)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'ville-brutaliste-V2.blend'))
exec(compile((R/'export_city_v2_guides.py').read_text(encoding='utf8'),str(R/'export_city_v2_guides.py'),'exec'))
