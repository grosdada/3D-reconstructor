"""Six overlapping reference/albedo/depth captures from the preserved V2."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'output/cockpit-albedo-multivues-test';OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'output/cockpit-photo-modulaire-v2/cockpit-patine-360.blend'))
sc=bpy.context.scene;sc.render.resolution_x=sc.render.resolution_y=1024;sc.render.resolution_percentage=100;sc.render.use_persistent_data=True
try:
    p=bpy.context.preferences.addons['cycles'].preferences;p.compute_device_type='OPTIX';p.get_devices()
    for d in p.devices:d.use=d.type!='CPU'
    sc.cycles.device='GPU'
except Exception as e:print(e)
c=bpy.data.collections.new('GPT · six vues albédo');sc.collection.children.link(c)
specs=[('avant',(0,.25,1.6),(0,1,-.02)),('droite',(.25,0,1.6),(1,0,-.02)),('arriere',(0,-.25,1.6),(0,-1,-.02)),('gauche',(-.25,0,1.6),(-1,0,-.02)),('plafond',(0,0,1.5),(0,0,1)),('sol',(0,0,2.35),(0,0,-1))]
views=[]
for name,loc,dir_ in specs:
    d=bpy.data.cameras.new('ALBEDO_'+name);o=bpy.data.objects.new(d.name,d);c.objects.link(o);o.location=loc;o.rotation_euler=Vector(dir_).to_track_quat('-Z','Y').to_euler();d.lens=15.5;d.sensor_width=36
    views.append({'name':name,'camera':o.name,'location':list(loc)})
bpy.context.view_layer.update()
for v in views:
    o=bpy.data.objects[v['camera']];v['matrix']=list(map(list,o.matrix_world));v['frame']=list(map(list,o.data.view_frame(scene=sc)))
    sc.camera=o;sc.cycles.samples=32;sc.cycles.use_denoising=True
    sc.render.filepath=str(OUT/(v['name']+'-geometrie.png'));bpy.ops.render.render(write_still=True)

# Temporary flat materials expose base color, not the shaded beauty. Glass stays a neutral dark placeholder.
originals={};mats={slot.material for o in sc.objects if o.type=='MESH' for slot in o.material_slots if slot.material}
for m in mats:
    if not m.node_tree:continue
    nt=m.node_tree;out=next((n for n in nt.nodes if n.type=='OUTPUT_MATERIAL' and n.is_active_output),None);bs=next((n for n in nt.nodes if n.type=='BSDF_PRINCIPLED'),None)
    if not out or not bs:continue
    originals[m]=out.inputs['Surface'].links[0].from_socket
    em=nt.nodes.new('ShaderNodeEmission');em.name='TEMP_ALBEDO'
    if any(s in m.name for s in ['Vitrage','Cyclorama','Oculus']):em.inputs['Color'].default_value=(.015,.02,.025,1)
    elif 'Plafonnier' in m.name:em.inputs['Color'].default_value=(.65,.65,.62,1)
    elif bs.inputs['Base Color'].is_linked:nt.links.new(bs.inputs['Base Color'].links[0].from_socket,em.inputs['Color'])
    else:em.inputs['Color'].default_value=bs.inputs['Base Color'].default_value
    nt.links.new(em.outputs[0],out.inputs['Surface'])
sc.view_settings.view_transform='Standard';sc.view_settings.look='None';sc.view_settings.exposure=0
sc.cycles.samples=4;sc.cycles.use_denoising=False
for v in views:
    sc.camera=bpy.data.objects[v['camera']];sc.render.filepath=str(OUT/(v['name']+'-basecolor.png'));bpy.ops.render.render(write_still=True)
for m,sock in originals.items():
    nt=m.node_tree;out=next(n for n in nt.nodes if n.type=='OUTPUT_MATERIAL' and n.is_active_output);nt.links.new(sock,out.inputs['Surface']);nt.nodes.remove(nt.nodes['TEMP_ALBEDO'])

depthmat=bpy.data.materials.new('TEMP_DEPTH');depthmat.use_nodes=True;nt=depthmat.node_tree;nt.nodes.clear()
tc=nt.nodes.new('ShaderNodeTexCoord');sep=nt.nodes.new('ShaderNodeSeparateXYZ');nt.links.new(tc.outputs['Object'],sep.inputs[0])
mul=nt.nodes.new('ShaderNodeMath');mul.operation='MULTIPLY';mul.inputs[1].default_value=-1;nt.links.new(sep.outputs['Z'],mul.inputs[0])
em=nt.nodes.new('ShaderNodeEmission');nt.links.new(mul.outputs[0],em.inputs['Color']);out=nt.nodes.new('ShaderNodeOutputMaterial');nt.links.new(em.outputs[0],out.inputs['Surface'])
sc.view_layers[0].material_override=depthmat;sc.cycles.samples=1;sc.render.filter_size=.01
sc.render.image_settings.file_format='OPEN_EXR';sc.render.image_settings.color_depth='32'
for v in views:
    sc.camera=bpy.data.objects[v['camera']];tc.object=sc.camera;sc.render.filepath=str(OUT/(v['name']+'-depth.exr'));bpy.ops.render.render(write_still=True)
sc.view_layers[0].material_override=None;bpy.data.materials.remove(depthmat)
sc.render.image_settings.file_format='PNG';sc.render.image_settings.color_depth='8';sc.render.filter_size=1
sc.view_settings.view_transform='AgX';sc.view_settings.look='AgX - Medium High Contrast';sc.view_settings.exposure=-.85
sc.camera=bpy.data.objects['CAM_ARRIERE_OBLIQUE'];sc.render.resolution_x=1456;sc.render.resolution_y=816;sc.cycles.samples=64;sc.cycles.use_denoising=True
(OUT/'views.json').write_text(json.dumps(views,ensure_ascii=False,indent=2),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'base-v2-six-vues.blend'))
print('SIX_VIEWS_READY',flush=True)
