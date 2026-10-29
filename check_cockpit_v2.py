import bpy,math,json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
OUT=Path(bpy.data.filepath).parent
sc=bpy.context.scene;dg=bpy.context.evaluated_depsgraph_get()
def bvh(objects):
    vs=[];fs=[]
    for o in objects:
        if o.type!='MESH':continue
        ev=o.evaluated_get(dg);me=ev.to_mesh();me.calc_loop_triangles();n=len(vs)
        vs.extend(ev.matrix_world@v.co for v in me.vertices);fs.extend(tuple(n+i for i in t.vertices) for t in me.loop_triangles);ev.to_mesh_clear()
    return BVHTree.FromPolygons(vs,fs,all_triangles=True)
def arch(o):
    if o.type!='MESH' or not o.parent:return False
    p=o.parent.name
    return (p.startswith(('M_FENETRE','M_TOIT','M_OCULUS','M_CLOISON','M_PORTE','M_SOL')) or p.startswith('M_ARR_') and not p.startswith(('M_ARR_CONSOLE','M_ARR_RANGEMENT','M_ARR_LAMPE')))
shell=bvh([o for o in sc.objects if arch(o)])
misses=[];sample_count=0
for pos in [(0,0,1.6),(.5,-.6,1.6),(-.5,.6,1.6),(-.6,-.6,1.6),(.6,.6,1.6)]:
    for elev in [0,15,25,40,50,65,75,88,-35]:
        e=math.radians(elev)
        for yaw in range(0,360,3):
            sample_count+=1
            a=math.radians(yaw);d=Vector((math.sin(a)*math.cos(e),math.cos(a)*math.cos(e),math.sin(e)))
            hit,normal,idx,dist=shell.ray_cast(Vector(pos),d,22)
            if hit is None:misses.append({'pos':pos,'yaw':yaw,'elevation':elev})
root=bpy.data.objects['M_ARR_CONSOLE_COMMUNICATIONS'];before={o:o.matrix_world.copy() for o in sc.objects};old=root.location.copy()
delta=Vector((.18,.21,.04));root.location+=delta;bpy.context.view_layer.update()
follows=all(((o.matrix_world.translation-before[o].translation)-delta).length<1e-4 for o in root.children)
unchanged=all((o.matrix_world.translation-before[o].translation).length<1e-5 for o in sc.objects if o!=root and o not in root.children)
root.location=old;bpy.context.view_layer.update()
generated=[bpy.data.images.get(n) for n in ['ivoire-patine.png','sol-resine-usee.png','instruments-atlas.png']]
geometry=json.loads((OUT/'scene-report.json').read_text(encoding='utf-8'))
checks={'front_geometry_preserved':geometry['front_geometry_before']==geometry['front_geometry_after'],
        'generated_textures_packed':all(im and im.packed_file for im in generated),'rear_module_moves_as_unit':follows,'neighbors_unchanged':unchanged,
        'horizontal_shell_coverage':not any(m['elevation']==0 for m in misses),'all_sampled_shell_coverage':not misses}
if 'v3_mesh_before' in geometry:
    checks['all_v2_meshes_and_parents_preserved']=geometry['v3_mesh_before']==geometry['v3_mesh_after']
    wear_mats=[m for m in bpy.data.materials if 'v3_wear_strength' in m]
    checks['wear_coordinates_local']=bool(wear_mats) and all(n.object is None for m in wear_mats for n in m.node_tree.nodes if n.type=='TEX_COORD')
(OUT/'validation.json').write_text(json.dumps({'checks':checks,'shell_sample_count':sample_count,'shell_misses':misses},indent=2),encoding='utf-8')
print('VALIDATION',json.dumps(checks),'MISSES',len(misses),flush=True)
assert all(checks.values()),'Cockpit validation failed; inspect validation.json'
