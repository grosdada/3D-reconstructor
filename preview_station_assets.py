import bpy,json,math
from pathlib import Path
from mathutils import Vector
R=Path(__file__).parent;O=R/'output/station-sas-v1';P=O/'asset-previews';P.mkdir(exist_ok=True)
files=json.loads((O/'kitbash-files.json').read_text(encoding='utf8'));report=[]
for entry in files:
    name=Path(entry['file']).name
    if name=='hatches-and-cover.blend':choose=[n for n in entry['objects'] if n.startswith('jro_cover')]
    elif name=='SCI-FI-PANEL-VOL-01.blend':choose=[n for n in entry['objects'] if n not in {'Effector'}]
    elif name=='KitBash_control_panel_industrial.blend':choose=[n for n in entry['objects'] if any(s in n for s in ('hatch','handwheel','fitting','switch_3','valve_8'))][:22]
    else:continue
    with bpy.data.libraries.load(entry['file'],link=False) as (a,b):b.objects=choose
    for ob in b.objects:
        if not ob or ob.type!='MESH':continue
        preview=ob.preview
        item={'file':entry['file'],'object':ob.name,'vertices':len(ob.data.vertices),'triangles':sum(len(p.vertices)-2 for p in ob.data.polygons),'dimensions':list(ob.dimensions),'bounds':[[min(v[k] for v in ob.bound_box),max(v[k] for v in ob.bound_box)] for k in range(3)],'rotation':list(ob.rotation_euler),'scale':list(ob.scale),'modifiers':[(m.name,m.type) for m in ob.modifiers]}
        if preview and preview.image_size[0]>0:
            w,h=preview.image_size;im=bpy.data.images.new('preview',w,h,alpha=True);im.pixels.foreach_set(preview.image_pixels_float[:]);im.filepath_raw=str(P/(ob.name+'.png'));im.file_format='PNG';im.save();bpy.data.images.remove(im);item['preview']=str(P/(ob.name+'.png'))
        report.append(item)
(O/'asset-candidates.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('ASSET_PREVIEWS_DONE',len(report),'previews',sum('preview' in r for r in report),flush=True)
