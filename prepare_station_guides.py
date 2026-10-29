import bpy,json,sys
from pathlib import Path
from mathutils import Vector
R=Path(__file__).parent;O=R/'output/station-sas-v1';G=O/'projections';G.mkdir(exist_ok=True);sys.path.insert(0,str(R))
from pano_atelier.multiview_albedo import atlas_material
bpy.ops.wm.open_mainfile(filepath=str(O/'station-structure-v1.blend'));sc=bpy.context.scene
p=bpy.context.preferences.addons['cycles'].preferences;p.compute_device_type='OPTIX';p.get_devices()
for d in p.devices:d.use=d.type!='CPU'
sc.cycles.device='GPU';sc.render.use_persistent_data=True
im=bpy.data.images.load(str(O/'textures/material-atlas-albedo.png'));im.pack()
for name,q,meters,strength in [('ST · panneaux ivoire vieilli',(0,.5),1.8,.85),('ST · sas email blanc chaud',(0,0),1.2,.82),('ST · sol resine creme',(.5,.5),1.5,.8),('ST · plaques circulation gris bleu',(.5,0),.9,.85)]:atlas_material(bpy.data.materials[name],im,q,meters,strength)
# Localize appended data; no runtime dependency on the commercial library.
for _ in range(3):
    for kind in ('objects','meshes','materials','node_groups','images','collections'):
        for it in list(getattr(bpy.data,kind)):
            if it.library:it.make_local()
sc.render.resolution_x=sc.render.resolution_y=1024;sc.render.resolution_percentage=100
specs=[('avant',(0,-1.2,1.6),(0,1,0)),('droite',(0,-1.0,1.6),(1,0,0)),('arriere',(0,-.6,1.6),(0,-1,0)),('gauche',(0,-1.0,1.6),(-1,0,0)),('plafond',(0,-1,1.55),(0,0,1)),('sol',(0,-1,2.2),(0,0,-1)),('couloir',(0,4.5,1.6),(0,1,0)),('retour',(0,-6.2,1.6),(0,-1,0))]
views=[]
for name,loc,direction in specs:
    o=bpy.data.objects.get('PROJ_'+name)
    if o is None:
        d=bpy.data.cameras.new('PROJ_'+name);o=bpy.data.objects.new(d.name,d);sc.collection.objects.link(o)
    d=o.data;o.location=loc;o.rotation_euler=Vector(direction).to_track_quat('-Z','Y').to_euler();d.lens=17;d.clip_start=.03;o['pa_projection_only']=True
    bpy.context.view_layer.update();views.append({'name':name,'camera':o.name,'matrix':list(map(list,o.matrix_world)),'frame':list(map(list,d.view_frame(scene=sc)))})
    sc.camera=o;sc.cycles.samples=16;sc.render.filepath=str(G/(name+'-beauty.png'));bpy.ops.render.render(write_still=True)
mats={s.material for o in sc.objects for s in o.material_slots if s.material};old={};temps={}
for m in mats:
    nt=m.node_tree
    if not nt:continue
    bs=next((n for n in nt.nodes if n.type=='BSDF_PRINCIPLED'),None);out=next((n for n in nt.nodes if n.type=='OUTPUT_MATERIAL' and n.is_active_output),None)
    if not bs or not out or not out.inputs['Surface'].is_linked:continue
    old[m]=out.inputs['Surface'].links[0].from_socket;e=nt.nodes.new('ShaderNodeEmission');temps[m]=e
    if bs.inputs['Base Color'].is_linked:nt.links.new(bs.inputs['Base Color'].links[0].from_socket,e.inputs['Color'])
    else:e.inputs['Color'].default_value=bs.inputs['Base Color'].default_value
    nt.links.new(e.outputs[0],out.inputs['Surface'])
sc.view_settings.view_transform='Standard';sc.view_settings.look='None';sc.view_settings.exposure=0;sc.cycles.samples=2;sc.cycles.use_denoising=False
for v in views:
    sc.camera=bpy.data.objects[v['camera']];sc.render.filepath=str(G/(v['name']+'-basecolor.png'));bpy.ops.render.render(write_still=True)
for m,e in temps.items():
    for link in list(e.inputs['Color'].links):m.node_tree.links.remove(link)
    value=1 if any(key in m.name for key in ('panneaux','sas email','sol resine','plaques circulation','coffrets')) else 0;e.inputs['Color'].default_value=(value,value,value,1)
sc.render.filter_size=.1
for v in views:
    sc.camera=bpy.data.objects[v['camera']];sc.render.filepath=str(G/(v['name']+'-eligible.png'));bpy.ops.render.render(write_still=True)
for m,sock in old.items():
    nt=m.node_tree;out=next(n for n in nt.nodes if n.type=='OUTPUT_MATERIAL' and n.is_active_output);nt.links.new(sock,out.inputs['Surface']);nt.nodes.remove(temps[m])
dm=bpy.data.materials.new('TEMP_DEPTH');dm.use_nodes=True;nt=dm.node_tree;nt.nodes.clear();tc=nt.nodes.new('ShaderNodeTexCoord');sep=nt.nodes.new('ShaderNodeSeparateXYZ');nt.links.new(tc.outputs['Object'],sep.inputs[0]);mu=nt.nodes.new('ShaderNodeMath');mu.operation='MULTIPLY';mu.inputs[1].default_value=-1;nt.links.new(sep.outputs['Z'],mu.inputs[0]);em=nt.nodes.new('ShaderNodeEmission');nt.links.new(mu.outputs[0],em.inputs[0]);ou=nt.nodes.new('ShaderNodeOutputMaterial');nt.links.new(em.outputs[0],ou.inputs['Surface'])
sc.view_layers[0].material_override=dm;sc.render.image_settings.file_format='OPEN_EXR';sc.render.image_settings.color_depth='32';sc.cycles.samples=1
for v in views:
    sc.camera=bpy.data.objects[v['camera']];tc.object=sc.camera;sc.render.filepath=str(G/(v['name']+'-depth.exr'));bpy.ops.render.render(write_still=True)
sc.view_layers[0].material_override=None;bpy.data.materials.remove(dm)
sc.view_settings.view_transform='AgX';sc.view_settings.look='AgX - Medium High Contrast';sc.view_settings.exposure=-.6;sc.render.image_settings.file_format='PNG';sc.render.image_settings.color_depth='8';sc.render.filter_size=1.5;sc.cycles.samples=64;sc.cycles.use_denoising=True
sc.camera=bpy.data.objects['CAM_01 · sas de reference'];sc.render.resolution_x=1440;sc.render.resolution_y=960
(G/'views.json').write_text(json.dumps(views,indent=2),encoding='utf8');bpy.ops.wm.save_as_mainfile(filepath=str(O/'station-base-projections.blend'))
print('STATION_GUIDES_DONE',flush=True)
