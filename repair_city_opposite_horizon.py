import bpy,sys
from pathlib import Path
R=Path(__file__).parent;O=R/'output/ville-brutaliste-v3-vis-a-vis';sys.path.insert(0,str(R))
from pano_atelier.city_opposite import soften_new_fog_boundaries,continuous_city_haze
from pano_atelier.modular_scene import Builder
from pano_atelier.city_optimize import freeze_coordinates
bpy.ops.wm.open_mainfile(filepath=str(O/'ville-brutaliste-vis-a-vis.blend'));sc=bpy.context.scene
if not bpy.data.objects.get('VIS · prolongement sol est'):
 b=Builder(sc,'VIS-A-VIS · sol lointain');root=bpy.data.objects['VIS-A-VIS · ensemble'];o=b.box('VIS · prolongement sol est',(440,30,-.3),(520,360,.6),bpy.data.materials['VILLE · asphalte humide'],root,0);o['pa_opposite']=True;bpy.context.view_layer.update();freeze_coordinates(o,root)
soften_new_fog_boundaries(sc)
ob=bpy.data.objects.get('VIS · atmosphere nord raccordee')
if ob and ob.data.users>1:
 m=ob.material_slots[0].material;ob.data=ob.data.copy();ob.data.materials.clear();ob.data.materials.append(m);ob.material_slots[0].link='DATA'
continuous_city_haze(sc)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'ville-brutaliste-vis-a-vis.blend'),compress=True)
