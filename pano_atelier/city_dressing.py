"""Curated A1 street dressing using the user's local library. No bundled assets.

One shared mesh per furniture type; imported sign UVs are preserved. Ring Fog
geometry keeps its editable modifiers, with a feathered city-scale volume.
"""
import bpy, math, random
from pathlib import Path
from mathutils import Vector, Matrix
from .modular_scene import Builder, material, camera
from .city_scene import Batch
from .station_procedural import node, feed, math as smath, mapped, noise, mix

SIGN_NAMES=['3d-Pann','3d-Pann.012','3d-Pann.003','3d-TEL','3d-Pann.006','HANDICAP','pAY-paRKING','do not enter']

def surface(name,color,metal=.0):
    m=material(name,color,.65,metal);t=m.node_tree;bs=t.nodes.get('Principled BSDF')
    tc=node(t,'ShaderNodeTexCoord','Coordonnees de l objet');co=tc.outputs['Object']
    n=noise(t,'Patine fine',co,13,3);f=mapped(t,'Depots discrets',n,.48,.78,0,.22)
    feed(t,bs.inputs['Base Color'],mix(t,'Teinte usee',f,(*color,1),(*(v*.45 for v in color),1)))
    fine=noise(t,'Micrograin',co,150,2);feed(t,bs.inputs['Roughness'],mapped(t,'Rugosite',fine,0,1,.49,.81))
    bump=node(t,'ShaderNodeBump','Microrelief');bump.inputs['Distance'].default_value=.0007;bump.inputs['Strength'].default_value=.25
    feed(t,bump.inputs['Height'],fine);feed(t,bs.inputs['Normal'],bump.outputs[0]);return m

def joined_mesh(scene,objects,name):
    """Evaluate just the small prototype, preserving multi-material indices."""
    bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();vs=[];fs=[];mi=[];mats=[]
    for o in objects:
        e=o.evaluated_get(dg);me=e.to_mesh();offset=len(vs)
        slots=[]
        for evaluated_material in me.materials:
            # Evaluated material pointers expire when depsgraph changes. Use originals.
            m=bpy.data.materials[evaluated_material.name]
            if m not in mats:mats.append(m)
            slots.append(mats.index(m))
        vs.extend(tuple(o.matrix_world@v.co) for v in me.vertices)
        for p in me.polygons:fs.append(tuple(offset+i for i in p.vertices));mi.append(slots[p.material_index] if slots else 0)
        e.to_mesh_clear()
    me=bpy.data.meshes.new(name);me.from_pydata(vs,[],fs);me.update()
    for m in mats:me.materials.append(m)
    for p,i in zip(me.polygons,mi):p.material_index=i
    for o in objects:bpy.data.objects.remove(o,do_unlink=True)
    return me

def ring_material(name,density):
    m=bpy.data.materials.new(name);m.use_nodes=True;t=m.node_tree;t.nodes.clear()
    out=node(t,'ShaderNodeOutputMaterial','Sortie');v=node(t,'ShaderNodeVolumePrincipled','Brume peripherique')
    v.inputs['Color'].default_value=(.90,.94,.84,1);v.inputs['Anisotropy'].default_value=.15
    v.inputs['Emission Color'].default_value=(.68,.75,.53,1)
    tc=node(t,'ShaderNodeTexCoord','Coordonnees locales de l anneau');co=tc.outputs['Object']
    sep=node(t,'ShaderNodeSeparateXYZ','Altitude locale');feed(t,sep.inputs[0],co)
    flat=node(t,'ShaderNodeCombineXYZ','Plan radial');feed(t,flat.inputs['X'],sep.outputs['X']);feed(t,flat.inputs['Y'],sep.outputs['Y'])
    length=node(t,'ShaderNodeVectorMath','Rayon local');length.operation='LENGTH';feed(t,length.inputs[0],flat.outputs[0])
    # Ring geometry is 10.172..15.072 local radius; fade before every boundary.
    inner=mapped(t,'Entree douce',length.outputs['Value'],10.20,11.7,0,1)
    outer=mapped(t,'Sortie douce',length.outputs['Value'],13.8,15.04,1,0)
    top=mapped(t,'Sommet diffus',sep.outputs['Z'],.4,2.0,1,0)
    bottom=mapped(t,'Base diffuse',sep.outputs['Z'],-2.68,-2.05,0,1)
    n=noise(t,'Variation lente',co,.33,2);variation=mapped(t,'Homogeneite',n,0,1,.82,1)
    mask=smath(t,'MULTIPLY',smath(t,'MULTIPLY',inner,outer),smath(t,'MULTIPLY',top,bottom))
    strength=node(t,'ShaderNodeValue','Densite anneau');strength.outputs[0].default_value=density
    d=smath(t,'MULTIPLY',smath(t,'MULTIPLY',mask,variation),strength.outputs[0])
    feed(t,v.inputs['Density'],d);feed(t,v.inputs['Emission Strength'],smath(t,'MULTIPLY',d,.233333))
    feed(t,out.inputs['Volume'],v.outputs['Volume']);m['pa_ring_fog']=True;return m

def build(scene,asset_root):
    if not scene.get('pa_city_opposite'):raise ValueError('Construire le vis-a-vis A1 avant le mobilier.')
    if scene.get('pa_city_dressing'):raise ValueError('Le mobilier urbain est deja present.')
    lib=Path(asset_root)/'Elements-decor'
    for f in ['circular-fog.blend','Select-Panneaux-LO.blend']:
        if not (lib/f).is_file():raise FileNotFoundError(lib/f)
    b=Builder(scene,'MOBILIER · rue et parvis');root=b.root('MOBILIER · ensemble');root['pa_module']=True
    prototypes={};counts={};rng=random.Random(627)
    steel=surface('RUE · fonte vert anthracite',(.045,.066,.058),.55)
    galvan=surface('RUE · galvanise mat',(.25,.27,.25),.7)
    wood=surface('RUE · lattes brun gris',(.11,.087,.057))
    cement=surface('RUE · beton des jardinieres',(.25,.27,.225))
    ivory=surface('RUE · peinture ivoire ternie',(.53,.53,.40))
    rubber=surface('RUE · creux et joints',(.012,.018,.014))
    soil=surface('RUE · terre des jardinieres',(.045,.040,.025))
    def proto(kind,fn):
        before=set(b.collection.objects);fn();obs=[o for o in b.collection.objects if o not in before]
        prototypes[kind]=joined_mesh(scene,obs,'RUE prototype · '+kind)
    def box(loc,size,mat,bevel=.008):return b.box('Prototype',loc,size,mat,bevel=bevel)
    def cyl(loc,r,d,mat,n=12):return b.cylinder('Prototype',loc,r,d,mat,vertices=n)
    def bollard():
        cyl((0,0,.46),.075,.92,steel);cyl((0,0,.045),.13,.09,steel)
        cyl((0,0,.80),.076,.085,ivory);cyl((0,0,.93),.082,.045,steel)
    def bench():
        for y in (-.19,-.065,.065,.19):box((0,y,.47),(1.85,.108,.065),wood)
        for z in (.70,.84,.98):box((0,.27,z),(1.85,.055,.10),wood)
        for x in (-.70,.70):
            for y in (-.18,.20):box((x,y,.23),(.07,.07,.46),steel)
            box((x,.27,.70),(.06,.055,.64),steel);box((x,0,.40),(.07,.59,.07),steel)
            box((x,0,.70),(.06,.55,.05),steel)
    def bin_():
        cyl((0,0,.43),.25,.78,steel,16);cyl((0,0,.08),.29,.12,steel,16)
        cyl((0,0,.85),.275,.065,galvan,16);cyl((0,0,.886),.175,.008,rubber,16)
        for i in range(16):
            a=i*math.tau/16;box((.252*math.cos(a),.252*math.sin(a),.46),(.016,.016,.61),galvan,.001)
    def cabinet():
        box((0,0,.10),(.89,.53,.20),cement);box((0,0,.80),(.82,.47,1.20),galvan)
        for x in (-.205,.205):box((x,-.245,.80),(.394,.018,1.15),steel,.004)
        for z in (.34,.39,.44,.49):box((0,-.26,z),(.63,.015,.012),rubber,.001)
        box((.06,-.27,.85),(.025,.04,.10),galvan)
    def planter():
        box((0,0,.10),(1.65,.72,.20),cement)
        for y in (-.35,.35):box((0,y,.35),(1.65,.09,.60),cement)
        for x in (-.78,.78):box((x,0,.35),(.09,.64,.60),cement)
        box((0,0,.56),(1.47,.58,.03),soil)
        for j in range(22):
            x=rng.uniform(-.68,.68);y=rng.uniform(-.22,.22);h=rng.uniform(.13,.36)
            b.pipe('Tiges seches',[(x,y,.57),(x+.035,y,.57+h*.65),(x+.08,y+.035,.57+h)],.005,wood,resolution=0)
    def rack():
        for x in (-.75,0,.75):b.pipe('Arceau',[(x,-.26,0),(x,-.26,.65),(x,-.20,.78),(x,.20,.78),(x,.26,.65),(x,.26,0)],.035,galvan,resolution=1)
    for kind,fn in [('borne',bollard),('banc',bench),('corbeille',bin_),('armoire',cabinet),('jardiniere',planter),('arceaux velos',rack)]:
        print('PROTOTYPE',kind,flush=True);proto(kind,fn)
    def place(kind,loc,angle=0):
        o=bpy.data.objects.new('RUE · '+kind,prototypes[kind]);b.collection.objects.link(o);o.parent=root;o.location=loc;o.rotation_euler.z=angle
        o['pa_street_furniture']=kind;o['pa_module']=True;counts[kind]=counts.get(kind,0)+1;return o
    # Bollards stop before crossings/entrances; no fence across the roadway.
    for y,ranges in [(-51.1,[(-47,-31),(-15,2),(17,30),(56,74),(87,101)]),(-35.1,[(-54,-39),(-17,-2),(14,29),(56,72)])]:
        for lo,hi in ranges:
            for x in range(lo,hi+1,4):place('borne',(x,y,.13),rng.uniform(-.05,.05))
    for x,y,a in [(-34,-57,math.pi),(-9,-57,math.pi),(23,-57,math.pi),(63,-57,math.pi),(94,-57,math.pi),(-38,-30,0),(9,-29,0),(67,-30,0), (56,-85,math.pi/2)]:place('banc',(x,y,.13),a)
    for x,y in [(-36,-57),(-16,-53),(25,-57),(61,-57),(96,-57),(-36,-30),(11,-29),(65,-30),(55,-82)]:place('corbeille',(x,y,.13))
    for x,y,a in [(-47,-60,0),(30,-60,0),(99,-61,0),(-30,-24,math.pi),(72,-24,math.pi),(30,-103,0)]:place('armoire',(x,y,.13),a)
    for x,y,a in [(-25,-58,0),(16,-60,0),(58,-61,0),(82,-61,0),(-5,-30,0),(20,-30,0),(56,-78,math.pi/2),(56,-91,math.pi/2)]:place('jardiniere',(x,y,.13),a)
    for x,y,a in [(-4,-59,0),(78,-58,0),(-21,-30,0),(56,-99,math.pi/2)]:place('arceaux velos',(x,y,.13),a)
    for y in (-77,-82,-98,-104):place('borne',(31.9,y,.13))
    place('banc',(30.5,-94,.13),-math.pi/2);place('corbeille',(30.5,-96,.13))
    for x in (-26,-9):place('jardiniere',(x,-85,.015))
    place('banc',(-18,-84,.015),math.pi);place('corbeille',(-20,-84,.015))
    # Real library signs, centered without altering UVs. Prefer the 2K atlas nearby.
    print('FURNITURE_PLACED',flush=True);bpy.context.view_layer.update()
    signs={};import_report=[]
    with bpy.data.libraries.load(str(lib/'Select-Panneaux-LO.blend'),link=False) as(a,d):
        missing=set(SIGN_NAMES)-set(a.objects)
        if missing:raise ValueError('Panneaux manquants: '+str(missing))
        d.objects=SIGN_NAMES
    print('SIGNS_IMPORTED',flush=True)
    for src in d.objects:
        me=src.data.copy();coords=[v.co.copy() for v in me.vertices];lo=Vector(tuple(min(v[i] for v in coords) for i in range(3)));hi=Vector(tuple(max(v[i] for v in coords) for i in range(3)));size=hi-lo
        for v in me.vertices:v.co-=(lo+hi)/2
        signs[src.name]=(me,size);import_report.append({'file':'Elements-decor/Select-Panneaux-LO.blend','asset':src.name,'triangles':sum(len(p.vertices)-2 for p in me.polygons)})
        bpy.data.objects.remove(src,do_unlink=True)
    # +X sign face rotates toward approaching traffic / pedestrian routes.
    placements=[('3d-Pann',-46,-51.8,math.pi/2,.62),('3d-Pann.012',29,-51.8,0,.62),('3d-Pann.003',55,-53,math.pi,.67),('3d-TEL',-16,-54,math.pi/2,.52),('3d-Pann.006',74,-52,math.pi/2,.58),('3d-Pann',-18,-34.2,-math.pi/2,.62),('3d-Pann.012',30,-34.2,math.pi,.62),('3d-Pann.006',-51,-34.2,-math.pi/2,.56),('HANDICAP',88,-52,math.pi/2,.55),('pAY-paRKING',-31,-52,math.pi/2,.50),('do not enter',32,-95,0,.58),('3d-Pann.003',54,-111,math.pi,.67),('pAY-paRKING',68,-34,-math.pi/2,.50)]
    for index,(name,x,y,angle,h) in enumerate(placements):
        p=b.root('RUE · signalisation %02d · %s'%(index+1,name),(x,y,.13),root);p.rotation_euler.z=angle;p['pa_module']=True;p['pa_street_sign']=name
        pole=b.cylinder('RUE · mat galvanise',(-.045,0,1.28),.033,2.56,galvan,p,vertices=10)
        me,size=signs[name];o=bpy.data.objects.new('RUE · panneau · '+name,me);b.collection.objects.link(o);o.parent=p;o.location=(0,0,2.25);s=h/size.z;o.scale=(s,s,s);o['pa_library_source']=name
        # Backing adds physical thickness to decal-only assets, without stretching their UVs.
        if size.x<.001:b.box('RUE · dos du panneau',(-.009,0,2.25),(.018,size.y*s,h),galvan,p,.008)
    print('SIGNS_PLACED',flush=True);bpy.context.view_layer.update()
    # Ring Fog from the library, with its screw/solidify construction preserved.
    fb=Builder(scene,'ATMOSPHERE · Ring Fog peripheriques')
    with bpy.data.libraries.load(str(lib/'circular-fog.blend'),link=False) as(a,d):d.objects=['Ring-Fog']
    print('RING_IMPORTED',flush=True)
    source=d.objects[0];source.parent=None;source.animation_data_clear();source.constraints.clear()
    rings=[]
    for i,(sx,sy,sz,z,density) in enumerate([(10.5,12.5,42,96,.045),(17,20.5,58,132,.070)]):
        o=source if i==0 else source.copy()
        if i:o.data=source.data.copy()
        fb.collection.objects.link(o);o.name='RING FOG · '+('transition' if i==0 else 'silhouettes lointaines');o.location=(10,-35,z);o.rotation_euler=(0,0,0);o.scale=(sx,sy,sz)
        o.data.materials.clear();o.data.materials.append(ring_material(o.name,density));o.display_type='WIRE';o.hide_select=True;o['pa_noncolliding']=True;o['pa_ring_fog']=True;o['pa_library_source']='Elements-decor/circular-fog.blend :: Ring-Fog';rings.append(o)
    print('RINGS_PLACED',flush=True);bpy.context.view_layer.update()
    cam=camera(b,'CAM_14 · mobilier et profondeur',(-42,-46,1.8),(-5,-57,3.0),35,1800,990);cam.data.clip_end=1500
    scene['pa_city_dressing']=True
    return {'furniture':counts,'signs':len(placements),'ring_fog':[{'name':o.name,'dimensions':list(o.dimensions),'location':list(o.location)} for o in rings],'imports':import_report,'notes':['No buildings or projection layers modified.','Shared mesh prototypes; each item or sign assembly remains movable.','Low resolution library decals kept at distance; nearby signs use 2K atlas.','Ring Fog material adapted to city scale with smooth radial and height fades.']}
