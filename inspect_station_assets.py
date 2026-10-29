import bpy,json
from pathlib import Path
R=Path(__file__).parent;O=R/'output/station-sas-v1';A=Path(r'K:\Connector-Blender\Blender-asset-lib-VDB\KitBash')
names=['hatches-and-cover.blend','200-hardsurface-kitbash-vol-02.blend','SCI-FI-PANEL-VOL-01.blend','Sci_Fi_Panels_vol_01.blend','Master-Kitbash-PACK.blend','KitBash_control_panel_industrial.blend','Hard Surface KitBash Vol 6.blend']
data=[]
for name in names:
    f=A/name
    if not f.exists():continue
    with bpy.data.libraries.load(str(f),link=False) as (a,b):
        data.append({'file':str(f),'size':f.stat().st_size,'objects':a.objects,'collections':a.collections})
(O/'kitbash-files.json').write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding='utf8')
print('ASSET_NAMES_DONE',[(Path(d['file']).name,len(d['objects'])) for d in data],flush=True)
