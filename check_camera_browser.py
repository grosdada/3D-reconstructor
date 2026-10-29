import bpy,sys,json
from pathlib import Path
R=Path(__file__).parent;sys.path.insert(0,str(R))
from pano_atelier import camera_navigation as nav
nav.register()
nav.register()
assert all(nav.registered_class(c) for c in nav.CLASSES)
nav.unregister();assert all(nav.registered_class(c) is None for c in nav.CLASSES)
nav.register();assert all(nav.registered_class(c) for c in nav.CLASSES)
bpy.ops.wm.open_mainfile(filepath=str(R/'output/tour-belvedere-v3/tour-belvedere-foret-360-v3.blend'))
sc=bpy.context.scene;items=nav.cameras(sc);old=sc.camera;start={o.name:o.matrix_world.copy() for o in items};selected=[o.name for o in bpy.context.selected_objects]
sc.camera=items[0]
for i in range(len(items)):
    assert bpy.ops.pa.camera_step(direction=1)=={'FINISHED'} and sc.camera==items[(i+1)%len(items)]
assert bpy.ops.pa.camera_step(direction=-1)=={'FINISHED'} and sc.camera==items[-1]
assert all(o.matrix_world==start[o.name] for o in items)
assert [o.name for o in bpy.context.selected_objects]==selected
assert bpy.ops.pa.camera_choose(camera_name='PROJ_avant')=={'CANCELLED'}
sc.camera=old
nav.unregister()
txt=bpy.data.texts.get('Pano Atelier · navigation cameras.py');txt.clear();txt.write((R/'pano_atelier/camera_navigation.py').read_text(encoding='utf8')+'\nregister()\n')
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
report={'registration_idempotent':True,'unregister_and_reregister':True,'wrap_both_directions':True,'transforms_unchanged':True,'selection_unchanged':True,'projection_camera_rejected':True,'shots':len(items)}
(R/'output/tour-belvedere-v3/validation-camera-browser.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('CAMERA_BROWSER_TESTS_DONE',json.dumps(report))
