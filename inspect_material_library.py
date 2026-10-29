import bpy,json
from pathlib import Path
R=Path(__file__).parent; O=R/'output/station-sas-v2.2';O.mkdir(parents=True,exist_ok=True)
path=r'K:\Connector-Blender\Blender-asset-lib-VDB\Elements-decor\Basic-Material-Select.blend'
with bpy.data.libraries.load(path,link=False) as (a,b):
    names=a.materials[:];b.materials=[x for x in names if any(k.lower() in x.lower() for k in ['Beige-Use','metal-paint-edges','grunge_metal','Wear'])]
def val(v):
    if isinstance(v,(str,float,int,bool)):return v
    try:return list(v)
    except:return str(v)
def tree(t,seen=None):
    seen=set() if seen is None else seen
    if t.name in seen:return {'ref':t.name}
    seen.add(t.name)
    return {'name':t.name,'nodes':[{'name':n.name,'type':n.bl_idname,'operation':getattr(n,'operation',None),'blend':getattr(n,'blend_type',None),'image':n.image.filepath if n.type=='TEX_IMAGE' and n.image else None,'inputs':{s.name:val(s.default_value) for s in n.inputs if hasattr(s,'default_value') and not s.is_linked},'ramp':[(e.position,list(e.color)) for e in n.color_ramp.elements] if n.type=='VALTORGB' else None,'group':tree(n.node_tree,seen) if n.type=='GROUP' and n.node_tree else None} for n in t.nodes],'links':[[l.from_node.name,l.from_socket.name,l.to_node.name,l.to_socket.name] for l in t.links]}
report={'source':path,'available':names,'materials':{m.name:tree(m.node_tree) for m in b.materials if m and m.node_tree}}
(O/'library-nodes.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('INSPECTED',list(report['materials']),flush=True)
