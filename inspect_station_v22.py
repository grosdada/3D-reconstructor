import bpy,json
from pathlib import Path
R=Path(__file__).parent;O=R/'output/station-sas-v2.2'
bpy.ops.wm.open_mainfile(filepath=str(R/'output/station-sas-v2.1/station-sas-modulaire-texturee-v2.1.blend'))
names=['ST · panneaux ivoire vieilli','ST · sol resine creme','ST · coffrets gris','V2 · email use des sas','V2 · plaques de sol use fine']
r={}
for name in names:
 m=bpy.data.materials.get(name)
 if not m:continue
 r[name]={'nodes':[(n.name,n.type,[(s.name,str(s.default_value)) for s in n.inputs if hasattr(s,'default_value') and not s.is_linked]) for n in m.node_tree.nodes],'links':[(l.from_node.name,l.from_socket.name,l.to_node.name,l.to_socket.name) for l in m.node_tree.links]}
r['objects']=[{'name':o.name,'dims':list(o.dimensions),'loc':list(o.location),'scale':list(o.scale),'verts':[list(v.co) for v in o.data.vertices],'mods':[(m.name,m.type) for m in o.modifiers]} for o in bpy.context.scene.objects if o.name in ['Plaque de passage antiderapante','Sas · seuil franchissable']]
(O/'scene-inspection.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf8')
print('INSPECT_OK')
