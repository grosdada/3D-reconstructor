import bpy,json
from mathutils import Vector
from mathutils.bvhtree import BVHTree
dg=bpy.context.evaluated_depsgraph_get()
def geometry(root):
    vs=[];fs=[]
    for ob in root.children:
        if ob.type!='MESH':continue
        ev=ob.evaluated_get(dg);me=ev.to_mesh();me.calc_loop_triangles();offset=len(vs)
        vs.extend(ev.matrix_world@v.co for v in me.vertices)
        fs.extend(tuple(i+offset for i in t.vertices) for t in me.loop_triangles);ev.to_mesh_clear()
    return vs,fs
names=['M_CONSOLE_ARRIERE_G','M_CONSOLE_ARRIERE_D','M_CONSOLE_LATERALE_G','M_CONSOLE_LATERALE_D','M_BUREAU_PREMIER_PLAN_G','M_BUREAU_PREMIER_PLAN_D','M_TABLE_CENTRALE']
obstacles=[BVHTree.FromPolygons(*geometry(bpy.data.objects[n]),all_triangles=True) for n in names]
for n in ['M_SIEGE_DROIT','M_SIEGE_GAUCHE']:
    obj=bpy.data.objects[n];vs,fs=geometry(obj)
    candidates=sorted([(x*.05,y*.05) for x in range(-16,17) for y in range(-16,17)],key=lambda q:q[0]**2+q[1]**2)
    found=[]
    for x,y in candidates:
        delta=Vector((x,y,0));tree=BVHTree.FromPolygons([v+delta for v in vs],fs,all_triangles=True)
        if not any(tree.overlap(o) for o in obstacles):
            found.append({'delta':[x,y,0],'position':list(obj.location+delta)})
            if len(found)==4:break
    print('CLEARANCE',n,json.dumps(found),flush=True)
