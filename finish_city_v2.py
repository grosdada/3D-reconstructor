import bpy,sys,json,time
from pathlib import Path
R=Path(__file__).parent;O=R/'output/ville-brutaliste-v2';sys.path.insert(0,str(R))
import pano_atelier
from pano_atelier.city_projection import apply
from pano_atelier.city_optimize import metrics
from pano_atelier.modular_scene import Builder,camera
bpy.ops.wm.open_mainfile(filepath=str(O/'ville-brutaliste-V2.blend'));pano_atelier.register();sc=bpy.context.scene
r=apply(sc,O/'projection',.60,incidence_exponent=1)
sc.pa_city.reference=str(R/'output/ville-brutaliste-v1/reference-A1.png');sc.pa_city.asset_root=r'K:\Connector-Blender\Blender-asset-lib-VDB';sc.pa_city.output=str(O);sc.pa_city.projection_folder=str(O/'projection');sc.pa_city.projection_strength=.6;sc.pa_city.fog_density=.0072
sc.pa_settings.output=str(O);sc.pa_modular.output=str(O)
cam4=next(o for o in sc.objects if o.type=='CAMERA' and o.name.startswith('CAM_04'))
from mathutils import Vector
cam4.location=(39,-42,17);cam4.rotation_euler=(Vector((10,-3,17))-cam4.location).to_track_quat('-Z','Y').to_euler();cam4.data.lens=43
b=Builder(sc,'VILLE V2 · camera de proximite');cam=camera(b,'CAM_08 · voitures et rez-de-chaussee',(22,-48,2.1),(14,-38.5,1.2),46,1800,1100);cam.data.clip_end=1500
for im in bpy.data.images:
 if im.source=='FILE' and not im.packed_file:
  try:im.pack()
  except RuntimeError:pass
sc.cycles.samples=64;sc.cycles.use_denoising=True;sc.cycles.use_light_tree=True;sc.cycles.use_adaptive_sampling=True;sc.cycles.adaptive_threshold=.035;sc.cycles.device='GPU'
sc.render.resolution_x=2400;sc.render.resolution_y=1333;sc.render.resolution_percentage=100;sc.render.filepath=str(O/'rendu-utilisateur.png')
sc.camera=next(o for o in sc.objects if o.type=='CAMERA' and o.name.startswith('CAM_01'));sc.camera['pa_resolution_x']=2400;sc.camera['pa_resolution_y']=1333
bpy.context.view_layer.update();bpy.ops.outliner.orphans_purge(do_local_ids=True,do_linked_ids=False,do_recursive=True)
result={'projection':r,'metrics':metrics(sc),'materials':len(bpy.data.materials),'images':len(bpy.data.images),'cameras':len([o for o in sc.objects if o.type=='CAMERA'])}
(O/'final-report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
bpy.ops.wm.save_as_mainfile(filepath=str(O/'ville-brutaliste-V2.blend'),compress=True)
print('V2_FINAL_SAVED',json.dumps(result),flush=True)
# All delivered images are actual Cycles renders, not the generated albedo.
p=bpy.context.preferences.addons['cycles'].preferences;p.compute_device_type='OPTIX';p.get_devices()
for d in p.devices:d.use=d.type!='CPU'
sc.render.use_persistent_data=True;sc.cycles.samples=48;sc.render.image_settings.file_format='PNG';sc.render.image_settings.color_mode='RGB'
cams=sorted([o for o in sc.objects if o.type=='CAMERA' and o.name.startswith('CAM_')],key=lambda o:o.name)
jobs=[]
for idx in (0,3,1,4,7):
 sc.camera=cams[idx];sc.render.resolution_x=2400 if idx==0 else 1800;sc.render.resolution_y=1333 if idx==0 else 1100
 sc.render.filepath=str(O/('CAM_%02d.png'%(idx+1)));t=time.perf_counter();bpy.ops.render.render(write_still=True)
 jobs.append({'camera':sc.camera.name,'file':sc.render.filepath,'seconds':time.perf_counter()-t});print('V2_RENDER_DONE',json.dumps(jobs[-1]),flush=True)
(O/'renders.json').write_text(json.dumps(jobs,ensure_ascii=False,indent=2),encoding='utf8')
print('V2_RENDERS_DONE',flush=True)
