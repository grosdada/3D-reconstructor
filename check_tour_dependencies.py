import bpy,json
from pathlib import Path
out=Path(bpy.data.filepath).parent
r={}
for key in ['objects','meshes','materials','node_groups','images','collections']:
    r[key]=[{'name':x.name,'lib':x.library.filepath,'users':x.users} for x in getattr(bpy.data,key) if x.library]
(out/'dependencies.json').write_text(json.dumps(r,indent=2),encoding='utf8')
print('DEPENDENCIES_CHECK', {k:len(v) for k,v in r.items()},flush=True)
