"""Final views, movement, relighting and projection coverage evidence. Does not overwrite the scene."""
import bpy,json,math
from mathutils import Vector
from pathlib import Path
OUT=Path(bpy.data.filepath).parent;sc=bpy.context.scene
try:
    p=bpy.context.preferences.addons['cycles'].preferences;p.compute_device_type='OPTIX';p.get_devices()
    for d in p.devices:d.use=d.type!='CPU'
    sc.cycles.device='GPU'
except Exception as e:print(e)
sc.render.use_persistent_data=True;sc.cycles.samples=80;sc.cycles.use_denoising=True;sc.render.resolution_percentage=100
for cam,name in [('CAM_ARRIERE_OBLIQUE','arriere-oblique-relit'),('CAM_PHOTO','avant-relit'),('CAM_RACCORD_GAUCHE','raccord-relit')]:
    sc.camera=bpy.data.objects[cam];sc.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
sc.camera=bpy.data.objects['CAM_ARRIERE_OBLIQUE'];old=sc.camera.location.copy()
sc.camera.location+=sc.camera.matrix_world.to_3x3()@Vector((.4,0,0));sc.render.filepath=str(OUT/'deplacement-40cm.png');bpy.ops.render.render(write_still=True);sc.camera.location=old
# Real relighting proof: the projected albedo remains in Base Color while lights are changed.
saved=[(o,o.data.energy) for o in sc.objects if o.type=='LIGHT']
for o,energy in saved:o.data.energy=energy*.22
data=bpy.data.lights.new('TEST relighting','AREA');o=bpy.data.objects.new('TEST relighting',data);sc.collection.objects.link(o)
o.location=(.4,-1.6,2.6);o.rotation_euler=(Vector((0,-2.5,.2))-o.location).to_track_quat('-Z','Y').to_euler();data.energy=450;data.color=(.60,.76,1);data.shape='DISK';data.size=1.1
sc.render.filepath=str(OUT/'controle-relighting.png');bpy.ops.render.render(write_still=True)
bpy.data.objects.remove(o,do_unlink=True)
for o,energy in saved:o.data.energy=energy
# A 360 view for joins; no new projection is made from this camera.
sc.camera=bpy.data.objects['CAM_360'];sc.camera.data.type='PANO';sc.camera.data.panorama_type='EQUIRECTANGULAR';sc.render.resolution_x=2560;sc.render.resolution_y=1280;sc.cycles.samples=48
sc.render.filepath=str(OUT/'panorama-360-relit.png');bpy.ops.render.render(write_still=True)
# Save the actual coverage/stitch mask in the oblique view, with all non-target materials black.
sc.camera=bpy.data.objects['CAM_ARRIERE_OBLIQUE'];sc.render.resolution_x=1456;sc.render.resolution_y=816
sc.view_settings.view_transform='Standard';sc.view_settings.look='None';sc.view_settings.exposure=0;sc.cycles.samples=2;sc.cycles.use_denoising=False
for m in bpy.data.materials:
    nt=m.node_tree
    if not nt:continue
    out=next((n for n in nt.nodes if n.type=='OUTPUT_MATERIAL' and n.is_active_output),None)
    if not out:continue
    em=nt.nodes.new('ShaderNodeEmission');em.inputs['Color'].default_value=(0,0,0,1)
    group=nt.nodes.get('GPT · projections albédo')
    if group:
        comb=nt.nodes.new('ShaderNodeCombineColor');nt.links.new(group.outputs['Coverage'],comb.inputs['Green']);nt.links.new(group.outputs['Overlap'],comb.inputs['Red']);nt.links.new(comb.outputs[0],em.inputs['Color'])
    nt.links.new(em.outputs[0],out.inputs['Surface'])
sc.render.filepath=str(OUT/'masque-couverture-raccords.png');bpy.ops.render.render(write_still=True)
print('FINAL_ALBEDO_RENDERS_DONE',flush=True)
