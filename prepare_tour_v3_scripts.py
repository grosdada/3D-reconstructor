"""Prepare an independent V3 workspace without overwriting V1/V2 assets."""
from pathlib import Path
import shutil,json
R=Path(__file__).parent
src=R/'output/tour-belvedere-v2'; dst=R/'output/tour-belvedere-v3';dst.mkdir(exist_ok=True)
for p in src.iterdir():
    if p.name.endswith(('-albedo.png','-depth.exr','-protection.png')) or p.name in ('generation.json','generation-detail.json'):
        if not (dst/p.name).exists():shutil.copy2(p,dst/p.name)
newviews="[('detail-est',(44,-27,4.8),(18,-12,2.5),32),('detail-nord',(29,35,5),(16,5,3),32),('detail-pied',(-17,12,5),(0,0,6),40),('detail-ouest',(-15,22,4),(13,-6,3),32)]"
s=(R/'prepare_tour_albedo.py').read_text(encoding='utf8')
s=s.replace("OUT=ROOT/'output/tour-belvedere-v2'","OUT=ROOT/'output/tour-belvedere-v3'")
start=s.index('specs=');end=s.index('\nviews=[]',start)
s=s[:start]+'specs='+newviews+s[end:]
s=s.replace("'priority':8 if name=='detail-facade' else 1","'priority':8")
s=s.replace("(OUT/'views.json').write_text", "views=json.loads((ROOT/'output/tour-belvedere-v2/views.json').read_text())+views\n(OUT/'views.json').write_text")
(R/'prepare_tour_v3_guides.py').write_text(s,encoding='utf8')
s=(R/'mask_tour_albedo.py').read_text(encoding='utf8').replace('tour-belvedere-v2','tour-belvedere-v3')
s=s.replace("['avant','droite','arriere','gauche','dessus','detail-facade']", "['detail-est','detail-nord','detail-pied','detail-ouest']")
(R/'mask_tour_v3.py').write_text(s,encoding='utf8')
s=(R/'build_tour_albedo.py').read_text(encoding='utf8').replace('tour-belvedere-v2','tour-belvedere-v3').replace('tour-belvedere-albedo-v2.blend','tour-belvedere-projections-v3.blend').replace(' · V2',' · V3').replace('6 projections','10 projections')
s=s.replace("    rawmask=mask", """    # Keep close repairs below the collar; preserve the approved upper tower.
    if name in {'detail-est','detail-nord','detail-pied','detail-ouest'}:
        world=node(ng,'ShaderNodeSeparateXYZ',name+' limite de reparation');ng.links.new(pos.outputs['Vector'],world.inputs[0])
        repair=math_(ng,'MINIMUM',math_(ng,'MAXIMUM',math_(ng,'DIVIDE',math_(ng,'SUBTRACT',11.0,world.outputs['Z']),.35),0),1)
        mask=math_(ng,'MULTIPLY',mask,repair)
    rawmask=mask""")
s=s.replace('Six GPT albedo projections','Ten GPT albedo projections').replace('Six generated albedo images','Ten generated albedo images')
(R/'build_tour_v3_projection.py').write_text(s,encoding='utf8')
print('V3_WORKSPACE_READY')
