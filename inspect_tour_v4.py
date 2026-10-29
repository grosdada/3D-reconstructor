import bpy,json
from pathlib import Path
from mathutils import Vector
R=Path(__file__).parent;O=R/'output/tour-belvedere-v4';O.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(R/'output/tour-belvedere-v3/tour-belvedere-foret-360-v3.blend'))
bpy.context.view_layer.update()
def bounds(o):
    vs=[o.matrix_world@Vector(p) for p in o.bound_box]
    return [[min(v[i] for v in vs),max(v[i] for v in vs)] for i in range(3)]
report={'surfaces':[{'name':o.name,'bounds':bounds(o),'parent':o.parent.name if o.parent else None,'materials':[s.material.name for s in o.material_slots if s.material]} for o in bpy.context.scene.objects if o.type=='MESH' and o.name.startswith(('Terrain','Dalle soubassement','Allege facade','Parvis','Trottoir','Route','Acces entre','SOL · disque'))],'grasses':[]}
A=Path(r'K:\Connector-Blender\Blender-asset-lib-VDB\botaniq_full-Assets\blends_280\grass')
for name in ['Grass_Basic-dry_D_spring-summer.blend','Grass_Basic-dry_A_spring-summer.blend','Grass_Cut_D_spring-summer.blend','Grass_Wild_C_spring-summer.blend','Grass_Basic-Strands_B_spring-summer.blend']:
    with bpy.data.libraries.load(str(A/name),link=False) as (a,b):b.objects=a.objects
    report['grasses'].append({'file':name,'objects':[{'name':o.name,'type':o.type,'bounds':bounds(o),'triangles':sum(len(p.vertices)-2 for p in o.data.polygons) if o.type=='MESH' else 0,'modifiers':[(m.name,m.type) for m in o.modifiers],'materials':[s.material.name for s in o.material_slots if s.material]} for o in b.objects if o]})
(O/'inspection.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('V4_INSPECTION_DONE',json.dumps(report['grasses']),flush=True)
