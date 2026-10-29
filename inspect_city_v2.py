import bpy,json,time
from pathlib import Path
R=Path(__file__).parent;O=R/'output/ville-brutaliste-v2';O.mkdir(exist_ok=True)
t=time.perf_counter();bpy.ops.wm.open_mainfile(filepath=str(R/'output/ville-brutaliste-v1/ville-brutaliste-A1.blend'))
sc=bpy.context.scene
roots=[{'name':o.name,'parent':o.parent.name if o.parent else None,'location':list(o.location),'children':len(o.children)} for o in sc.objects if o.type=='EMPTY' and not o.name.startswith('Etage')]
libs={}
base=Path(r'K:\Connector-Blender\Blender-asset-lib-VDB\SKetch-Fab')
for fn in ['All-Lo-Po-Cars-Cycles.blend','bagnoles.blend','bagnole-bank.blend','Low_Poly_Cars_Roh3D_1960.blend','BAGNOLES-COOL/GAZ-24 Volga (low-poly).blend']:
 try:
  with bpy.data.libraries.load(str(base/fn),link=False) as(a,d):libs[fn]={'objects':list(a.objects),'collections':list(a.collections)}
 except Exception as e:libs[fn]={'error':str(e)}
(O/'inspection.json').write_text(json.dumps({'load_seconds':time.perf_counter()-t,'roots':roots,'libraries':libs},ensure_ascii=False,indent=2),encoding='utf8')
print('INSPECTION_DONE',flush=True)
