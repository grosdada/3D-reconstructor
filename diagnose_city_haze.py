import bpy
from pathlib import Path
R=Path(__file__).parent;O=R/'output/ville-brutaliste-v3-vis-a-vis'
bpy.ops.wm.open_mainfile(filepath=str(O/'ville-brutaliste-vis-a-vis.blend'));s=bpy.context.scene
for o in s.objects:
 if o.get('pa_noncolliding') and not o.get('pa_opposite'):o.hide_render=True
s.camera=next(o for o in s.objects if o.type=='CAMERA' and o.name.startswith('CAM_10'));s.render.resolution_x=1200;s.render.resolution_y=660;s.cycles.samples=16;s.cycles.device='GPU'
p=bpy.context.preferences.addons['cycles'].preferences;p.compute_device_type='OPTIX';p.get_devices()
for d in p.devices:d.use=d.type!='CPU'
s.render.filepath=str(O/'diagnostic-sans-brume-nord.png');bpy.ops.render.render(write_still=True)
