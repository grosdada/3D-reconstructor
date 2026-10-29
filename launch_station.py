import bpy,sys,json,importlib.util,types
from pathlib import Path
R=Path(__file__).parent
# Load this project version for this process only, even if an older packaged add-on is enabled.
for module in list(sys.modules.values()):
    info = vars(module).get('bl_info', {}) if isinstance(module, types.ModuleType) else {}
    if isinstance(info, dict) and info.get('name')=='Pano Atelier' and bpy.types.Panel.bl_rna_get_subclass_py('PA_PT_main'):
        module.unregister()
spec=importlib.util.spec_from_file_location('pano_atelier_station_session',R/'pano_atelier/__init__.py',submodule_search_locations=[str(R/'pano_atelier')]);pano_atelier=importlib.util.module_from_spec(spec);sys.modules[spec.name]=pano_atelier;spec.loader.exec_module(pano_atelier);pano_atelier.register()
sc=bpy.context.scene
try:
    p=bpy.context.preferences.addons['cycles'].preferences;p.compute_device_type='OPTIX';p.get_devices()
    for d in p.devices:d.use=d.type!='CPU'
except Exception:pass
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.show_region_ui=True;area.spaces.active.region_3d.view_perspective='CAMERA';area.spaces.active.shading.type='MATERIAL';area.spaces.active.shading.use_scene_lights=True;area.spaces.active.shading.use_scene_world=True
            try:next(r for r in area.regions if r.type=='UI').active_panel_category='Pano Atelier'
            except Exception:pass
O=Path(bpy.data.filepath).parent
(O/'opened-in-blender.json').write_text(json.dumps({'filepath':bpy.data.filepath,'background':bpy.app.background,'addon_version':list(pano_atelier.bl_info['version']),'scene':sc.name,'windows':len(bpy.context.window_manager.windows),'camera_count':len(pano_atelier.camera_navigation.cameras(sc)),'modular_panel_registered':bpy.types.Panel.bl_rna_get_subclass_py('PA_PT_modular') is not None,'mouse_navigation_registered':bpy.types.Operator.bl_rna_get_subclass_py('PA_OT_explore_modular') is not None},indent=2,ensure_ascii=False),encoding='utf8')
