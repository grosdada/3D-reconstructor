import bpy,sys,shutil
from pathlib import Path
R=Path(__file__).parent;sys.path.insert(0,str(R))
from pano_atelier.city_projection import apply
from pano_atelier.modular_scene import Builder,material
source=R/'output/ville-brutaliste-v2/projection';folders=[]
for name in ('a','b'):
 p=R/'test-output/city-multiview'/name;p.mkdir(parents=True,exist_ok=True)
 for f in ('detail-albedo.png','guide-depth.exr','guide-mask.png','projection.json'):shutil.copyfile(source/f,p/f)
 folders.append(p)
bpy.ops.wm.read_factory_settings(use_empty=True);sc=bpy.context.scene;b=Builder(sc,'Test');root=b.root('Building');m=material('Concrete',(.3,.3,.3));n=m.node_tree.nodes.new('ShaderNodeTexNoise');m.node_tree.links.new(n.outputs['Color'],m.node_tree.nodes['Principled BSDF'].inputs['Base Color'])
o=b.box('Wall',(0,0,1),(2,1,2),m,root,0);o['pa_city_project']=True;bpy.context.view_layer.update()
apply(sc,folders[0]);old=[tuple(x.vector) for x in o.data.attributes['PA_CityRest'].data];oldn=[tuple(x.vector) for x in o.data.attributes['PA_CityNormal'].data]
root.location.x+=3;root.rotation_euler.z=.4;bpy.context.view_layer.update();apply(sc,folders[1],append=True)
assert old==[tuple(x.vector) for x in o.data.attributes['PA_CityRest'].data]
assert oldn==[tuple(x.vector) for x in o.data.attributes['PA_CityNormal'].data]
assert old!=[tuple(x.vector) for x in o.data.attributes['PA_CityRest_02'].data]
for v,x in zip(o.data.vertices,o.data.attributes['PA_CityRest_02'].data):assert (o.matrix_world@v.co-x.vector).length<.00001
counts=(len(bpy.data.materials),len(bpy.data.node_groups),len(o.data.attributes))
try:apply(sc,folders[1],append=True)
except ValueError:pass
else:raise AssertionError('Duplicate view not rejected')
assert counts==(len(bpy.data.materials),len(bpy.data.node_groups),len(o.data.attributes))
print('MULTIVIEW_REST_COORDINATES_AND_DUPLICATE_GUARD_OK',flush=True)
