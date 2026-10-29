import bpy,json,math,sys
from pathlib import Path
from mathutils import Vector
R=Path(__file__).parent;O=R/'output/station-sas-v1';sys.path.insert(0,str(R));import pano_atelier
bpy.ops.wm.open_mainfile(filepath=str(O/'station-sas-modulaire-texturee-v1.blend'));pano_atelier.register();sc=bpy.context.scene;bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get()
# Coverage from several positions, including both sides of the reference hatch.
origins=[Vector((0,y,1.6)) for y in (-12,-6,-1,4,10,17)];missing=[];total=0
for oi,origin in enumerate(origins):
    for az in range(48):
        a=az*math.tau/48
        for el in range(1,18):
            e=-math.pi/2+el*math.pi/18;d=Vector((math.cos(a)*math.cos(e),math.sin(a)*math.cos(e),math.sin(e)));hit,loc,normal,index,obj,matrix=sc.ray_cast(dg,origin,d,distance=80);total+=1
            if not hit:missing.append([oi,az,el])
# Actual inspection path samples: segment casts at centre plus four safety offsets.
path=bpy.data.objects['CAM_09 · parcours automatique'];oldframe=sc.frame_current;previous=None;blocked=[];segments=0
offsets=[Vector((0,0,0)),Vector((.16,0,0)),Vector((-.16,0,0)),Vector((0,0,.16)),Vector((0,0,-.16))]
for frame in range(1,301,3):
    sc.frame_set(frame);bpy.context.view_layer.update();pos=path.matrix_world.translation.copy()
    if previous is not None:
        delta=pos-previous
        for off in offsets:
            hit,loc,normal,index,obj,matrix=sc.ray_cast(dg,previous+off,delta.normalized(),distance=delta.length+.03);segments+=1
            if hit:blocked.append({'frame':frame,'object':obj.name})
    previous=pos
sc.frame_set(oldframe)
cams=pano_atelier.camera_navigation.cameras(sc);old=sc.camera;start=cams[0];sc.camera=start
for _ in cams:assert bpy.ops.pa.camera_step(direction=1)=={'FINISHED'}
camera_cycle=sc.camera==start;sc.camera=old
usedmeshes={o.data for o in sc.objects if o.type=='MESH'}
report={'coverage_rays':total,'coverage_misses':missing,'path_segment_rays':segments,'path_collisions':blocked,'camera_count':len(cams),'camera_cycle_ok':camera_cycle,'unique_mesh_triangles':sum(sum(len(p.vertices)-2 for p in me.polygons) for me in usedmeshes),'scene_mesh_triangles':sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in sc.objects if o.type=='MESH'),'objects':len(sc.objects),'packed_images':sum(bool(im.packed_file) for im in bpy.data.images),'linked_libraries':len(bpy.data.libraries),'scope':'Sampled enclosure and small camera clearance only; not a full character physics or universal collision proof.'}
(O/'validation-navigation.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf8');print('STATION_NAVIGATION',report,flush=True)
assert camera_cycle and not blocked
