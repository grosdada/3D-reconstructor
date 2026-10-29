import runpy,bpy,json
from pathlib import Path
R=Path(__file__).parent
runpy.run_path(str(R/'launch_city_v2.py'),run_name='__main__')
sc=bpy.context.scene
sc.cycles.preview_samples=24
for screen in bpy.data.screens:
 for area in screen.areas:
  if area.type=='VIEW_3D':
   sp=area.spaces.active;sp.shading.type='RENDERED';sp.region_3d.view_camera_zoom=0
(Path(bpy.data.filepath).parent/'opened-in-blender.json').write_text(json.dumps({'file':bpy.data.filepath,'background':bpy.app.background,'addon':[0,6,1],'gas_panel':bool(bpy.types.Panel.bl_rna_get_subclass_py('PA_PT_gas')),'camera':sc.camera.name,'display':'RENDERED'},indent=2),encoding='utf8')
