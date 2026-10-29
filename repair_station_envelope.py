import bpy,sys,json
from pathlib import Path
R=Path(__file__).parent;O=R/'output/station-sas-v1';sys.path.insert(0,str(R));from pano_atelier.station_scene import seal_backing
bpy.ops.wm.open_mainfile(filepath=str(O/'station-sas-modulaire-texturee-v1.blend'));changed=seal_backing(bpy.context.scene)
(O/'envelope-repair.json').write_text(json.dumps({'hidden_backing_walls_overlapped_with_floor':changed,'visible_geometry_changed':False},ensure_ascii=False,indent=2),encoding='utf8')
bpy.ops.wm.save_as_mainfile(filepath=str(O/'station-sas-modulaire-texturee-v1.blend'));print('ENVELOPE_REPAIRED',len(changed),flush=True)
