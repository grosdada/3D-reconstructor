import bpy,sys,json
from pathlib import Path
R=Path(__file__).parent;sys.path.insert(0,str(R));import pano_atelier
bpy.ops.wm.read_factory_settings(use_empty=True);pano_atelier.register();sc=bpy.context.scene;s=sc.pa_modular;s.asset_root=r'K:\Connector-Blender\Blender-asset-lib-VDB\KitBash';s.output=str(R/'test-output/station-recipe')
assert bpy.ops.pa.build_station()=={'FINISHED'}
shots=pano_atelier.camera_navigation.cameras(sc);projections=[o for o in sc.objects if o.type=='CAMERA' and o.name.startswith('PROJ_')]
assert len(shots)==9 and len(projections)==8
walls=[o for o in sc.objects if o.name.startswith('Cloison · support continu')];assert len(walls)==12
bpy.context.view_layer.update()
from mathutils import Vector
assert all(min((o.matrix_world@Vector(v)).z for v in o.bound_box)<-.19 for o in walls)
count=len(sc.objects)
try:bpy.ops.pa.build_station()
except RuntimeError:pass
assert len(sc.objects)==count
result={'operator_build':True,'shot_cameras':len(shots),'projection_cameras':len(projections),'wall_floor_overlap':True,'repeat_build_rejected_without_mutation':True,'objects':count}
(R/'test-output/station-recipe/test.json').write_text(json.dumps(result,indent=2),encoding='utf8');print('STATION_RECIPE_TEST_DONE',result,flush=True)
