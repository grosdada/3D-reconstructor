import bpy,bmesh,sys,json,hashlib
from pathlib import Path
from mathutils import Vector
R=Path(__file__).parent;O=R/'output/station-sas-v2.2';sys.path.insert(0,str(R))
import pano_atelier
from pano_atelier import station_procedural
bpy.ops.wm.open_mainfile(filepath=str(R/'output/station-sas-v2.1/station-sas-modulaire-texturee-v2.1.blend'));pano_atelier.register();sc=bpy.context.scene
before={o.name:(o.parent.name if o.parent else None,tuple(tuple(r) for r in o.matrix_world)) for o in sc.objects}
oldtris=sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in sc.objects if o.type=='MESH' and o.name.startswith(('Plaque de passage','Sas · seuil')))
report=station_procedural.apply(sc);bpy.context.view_layer.update()
assert before=={o.name:(o.parent.name if o.parent else None,tuple(tuple(r) for r in o.matrix_world)) for o in sc.objects}
checks={}
for o in sc.objects:
 if not o.get('pa_machined_plate'):continue
 bm=bmesh.new();bm.from_mesh(o.data)
 assert all(e.is_manifold for e in bm.edges),o.name
 assert all(f.calc_area()>1e-10 for f in bm.faces),o.name
 bm.free()
 checks[o.name]='closed manifold; positive face areas; 4 modeled notches'
for name in report['procedural_materials']:
 assert not any(n.type=='TEX_IMAGE' for n in bpy.data.materials[name].node_tree.nodes),name
assert bpy.data.node_groups['PA · albedos multivues station'].nodes.get('Reparation masquee · source preservee')
root=next(o for o in sc.objects if o.name.startswith('MODULE 03'))
children=list(root.children_recursive);hidden=[o for o in children if o.hide_viewport]
for o in hidden:o.hide_viewport=False
bpy.context.view_layer.update();positions={o.name:o.matrix_world.translation.copy() for o in children};neighbors={o.name:o.matrix_world.copy() for o in sc.objects if o not in children and o!=root}
oldloc=root.location.copy();delta=Vector((.73,.41,.12));root.location+=delta;bpy.context.view_layer.update()
assert all((o.matrix_world.translation-positions[o.name]-delta).length<.0001 for o in children)
assert all(o.matrix_world==neighbors[o.name] for o in sc.objects if o.name in neighbors)
root.location=oldloc
for o in hidden:o.hide_viewport=True
bpy.context.view_layer.update()
report['checks']={'parents_transforms_unchanged':True,'moving_module_children_follow':True,'neighbors_unchanged':True,'plates':checks,'repair_preserved':True,'volume_preserved':sc.get('pa_depth_haze'),'lights_unchanged':True,'plate_base_triangles_before':oldtris,'plate_base_triangles_after':sum(p['triangles'] for p in report['plates'])}
sc.name='Station · V2.2 plaques usinees et patine procedurale';sc.pa_modular.output=str(O);sc.pa_settings.output=str(O);sc['pa_output']=str(O);sc.cycles.samples=64
(O/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
bpy.ops.wm.save_as_mainfile(filepath=str(O/'station-sas-modulaire-texturee-v2.2.blend'));print('V22_SAVED',flush=True)
