import bpy,json,math
from pathlib import Path
R=Path(__file__).parent;B=Path(r'K:\Connector-Blender\Blender-asset-lib-VDB\Elements-decor')
with bpy.data.libraries.load(str(B/'circular-fog.blend'),link=False) as(a,b):b.objects=['Ring-Fog']
o=b.objects[0];bpy.context.scene.collection.objects.link(o);bpy.context.view_layer.update();e=o.evaluated_get(bpy.context.evaluated_depsgraph_get());me=e.to_mesh()
print('PROFILE',len(me.vertices),min(math.hypot(v.co.x,v.co.y) for v in me.vertices),max(math.hypot(v.co.x,v.co.y) for v in me.vertices),sorted(set(round(v.co.z,3) for v in me.vertices)),flush=True)
print('MODIFIERS',[(m.name, {p.identifier:str(getattr(m,p.identifier)) for p in m.bl_rna.properties if p.identifier in ['steps','render_steps','screw_offset','angle','axis','strength','thickness','offset']}) for m in o.modifiers],flush=True)
with bpy.data.libraries.load(str(B/'Select-Panneaux-LO.blend'),link=False) as(a,b):b.objects=['3d-Pann','3d-TEL','HANDICAP','HOSPITAL','pAY-paRKING','velo','do not enter','3d-Pann.003']
for o in b.objects:
 bpy.context.scene.collection.objects.link(o)
 print('SIGN',o.name,list(o.dimensions),list(o.data.polygons[0].normal),list(o.location),flush=True)
for im in bpy.data.images:
 if im.source=='FILE': print('IMAGE',im.name,im.filepath,bool(im.packed_file),list(im.size),flush=True)
