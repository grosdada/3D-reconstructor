import bpy,sys,json
from pathlib import Path
R=Path(__file__).parent;O=R/'output/ville-brutaliste-v3-vis-a-vis';sys.path.insert(0,str(R))
from pano_atelier.city_projection import apply
bpy.ops.wm.open_mainfile(filepath=str(O/'ville-brutaliste-vis-a-vis.blend'));sc=bpy.context.scene
reports=[]
existing={x['folder'] for x in json.loads(sc.get('pa_city_projection_layers','[]'))}
for shot,strength in [('09',.62),('11',.76),('12',.67)]:
 if str(O/('projection-'+shot)) in existing:continue
 reports.append(apply(sc,O/('projection-'+shot),strength,incidence_exponent=2,append=True,scope='OPPOSITE'))
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(O/'ville-brutaliste-vis-a-vis.blend'),compress=True)
(O/'projection-report.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2),encoding='utf8')
print('OPPOSITE_PROJECTIONS_READY',flush=True)
