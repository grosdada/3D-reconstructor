import bpy,sys,json,math
from pathlib import Path
from mathutils import Vector
R=Path(__file__).parent;O=R/'output/ville-brutaliste-v1';sys.path.insert(0,str(R))
import pano_atelier
from pano_atelier import city_projection
from pano_atelier.modular_scene import Builder,camera,material
bpy.ops.wm.open_mainfile(filepath=str(O/'ville-brutaliste-geometrie.blend'));sc=bpy.context.scene;pano_atelier.register()
# The atmosphere is pale in the reference, with a strong separation behind the hero.
sc.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.85
sc.view_settings.exposure=-.15
fog=bpy.data.materials['VILLE · brume atmospherique'];fog.node_tree.nodes.get('MULTIPLY').inputs[1].default_value=.8
bpy.data.objects['EXT · ilot 03'].location=(125,65,0)
b=Builder(sc,'VILLE · liaisons et details proches');hero=bpy.data.objects['ILOT · ensemble principal A1'];city=bpy.data.objects['VILLE · ensemble']
cement=bpy.data.materials['VILLE · beton brut gris sauge'];dark=bpy.data.materials['VILLE · beton humide sombre'];glass=bpy.data.materials['VILLE · vitrage vert gris'];trim=bpy.data.materials['VILLE · cadres aluminium terni']
p=b.root('A1 · galerie basse de liaison',(22,5,0),hero);p['pa_module']=True
b.box('Galerie · noyau vitre',(0,0,6),(11.2,18.5,12),glass,p,.025)
for z in (0.3,4.3,8.3,12.3):b.box('Galerie · bandeau',(0,0,z),(12,20,.55),cement,p,.035)
for x in (-5.8,-2,2,5.8):b.box('Galerie · poteau',(x,-9.6,6.3),(.35,.45,12.6),dark,p,.025)
# Small genuinely modeled service details, intentionally subordinate to the architecture.
for rootname,w,y in [('A1 · tour mince perforee',12,-8.25),('A1 · noyau porteur tour droite',12,-7.75),('A1 · aile droite ajouree',19,-9.75)]:
 p=bpy.data.objects[rootname]
 for x in (-w*.32,w*.32):
  b.box('Ventilation · encadrement',(x,y,.95),(1.2,.18,.75),trim,p,.015)
  for z in (.69,.81,.93,1.05,1.17):b.box('Ventilation · lame',(x,y-.11,z),(1.08,.10,.045),dark,p,.006)
 p['pa_module']=True
for o in list(sc.objects):
 if o.type=='EMPTY' and o.name.startswith('VEHICULE · voiture'):o.location.z=-.06
 if o.type=='EMPTY' and o.name.startswith('VEGETATION · arbre hiver'):
  x,y=o.location[:2];o.location.z=.16 if abs(x)<56 and -36.5<y<28.5 else 0
  soil=bpy.data.materials.get('VILLE · terre des pieds arbres') or material('VILLE · terre des pieds arbres',(.045,.052,.035),.96)
  b.cylinder('Arbre · fosse terre',(0,0,.005),1.25,.04,soil,o,vertices=16)
walk=next((o for o in sc.objects if o.type=='CAMERA' and o.name.startswith('CAM_07')),None)
if walk is None:walk=camera(b,'CAM_07 · promenade au sol',(35,-32,1.7),(18,-10,8),24,1800,1100)
walk.data.clip_end=1500;walk.data.clip_start=.15
bpy.context.view_layer.update()
r=city_projection.apply(sc,O/'projection',.32)
sc.pa_city.reference=str(O/'reference-A1.png');sc.pa_city.asset_root=r'K:\Connector-Blender\Blender-asset-lib-VDB';sc.pa_city.output=str(O);sc.pa_city.projection_folder=str(O/'projection');sc.pa_city.projection_strength=.32
sc.pa_settings.output=str(O);sc.pa_modular.output=str(O)
sc.name='Ville brutaliste · A1 · procedurale et albedo detail';sc.cycles.samples=64;sc.render.resolution_percentage=100;sc.render.resolution_x=1800;sc.render.resolution_y=1000
for im in bpy.data.images:
 if im.source=='FILE' and not im.packed_file:
  try:im.pack()
  except RuntimeError:pass
(O/'projection-report.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf8')
bpy.ops.wm.save_as_mainfile(filepath=str(O/'ville-brutaliste-A1.blend'));print('CITY_FINAL_SAVED',json.dumps(r),flush=True)
