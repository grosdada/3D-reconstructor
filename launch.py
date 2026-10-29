"""Portable development launcher; does not change Blender's saved preferences."""
import sys
from pathlib import Path
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
# Respect the user's saved mouse/keymap preferences. If an installed copy has
# already registered these panels, replace its runtime registration in this new
# process; do not edit Blender's saved preferences or the installed add-on.
panel=bpy.types.Panel.bl_rna_get_subclass_py('PA_PT_main')
if panel:
    previous=sys.modules.get(panel.__module__)
    if previous and hasattr(previous,'unregister'): previous.unregister()
for module_name in list(sys.modules):
    if module_name=='pano_atelier' or module_name.startswith('pano_atelier.'):
        del sys.modules[module_name]
import pano_atelier
pano_atelier.register()
scene=bpy.context.scene
scene.pa_settings.moge_python=str(ROOT/'.venv'/'Scripts'/'python.exe')
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            space=area.spaces.active
            space.show_region_ui=True
            space.shading.type='MATERIAL'
            space.overlay.show_overlays=False
            if scene.camera:
                space.region_3d.view_perspective='CAMERA'
                space.region_3d.view_camera_zoom=0
def reveal_panel():
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=='VIEW_3D':
                for region in area.regions:
                    if region.type=='UI':
                        try: region.active_panel_category='Pano Atelier'
                        except (TypeError,AttributeError): pass
    return None
bpy.app.timers.register(reveal_panel,first_interval=1.5)
