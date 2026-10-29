"""Frozen approved geometry -> beauty, flat color, semantic and depth projection guides."""
import bpy,json
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).parent;OUT=ROOT/'output/tour-belvedere-v2';OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'output/tour-belvedere-v1/tour-belvedere-geometrie-v1.blend'))
sc=bpy.context.scene
pref=bpy.context.preferences.addons['cycles'].preferences;pref.compute_device_type='OPTIX';pref.get_devices()
for d in pref.devices:d.use=d.type!='CPU'
sc.cycles.device='GPU';sc.render.resolution_x=sc.render.resolution_y=1536;sc.render.resolution_percentage=100
sc.render.use_persistent_data=True;sc.cycles.samples=24
vegetation=bpy.data.collections['05 · Vegetation botaniq'];vegetation.hide_render=True
c=bpy.data.collections.new('07 · Cameras projection albedo');sc.collection.children.link(c)
specs=[('avant',(6,-108,20),(6,-8,19),58),('droite',(106,-8,20),(6,-8,19),58),('arriere',(6,92,20),(6,-8,19),58),('gauche',(-94,-8,20),(6,-8,19),58),('dessus',(6,-8,110),(6,-8,0),62),('detail-facade',(3,-40,3),(14,-17,2.5),40)]
views=[]
for name,loc,target,lens in specs:
    d=bpy.data.cameras.new('PROJ_'+name);o=bpy.data.objects.new(d.name,d);c.objects.link(o)
    o.location=loc;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();d.lens=lens;d.clip_end=500
    bpy.context.view_layer.update()
    views.append({'name':name,'camera':o.name,'matrix':list(map(list,o.matrix_world)),'frame':list(map(list,d.view_frame(scene=sc))),'priority':8 if name=='detail-facade' else 1})
    sc.camera=o;sc.render.filepath=str(OUT/(name+'-geometrie.png'));bpy.ops.render.render(write_still=True)
mats={s.material for o in sc.objects if o.type=='MESH' for s in o.material_slots if s.material}
originals={};temps={}
classes={'Beton · celadon pale':(1,0,0,1),'Beton · pied beige':(0,1,0,1),'Couverture · rose passe':(0,0,1,1),'Couverture · rose clair':(0,0,1,1),'Couverture · panneaux creme':(0,0,1,1),'Batiments · peinture vert eau':(1,1,0,1),'Etancheite · gris brun':(1,0,1,1),'Menuiseries · gris clair':(0,1,1,1),'Trottoirs · beton':(.5,0,0,1),'Voirie · asphalte':(0,.5,0,1)}
for m in mats:
    nt=m.node_tree
    if not nt:continue
    bs=next((n for n in nt.nodes if n.type=='BSDF_PRINCIPLED'),None);out=next((n for n in nt.nodes if n.type=='OUTPUT_MATERIAL' and n.is_active_output),None)
    if not bs or not out or not out.inputs['Surface'].is_linked:continue
    originals[m]=out.inputs['Surface'].links[0].from_socket
    e=nt.nodes.new('ShaderNodeEmission');temps[m]=e
    color=tuple(bs.inputs['Base Color'].default_value)
    if m.name.startswith('Vitrages'):color=(.025,.04,.04,1)
    e.inputs['Color'].default_value=color;nt.links.new(e.outputs[0],out.inputs['Surface'])
sc.view_settings.view_transform='Standard';sc.view_settings.look='None';sc.cycles.samples=2;sc.cycles.use_denoising=False
for v in views:
    sc.camera=bpy.data.objects[v['camera']];sc.render.filepath=str(OUT/(v['name']+'-basecolor.png'));bpy.ops.render.render(write_still=True)
sc.world.node_tree.nodes['Background'].inputs['Color'].default_value=(0,0,0,1)
for m,e in temps.items():e.inputs['Color'].default_value=classes.get(m.name,(0,0,0,1))
sc.render.filter_size=.01
for v in views:
    sc.camera=bpy.data.objects[v['camera']];sc.render.filepath=str(OUT/(v['name']+'-classes.png'));bpy.ops.render.render(write_still=True)
for m,s in originals.items():
    nt=m.node_tree;out=next(n for n in nt.nodes if n.type=='OUTPUT_MATERIAL' and n.is_active_output);nt.links.new(s,out.inputs['Surface']);nt.nodes.remove(temps[m])
dm=bpy.data.materials.new('TEMP_DEPTH');dm.use_nodes=True;nt=dm.node_tree;nt.nodes.clear()
t=nt.nodes.new('ShaderNodeTexCoord');sep=nt.nodes.new('ShaderNodeSeparateXYZ');nt.links.new(t.outputs['Object'],sep.inputs[0]);mul=nt.nodes.new('ShaderNodeMath');mul.operation='MULTIPLY';mul.inputs[1].default_value=-1;nt.links.new(sep.outputs['Z'],mul.inputs[0])
e=nt.nodes.new('ShaderNodeEmission');nt.links.new(mul.outputs[0],e.inputs[0]);o=nt.nodes.new('ShaderNodeOutputMaterial');nt.links.new(e.outputs[0],o.inputs['Surface'])
sc.view_layers[0].material_override=dm;sc.render.image_settings.file_format='OPEN_EXR';sc.render.image_settings.color_depth='32';sc.cycles.samples=1
for v in views:
    sc.camera=bpy.data.objects[v['camera']];t.object=sc.camera;sc.render.filepath=str(OUT/(v['name']+'-depth.exr'));bpy.ops.render.render(write_still=True)
sc.view_layers[0].material_override=None;bpy.data.materials.remove(dm)
vegetation.hide_render=False;sc.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.78,.81,.85,1)
sc.render.image_settings.file_format='PNG';sc.render.image_settings.color_depth='8';sc.render.filter_size=1.5
sc.view_settings.view_transform='AgX';sc.view_settings.look='AgX - Medium High Contrast';sc.cycles.samples=64;sc.cycles.use_denoising=True
sc.camera=bpy.data.objects['CAM_01 · reference portrait'];sc.render.resolution_x=1000;sc.render.resolution_y=1200
(OUT/'views.json').write_text(json.dumps(views,indent=2),encoding='utf8')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'base-projections.blend'))
print('TOUR_GUIDES_DONE',flush=True)
