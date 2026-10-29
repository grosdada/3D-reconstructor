"""Reproducible cockpit template iteration; never overwrite the depth study."""
import sys
import json
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import pano_atelier
from pano_atelier import structural,engine
pano_atelier.register()
OUT=ROOT/'output'/'cockpit-lowpoly-v1'; OUT.mkdir(parents=True,exist_ok=True)
scene=bpy.data.scenes.new('Cockpit — architecture low-poly')
bpy.context.window.scene=scene
objects=structural.build(scene,OUT)
structural.export_guides(scene,OUT/'guides')
triangles=0
for obj in objects:
    obj.data.calc_loop_triangles(); triangles+=len(obj.data.loop_triangles)
report={'objects':len(objects),'vertices':sum(len(o.data.vertices) for o in objects),
        'faces':sum(len(o.data.polygons) for o in objects),'triangles':triangles,
        'geometry':'manual architectural hexagonal template, not automatic image reconstruction'}
(OUT/'geometry-report.json').write_text(json.dumps(report,indent=2))
scene.pa_settings.status='Structure low-poly 360 : en attente des textures projetées.'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'cockpit-lowpoly-guide.blend'))
print(json.dumps(report),flush=True)
