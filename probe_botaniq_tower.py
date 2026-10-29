import bpy,json
from pathlib import Path
from mathutils import Vector
ROOT=Path(r'K:\Connector-Blender\Blender-asset-lib-VDB\botaniq_full-Assets')
OUT=Path(__file__).parent/'output/tour-belvedere-v1'
bpy.ops.wm.read_factory_settings(use_empty=True)
files=['deciduous/Tree_Quercus-agrifolia_A_summer.blend','deciduous/Tree_Tilia-europaea_B_summer.blend','deciduous/Tree_Ficus-carica_A_summer.blend','shrubs/Shrub_Corylus-avellana_A_spring-summer.blend']
report=[]
for f in files:
    path=ROOT/'blends_280'/f
    with bpy.data.libraries.load(str(path),link=False) as (a,b):
        names=list(a.objects); collections=list(a.collections); b.objects=a.objects
    objs=[o for o in b.objects if o]
    for o in objs:bpy.context.scene.collection.objects.link(o)
    bpy.context.view_layer.update()
    meshes=[o for o in objs if o.type=='MESH']
    report.append({'file':f,'objects':names,'collections':collections,'details':[{'name':o.name,'dimensions':list(o.dimensions),'verts':len(o.data.vertices),'polys':len(o.data.polygons),'location':list(o.location)} for o in meshes]})
report.append({'images':[{'name':im.name,'path':bpy.path.abspath(im.filepath),'exists':Path(bpy.path.abspath(im.filepath)).exists()} for im in bpy.data.images if im.source=='FILE']})
(OUT/'botaniq-probe.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('BOTANIQ_PROBE_DONE',flush=True)
