"""Render semantic protection masks from real geometry; no generated albedo is modified."""
import bpy,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'output/cockpit-albedo-multivues-test'
bpy.ops.wm.open_mainfile(filepath=str(OUT/'base-v2-six-vues.blend'))
sc=bpy.context.scene;views=json.loads((OUT/'views.json').read_text())
colors={'paint':(1,0,0,1),'floor':(0,1,0,1),'seat':(0,0,1,1),'wood':(1,1,0,1),'other':(0,0,0,1)}
for m in bpy.data.materials:
    if not m.node_tree:continue
    name=m.name
    kind='paint' if name.startswith(('Coque ·','Chants ·','Panneaux ·','Abat-jour ·')) else 'floor' if name.startswith('Sol ·') else 'seat' if name.startswith('Siège ·') else 'wood' if name.startswith('Porte ·') else 'other'
    nt=m.node_tree;nt.nodes.clear();em=nt.nodes.new('ShaderNodeEmission');em.inputs['Color'].default_value=colors[kind];out=nt.nodes.new('ShaderNodeOutputMaterial');nt.links.new(em.outputs[0],out.inputs['Surface'])
sc.view_settings.view_transform='Standard';sc.view_settings.look='None';sc.view_settings.exposure=0
sc.render.resolution_x=sc.render.resolution_y=1024;sc.render.resolution_percentage=100;sc.render.filter_size=.01;sc.cycles.samples=1;sc.cycles.use_denoising=False;sc.cycles.device='CPU';sc.render.use_persistent_data=True
for v in views:
    sc.camera=bpy.data.objects[v['camera']];sc.render.filepath=str(OUT/(v['name']+'-classes.png'));bpy.ops.render.render(write_still=True)
print('CLASS_MASKS_DONE')
