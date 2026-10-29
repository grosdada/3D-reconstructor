import bpy,json
from pathlib import Path
R=Path(__file__).parent;O=R/'output/ville-brutaliste-v4-mobilier';O.mkdir(exist_ok=True)
B=Path(r'K:\Connector-Blender\Blender-asset-lib-VDB\Elements-decor')
report={}
for filename in ['circular-fog.blend','Select-Panneaux-LO.blend','road-Sign-Lo.blend']:
 with bpy.data.libraries.load(str(B/filename),link=False) as(a,b):
  report[filename]={'names':a.objects[:],'collections':a.collections[:]}
  b.objects=a.objects if 'fog' in filename else [n for n in a.objects if n in ['3d-Pann','3d-Pann.012','3d-RESERVED PARK','3d-TEL','HANDICAP','HOSPITAL','3d-panneaux.001','3d-Pann.002']]
 objs=[o for o in b.objects if o]
 for o in objs:bpy.context.scene.collection.objects.link(o)
 bpy.context.view_layer.update()
 report[filename]['objects']=[{'name':o.name,'type':o.type,'loc':list(o.location),'rot':list(o.rotation_euler),'scale':list(o.scale),'dimensions':list(o.dimensions),'bounds':[list(v) for v in o.bound_box],'verts':len(o.data.vertices) if o.type=='MESH' else 0,'mods':[{'name':m.name,'type':m.type} for m in o.modifiers],'materials':[m.name if m else None for m in o.data.materials] if o.type=='MESH' else []} for o in objs]
report['materials']=[]
for m in bpy.data.materials:
 if not m.use_nodes:continue
 report['materials'].append({'name':m.name,'nodes':[{'type':n.type,'name':n.name,'label':n.label,'inputs':{i.name:str(i.default_value) for i in n.inputs if hasattr(i,'default_value') and not i.is_linked},'group':n.node_tree.name if n.type=='GROUP' else None} for n in m.node_tree.nodes],'links':[[l.from_node.name,l.from_socket.name,l.to_node.name,l.to_socket.name] for l in m.node_tree.links]})
report['groups']=[{'name':t.name,'nodes':[(n.name,n.type) for n in t.nodes]} for t in bpy.data.node_groups]
(O/'asset-inspection.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('DRESSING_INSPECTED',flush=True)
