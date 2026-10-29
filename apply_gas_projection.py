import bpy,sys,json
from pathlib import Path
R=Path(__file__).parent;sys.path.insert(0,str(R));O=R/'output/gas-station-exterior-v1'
from pano_atelier.city_projection import apply
shot=sys.argv[-1] if sys.argv[-1] in ('01','02','03','05') else '01'
bpy.ops.wm.open_mainfile(filepath=str(O/('station-exterieur-base.blend' if shot=='01' else 'station-exterieur-textures.blend')))
sc=bpy.context.scene;report=apply(sc,O/('projection-'+shot),strength=.90,incidence_exponent=1.2,append=shot!='01')
sc['pa_gas_texturing']='GPT Image albedo detail, depth-gated camera projections over procedural materials; lighting remains physical.'
(O/('projection-'+shot)/'application-report.json').write_text(json.dumps(report,indent=2),encoding='utf8')
bpy.ops.wm.save_as_mainfile(filepath=str(O/'station-exterieur-textures.blend'),compress=True)
print('GAS_PROJECTION_APPLIED',shot,flush=True)
