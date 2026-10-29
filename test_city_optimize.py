import bpy,sys,json,math
from pathlib import Path
from mathutils import Vector
R=Path(__file__).parent;sys.path.insert(0,str(R))
from pano_atelier.modular_scene import Builder,material
from pano_atelier.city_optimize import optimize
bpy.ops.wm.read_factory_settings(use_empty=True);sc=bpy.context.scene;b=Builder(sc,'Test');r=b.root('A1 · test',(4,3,0));r.rotation_euler.z=.3
m=material('VILLE · test',(.3,.3,.3));m2=material('VILLE · override',(.1,.2,.3))
tc=m.node_tree.nodes.new('ShaderNodeTexCoord');n=m.node_tree.nodes.new('ShaderNodeTexNoise');m.node_tree.links.new(tc.outputs['Object'],n.inputs['Vector'])
a=b.box('A',(2,0,1),(1,2,2),m,r,0);c=b.box('C',(-2,0,1),(1,1,2),m,r,0);c.material_slots[0].link='OBJECT';c.material_slots[0].material=m2
other=b.root('A1 · neighbor',(20,0,0));d=b.box('D',(0,0,1),(2,2,2),m,other,0)
bpy.context.view_layer.update();positions=sorted(tuple(round(v,5) for v in o.matrix_world@q.co) for o in (a,c) for q in o.data.vertices)
for o in (a,c):
 o['pa_city_project']=True;att=o.data.attributes.new('PA_CityRest','FLOAT_VECTOR','POINT')
 for q,x in zip(o.data.vertices,att.data):x.vector=o.matrix_world@q.co
report=optimize(sc);merged=next(x for x in r.children if x.type=='MESH')
assert len(r.children)==1
assert {x.name for x in merged.data.materials}=={m.name,m2.name}
after_positions=sorted(tuple(round(v,5) for v in merged.matrix_world@q.co) for q in merged.data.vertices)
print('POSITIONS',positions,after_positions,'MATRIX',list(merged.matrix_world),flush=True)
assert max(abs(x-y) for a,b in zip(positions,after_positions) for x,y in zip(a,b))<.0001
assert positions==sorted(tuple(round(v,5) for v in q.vector) for q in merged.data.attributes['PA_CityRest'].data)
assert not tc.outputs['Object'].links
before=merged.matrix_world.copy();attrs=[tuple(q.vector) for q in merged.data.attributes['PA_SourceLocal'].data];neighbor=d.matrix_world.copy();r.location.x+=5;r.rotation_euler.z+=.4;bpy.context.view_layer.update()
assert merged.matrix_world!=before and d.matrix_world==neighbor
assert attrs==[tuple(q.vector) for q in merged.data.attributes['PA_SourceLocal'].data]
try:optimize(sc)
except ValueError:pass
else:raise AssertionError('Repeated optimization was not rejected')
print('OPTIMIZER_TESTS_OK',json.dumps(report),flush=True)
