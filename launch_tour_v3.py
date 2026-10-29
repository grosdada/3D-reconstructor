"""Open camera browser for this session only, without changing saved user preferences."""
import bpy,json,importlib.util
from pathlib import Path
R=Path(__file__).parent
spec=importlib.util.spec_from_file_location('pa_navigation_v3',R/'pano_atelier/camera_navigation.py')
nav=importlib.util.module_from_spec(spec);spec.loader.exec_module(nav);nav.register()
try:
    p=bpy.context.preferences.addons['cycles'].preferences;p.compute_device_type='OPTIX';p.get_devices()
    for d in p.devices:d.use=d.type!='CPU'
except Exception:pass
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.show_region_ui=True
            try:
                region=next(r for r in area.regions if r.type=='UI');region.active_panel_category='Pano Atelier'
            except Exception:pass
out=Path(bpy.data.filepath).parent
(out/'opened-in-blender.json').write_text(json.dumps({'file':bpy.data.filepath,'background':bpy.app.background,'scene':bpy.context.scene.name,'camera':bpy.context.scene.camera.name,'windows':len(bpy.context.window_manager.windows),'camera_browser_registered':nav.registered_class(nav.PA_CameraBrowser) is not None,'camera_count':len(nav.cameras(bpy.context.scene))},ensure_ascii=False,indent=2),encoding='utf8')
