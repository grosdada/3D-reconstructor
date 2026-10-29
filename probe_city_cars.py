import bpy,json
from pathlib import Path
from mathutils import Vector
R=Path(__file__).parent;O=R/'output/ville-brutaliste-v2'
lib=r'K:\Connector-Blender\Blender-asset-lib-VDB\SKetch-Fab\bagnoles.blend'
report=[]
for name in ['1967_rover_p6_2000tc_low_poly','triumph_dolomite_sprint','low-poly_jaguar_xj-s']:
 with bpy.data.libraries.load(lib,link=False) as(a,d):d.collections=[name]
 col=d.collections[0];bpy.context.scene.collection.children.link(col);bpy.context.view_layer.update()
 obs=[o for o in col.all_objects if o.type=='MESH'];points=[o.matrix_world@Vector(v) for o in obs for v in o.bound_box]
 report.append({'name':name,'objects':[{'name':o.name,'verts':len(o.data.vertices),'tris':sum(len(p.vertices)-2 for p in o.data.polygons),'matrix':[list(r) for r in o.matrix_world]} for o in obs],'bounds':[[min(v[i] for v in points),max(v[i] for v in points)] for i in range(3)]})
report.append({'images':[{'name':im.name,'packed':bool(im.packed_file),'path':bpy.path.abspath(im.filepath,library=im.library),'size':list(im.size)} for im in bpy.data.images if im.source=='FILE']})
(O/'cars-inspection.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('CARS_INSPECTED',flush=True)
