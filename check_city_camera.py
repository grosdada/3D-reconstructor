import bpy,json
from pathlib import Path
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
R=Path(__file__).parent;O=R/'output/ville-brutaliste-v1';bpy.ops.wm.open_mainfile(filepath=str(O/'ville-brutaliste-geometrie.blend'));sc=bpy.context.scene
r={'camera':sc.camera.name,'matrix':[list(r) for r in sc.camera.matrix_world],'lens':sc.camera.data.lens,'objects':[]}
for o in sc.objects:
 if o.name.startswith(('A1 · tour mince','A1 · noyau porteur','A1 · couronne','BG · tour sombre')):
  r['objects'].append({'name':o.name,'loc':list(o.matrix_world.translation),'parent':o.parent.name,'top_projected':list(world_to_camera_view(sc,sc.camera,o.matrix_world@Vector((0,0,60))))})
print(json.dumps(r,ensure_ascii=False),flush=True)
