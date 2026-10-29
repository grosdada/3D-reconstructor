import bpy,json
from pathlib import Path
O=Path(__file__).parent/'output/gas-station-v2';O.mkdir(exist_ok=True)
lib=r'K:\Connector-Blender\Blender-asset-lib-VDB\Trash-kit\TrashKit.blend'
with bpy.data.libraries.load(lib,link=False) as (a,b):
 names=a.objects
 chosen=[n for n in names if n in ('Base_Trash_Heap_A','Base_Trash_Heap_C','Base_Trash_Heap_F','Base_Trash_Bag_A','Base_Trash_Rubble_A','Base_Trash_Rubble_C','Base_Trash_Bottle_A','Base_Trash_Can_A','Base_Trash_Plastic_A')]
 if not chosen:chosen=[n for n in names if any(k in n.lower() for k in ('base_trash_heap','base_trash_bag','base_trash_rubble'))][:10]
 b.objects=chosen
report={'library':lib,'available_candidates':[n for n in names if any(k in n.lower() for k in ('heap','bag','rubble','bottle','pallet'))][:100],'loaded':[]}
for o in b.objects:
 bpy.context.scene.collection.objects.link(o);bpy.context.view_layer.update()
 report['loaded'].append({'name':o.name,'type':o.type,'dimensions':list(o.dimensions),'location':list(o.location),'triangles':sum(len(p.vertices)-2 for p in o.data.polygons) if o.type=='MESH' else 0,'materials':[s.material.name if s.material else None for s in o.material_slots],'children':[c.name for c in o.children]})
report['images']=[{'name':i.name,'size':list(i.size),'path':bpy.path.abspath(i.filepath),'packed':bool(i.packed_file)} for i in bpy.data.images if i.source=='FILE']
(O/'trash-inspection.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report),flush=True)
