import bpy,sys,json,hashlib
from pathlib import Path
from mathutils import Vector
R=Path(__file__).parent;O=R/'output/station-sas-v2';O.mkdir(exist_ok=True)
sys.path.insert(0,str(R));import pano_atelier
from pano_atelier import station_refinement
bpy.ops.wm.open_mainfile(filepath=str(R/'output/station-sas-v1/station-sas-modulaire-texturee-v1.blend'));pano_atelier.register();sc=bpy.context.scene
sc.pa_modular.asset_root=r'K:\Connector-Blender\Blender-asset-lib-VDB\KitBash';sc.pa_modular.detail_albedo=str(O/'textures/hatch-painted-metal-albedo.png')
assert bpy.ops.pa.refine_station()=={'FINISHED'}
report=json.loads(sc['pa_station_refinement_report'])
# Replace selected single-view albedos only; original depth and protection gates
# and mesh rest coordinates are retained, so projection follows movable objects.
updates=[]
for stem in ('avant','droite'):
    replacement=O/'textures'/(stem+'-albedo-v2.png')
    if not replacement.is_file():continue
    im=bpy.data.images.load(str(replacement),check_existing=True);im.pack()
    for tree in list(bpy.data.node_groups)+[m.node_tree for m in bpy.data.materials if m.use_nodes]:
        for node in tree.nodes:
            if node.type=='TEX_IMAGE' and node.image and node.image.name==stem+'-albedo.png':
                updates.append({'view':stem,'previous':node.image.name,'replacement':im.name,'native_pixels':list(im.size)});node.image=im
report['projection_replacements']=updates
bpy.context.view_layer.update()
# Disabled viewport objects do not have evaluated transforms. Include them by
# temporarily enabling evaluation for this check, then restore their visibility.
disabled=[o for o in sc.objects if o.hide_viewport]
for o in disabled:o.hide_viewport=False
bpy.context.view_layer.update()
# New details and preexisting rest-projected children must follow their assembly.
checks=[]
for name in ('SAS 04 · anneau et cloison','MODULE 03 · cabine pressurisee'):
    root=bpy.data.objects[name];children=list(root.children_recursive);before={o:o.matrix_world.copy() for o in children};outside={o:o.matrix_world.copy() for o in sc.objects if o not in children and o!=root};old=root.matrix_world.copy()
    root.location+=Vector((.9,.3,.1));root.rotation_euler.z+=.17;bpy.context.view_layer.update();delta=root.matrix_world@old.inverted()
    bad_children=[o.name for o,mat in before.items() if max(abs(v) for row in (o.matrix_world-delta@mat) for v in row)>=1e-4];bad_neighbors=[o.name for o,mat in outside.items() if max(abs(v) for row in (o.matrix_world-mat) for v in row)>=1e-4]
    follow=not bad_children;neighbors=not bad_neighbors
    print('MOVE_CHECK',name,bad_children[:30],bad_neighbors[:10],flush=True)
    root.matrix_world=old;bpy.context.view_layer.update();assert follow and neighbors;checks.append({'root':name,'children':len(children),'follow_rotation_translation':follow,'neighbors_unchanged':neighbors})
for o in disabled:o.hide_viewport=True
sc.name='Station · sas modulaires · V2 details et lumiere';sc['pa_output']=str(O);sc.pa_modular.output=str(O);sc.pa_settings.output=str(O);sc.camera=bpy.data.objects['CAM_01 · sas de reference'];sc.render.resolution_x=1440;sc.render.resolution_y=960;sc.cycles.samples=64
for im in bpy.data.images:
    if im.source=='FILE' and im.has_data:im.pack()
report['editability_checks']=checks;report['image_inventory']=[{'name':im.name,'size':list(im.size),'packed':bool(im.packed_file)} for im in bpy.data.images if im.has_data]
(O/'refinement-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
bpy.ops.wm.save_as_mainfile(filepath=str(O/'station-sas-modulaire-texturee-v2.blend'));print('STATION_V2_SAVED',len(sc.objects),flush=True)
