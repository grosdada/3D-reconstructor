import bpy,sys,math,json,random,time,importlib.util
from pathlib import Path
from mathutils import Vector,Matrix
R=Path(__file__).parent;O=R/'output/ville-brutaliste-v2';O.mkdir(exist_ok=True)
spec=importlib.util.spec_from_file_location('pa_city_v2',R/'pano_atelier/__init__.py',submodule_search_locations=[str(R/'pano_atelier')]);addon=importlib.util.module_from_spec(spec);sys.modules[spec.name]=addon;spec.loader.exec_module(addon)
from pa_city_v2.modular_scene import Builder,material
from pa_city_v2.city_scene import Batch
from pa_city_v2.city_optimize import optimize,metrics
from pa_city_v2.station_procedural import node,feed,noise,mapped,mix,math as smath
start=time.perf_counter();bpy.ops.wm.open_mainfile(filepath=str(R/'output/ville-brutaliste-v1/ville-brutaliste-A1.blend'));sc=bpy.context.scene
baseline=metrics(sc);rng=random.Random(271026);b=Builder(sc,'VILLE V2 · details architecturaux')
def mat(name):return bpy.data.materials[name]
cement=mat('VILLE · beton brut gris sauge');light=mat('VILLE · beton clair erode');dark=mat('VILLE · beton humide sombre');old=mat('VILLE · enduit gris brun');metal=mat('VILLE · cadres aluminium terni');black=mat('VILLE · interieur profond')
oxide=material('VILLE · serrurerie brun oxyde',(.10,.075,.05),.73,.5)
patch=material('VILLE · ragréage ponctuel',(.28,.285,.245),.92)
def box(parent,name,loc,size,m=cement,bev=.025,project=True):
 o=b.box(name,loc,size,m,parent,bev);o['pa_city_project']=bool(project and m in (cement,light,dark,old,patch));return o
def balcony(p,x,y,z,w=3.2,depth=1.6):
 box(p,'Loggia · dalle et nez',(x,y-depth/2,z),(w,depth,.24),dark)
 box(p,'Loggia · garde-corps',(x,y-depth+.06,z+.64),(w,.16,1.05),cement)
 for dx in (-w/2,w/2):box(p,'Loggia · joue',(x+dx,y-depth/2,z+.64),(.16,depth,1.05),cement)
 # Functional thin metal cap along the exposed parapet.
 box(p,'Loggia · couvertine',(x,y-depth+.05,z+1.20),(w+.12,.23,.055),oxide,.012,False)
def band(p,w,d,z):
 box(p,'Corniche · larmier frontal',(0,-d/2-.10,z),(w+.24,.40,.19),dark)
 box(p,'Corniche · larmier lateral',(w/2+.10,0,z),(.40,d+.2,.19),dark)
def pipe(p,points,r=.055):return b.pipe('Reseau · descente zinc',points,r,metal,p,1)
def louvre(p,x,y,z,w=1.1,h=.8):
 box(p,'Ventilation · caisson',(x,y,z),(w,.28,h),metal,.025,False)
 for i in range(6):box(p,'Ventilation · lame',(x,y-.16,z-h*.40+i*h*.16),(w*.9,.11,.045),black,.0,False)

# Remove V1 image blend; regenerate a geometry-aligned albedo after the new details.
for m in bpy.data.materials:
 if not m.node_tree:continue
 nt=m.node_tree;bs=nt.nodes.get('Principled BSDF');mx=nt.nodes.get('Procedural majoritaire / albedo detail')
 if bs and mx and mx.inputs[1].is_linked:
  nt.links.new(mx.inputs[1].links[0].from_socket,bs.inputs['Base Color']);nt.nodes.remove(mx)
 if 'pa_projection_strength' in m:del m['pa_projection_strength']
if 'pa_city_projection' in sc:del sc['pa_city_projection']

# Large blank service panels, asymmetrical loggias and structural seams are modeled.
p=bpy.data.objects['A1 · couronne en porte-a-faux']
box(p,'Couronne · pan de beton aveugle',(-8.1,-10.61,7),(8.7,.30,14),cement,.04)
box(p,'Couronne · voile lateral',(12.61,3.2,7),(.30,9.6,14),cement,.04)
for z,x in [(2.2,4.8),(7.7,8.0)]:balcony(p,x,-10.6,z,3.9,1.6)
for z in (.2,13.7):band(p,25,21,z)
p=bpy.data.objects['A1 · noyau haut']
box(p,'Noyau · face technique aveugle',(-2.9,-6.15,5.5),(3.8,.25,11),cement)
for x in (-2.4,-1.6):pipe(p,[(x,-6.43,1),(x,-6.43,9.6),(x+.5,-6.43,10.1)],.065)
louvre(p,2.5,-6.35,9,1.5,1)
p=bpy.data.objects['A1 · noyau porteur tour droite']
box(p,'Noyau · grand voile continu',(-2.8,-7.65,31),(5.8,.28,37),cement,.03)
for z in (20,35,46):balcony(p,3.8,-7.6,z,2.8,1.2)
p=bpy.data.objects['A1 · tour mince perforee']
for z in (12,23,34,45,56,64):
 balcony(p,-3.9,-8.25,z,3.5,1.2)
for z in (18.9,38.2,57.7,69.6):band(p,12,16,z)
# Sparse window conversions, repair panels and antenna cables break identical bay repetition.
for z,x in [(6.9,1.5),(30.3,4.5),(46.0,1.5),(61.4,-1.5)]:box(p,'Fenetre · ancien remplissage',(x,-8.25,z),(1.12,.16,1.58),dark,.008)
pipe(p,[(5.3,-8.42,3),(5.3,-8.42,44),(5.7,-8.42,44.4),(5.7,-8.42,71)],.065)

p=bpy.data.objects['A1 · podium haut']
# Alter selected ribbon bays into deep full-height loggias; keep the monumental blade.
box(p,'Podium · panneau plein ouest',(-11.5,-10.8,17.8),(7.8,.50,12.2),light,.04)
for z in (7.9,15.9,23.8):band(p,31,21,z)
for z in (7.0,15.0):balcony(p,3.2,-10.85,z,4.6,1.25)
for x,z in [(-14,3.3),(11,18.9),(10.5,10.2)]:louvre(p,x,-11.0,z,1.3,.7)
box(p,'Entree · auvent',(4,-12.0,3.0),(7.5,3.6,.32),dark)
for x in (1,7):box(p,'Entree · poteau',(x,-13.4,1.5),(.24,.24,3),metal,.02,False)
p=bpy.data.objects['A1 · aile droite ajouree']
box(p,'Aile · bande technique aveugle',(6.2,-9.68,31),(5.7,.25,18),cement)
for z in (11.8,23.8,39.6):band(p,19,19,z)
for x in (-7,-2):pipe(p,[(x,-9.90,0),(x,-9.90,39.8)],.055)
for x,z in [(-5.7,18.5),(1.9,26.5),(-1.9,10.5)]:louvre(p,x,-9.95,z,1.2,.8)

# Older low buildings: articulated cornices, pilasters, external service pipes.
for name,w,d,h,floors in [('A1 · batiment bas longitudinal',31,13,14,4),('A1 · immeuble ancien angle',15,19,24,6)]:
 p=bpy.data.objects[name]
 for z in [h*i/floors for i in range(1,floors+1)]:band(p,w,d,z)
 for x in (-w*.46,-w*.17,w*.17,w*.46):
  box(p,'Ancien · pilastre',(x,-d/2-.19,h/2),(.34,.44,h),light,.015)
 for x in (-w*.42,w*.42):pipe(p,[(x,-d/2-.50,.5),(x,-d/2-.50,h+.15)],.065)
 for x in (-w*.28,w*.27):louvre(p,x,-d/2-.45,h*.62,1.0,.65)
 box(p,'Commerce · bandeau',(0,-d/2-.22,3.0),(w,.40,.50),dark)
 for x in (-w*.25,w*.25):
  box(p,'Commerce · auvent',(x,-d/2-1.0,2.8),(w*.42,2,.14),oxide,.018,False)

# Rooftop plant groups with ducts, vents and railings; much fewer objects after batching.
for name,w,d,h in [('A1 · tour mince perforee',12,16,70),('A1 · noyau haut',10,12,11),('A1 · podium haut',31,21,24),('A1 · aile droite ajouree',19,19,40),('A1 · immeuble ancien angle',15,19,24)]:
 p=bpy.data.objects[name]
 for j in range(3):
  x=-w*.25+j*1.9;y=d*.18
  box(p,'Toit · groupe technique',(x,y,h+.65),(1.2,1.8,1.3),metal,.06,False)
  for k in range(5):box(p,'Toit · ouies',(x,y-.93,h+.25+k*.18),(.95,.06,.045),black,0,False)
  pipe(p,[(x+.4,y+1,h+.4),(x+.4,y+1,h+1.9),(x+1.3,y+1,h+1.9)],.15)
 for x in (-w*.38,w*.38):
  pipe(p,[(x,d*.34,h),(x,d*.34,h+3.4)],.045)
  for z in (1.6,2.4,3.2):pipe(p,[(x-.7,d*.34,h+z),(x+.7,d*.34,h+z)],.018)

# Physical glazing variation and occasional blinds, attached to the parent building.
blind=material('VILLE · stores fanes',(.23,.24,.20),.88)
for name,w,d,h,floors,cols in [('A1 · podium haut',31,21,24,6,6),('A1 · batiment bas longitudinal',31,13,14,4,11),('A1 · aile droite ajouree',19,19,40,10,5)]:
 p=bpy.data.objects[name];batch=Batch(b,p,'Stores et croisillons non repetitifs');fh=h/floors;step=w/cols
 for row in range(floors):
  for col in range(cols):
   x=-w/2+(col+.5)*step
   if rng.random()<.22:
    wh=fh*(.39 if 'droite' in name else .52);bw=step*(.30 if 'droite' in name else .73)
    bh=wh*rng.uniform(.35,.85);z=row*fh+fh*.31+wh-bh/2
    batch.box((x,-d/2+.20,z),(bw-.12,.03,bh),blind)
 batch.emit(0)

# Mineral wear kept in metres, independent of image resolution and camera position.
for m in list(bpy.data.materials):
 if not m.node_tree or not m.name.startswith('VILLE'):continue
 nt=m.node_tree;bs=nt.nodes.get('Principled BSDF')
 if not bs or not nt.nodes.get('Granulat mineral'):continue
 if any(s in m.name for s in ('asphalte','trottoir','etancheite','tole')):continue
 base=bs.inputs['Base Color'].links[0].from_socket
 a=node(nt,'ShaderNodeAttribute','Patine · coordonnees du batiment');a.attribute_name='PA_BuildingLocal';co=a.outputs['Vector']
 v=node(nt,'ShaderNodeVectorMath','Patine · pluies minerales');v.operation='MULTIPLY';feed(nt,v.inputs[0],co);v.inputs[1].default_value=(1.7,1.7,.15)
 n=noise(nt,'Patine · depots irreguliers',v.outputs[0],2.1,5)
 patches=noise(nt,'Patine · erosion discontinue',co,.65,4)
 streak=smath(nt,'MULTIPLY',mapped(nt,'Patine · traces selectionnees',n,.43,.68,0,.58),mapped(nt,'Patine · variation de zone',patches,.3,.7,.15,1))
 color=mix(nt,'Patine · noir mineral',streak,base,(.035,.043,.035,1))
 ao=node(nt,'ShaderNodeAmbientOcclusion','Patine · humidite des raccords');ao.samples=4;ao.only_local=True;ao.inputs['Distance'].default_value=.9
 color=mix(nt,'Patine · joints et abris',smath(nt,'MULTIPLY',smath(nt,'SUBTRACT',1,ao.outputs['AO']),.42),color,(.028,.036,.027,1))
 repairs=mapped(nt,'Patine · reprises eparses',noise(nt,'Patine · masque reparation',co,.36,2),.67,.78,0,.20)
 color=mix(nt,'Patine · ciment de reparation',repairs,color,(.33,.32,.26,1));feed(nt,bs.inputs['Base Color'],color)
 m['pa_v2_weathering']=True

# Replace proxy cars by three local, textured assets. Consolidate each source once.
car_roots=sorted([o for o in sc.objects if o.type=='EMPTY' and o.name.startswith('VEHICULE ·')],key=lambda o:o.name)
positions=[(o.name,o.matrix_world.copy()) for o in car_roots]
for p in car_roots:
 for o in list(p.children_recursive):bpy.data.objects.remove(o,do_unlink=True)
 bpy.data.objects.remove(p,do_unlink=True)
lib=r'K:\Connector-Blender\Blender-asset-lib-VDB\SKetch-Fab\bagnoles.blend';sources=[];assets=[]
for name,length in [('1967_rover_p6_2000tc_low_poly',4.53),('triumph_dolomite_sprint',4.12),('low-poly_jaguar_xj-s',4.87)]:
 with bpy.data.libraries.load(lib,link=False) as(a,d):d.collections=[name]
 col=d.collections[0];sc.collection.children.link(col);bpy.context.view_layer.update();obs=[o for o in col.all_objects if o.type=='MESH']
 bpy.ops.object.select_all(action='DESELECT')
 for o in obs:
  mw=o.matrix_world.copy();o.parent=None;o.matrix_world=mw;o.hide_select=False;o.hide_set(False);o.select_set(True)
 bpy.context.view_layer.objects.active=obs[0];bpy.ops.object.join();o=obs[0]
 me=o.data.copy();me.transform(o.matrix_world)
 lo=Vector([min(v.co[i] for v in me.vertices) for i in range(3)]);hi=Vector([max(v.co[i] for v in me.vertices) for i in range(3)]);dim=hi-lo;center=(lo+hi)/2
 rotation=Matrix.Rotation(math.pi/2 if dim.x>dim.y else 0,4,'Z');s=length/max(dim.x,dim.y)
 for v in me.vertices:v.co=rotation@(v.co-Vector((center.x,center.y,lo.z)))*s
 me.use_fake_user=True;sources.append(me);assets.append({'library':lib,'collection':name,'triangles':sum(len(p.vertices)-2 for p in me.polygons),'length_m':length})
 # Remove temporary source hierarchy only; local mesh/material data are retained.
 for item in list(col.all_objects):bpy.data.objects.remove(item,do_unlink=True)
 bpy.data.collections.remove(col)
for i,(name,mx) in enumerate(positions):
 p=b.root(name+' · asset bibliotheque');p.matrix_world=mx;p.location.z=.015;p.rotation_euler.z=math.pi/2+rng.uniform(-.025,.025);p['pa_module']=True
 o=bpy.data.objects.new(assets[i%3]['collection'],sources[i%3]);b.collection.objects.link(o);o.parent=p
 o['pa_asset_instance']=True

# Simplify only shared tree data; all placements remain instances.
tree_meshes={o.data for o in sc.objects if o.type=='MESH' and o.name.startswith('Botaniq')}
for me in tree_meshes:
 users=[o for o in sc.objects if o.type=='MESH' and o.data==me];o=users[0]
 mod=o.modifiers.new('Branches LOD quartier','DECIMATE');mod.ratio=.38
 bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();new=bpy.data.meshes.new_from_object(o.evaluated_get(dg),preserve_all_data_layers=True,depsgraph=dg);o.modifiers.remove(mod)
 for q in users:q.data=new
print('DETAILS_AND_CARS_READY',flush=True)
report=optimize(sc);report['original_v1']=baseline;report['assets']=assets

# Contrasted overcast daylight: reduce uniform fill, keep broad directional shadows.
wt=sc.world.node_tree;wt.nodes['Background'].inputs['Strength'].default_value=.34;wt.nodes['Background'].inputs['Color'].default_value=(.61,.68,.62,1)
for n in wt.nodes:
 if n.type=='BACKGROUND' and n.name!='Background':n.inputs['Color'].default_value=(.76,.81,.61,1);n.inputs['Strength'].default_value=1.65
for o in sc.objects:
 if o.type=='LIGHT' and o.data.type=='SUN':o.data.energy=2.3;o.data.angle=math.radians(18);o.rotation_euler=(math.radians(32),math.radians(-38),math.radians(-28));o.data.color=(.92,.95,.81)
fog=mat('VILLE · brume atmospherique');nt=fog.node_tree
for n in nt.nodes:
 if n.name=='Brume · faible devant dense derriere':n.inputs['To Min'].default_value=.00025;n.inputs['To Max'].default_value=.0072
sc.view_settings.exposure=-.10;sc.view_settings.look='AgX - Medium High Contrast'
# Less shiny and less wavy asphalt; keep a modest damp sheen.
a=mat('VILLE · asphalte humide');n=a.node_tree.nodes.get('Humidite')
if n:n.inputs['To Min'].default_value=.34;n.inputs['To Max'].default_value=.69
sc.camera=next(o for o in sc.objects if o.type=='CAMERA' and o.name.startswith('CAM_01'))
sc.cycles.samples=48;sc.cycles.use_denoising=True;sc.render.resolution_x=1800;sc.render.resolution_y=1000;sc.render.resolution_percentage=100
p=bpy.context.preferences.addons['cycles'].preferences;p.compute_device_type='OPTIX';p.get_devices()
for d in p.devices:d.use=d.type!='CPU'
sc.cycles.device='GPU';sc['pa_output']=str(O);sc['pa_city_version']='2.0';sc.name='Ville A1 · V2 · architecture et patine'
for screen in bpy.data.screens:
 for area in screen.areas:
  if area.type=='VIEW_3D':area.spaces.active.shading.type='SOLID';area.spaces.active.clip_end=2000;area.spaces.active.region_3d.view_perspective='CAMERA'
for _ in range(4):
 for seq in (bpy.data.objects,bpy.data.meshes,bpy.data.materials,bpy.data.node_groups,bpy.data.images):
  for item in list(seq):
   if item.library:
    try:item.make_local()
    except RuntimeError:pass
for im in bpy.data.images:
 if im.source=='FILE' and not im.packed_file:
  try:im.pack()
  except RuntimeError:pass
bpy.ops.outliner.orphans_purge(do_local_ids=True,do_linked_ids=False,do_recursive=True)
report['after']=metrics(sc);report['total_seconds']=time.perf_counter()-start
(O/'optimization.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
bpy.ops.wm.save_as_mainfile(filepath=str(O/'ville-brutaliste-V2.blend'))
print('V2_SAVED',json.dumps(report),flush=True)
sc.cycles.samples=24;sc.render.resolution_percentage=70;sc.render.filepath=str(O/'preview-A1.png');bpy.ops.render.render(write_still=True)
print('V2_PREVIEW_READY',flush=True)
