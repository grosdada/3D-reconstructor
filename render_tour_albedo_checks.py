"""Validate V2 against the approved V1, then render multiview/movement/relighting evidence."""
import bpy,json,hashlib
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).parent;OUT=ROOT/'output/tour-belvedere-v2'
def fingerprint():
    return hashlib.sha256(str([(o.name,o.type,o.parent.name if o.parent else None,list(map(tuple,o.matrix_world)),[tuple(v.co) for v in o.data.vertices] if o.type=='MESH' else None,[tuple(sorted(p.vertices)) for p in o.data.polygons] if o.type=='MESH' else None) for o in sorted(bpy.context.scene.objects,key=lambda x:x.name) if o.type not in {'CAMERA','LIGHT'}]).encode()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'output/tour-belvedere-v1/tour-belvedere-geometrie-v1.blend'))
approved=fingerprint()
bpy.ops.wm.open_mainfile(filepath=str(OUT/'tour-belvedere-albedo-v2.blend'))
current=fingerprint();assert approved==current, 'Approved V1 geometry changed'
sc=bpy.context.scene
p=bpy.context.preferences.addons['cycles'].preferences;p.compute_device_type='OPTIX';p.get_devices()
for d in p.devices:d.use=d.type!='CPU'
sc.cycles.device='GPU';sc.cycles.samples=96;sc.cycles.use_denoising=True;sc.render.use_persistent_data=True
sc.render.resolution_percentage=100
def render(camera,name,w=1440,h=960):
    sc.camera=camera;sc.render.resolution_x=w;sc.render.resolution_y=h;sc.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True);print('CHECK_RENDER',name,flush=True)
views=[('CAM_01 · reference portrait','01-reference',1000,1200),('CAM_02 · ensemble frontal','02-ensemble',1440,960),('CAM_04 · vue aerienne','03-aerienne',1200,1200),('CAM_03 · approche pieton','04-approche',1000,1200)]
for cam,name,w,h in views:render(bpy.data.objects[cam],name,w,h)
veg=bpy.data.collections['05 · Vegetation botaniq'];veg.hide_render=True
render(bpy.data.objects['CAM_05 · controle lateral'],'05-architecture-sans-arbres')
veg.hide_render=False
d=bpy.data.cameras.new('TEMP_camera_check');o=bpy.data.objects.new(d.name,d);sc.collection.objects.link(o)
o.location=(3,-40,3);o.rotation_euler=(Vector((14,-17,2.5))-o.location).to_track_quat('-Z','Y').to_euler();d.lens=40
render(o,'06-facade-proche')
# Same view, translated building: real texture movement, not a world-space slide.
building=bpy.data.objects['BATIMENT · prolongement premier plan'];old=building.location.copy();building.location+=Vector((1.8,0,0));bpy.context.view_layer.update()
render(o,'07-module-deplace');building.location=old;bpy.context.view_layer.update()
# Different view after camera movement across a multiview junction.
o.location=(-34,-28,22);o.rotation_euler=(Vector((0,0,26))-o.location).to_track_quat('-Z','Y').to_euler();d.lens=43
render(o,'08-raccord-oblique',1200,1200)
o.location=(-29,-24,22);o.rotation_euler=(Vector((0,0,26))-o.location).to_track_quat('-Z','Y').to_euler()
render(o,'09-raccord-deplacement-5m',1200,1200)
# True material relighting test (diagnostic only, never saved to production scene).
for light in [x for x in sc.objects if x.type=='LIGHT']:light.data.energy*=.10
sc.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.10
ld=bpy.data.lights.new('TEMP soleil rasant','SUN');lo=bpy.data.objects.new(ld.name,ld);sc.collection.objects.link(lo);ld.energy=2.5;ld.color=(1,.72,.44);lo.rotation_euler=(.75,-.5,-.7);ld.angle=.06
render(o,'10-controle-relighting',1200,1200)
report={'approved_v1_fingerprint':approved,'v2_fingerprint':current,'approved_geometry_preserved':approved==current,'all_images_packed':all(im.packed_file for im in bpy.data.images if im.source=='FILE'),'all_asset_data_local':all(not x.library for k in ['objects','meshes','materials','images','node_groups','collections'] for x in getattr(bpy.data,k)),'renders':[x[1]+'.png' for x in views]+[str(x) for x in ['05-architecture-sans-arbres.png','06-facade-proche.png','07-module-deplace.png','08-raccord-oblique.png','09-raccord-deplacement-5m.png','10-controle-relighting.png']],'note':'Movement and changed-light images are checks, not saved transforms or lighting. Multiview imagery remains an approximate generated albedo.'}
(OUT/'validation-renders.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf8')
print('TOUR_V2_CHECKS_DONE',flush=True)
