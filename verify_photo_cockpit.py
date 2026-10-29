"""Observable checks on the saved modular scene, followed by off-axis renders."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
OUT=Path(__file__).resolve().parent/'output/cockpit-photo-modulaire-v1'
sc=bpy.context.scene; dg=bpy.context.evaluated_depsgraph_get()
checks={}; errors=[]
def check(name,value):
    checks[name]=bool(value)
    if not value:errors.append(name)
meshes=[o for o in sc.objects if o.type=='MESH']; modules=[o for o in sc.objects if o.get('module')]
check('all_meshes_in_modules',all(o.parent and o.parent.get('module') for o in meshes))
check('finite_mesh_coordinates',all(math.isfinite(c) for o in meshes for v in o.data.vertices for c in v.co))
check('every_external_texture_packed',all(im.packed_file for im in bpy.data.images if im.source=='FILE'))
check('six_screen_maps',len([im for im in bpy.data.images if im.name.startswith('crt-')])==6)
windows=[o for o in meshes if o.get('window_glass')]
check('glazing_has_thickness',all(any(m.type=='SOLIDIFY' for m in o.modifiers) for o in windows))
glass=bpy.data.materials['Vitrage · transparent IOR 1.45'].node_tree.nodes.get('Principled BSDF')
check('transparent_glass_shader',glass.inputs['Transmission Weight'].default_value==1 and abs(glass.inputs['IOR'].default_value-1.45)<1e-5)
cyc=bpy.data.objects.get('Cyclorama demi-cercle · 180°')
check('semicircle_cyclorama',cyc and cyc.get('arc_degrees')==180 and len(cyc.data.polygons)==64 and len(cyc.data.uv_layers)==1)
check('no_camera_dependent_texture_coords',all(n.type!='TEX_COORD' or not n.object or n.object.type!='CAMERA' for m in bpy.data.materials if m.use_nodes for n in m.node_tree.nodes))
move=bpy.data.objects['M_CONSOLE_ARRIERE_G']; before={o:o.matrix_world.copy() for o in sc.objects}; initial=move.location.copy()
delta=Vector((.237,-.129,.083)); move.location+=delta;bpy.context.view_layer.update()
check('module_children_follow',all(((o.matrix_world.translation-before[o].translation)-delta).length<1e-4 for o in move.children))
check('other_modules_unchanged',all((o.matrix_world.translation-before[o].translation).length<1e-5 for o in sc.objects if o!=move and o not in move.children))
move.location=initial;bpy.context.view_layer.update()
check('module_move_restored',all((o.matrix_world.translation-before[o].translation).length<1e-5 for o in sc.objects))
def module_bvh(root):
    vs=[];fs=[]
    for ob in root.children:
        if ob.type!='MESH':continue
        ev=ob.evaluated_get(dg);me=ev.to_mesh();me.calc_loop_triangles();offset=len(vs)
        vs.extend(ev.matrix_world@v.co for v in me.vertices)
        fs.extend(tuple(i+offset for i in t.vertices) for t in me.loop_triangles);ev.to_mesh_clear()
    return BVHTree.FromPolygons(vs,fs,all_triangles=True)
cabinet_names=['M_CONSOLE_ARRIERE_G','M_CONSOLE_ARRIERE_D','M_CONSOLE_LATERALE_G','M_CONSOLE_LATERALE_D','M_BUREAU_PREMIER_PLAN_G','M_BUREAU_PREMIER_PLAN_D']
cabinets={n:module_bvh(bpy.data.objects[n]) for n in cabinet_names}
collisions=[]
for n in ['M_SIEGE_GAUCHE','M_SIEGE_DROIT']:
    tree=module_bvh(bpy.data.objects[n])
    for other,t in cabinets.items():
        if tree.overlap(t):collisions.append([n,other])
check('chairs_do_not_cross_cabinets',not collisions)
report={'checks':checks,'errors':errors,'modules':len(modules),'meshes':len(meshes),'glazing_parts':len(windows),'source_view':'rendu-photo.png',
        'chair_cabinet_intersections':collisions,
        'limits':['Camera and scale estimated from one photograph.','Unseen rear has not been invented in this phase.','Fine instruments interpreted, not copied pixel for pixel.','This is a photo-specific scripted reconstruction, not an automatic general reconstruction add-on.']}
(OUT/'validation.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
if errors: raise RuntimeError(errors)
# The temporary move is restored; these views only change render settings, not the saved blend.
try:
    prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
    for d in prefs.devices:d.use=d.type!='CPU'
    sc.cycles.device='GPU'
except:pass
sc.cycles.samples=48;sc.render.resolution_percentage=75
for cname,fname in [('CAM_LATERALE','rendu-lateral.png'),('CAM_DETAIL','rendu-detail.png')]:
    sc.camera=bpy.data.objects[cname];sc.render.filepath=str(OUT/fname);bpy.ops.render.render(write_still=True)
print('MODULAR_SCENE_VERIFIED',json.dumps(checks),flush=True)
