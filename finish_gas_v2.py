import bpy,sys,json,hashlib,math
from pathlib import Path
from mathutils import Vector,Matrix
R=Path(__file__).parent;sys.path.insert(0,str(R));O=R/'output/gas-station-v2'
import pano_atelier as addon
from pano_atelier.modular_scene import Builder,material,camera
addon.register()
# Exercise the new public operators on the previous scene, without saving it.
bpy.ops.wm.open_mainfile(filepath=str(R/'output/gas-station-exterior-v1/station-exterieur.blend'))
assert bpy.ops.pa.gas_procedural_weather()=={'FINISHED'}
assert bpy.ops.pa.gas_interior()=={'FINISHED'}
assert not bpy.ops.pa.gas_interior.poll()
report={'addon_version':list(addon.bl_info['version']),'weather_and_interior_operators':'passed','duplicate_build_guard':'passed'}
bpy.ops.wm.open_mainfile(filepath=str(O/'station-v2-exterieur-interieur.blend'));sc=bpy.context.scene
assert not bpy.ops.pa.gas_debris.poll()
sc.pa_gas.gpt_reminder=.4
mixes=[m.node_tree.nodes.get('Procedural + rappel GPT') for m in bpy.data.materials if m.node_tree]
mixes=[n for n in mixes if n]
assert len(mixes)==2 and all(abs(n.inputs[0].default_value-.4)<1e-5 for n in mixes)
sc.pa_gas.gpt_reminder=.25;report['projection_mix_slider']='passed'
images=[i for i in bpy.data.images if i.source=='FILE']
assert all(i.packed_file or i.packed_files for i in images)
report['packed_images']=len(images)
report['image_sizes']={i.name:list(i.size) for i in images}
with bpy.data.libraries.load(str(O/'Peintures-procedurales.blend'),link=False) as (a,d):
    report['material_library']={'materials':list(a.materials),'images':list(a.images)}
assert len(report['material_library']['materials'])==2 and not report['material_library']['images']
mods=[o for o in sc.objects if o.get('pa_module')]
def attr_hash():
    h=hashlib.sha256()
    for me in sorted({o.data for o in sc.objects if o.type=='MESH'},key=lambda m:m.name):
        for a in me.attributes:
            if a.name.startswith(('PA_Weather','PA_CityRest')):
                for v in a.data:h.update(str(tuple(v.vector)).encode())
    return h.hexdigest()
digest=attr_hash()
for root in mods:
    kids=list(root.children_recursive);before={o.name:o.matrix_world.copy() for o in kids};orig=root.matrix_world.copy()
    delta=Matrix.Translation((1.3,-2.1,.4))@Matrix.Rotation(.31,4,'Z');root.matrix_world=delta@orig;bpy.context.view_layer.update()
    assert all(max(abs(a-b) for ra,rb in zip(o.matrix_world,delta@before[o.name]) for a,b in zip(ra,rb))<2e-4 for o in kids),root.name
    root.matrix_world=orig;bpy.context.view_layer.update()
assert digest==attr_hash();report['movable_module_checks']=len(mods);report['projection_and_weather_attributes_preserved']=True
# Confirm the two exterior shells are genuinely open at the connecting doorway.
shells=[o for o in sc.objects if o.type=='MESH' and o.name.startswith(('Boutique · murs','Annexe · enduit'))]
origin=Vector((-7.2,1.8,1.6));direction=Vector((1,0,0))
for o in shells:
    inv=o.matrix_world.inverted();hit,*_=o.ray_cast(inv@origin,inv.to_3x3()@direction,distance=1.0)
    assert not hit,o.name
report['connecting_shell_openings']='clear at doorway centre; not a complete navigation collision test'
source=Path(json.loads((O/'scene-report.json').read_text(encoding='utf8'))['source'])
assert hashlib.sha256(source.read_bytes()).hexdigest()==json.loads((O/'scene-report.json').read_text(encoding='utf8'))['source_sha256']
report['v1_unchanged']=True
(O/'validation.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf8')
addon.unregister();addon.register();addon.unregister()
print('GAS_V2_VALIDATED',json.dumps(report),flush=True)
# Reload to remove every test transform before saving camera/settings and rendering.
bpy.ops.wm.open_mainfile(filepath=str(O/'station-v2-exterieur-interieur.blend'));sc=bpy.context.scene
p=bpy.context.preferences.addons['cycles'].preferences;p.compute_device_type='OPTIX';p.get_devices()
for d in p.devices:d.use=d.type!='CPU'
sc.cycles.device='GPU';sc.cycles.samples=64;sc.cycles.use_denoising=True
sc.render.resolution_x=1800;sc.render.resolution_y=1200;sc.render.resolution_percentage=100
sc.camera=next(o for o in sc.objects if o.type=='CAMERA' and o.name.startswith('CAM_07'))
for scr in bpy.data.screens:
    for ar in scr.areas:
        if ar.type=='VIEW_3D':ar.spaces.active.region_3d.view_perspective='CAMERA'
bpy.ops.wm.save_as_mainfile(filepath=str(O/'station-v2-exterieur-interieur.blend'),compress=True)
sc.render.use_persistent_data=True
for i in (1,3,4,7,8,9,10):
    sc.camera=next(o for o in sc.objects if o.type=='CAMERA' and o.name.startswith('CAM_%02d'%i))
    sc.render.filepath=str(O/('rendu-%02d.png'%i));bpy.ops.render.render(write_still=True);print('FINAL_RENDER',i,flush=True)
# Neutral material specimen, kept out of the production file.
old=sc;sc=bpy.data.scenes.new('Echantillons proceduraux');bpy.context.window.scene=sc
b=Builder(sc,'Echantillons');sc.render.engine='CYCLES';sc.cycles.device='GPU';sc.cycles.samples=64;sc.cycles.use_denoising=True
sc.world=bpy.data.worlds.new('Studio neutre');sc.world.use_nodes=True;sc.world.node_tree.nodes['Background'].inputs[0].default_value=(.35,.35,.35,1);sc.world.node_tree.nodes['Background'].inputs[1].default_value=.5
for x,name in [(-1.25,'PA · BLANC patine procedural'),(1.25,'PA · BLEU patine procedural')]:
    m=bpy.data.materials[name];ob=b.box(name,(x,0,0),(2.1,.16,3),m,bevel=.012)
    for v in ob.data.vertices:v.co.z+=1.5
ground=material('Sol studio',(.10,.105,.11),.8);b.box('Socle',(0,0,-.1),(7,5,.2),ground)
cam=camera(b,'Echantillons',(4,-9,4.1),(0,0,1.45),48,1600,1000);sc.camera=cam
ld=bpy.data.lights.new('Softbox','AREA');ld.energy=850;ld.shape='DISK';ld.size=5;lo=bpy.data.objects.new('Softbox',ld);sc.collection.objects.link(lo);lo.location=(-3,-4,6);lo.rotation_euler=(Vector((0,0,1.5))-lo.location).to_track_quat('-Z','Y').to_euler()
sc.render.resolution_x=1600;sc.render.resolution_y=1000;sc.render.resolution_percentage=100;sc.render.filepath=str(O/'materiaux-proceduraux.png');bpy.ops.render.render(write_still=True)
print('GAS_V2_FINISHED',flush=True)
