import bpy,sys,json,math
from pathlib import Path
from mathutils import Vector
R=Path(__file__).parent;O=R/'output/station-sas-v2';sys.path.insert(0,str(R));import pano_atelier
from pano_atelier import station_refinement
bpy.ops.wm.open_mainfile(filepath=str(O/'station-sas-modulaire-texturee-v2.blend'));pano_atelier.register();sc=bpy.context.scene;bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get()
count=len(sc.objects)
try:station_refinement.apply(sc,'','')
except ValueError:pass
else:raise AssertionError('Duplicate refinement was accepted')
assert len(sc.objects)==count and not bpy.ops.pa.refine_station.poll()
total=0;miss=[]
for y in (-12,-6,-1,4,10,17):
    for az in range(48):
        a=az*math.tau/48
        for el in range(1,18):
            e=-math.pi/2+el*math.pi/18;d=Vector((math.cos(a)*math.cos(e),math.sin(a)*math.cos(e),math.sin(e)))
            if not sc.ray_cast(dg,Vector((0,y,1.6)),d,distance=80)[0]:miss.append((y,az,el))
            total+=1
path=bpy.data.objects['CAM_09 · parcours automatique'];old=sc.frame_current;last=None;blocked=[];segments=0
for frame in range(1,301,3):
    sc.frame_set(frame);bpy.context.view_layer.update();pos=path.matrix_world.translation.copy()
    if last is not None:
        delta=pos-last
        for off in ((0,0,0),(.16,0,0),(-.16,0,0),(0,0,.16),(0,0,-.16)):
            hit,loc,n,i,obj,mat=sc.ray_cast(dg,last+Vector(off),delta.normalized(),distance=delta.length+.03);segments+=1
            if hit:blocked.append([frame,obj.name])
    last=pos
sc.frame_set(old)
# Load packed buffers to verify sizes after save/reopen, including preexisting maps.
images=[]
for im in bpy.data.images:
    if im.source=='FILE':
        size=list(im.size);assert im.packed_file,(im.name,'not packed');images.append({'name':im.name,'size':size,'packed':True})
localmats=[m for m in bpy.data.materials if m.get('pa_local_texture')]
for m in localmats:
    bs=m.node_tree.nodes.get('Principled BSDF');assert not bs.inputs['Emission Color'].is_linked and bs.inputs['Emission Strength'].default_value==0
roots=[o for o in sc.objects if o.name.startswith('V2 ·') and o.type=='EMPTY'];assert roots and all(o.parent for o in roots)
curves=[o for o in sc.objects if o.type=='CURVE' and o.get('pa_detail_pass')=='v2'];assert curves and all(o.data.splines[0].type=='BEZIER' for o in curves)
origcam=sc.camera;cams=pano_atelier.camera_navigation.cameras(sc);sc.camera=cams[0]
for _ in cams:assert bpy.ops.pa.camera_step(direction=1)=={'FINISHED'}
assert sc.camera==cams[0];sc.camera=origcam
meshes={o.data for o in sc.objects if o.type=='MESH'}
evaltris=0
for o in sc.objects:
    if o.type in {'MESH','CURVE','FONT'} and not o.hide_render:
        ev=o.evaluated_get(dg);me=ev.to_mesh();evaltris+=sum(len(p.vertices)-2 for p in me.polygons);ev.to_mesh_clear()
report={'coverage_rays':total,'coverage_misses':miss,'path_segment_rays':segments,'path_collisions':blocked,'camera_count':len(cams),'objects':len(sc.objects),'unique_mesh_triangles':sum(sum(len(p.vertices)-2 for p in me.polygons) for me in meshes),'evaluated_visible_triangles':evaltris,'packed_images':images,'local_albedo_materials_without_emission':len(localmats),'smooth_cable_objects':len(curves),'duplicate_application_rejected':True,'linked_libraries':len(bpy.data.libraries),'scope':'Sampled closure and eye-path clearances only; no full character collision guarantee.'}
(O/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8');assert not miss and not blocked
print('STATION_V2_VALIDATED',total,segments,'triangles',evaltris,flush=True)
