import bpy,sys,json,math,random

from pathlib import Path

from mathutils import Vector

R=Path(__file__).parent;sys.path.insert(0,str(R));O=R/'output/gas-station-exterior-v1'

from pano_atelier.station_procedural import node,feed,noise,mapped,mix,math as smath

from pano_atelier.city_optimize import metrics

bpy.ops.wm.open_mainfile(filepath=str(O/'station-exterieur-textures.blend'));sc=bpy.context.scene

# Ground uses metric procedural aggregate and patchy moisture, never a projected photo.

m=bpy.data.materials.get('STATION · asphalte mouille');t=m.node_tree;bs=t.nodes.get('Principled BSDF');tc=node(t,'ShaderNodeTexCoord','Sol metres');co=tc.outputs['Object']

aggregate=noise(t,'Granulat bitumineux',co,78,3);patch=noise(t,'Humidite et reparations',co,.72,4)

base=mix(t,'Gravier sombre',mapped(t,'Granulats clairs',aggregate,.35,.70,0,1),(.025,.030,.031,1),(.066,.071,.069,1))

base=mix(t,'Plaques humides',mapped(t,'Humidite discontinue',patch,.40,.72,0,.20),base,(.012,.017,.019,1));feed(t,bs.inputs['Base Color'],base)

feed(t,bs.inputs['Roughness'],mapped(t,'Sec et humide',patch,.28,.73,.73,.48))

bump=node(t,'ShaderNodeBump','Granulat 4 mm');bump.inputs['Distance'].default_value=.004;bump.inputs['Strength'].default_value=.7;feed(t,bump.inputs['Height'],aggregate);feed(t,bs.inputs['Normal'],bump.outputs[0])

# Break the square silhouettes of rubble without adding objects.

rng=random.Random(35028)

for o in sc.objects:

 if o.type=='MESH' and 'Gravats regroupes' in o.name:

  for start in range(0,len(o.data.vertices),8):

   vs=list(o.data.vertices)[start:start+8]

   if len(vs)!=8:continue

   center=sum((v.co for v in vs),Vector())/8;angle=rng.uniform(-math.pi,math.pi)

   for v in vs:

    q=v.co-center;xx=q.x*math.cos(angle)-q.y*math.sin(angle);yy=q.x*math.sin(angle)+q.y*math.cos(angle)

    v.co=center+Vector((xx*rng.uniform(.72,1.15),yy*rng.uniform(.72,1.15),q.z*rng.uniform(.6,1.05)))

# Roof weathering is procedural and independent of oblique image projections.

from pano_atelier.gas_station import weather

roofmat=weather('STATION · membrane de toiture usee',(.115,.13,.125),rough=.87,peeling=.30)

t=roofmat.node_tree;bs=t.nodes.get('Principled BSDF');tc=node(t,'ShaderNodeTexCoord','Toiture metres');co=tc.outputs['Object']

patch=noise(t,'Depots anciens sur toit',co,1.5,4);fine=noise(t,'Grain etancheite',co,95,2)

brick=node(t,'ShaderNodeTexBrick','Les de membrane');brick.inputs['Color1'].default_value=(.09,.102,.094,1);brick.inputs['Color2'].default_value=(.075,.086,.080,1);brick.inputs['Mortar'].default_value=(.040,.045,.040,1);brick.inputs['Scale'].default_value=1;brick.inputs['Mortar Size'].default_value=.006;brick.inputs['Brick Width'].default_value=1.5;brick.inputs['Row Height'].default_value=4;feed(t,brick.inputs['Vector'],co);base=mix(t,'Patine toiture',mapped(t,'Taches de toiture',patch,.30,.70,0,.16),brick.outputs['Color'],(.055,.063,.058,1));feed(t,bs.inputs['Base Color'],base)

feed(t,bs.inputs['Roughness'],mapped(t,'Humidite toiture',fine,0,1,.68,.92))

for o in sc.objects:

 if o.type=='MESH' and (o.name.startswith('Boutique · toit') or o.name.startswith('Annexe · toit')):

  for slot in o.material_slots:slot.link='OBJECT';slot.material=roofmat

# Dimensional grain on steel, with no large-scale shader marbling.

for m in bpy.data.materials:

 if m.name.startswith('STATION · acier') and m.node_tree:

  bs=m.node_tree.nodes.get('Principled BSDF');b=next((n for n in m.node_tree.nodes if n.type=='BUMP'),None)

  if b:b.inputs['Distance'].default_value=.0007

rear=next(o for o in sc.objects if o.type=='CAMERA' and o.name.startswith('CAM_05'));rear.location=(-20,18,3.2);rear.rotation_euler=(Vector((-1,2,2.6))-rear.location).to_track_quat('-Z','Y').to_euler()

sc.camera=next(o for o in sc.objects if o.type=='CAMERA' and o.name.startswith('CAM_01'))

sc.cycles.samples=64;sc.cycles.use_denoising=True;sc.render.resolution_percentage=100

sc.render.resolution_x=1800;sc.render.resolution_y=1200

p=bpy.context.preferences.addons['cycles'].preferences;p.compute_device_type='OPTIX';p.get_devices()

for d in p.devices:d.use=d.type!='CPU'

sc.cycles.device='GPU'

sc['pa_gas_phase']='Exterior V1 - procedural substrates + GPT Image albedo from 3 cameras; exterior covered, interior deferred.'

report={'metrics':metrics(sc),'modules':[o.name for o in sc.objects if o.get('pa_module')],'projections':json.loads(sc.get('pa_city_projection_layers','[]')),'camera_views':6}

bpy.ops.wm.save_as_mainfile(filepath=str(O/'station-exterieur.blend'),compress=True)

(O/'final-report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf8')

sc.render.use_persistent_data=True

for i in range(1,7):

 sc.camera=next(o for o in sc.objects if o.type=='CAMERA' and o.name.startswith('CAM_%02d'%i));sc.render.filepath=str(O/('render-%02d.png'%i));bpy.ops.render.render(write_still=True);print('GAS_FINAL_RENDER',i,flush=True)
