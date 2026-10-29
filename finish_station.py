import bpy,sys,json,hashlib,math
from pathlib import Path
from mathutils import Vector
R=Path(__file__).parent;O=R/'output/station-sas-v1';sys.path.insert(0,str(R));import pano_atelier
bpy.ops.wm.open_mainfile(filepath=str(O/'station-base-projections.blend'));pano_atelier.register();sc=bpy.context.scene
def signature():
    return hashlib.sha256(str([(o.name,o.parent.name if o.parent else None,list(map(tuple,o.matrix_world)),[tuple(v.co) for v in o.data.vertices] if o.type=='MESH' else None) for o in sorted(sc.objects,key=lambda o:o.name)]).encode()).hexdigest()
before=signature();sc.pa_modular.projection_manifest=str(O/'projections/views.json');assert bpy.ops.pa.apply_multiview_albedo()=={'FINISHED'};assert signature()==before
root=bpy.data.objects['MODULE 03 · cabine pressurisee'];sample=next(o for o in root.children_recursive if o.type=='MESH' and 'PA_RestWorld' in o.data.attributes)
def attrs():
    ev=sample.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();values=[tuple(d.vector) for d in me.attributes['PA_RestWorld'].data];ev.to_mesh_clear();return values
prior=attrs();old=root.location.copy();rot=root.rotation_euler.copy();children={o:o.matrix_world.copy() for o in root.children_recursive};outside={o:o.matrix_world.copy() for o in sc.objects if o not in children and o!=root}
root.location+=Vector((1.1,.4,.2));bpy.context.view_layer.update();translation=attrs()==prior;followers=all((o.matrix_world.translation-m.translation-Vector((1.1,.4,.2))).length<1e-4 for o,m in children.items());neighbors=all((o.matrix_world.translation-m.translation).length<1e-5 for o,m in outside.items());root.rotation_euler.z+=.2;bpy.context.view_layer.update();rotation=attrs()==prior;root.location=old;root.rotation_euler=rot;bpy.context.view_layer.update()
assert translation and rotation and followers and neighbors
preserved=signature()==before
pano_atelier.modular_workflow.station_scene.finish_details(sc)
for im in bpy.data.images:
    if im.source=='FILE' and im.has_data:im.pack()
sc['pa_stage']='03 · albedos GPT multivues et eclairage physique';sc.name='Station · sas modulaires textures · V1'
# Useful camera path is retained and all texture coordinates remain object-attached.
sc.camera=bpy.data.objects['CAM_01 · sas de reference'];sc.render.resolution_x=1440;sc.render.resolution_y=960;sc.cycles.samples=64;sc.render.resolution_percentage=100
sc.pa_modular.asset_root=r'K:\Connector-Blender\Blender-asset-lib-VDB\KitBash';sc.pa_modular.output=str(O);sc.pa_modular.reference=str(O/'reference/panorama-stitched.png')
sc.pa_settings.output=str(O);sc.pa_settings.image=sc.pa_modular.reference
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':area.spaces.active.region_3d.view_perspective='CAMERA';area.spaces.active.show_region_ui=True;area.spaces.active.clip_end=200
validation={'geometry_transforms_parents_preserved_during_projection':preserved,'additional_physical_fittings':sc['pa_station_details'],'rest_coordinates_stable_translation':translation,'rest_coordinates_stable_rotation':rotation,'module_children_follow':followers,'neighbors_unchanged':neighbors,'multiview':json.loads(sc['pa_multiview_report']),'unpacked_images':[im.name for im in bpy.data.images if im.source=='FILE' and im.has_data and not im.packed_file],'linked_objects':[o.name for o in sc.objects if o.library],'note':'Generated albedo remains an approximation; no guarantee of perfect intrinsic decomposition. Rest attributes validated after bevels. Additional fittings are a separate final collection.'}
assert not validation['unpacked_images'] and not validation['linked_objects'];(O/'validation.json').write_text(json.dumps(validation,ensure_ascii=False,indent=2),encoding='utf8')
bpy.ops.wm.save_as_mainfile(filepath=str(O/'station-sas-modulaire-texturee-v1.blend'));print('STATION_FINAL_SAVED',validation,flush=True)
