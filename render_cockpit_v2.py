import bpy,sys
from pathlib import Path
OUT=Path(bpy.data.filepath).parent
sc=bpy.context.scene
try:
    prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
    for dev in prefs.devices:dev.use=dev.type!='CPU'
    sc.cycles.device='GPU'
except Exception as e:print(e)
sc.render.use_persistent_data=True;sc.cycles.use_denoising=True
for name,f in [('CAM_PHOTO','avant'),('CAM_ARRIERE','arriere'),('CAM_ARRIERE_OBLIQUE','arriere-oblique'),('CAM_RACCORD_GAUCHE','raccord-gauche')]:
    sc.camera=bpy.data.objects[name];sc.render.filepath=str(OUT/(f+'.png'));bpy.ops.render.render(write_still=True)
sc.camera=bpy.data.objects['CAM_360'];sc.camera.data.type='PANO';sc.camera.data.panorama_type='EQUIRECTANGULAR'
sc.render.resolution_x=2560;sc.render.resolution_y=1280;sc.render.resolution_percentage=100;sc.cycles.samples=64
sc.render.filepath=str(OUT/'panorama-360.png');bpy.ops.render.render(write_still=True)
print('COCKPIT_RENDERS_DONE',str(OUT),flush=True)
