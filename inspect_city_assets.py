import bpy,json
from pathlib import Path
R=Path(__file__).parent;O=R/'output/ville-brutaliste-v1';B=Path(r'K:\Connector-Blender\Blender-asset-lib-VDB')
r=[]
for f in ['botaniq_full-Assets/blends_280/deciduous/Tree_Tilia-europaea_A_winter.blend','botaniq_full-Assets/blends_280/deciduous/Tree_Ulmus-minor_B_winter.blend','Elements-decor/streetlight.blend']:
 with bpy.data.libraries.load(str(B/f),link=False) as(a,b):b.objects=a.objects
 objs=[o for o in b.objects if o]
 for o in objs:bpy.context.scene.collection.objects.link(o)
 bpy.context.view_layer.update()
 r.append({'file':f,'objects':[{'name':o.name,'type':o.type,'dimensions':list(o.dimensions),'vertices':len(o.data.vertices) if o.type=='MESH' else 0,'parent':o.parent.name if o.parent else None} for o in objs]})
(O/'asset-inspection.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf8');print('CITY_ASSETS',json.dumps(r),flush=True)
