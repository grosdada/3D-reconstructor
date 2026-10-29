"""Read the saved scene, render real checks, do not save diagnostic changes."""
import bpy,json
from pathlib import Path
from mathutils import Vector
out=Path(bpy.data.filepath).parent;sc=bpy.context.scene
p=bpy.context.preferences.addons['cycles'].preferences;p.compute_device_type='OPTIX';p.get_devices()
for d in p.devices:d.use=d.type!='CPU'
sc.cycles.device='GPU';sc.cycles.samples=64;sc.cycles.use_denoising=True
sc.render.resolution_percentage=100;sc.render.use_persistent_data=True
views=[('CAM_01 · reference portrait','01-reference',1000,1200),('CAM_02 · ensemble frontal','02-ensemble',1440,960),('CAM_04 · vue aerienne','03-aerienne',1200,1200),('CAM_03 · approche pieton','04-approche',1000,1200)]
for cam,name,w,h in views:
    sc.camera=bpy.data.objects[cam];sc.render.resolution_x=w;sc.render.resolution_y=h
    sc.render.filepath=str(out/(name+'.png'));bpy.ops.render.render(write_still=True)
    print('CONTROL_RENDER',name,flush=True)
veg=bpy.data.collections['05 · Vegetation botaniq'];veg.hide_render=True
sc.camera=bpy.data.objects['CAM_05 · controle lateral'];sc.render.resolution_x=1440;sc.render.resolution_y=960
sc.render.filepath=str(out/'05-architecture-sans-arbres.png');bpy.ops.render.render(write_still=True)
veg.hide_render=False
# Rotation test on a complete facade assembly after reloading, restored without saving.
o=bpy.data.objects['BATIMENT · aile principale'];child=next(c for c in o.children_recursive if c.type=='MESH')
before=o.matrix_world.inverted()@child.matrix_world
orig=o.rotation_euler.copy();o.rotation_euler.z+=.31;bpy.context.view_layer.update()
after=o.matrix_world.inverted()@child.matrix_world
rotation_ok=max(abs(before[i][j]-after[i][j]) for i in range(4) for j in range(4))<1e-5
o.rotation_euler=orig;bpy.context.view_layer.update()
linked={key:[x.name for x in getattr(bpy.data,key) if x.library] for key in ['objects','meshes','materials','node_groups','images','collections']}
packed=all(im.packed_file for im in bpy.data.images if im.source=='FILE')
report={'reopened_file':bpy.data.filepath,'renders':[n+'.png' for _,n,_,_ in views]+['05-architecture-sans-arbres.png'],'rotation_preserves_child_local_transform':rotation_ok,'all_asset_data_local':not any(linked.values()),'linked_data':linked,'all_images_packed':packed,'camera_count':sum(o.type=='CAMERA' for o in sc.objects),'note':'These checks do not prove a surveyed match, complete collision clearance or a finished texture pass.'}
(out/'validation.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf8')
print('TOWER_CHECKS_DONE',flush=True)
