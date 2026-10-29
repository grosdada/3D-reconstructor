import bpy,sys,json
from pathlib import Path
R=Path(__file__).parent;O=R/'output/ville-brutaliste-v1';sys.path.insert(0,str(R))
from pano_atelier.city_material_detail import refine
bpy.ops.wm.open_mainfile(filepath=str(O/'ville-brutaliste-A1.blend'))
changed=[m.name for m in bpy.data.materials if refine(m)]
bpy.ops.wm.save_as_mainfile(filepath=str(O/'ville-brutaliste-A1.blend'))
(O/'material-refinement.json').write_text(json.dumps({'materials':changed,'reason':'Reduce wood-like regular streaks; add local mineral variation and fine formwork joints.'},ensure_ascii=False,indent=2),encoding='utf8');print('MINERAL_REFINEMENT_DONE',len(changed),flush=True)
