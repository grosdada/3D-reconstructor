"""Configure this Blender session only; preserve saved input/preferences."""
import bpy,json
from pathlib import Path
try:
    p=bpy.context.preferences.addons['cycles'].preferences;p.compute_device_type='OPTIX';p.get_devices()
    for d in p.devices:d.use=d.type!='CPU'
except Exception:pass
out=Path(bpy.data.filepath).parent
report={'file':bpy.data.filepath,'background':bpy.app.background,'scene':bpy.context.scene.name,
        'objects':len(bpy.context.scene.objects),'camera':bpy.context.scene.camera.name if bpy.context.scene.camera else None,
        'windows':len(bpy.context.window_manager.windows),'version':bpy.app.version_string}
(out/'opened-in-blender.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
