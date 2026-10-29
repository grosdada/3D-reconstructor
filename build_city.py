import bpy,sys,json
from pathlib import Path
R=Path(__file__).parent;O=R/'output/ville-brutaliste-v1';sys.path.insert(0,str(R))
from pano_atelier.city_scene import build
bpy.ops.wm.read_factory_settings(use_empty=True)
sc,r=build(bpy.context.scene,O,r'K:\Connector-Blender\Blender-asset-lib-VDB',O/'reference-A1.png')
sc.name='Ville brutaliste · A1 · reconstruction modulaire'
bpy.ops.wm.save_as_mainfile(filepath=str(O/'ville-brutaliste-geometrie.blend'));print('CITY_BUILT',r['objects'],flush=True)
p=bpy.context.preferences.addons['cycles'].preferences;p.compute_device_type='OPTIX';p.get_devices()
for d in p.devices:d.use=d.type!='CPU'
sc.cycles.device='GPU';sc.cycles.samples=24;sc.render.resolution_percentage=65;sc.render.filepath=str(O/'A1-preview.png');bpy.ops.render.render(write_still=True);print('CITY_PREVIEW_DONE',flush=True)
