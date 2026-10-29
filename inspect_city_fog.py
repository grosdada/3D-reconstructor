import bpy,json
from pathlib import Path
R=Path(__file__).parent;O=R/'output/ville-brutaliste-v3-vis-a-vis'
bpy.ops.wm.open_mainfile(filepath=str(O/'ville-brutaliste-vis-a-vis.blend'))
result={'fog':[{'name':o.name,'hide_render':o.hide_render,'hide_viewport':o.hide_viewport,'parent':o.parent.name if o.parent else None,'materials':[(s.material.name,s.link) for s in o.material_slots if s.material],'nodes':[(n.name,n.type,getattr(n,'attribute_name','')) for s in o.material_slots if s.material for n in s.material.node_tree.nodes if n.type in ('ATTRIBUTE','TEX_COORD','PRINCIPLED_VOLUME')]} for o in bpy.context.scene.objects if o.get('pa_noncolliding')]}
(O/'fog-diagnosis.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(result,ensure_ascii=False))
for name in ['VILLE · brume atmospherique','VIS · brume nord raccordee']:
 m=bpy.data.materials[name]
 print('FLAGS',name,[(p.identifier,str(getattr(m.cycles,p.identifier))) for p in m.cycles.bl_rna.properties if p.identifier!='rna_type'])
 print('VOLUME LINKS',[(l.from_node.name,l.from_socket.name,l.to_node.name,l.to_socket.name) for l in m.node_tree.links if l.to_node.type in ('PRINCIPLED_VOLUME','OUTPUT_MATERIAL')])
old=json.loads((O/'baseline-v2.json').read_text(encoding='utf8'))['ATMOSPHERE · brume'];ob=bpy.data.objects['ATMOSPHERE · brume'];print('COMPARE',old,{'matrix':[list(r) for r in ob.matrix_world],'data':ob.data.name})
