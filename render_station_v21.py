import bpy,sys,json
from pathlib import Path
from mathutils import Vector
R=Path(__file__).parent;O=R/'output/station-sas-v2.1'
bpy.ops.wm.open_mainfile(filepath=str(O/'station-sas-modulaire-texturee-v2.1.blend'));sc=bpy.context.scene
p=bpy.context.preferences.addons['cycles'].preferences;p.compute_device_type='OPTIX';p.get_devices()
for d in p.devices:d.use=d.type!='CPU'
sc.cycles.device='GPU';sc.cycles.samples=48;sc.cycles.use_denoising=True;sc.render.use_persistent_data=True;sc.render.resolution_percentage=100
cams=sorted([o for o in sc.objects if o.type=='CAMERA' and o.name.startswith('CAM_')],key=lambda o:o.name)
quick='--quick' in sys.argv
if quick:cams=[cams[0],cams[1],cams[5]];sc.cycles.samples=32
jobs=[]
for cam in cams:
    sc.camera=cam;w=1440 if quick else 1800;h=int(w*2/3)
    if cam.data.type=='PANO':w=3000;h=1500
    sc.render.resolution_x=w;sc.render.resolution_y=h;name=cam.name.split(' · ')[0]+('-preview' if quick else '')
    sc.render.filepath=str(O/(name+'.png'));bpy.ops.render.render(write_still=True);jobs.append({'camera':cam.name,'file':name+'.png','size':[w,h]});print('V21_RENDER',name,flush=True)
# A grazing-angle floor inspection, not saved as another scene camera.
cam=bpy.data.objects.new('TEMP_detail_sol',bpy.data.cameras.new('TEMP_detail_sol'));sc.collection.objects.link(cam);cam.location=(.45,.0,1.35);target=Vector((0,1.25,.23));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.lens=40;sc.camera=cam
sc.render.resolution_x=1400;sc.render.resolution_y=1100;sc.render.filepath=str(O/'detail-sol.png');bpy.ops.render.render(write_still=True)
(O/('renders-preview.json' if quick else 'renders.json')).write_text(json.dumps(jobs,ensure_ascii=False,indent=2),encoding='utf8');print('V21_RENDERS_DONE',flush=True)
