import bpy,json
from pathlib import Path
from mathutils import Vector
R=Path(__file__).parent;O=R/'output/station-sas-v2.2'
bpy.ops.wm.open_mainfile(filepath=str(O/'station-sas-modulaire-texturee-v2.2.blend'));sc=bpy.context.scene
p=bpy.context.preferences.addons['cycles'].preferences;p.compute_device_type='OPTIX';p.get_devices()
for d in p.devices:d.use=d.type!='CPU'
sc.cycles.device='GPU';sc.cycles.samples=48;sc.cycles.use_denoising=True;sc.render.use_persistent_data=True;sc.render.resolution_percentage=100
cams=sorted([o for o in sc.objects if o.type=='CAMERA' and o.name.startswith('CAM_')],key=lambda o:o.name)
detail=bpy.data.objects.new('TEMP_detail_sol',bpy.data.cameras.new('TEMP_detail_sol'));sc.collection.objects.link(detail);detail.location=(.45,0,1.35);detail.rotation_euler=(Vector((0,1.25,.23))-detail.location).to_track_quat('-Z','Y').to_euler();detail.data.lens=40
jobs=[(detail,'detail-sol',1400,1100),(cams[0],'CAM_01',1800,1200),(cams[1],'CAM_02',1800,1200),(cams[5],'CAM_06',1800,1200)]
for cam,name,w,h in jobs:
 sc.camera=cam;sc.render.resolution_x=w;sc.render.resolution_y=h;sc.render.filepath=str(O/(name+'.png'));bpy.ops.render.render(write_still=True);print('V22_RENDER',name,flush=True)
print('V22_RENDERS_DONE',flush=True)
