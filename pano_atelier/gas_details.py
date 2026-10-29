"""Lightweight dressing from the user's Trash-Kit; library is read-only."""
import bpy,random,math
from mathutils import Vector
from .modular_scene import Builder
from .gas_station import weather
from .gas_weather import roof_material

def dress(sc,library):
    if sc.get('pa_gas_dressing'):raise ValueError('Habillage deja ajoute.')
    b=Builder(sc,'STATION · details et debris');whole=bpy.data.objects.get('STATION · ensemble');rng=random.Random(352)
    groups={}
    for key,label in [('ground','debris du parvis'),('roof','debris et depots toiture'),('inside','debris interieurs')]:
        p=b.root('STATION · '+label,parent=whole);p['pa_module']=True;groups[key]=p
    wanted=['Base_Trash_Heap_A','Base_Trash_Heap_C','Base_Trash_Heap_F','Base_Trash_Bag_A','Base_Trash_Rubble_A','Base_Trash_Rubble_C','Base_Trash_Bottle_A','Base_Trash_Can_A','Base_Trash_Plastic_A']
    with bpy.data.libraries.load(str(library),link=False) as (a,data):
        missing=set(wanted)-set(a.objects)
        if missing:raise ValueError('Assets absents : '+str(missing))
        data.objects=list(wanted)
    prototypes={};report=[]
    for src in data.objects:
        b.collection.objects.link(src);bpy.context.view_layer.update();me=src.data.copy();me.transform(src.matrix_world.to_3x3().to_4x4())
        lo=Vector(tuple(min(v.co[k] for v in me.vertices) for k in range(3)));hi=Vector(tuple(max(v.co[k] for v in me.vertices) for k in range(3)));center=Vector(((lo.x+hi.x)/2,(lo.y+hi.y)/2,lo.z));dim=hi-lo
        for v in me.vertices:v.co-=center
        prototypes[src.name]=(me,max(dim.x,dim.y));report.append({'asset':src.name,'triangles':sum(len(p.vertices)-2 for p in me.polygons)})
        bpy.data.objects.remove(src,do_unlink=True)
    instances=[]
    def place(name,loc,width,group):
        me,extent=prototypes[name];o=bpy.data.objects.new('DEBRIS · '+name,me);b.collection.objects.link(o);o.parent=groups[group];o.location=loc;o.rotation_euler.z=rng.uniform(0,math.tau);s=width/extent;o.scale=(s,s,s);o['pa_asset_source']=str(library);o['pa_asset_object']=name;instances.append(o);return o
    heaps=wanted[:3];small=wanted[3:]
    for k,(x,y) in enumerate([(-11.5,-3.0),(-10.8,-5.15),(-7.2,-5.15),(-11.45,1),(-11.5,3.9),(-5.4,-.45),(5.8,-.4),(7.0,5.0),(7.2,7.8),(3.5,8),(-2.5,8),(-6.8,8),(-3.1,-5.4),(2.7,-5.6),(9.8,-7.7)]):place(heaps[k%3],(x,y,-.023),rng.uniform(.65,1.30),'ground')
    for k in range(55):
        x=rng.uniform(-14,13);y=rng.uniform(-12,9)
        if -11.3<x<6.9 and -.1<y<7.8:continue
        if -10.5<x<-8.8 and -5.8<y<-3.8:continue
        place(rng.choice(small),(x,y,-.022),rng.uniform(.12,.44),'ground')
    for k,(x,y,z) in enumerate([(-6.4,-7.5,5.33),(6.4,-7.4,5.33),(5.8,-1.0,5.33),(-4,-.7,5.33),(0,-1.1,5.33),(-5.7,6.7,5.04),(5.6,6.8,5.04),(-1,7.0,5.04),(-10.6,2.6,4.23),(-9.9,-3.7,4.23)]):place(rng.choice(heaps),(x,y,z),rng.uniform(.42,.75),'roof')
    for k in range(24):
        x=rng.choice([-10.7,-9.2,-8.8,-7.0])+rng.uniform(-.08,.08);y=rng.uniform(-4.1,3.25);place(rng.choice(small),(x,y,.151),rng.uniform(.10,.28),'inside')
    for x,y in [(-5.9,4.2),(-5.8,1.0),(5.9,3.8),(5.5,6.7),(0,6.9)]:place(rng.choice(heaps),(x,y,.136),rng.uniform(.38,.60),'inside')
    rm=roof_material();roofs=[]
    for o in sc.objects:
        if o.type=='MESH' and o.name.startswith(('Boutique · toit','Annexe · toit','Tole de couverture et nervures')):
            for slot in o.material_slots:slot.link='OBJECT';slot.material=rm
            roofs.append(o.name)
    # Real roof details: vent stacks, flashing, cable route and a displaced sheet.
    grey=weather('DETAILS · zinc noirci',(.095,.105,.095),metal=.5,rough=.72,peeling=.5)
    rust=weather('DETAILS · fer rouille',(.115,.050,.020),metal=.3,rough=.85,peeling=.65)
    p=groups['roof']
    for x,y,z in [(-4.6,6.3,5.03),(4.8,5.7,5.03),(-10.1,2.4,4.22)]:
        b.box('Solin de ventilation',(x,y,z+.03),(.48,.48,.055),grey,p,.012)
        b.cylinder('Cheminee ventilation',(x,y,z+.28),.12,.5,grey,p,vertices=16)
        b.cylinder('Chapeau ventilation',(x,y,z+.56),.21,.065,rust,p,vertices=16)
    for k in range(3):b.pipe('Cable abandonne sur toiture',[(-6.1,5.5+k*.07,5.06),(-3,5.5+k*.07,5.06),(-1.5,4.8+k*.07,5.06),(1.6,5.1+k*.07,5.06)],.012,grey,p,1)
    sheet=b.box('Tole deposee sur toit',(-4,6.7,5.10),(1.65,.75,.018),rust,p,.008);sheet.rotation_euler=(.04,.02,.25)
    # A bent gutter bracket and a loose junction box add small-scale silhouettes.
    front=groups['ground']
    b.box('Boitier electrique abandonne',(-11.35,2.6,.46),(.28,.50,.76),grey,front,.018)
    b.pipe('Cable de boitier',[(-11.2,2.6,.6),(-11.4,2.6,.05),(-11.9,2.3,.02),(-12.3,2.5,.02)],.018,rust,front,1)
    sc['pa_gas_dressing']=True
    return {'library':str(library),'source_meshes':report,'instances':len(instances),'unique_triangles':sum(x['triangles'] for x in report),'roofs':roofs,'placement':'Weighted to edges and corners, clear main entrance, independent movable parents, shared mesh and UV atlas.'}
