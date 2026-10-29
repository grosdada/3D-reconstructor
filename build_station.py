import bpy,sys,json
from pathlib import Path
R=Path(__file__).parent;O=R/'output/station-sas-v1';sys.path.insert(0,str(R))
import pano_atelier
bpy.ops.wm.read_factory_settings(use_empty=True);pano_atelier.register()
s=bpy.context.scene.pa_modular;s.asset_root=r'K:\Connector-Blender\Blender-asset-lib-VDB\KitBash';s.output=str(O);s.reference=str(O/'reference/panorama-stitched.png')
assert bpy.ops.pa.build_station()=={'FINISHED'}
sc=bpy.context.scene;sc.name='Station · sas et couloirs · V1 geometrie'
p=bpy.context.preferences.addons['cycles'].preferences;p.compute_device_type='OPTIX';p.get_devices()
for d in p.devices:d.use=d.type!='CPU'
sc.cycles.device='GPU'
# Only used scene assets are retained; remove unused inherited library datablocks.
bpy.ops.outliner.orphans_purge(do_local_ids=True,do_linked_ids=True,do_recursive=True)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'station-structure-v1.blend'))
for cam,name in [('CAM_01 · sas de reference','01-geometry-front'),('CAM_03 · arriere raccorde','02-geometry-back'),('CAM_02 · oblique avant','03-geometry-oblique')]:
    sc.camera=bpy.data.objects[cam];sc.cycles.samples=24;sc.render.resolution_x=1200;sc.render.resolution_y=800;sc.render.filepath=str(O/(name+'.png'));bpy.ops.render.render(write_still=True)
print('STATION_BUILD_AND_RENDER_DONE',flush=True)
