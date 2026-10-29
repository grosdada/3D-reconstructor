import bpy,sys,json
from pathlib import Path
R=Path(__file__).parent;O=R/'output/ville-brutaliste-v3-vis-a-vis';sys.path.insert(0,str(R))
from pano_atelier.city_opposite import add_street_background
bpy.ops.wm.open_mainfile(filepath=str(O/'ville-brutaliste-vis-a-vis.blend'));sc=bpy.context.scene
add_street_background(sc)
layers=json.loads(sc['pa_city_projection_layers'])
for layer in layers[2:]:layer['target_scope']='OPPOSITE'
sc['pa_city_projection_layers']=json.dumps(layers)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'ville-brutaliste-vis-a-vis.blend'),compress=True)
