"""Art-directed wear and motivated light, preserving V2 mesh/pivots and local maps."""
import bpy, json, hashlib, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'output/cockpit-photo-modulaire-v3';OUT.mkdir(parents=True,exist_ok=True)
SOURCE=ROOT/'output/cockpit-photo-modulaire-v2/cockpit-patine-360.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
sc=bpy.context.scene;sc.name='Cockpit — usure et lumière V3'
def digest():
    h=hashlib.sha256()
    for o in sorted(sc.objects,key=lambda o:o.name):
        if o.type!='MESH':continue
        h.update(str((o.name,o.parent.name if o.parent else None,list(map(tuple,o.matrix_world)),[tuple(v.co) for v in o.data.vertices],[tuple(p.vertices) for p in o.data.polygons])).encode())
    return h.hexdigest()
before=digest()

def node(nt,kind,label):
    n=nt.nodes.new(kind);n.label=label;n.name='V3 · '+label;return n
def noise(nt,coords,scale,label):
    v=node(nt,'ShaderNodeVectorMath',label+' échelle');v.operation='MULTIPLY';v.inputs[1].default_value=scale;nt.links.new(coords,v.inputs[0])
    n=node(nt,'ShaderNodeTexNoise',label);n.inputs['Scale'].default_value=1;n.inputs['Detail'].default_value=3;n.inputs['Roughness'].default_value=.7;nt.links.new(v.outputs[0],n.inputs['Vector']);return n.outputs['Fac']
def ramp(nt,source,a,b,ca,cb,label):
    r=node(nt,'ShaderNodeValToRGB',label);r.color_ramp.elements[0].position=a;r.color_ramp.elements[1].position=b
    r.color_ramp.elements[0].color=ca;r.color_ramp.elements[1].color=cb;nt.links.new(source,r.inputs[0]);return r.outputs[0]
def math_(nt,op,a,b,label):
    n=node(nt,'ShaderNodeMath',label);n.operation=op
    for i,val in enumerate([a,b]):
        if isinstance(val,(int,float)):n.inputs[i].default_value=val
        else:nt.links.new(val,n.inputs[i])
    return n.outputs[0]
def mix(nt,fac,a,b,label,blend='MIX'):
    n=node(nt,'ShaderNodeMixRGB',label);n.blend_type=blend
    for i,val in enumerate([fac,a,b]):
        if isinstance(val,(tuple,list)):n.inputs[i].default_value=val
        elif isinstance(val,(int,float)):n.inputs[i].default_value=val
        else:nt.links.new(val,n.inputs[i])
    return n.outputs[0]
def input_source(socket):return socket.links[0].from_socket if socket.is_linked else tuple(socket.default_value)

def wear(m,strength):
    nt=m.node_tree;bs=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED');base=input_source(bs.inputs['Base Color'])
    tc=node(nt,'ShaderNodeTexCoord','Usure locale solidaire du meuble')
    cloud=noise(nt,tc.outputs['Object'],(10,10,4),'Voiles de graisse')
    mask=ramp(nt,cloud,.43,.73,(0,0,0,1),(strength,strength,strength,1),'Patine irrégulière')
    stained=mix(nt,mask,base,(.085,.067,.043,1),'Peinture vieillie')
    ao=node(nt,'ShaderNodeAmbientOcclusion','Dépôt dans les creux');ao.inputs['Distance'].default_value=.065;ao.samples=8;ao.only_local=True
    crevices=math_(nt,'MULTIPLY',math_(nt,'SUBTRACT',1,ao.outputs['AO'],'Creux'),.48,'Intensité des dépôts')
    stained=mix(nt,crevices,stained,(.065,.052,.035,1),'Salissure des jonctions')
    scratch=noise(nt,tc.outputs['Object'],(95,4,48),'Frottements fins')
    scratch=ramp(nt,scratch,.65,.76,(0,0,0,1),(.28,.28,.28,1),'Rayures de surface')
    result=mix(nt,scratch,stained,(.38,.36,.29,1),'Traces sur émail')
    nt.links.new(result,bs.inputs['Base Color'])
    rough=ramp(nt,cloud,.25,.75,(.23,.23,.23,1),(.58,.58,.58,1),'Peinture polie et salie')
    nt.links.new(rough,bs.inputs['Roughness'])
    m['v3_wear_strength']=strength;m['v3_coordinates']='Object local; no external coordinate object'

# Clone the shared paint only for furniture: architecture keeps a lighter patina.
paint_names=['Coque · peinture ivoire satinée','Chants · ivoire clair','Panneaux · gris chaud']
copies={}
for o in sc.objects:
    if o.type!='MESH' or not o.parent:continue
    is_furniture=o.parent.name.startswith(('M_CONSOLE','M_BUREAU','M_TABLE','M_ARR_CONSOLE','M_ARR_RANGEMENT'))
    if is_furniture:
        for slot in o.material_slots:
            if slot.material and slot.material.name in paint_names:
                name=slot.material.name
                if name not in copies:copies[name]=slot.material.copy();copies[name].name=name+' · usure mobilier V3'
                slot.material=copies[name]
for m in copies.values():wear(m,.46)
for name in paint_names:wear(bpy.data.materials[name],.22)
for m in list(bpy.data.materials):
    if m.name.startswith('Instrumentation '):wear(m,.29)

floor=bpy.data.materials['Sol · résine taupe satinée'];nt=floor.node_tree;bs=nt.nodes.get('Principled BSDF')
tc=node(nt,'ShaderNodeTexCoord','Sol : coordonnées métriques locales')
cloud=noise(nt,tc.outputs['Object'],(1.5,1.5,1.5),'Zones de passage')
fine=noise(nt,tc.outputs['Object'],(115,7,2),'Rayures longitudinales')
cross=noise(nt,tc.outputs['Object'],(8,135,2),'Rayures croisées')
scratches=math_(nt,'MAXIMUM',fine,cross,'Réseau de micro-rayures')
scratches=ramp(nt,scratches,.62,.76,(0,0,0,1),(1,1,1,1),'Éraflures discontinues')
old=input_source(bs.inputs['Base Color'])
stain=ramp(nt,cloud,.30,.73,(.05,.05,.05,1),(.34,.34,.34,1),'Traces sombres de passage')
base=mix(nt,stain,old,(.075,.068,.05,1),'Résine marquée')
base=mix(nt,math_(nt,'MULTIPLY',scratches,.2,'Visibilité rayures'),base,(.34,.32,.27,1),'Usure du vernis')
nt.links.new(base,bs.inputs['Base Color'])
rough=ramp(nt,cloud,.25,.78,(.065,.065,.065,1),(.22,.22,.22,1),'Vernis poli par zones')
rough=math_(nt,'ADD',rough,math_(nt,'MULTIPLY',scratches,.16,'Rayures plus mates'),'Rugosité usée')
nt.links.new(rough,bs.inputs['Roughness'])
bs.inputs['Coat Weight'].default_value=.42;bs.inputs['Coat Roughness'].default_value=.085
nt.links.new(rough,bs.inputs['Coat Roughness'])
bump=node(nt,'ShaderNodeBump','Micro-rayures : relief fin');bump.inputs['Strength'].default_value=.18;bump.inputs['Distance'].default_value=.00035
nt.links.new(scratches,bump.inputs['Height']);nt.links.new(bump.outputs[0],bs.inputs['Normal'])

# Light pools with deliberate differences; no change to fixture geometry.
light_report=[];idx=0;rear=0
for o in sorted(sc.objects,key=lambda o:o.name):
    if o.type!='LIGHT':continue
    prev=o.data.energy
    if 'Oculus' in o.name:o.data.energy=125;o.data.color=(.83,.89,1)
    elif 'Remplissage' in o.name:o.data.energy=30;o.data.color=(.85,.90,1)
    elif 'Rebond' in o.name:o.data.energy*=.38
    elif 'Éclairage arrière' in o.name:
        o.data.energy=[92,22,48][rear%3];o.data.color=[(1,.73,.45),(.78,.86,1),(1,.86,.65)][rear%3];rear+=1
    elif 'Plafonnier' in o.name:
        o.data.energy=[55,16,38,9,65,22,44,12][idx%8];o.data.color=[(1,.78,.53),(.82,.89,1),(1,.87,.67)][idx%3]
        # Small real practical sources may reflect on the worn floor.
        o.visible_glossy=True;idx+=1
    light_report.append({'name':o.name,'before':prev,'after':o.data.energy,'color':list(o.data.color)})
for o in sc.objects:
    if o.type!='MESH':continue
    for slot in o.material_slots:
        if slot.material and slot.material.name=='Plafonniers · blanc opalin':
            m=slot.material.copy();m.name='Opale V3 · '+o.name;slot.material=m
            p=m.node_tree.nodes.get('Principled BSDF');seed=sum(o.name.encode())%4
            p.inputs['Emission Strength'].default_value=[6,11,3,8][seed]
            p.inputs['Emission Color'].default_value=[(1,.78,.53,1),(.87,.92,1,1),(1,.87,.67,1),(1,.8,.6,1)][seed]
sc.view_settings.exposure=-.65;sc.cycles.samples=112;sc.cycles.use_denoising=True
sc.render.use_persistent_data=True
try:
    prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
    for d in prefs.devices:d.use=d.type!='CPU'
    sc.cycles.device='GPU'
except Exception as e:print(e)
sc.camera=bpy.data.objects['CAM_PHOTO'];sc.render.resolution_percentage=100
after=digest();assert before==after,'Geometry or parenting changed'
report=json.loads((SOURCE.parent/'scene-report.json').read_text(encoding='utf-8'))
report.update({'v3_mesh_before':before,'v3_mesh_after':after,'lights':light_report,'source':str(SOURCE),'pass':'Procedural wear layered over packed GPT Image albedos; no new image generation'})
(OUT/'scene-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'cockpit-usure-lumiere.blend'))
if '--preview' in sys.argv:
    sc.render.resolution_percentage=75;sc.cycles.samples=48
    for cam,name in [('CAM_PHOTO','avant-preview'),('CAM_ARRIERE_OBLIQUE','arriere-preview')]:
        sc.camera=bpy.data.objects[cam];sc.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
print('V3_SAVED',flush=True)
