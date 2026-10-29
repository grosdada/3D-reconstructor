import bpy,sys,json,importlib.util,types
from pathlib import Path
R=Path(__file__).parent
for module in list(sys.modules.values()):
 info=vars(module).get('bl_info',{}) if isinstance(module,types.ModuleType) else {}
 if isinstance(info,dict) and info.get('name')=='Pano Atelier' and bpy.types.Panel.bl_rna_get_subclass_py('PA_PT_main'):module.unregister()
for module_name in list(sys.modules):
 if module_name=='pano_atelier_city_session' or module_name.startswith('pano_atelier_city_session.'):del sys.modules[module_name]
spec=importlib.util.spec_from_file_location('pano_atelier_city_session',R/'pano_atelier/__init__.py',submodule_search_locations=[str(R/'pano_atelier')]);addon=importlib.util.module_from_spec(spec);sys.modules[spec.name]=addon;spec.loader.exec_module(addon);addon.register()
sc=bpy.context.scene
try:
 p=bpy.context.preferences.addons['cycles'].preferences;p.compute_device_type='OPTIX';p.get_devices()
 for d in p.devices:d.use=d.type!='CPU'
 sc.cycles.device='GPU'
except Exception:pass
for screen in bpy.data.screens:
 for area in screen.areas:
  if area.type=='VIEW_3D':
   sp=area.spaces.active;sp.clip_end=2000;sp.show_region_ui=True;sp.region_3d.view_perspective='CAMERA';sp.shading.type='SOLID';sp.shading.use_scene_lights=True;sp.shading.use_scene_world=True
   try:next(r for r in area.regions if r.type=='UI').active_panel_category='Pano Atelier'
   except Exception:pass
(Path(bpy.data.filepath).parent/'opened-in-blender.json').write_text(json.dumps({'file':bpy.data.filepath,'background':bpy.app.background,'addon':list(addon.bl_info['version']),'city_panel':bool(bpy.types.Panel.bl_rna_get_subclass_py('PA_PT_city')),'cameras':len(addon.camera_navigation.cameras(sc))},indent=2),encoding='utf8')
