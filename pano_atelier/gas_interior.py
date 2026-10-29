"""Reference-directed corridor, service room and modest abandoned shop."""
import bpy,math
from mathutils import Vector
from .modular_scene import Builder,material,camera
from .city_scene import Batch
from .gas_station import weather
from .gas_weather import coordinates

def build(sc,white,blue):
    if sc.get('pa_gas_interior'):raise ValueError('Interieur deja construit')
    b=Builder(sc,'STATION · interieur amenage');whole=bpy.data.objects.get('STATION · ensemble')
    root=b.root('STATION · interieur',(0,0,0),whole);root['pa_module']=True
    roots=[]
    def module(name,loc=(0,0,0)):
        p=b.root('INTERIEUR · '+name,loc,root);p['pa_module']=True;roots.append(p);return p
    # Independent procedural materials, with per-object metric height attributes.
    cream=white.copy();cream.name='INTERIEUR · peinture blanc casse';cream['pa_gas_procedural_paint']=True
    blue=blue.copy();blue.name='INTERIEUR · peinture bleue usee';blue['pa_gas_procedural_paint']=True
    for m in (cream,blue):
        nt=m.node_tree;gr=nt.nodes.get('Peinture procedurale reglable')
        gr.inputs['Ecaillage'].default_value=.28;gr.inputs['Crasse'].default_value=.42;gr.inputs['Echelle'].default_value=1.3
        for name,label in [('PA_WeatherMeters','Metres lies au module'),('PA_WeatherBands','Pied et rive du panneau')]:
            a=nt.nodes.new('ShaderNodeAttribute');a.attribute_name=name;nt.links.new(a.outputs['Vector'],gr.inputs[0 if name.endswith('Meters') else 1])
    brown=weather('INTERIEUR · huisserie brun oxyde',(.10,.065,.045),rough=.68,peeling=.45)
    metal=weather('INTERIEUR · metal mat ancien',(.095,.12,.12),metal=.35,rough=.66)
    wood=weather('INTERIEUR · stratifie gris brun',(.21,.20,.16),rough=.76,peeling=.20)
    dark=material('INTERIEUR · caoutchouc et cadrans',(.013,.016,.014),.75)
    glass=material('INTERIEUR · vitre ancienne',(.83,.88,.88),.14);pbs=glass.node_tree.nodes.get('Principled BSDF');pbs.inputs['Transmission Weight'].default_value=1
    oldglass=bpy.data.materials.get('STATION · vitrage poussiereux')
    if oldglass:
        bs=oldglass.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.74,.82,.82,1);bs.inputs['Metallic'].default_value=0;bs.inputs['Transmission Weight'].default_value=1;bs.inputs['Roughness'].default_value=.045
    ceiling=cream.copy();ceiling.name='INTERIEUR · plafond peinture fatiguee';gr=ceiling.node_tree.nodes.get('Peinture procedurale reglable');gr.inputs['Ecaillage'].default_value=.12;gr.inputs['Crasse'].default_value=.09
    floor=weather('INTERIEUR · sol ciment patine',(.13,.135,.12),rough=.58,peeling=.35)
    # Existing placeholders are retained in the file but excluded from the V2 scene.
    hidden=[]
    for o in sc.objects:
        if o.name.startswith(('Boutique · reserve sombre','Annexe · fond porte','Annexe · porte condamnee','Annexe · fenetre sombre')):
            o.hide_render=True;o.hide_set(True);o['pa_replaced_by_interior']=True;hidden.append(o.name)
    # Split only the relevant box primitives. A Boolean on overlapping wall boxes
    # can silently delete unrelated facade spans; explicit spans are deterministic.
    affected=[]
    for o in list(sc.objects):
        if o.type!='MESH' or not o.name.startswith(('Boutique · murs','Annexe · enduit')):continue
        if not any(s.material and s.material.name.startswith('STATION · enduit ivoire') for s in o.material_slots):continue
        main=o.name.startswith('Boutique');vs=[];fs=[];mat=o.material_slots[0].material
        def addbox(loc,size):
            n=len(vs);x,y,z=(q/2 for q in size);a,c,d=loc
            vs.extend([(a+xx,c+yy,d+zz) for xx,yy,zz in [(-x,-y,-z),(x,-y,-z),(x,y,-z),(-x,y,-z),(-x,-y,z),(x,-y,z),(x,y,z),(-x,y,z)]])
            fs.extend([tuple(n+j for j in f) for f in [(3,2,1,0),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)]])
        verts=list(o.data.vertices)
        for j in range(0,len(verts),8):
            vv=[v.co for v in verts[j:j+8]];lo=Vector(tuple(min(v[k] for v in vv) for k in range(3)));hi=Vector(tuple(max(v[k] for v in vv) for k in range(3)));c=(lo+hi)/2;dim=hi-lo
            if dim.x<.4 and abs(c.x-(-6.7 if main else 2.2))<.02:
                ga,gb=(-2.68,-1.32) if main else (1.62,2.98)
                for ya,yb in [(lo.y,ga),(gb,hi.y)]:addbox((c.x,(ya+yb)/2,c.z),(dim.x,yb-ya,dim.z))
                addbox((c.x,(ga+gb)/2,(2.78+hi.z)/2),(dim.x,gb-ga,hi.z-2.78))
            elif not main and dim.y<.4 and abs(c.y-4.3)<.02:
                for xa,xb in [(lo.x,-1.7),(-.6,hi.x)]:addbox(((xa+xb)/2,c.y,c.z),(xb-xa,dim.y,dim.z))
                addbox((-1.15,c.y,.6),(1.1,dim.y,1.2));addbox((-1.15,c.y,(2.4+hi.z)/2),(1.1,dim.y,hi.z-2.4))
            else:addbox(c,dim)
        me=bpy.data.meshes.new(o.name+' · passages reconstruits');me.from_pydata(vs,[],fs);me.update();me.materials.append(mat);o.data=me;o.material_slots[0].link='OBJECT';o.material_slots[0].material=mat
        for suffix in ('','_02','_03'):
            a=me.attributes.new('PA_CityRest'+suffix,'FLOAT_VECTOR','POINT');a.data.foreach_set('vector',[q for v in me.vertices for q in o.matrix_world@v.co]);n=me.attributes.new('PA_CityNormal'+suffix,'FLOAT_VECTOR','CORNER');nm=o.matrix_world.inverted().transposed().to_3x3()
            for face in me.polygons:
                normal=(nm@face.normal).normalized()
                for li in face.loop_indices:n.data[li].vector=normal
        coordinates(o);affected.append(o.name)
    annex=module('couloir et cloisons annexe');batch=Batch(b,annex,'Cloisons du couloir')
    # Clear corridor at x -10.9..-9.1; two rooms lie to its right.
    for lo,hi in [(-4.55,-2.23),(-.97,1.35),(2.65,3.60)]:batch.box((-9.05,(lo+hi)/2,1.55),(.13,hi-lo,2.9),cream)
    for y in (-1.6,2.0):batch.box((-9.05,y,2.76),(.13,1.26,.47),cream)
    batch.box((-7.88,.50,1.55),(2.20,.12,2.9),cream)
    batch.box((-8.9,-.5,.07),(4.10,8.2,.14),floor)
    batch.box((-8.9,-.5,3.02),(4.10,8.2,.12),ceiling)
    batch.box((-10.93,-.5,1.55),(.025,8.1,2.9),cream)
    # Corridor end has a recessed open doorway, not a painted door silhouette.
    for x,w in [(-10.70,.50),(-9.30,.35)]:batch.box((x,2.75,1.55),(w,.13,2.9),cream)
    batch.box((-10.0,2.75,2.76),(1.0,.13,.47),cream)
    batch.emit(.006)
    for x in (-10.91,-9.13):b.box('Plinthe couloir',(x,-.50,.23),(.035,8.1,.19),brown,annex,.004)
    def door(name,loc,width=.98,height=2.36,yaw=0,opening=0,glazed=False):
        p=module(name,loc);p.rotation_euler.z=yaw
        for x in (-width/2-.045,width/2+.045):b.box('Huisserie porte',(x,0,height/2),(.085,.17,height+.1),brown,p,.008)
        b.box('Linteau de porte',(0,0,height+.025),(width+.18,.17,.085),brown,p,.008)
        hinge=b.root('INTERIEUR · gond '+name,(-width/2,0,0),p);hinge.rotation_euler.z=opening
        if glazed:
            b.box('Porte panneau bas',(width/2,0,.64),(width,.055,1.25),cream,hinge,.01)
            for x in (.04,width-.04):b.box('Montant porte vitree',(x,0,1.79),(.08,.055,1.1),cream,hinge,.006)
            for z in (1.29,height-.04):b.box('Traverse porte vitree',(width/2,0,z),(width,.055,.08),cream,hinge,.006)
            b.box('Vitre porte en retrait',(width/2,.012,1.8),(width-.16,.012,.92),glass,hinge,.002)
        else:
            b.box('Vantail',(width/2,0,height/2),(width,.055,height),cream,hinge,.009)
            for z in (.63,1.75):b.box('Panneau rapporte porte',(width/2,-.034,z),(width-.20,.015,.80),blue if name=='porte de service' else cream,hinge,.005)
        b.box('Poignee',(width-.12,-.07,1.02),(.12,.035,.025),metal,hinge,.008)
        for z in (.25,height-.25):b.cylinder('Paumelle',(0,.01,z),.018,.12,metal,hinge,vertices=12)
        return p
    door('entree annexe',(-9.55,-4.67,.14),1.0,2.47,opening=math.radians(-75),glazed=True)
    door('atelier lateral',(-9.05,-1.6,.14),1.16,2.36,yaw=math.pi/2,opening=math.radians(170))
    door('porte de service',(-9.05,2.0,.14),1.16,2.36,yaw=math.pi/2,opening=math.radians(-170),glazed=True)
    door('fond du couloir',(-10.0,2.75,.14),.95,2.36,opening=math.radians(80),glazed=True)
    door('liaison boutique',(-6.7,1.8,.14),1.20,2.48,yaw=math.pi/2,opening=math.radians(-80))
    b.box('Vitre annexe',( -7.85,-4.69,2.02),(.76,.015,1.53),glass,annex,.001)
    b.box('Vitre arriere couloir',(-10.05,3.79,1.80),(1.02,.015,1.12),glass,annex,.002)
    for x in (-10.61,-9.49):b.box('Cadre fenetre arriere',(x,3.63,1.8),(.07,.12,1.28),brown,annex,.006)
    for z in (1.17,2.43):b.box('Cadre fenetre arriere',(-10.05,3.63,z),(1.19,.12,.07),brown,annex,.006)
    # Service room: desk, hanging open cabinet and a narrow floor shelving unit.
    desk=module('etabli atelier',(-7.85,.10,.14));furn=Batch(b,desk,'Etabli et rangement')
    furn.box((0,0,.82),(1.65,.66,.065),wood)
    for x in (-.74,.74):furn.box((x,.03,.40),(.08,.53,.80),cream)
    furn.box((.36,.0,.68),(.66,.54,.20),cream);furn.box((.36,-.28,.68),(.20,.025,.025),brown)
    for x in (-.81,.81):furn.box((x,.18,1.80),(.06,.32,.88),brown)
    for z in (1.36,1.78,2.24):furn.box((0,.18,z),(1.68,.33,.045),wood)
    furn.box((0,.34,1.80),(1.68,.025,.88),cream);furn.emit(.008)
    shelf=module('etagere haute',(-6.98,-2.75,.14));sf=Batch(b,shelf,'Rayonnage atelier')
    for y in (-.65,.65):sf.box((0,y,1.07),(.40,.055,2.14),wood)
    for z in (.08,.51,.95,1.40,1.86,2.14):sf.box((0,0,z),(.42,1.35,.045),wood)
    sf.emit(.005)
    # Main shop: suspended ceiling, rear storage partition and free circulation.
    shop=module('boutique et arriere boutique');ba=Batch(b,shop,'Cloisons boutique')
    ba.box((0,3.8,3.35),(13.0,7.20,.12),ceiling)
    for x,w in [(-1.9,9.2),(5.75,1.6)]:ba.box((x,4.8,1.72),(w,.12,3.2),cream)
    ba.box((3.55,4.8,2.98),(1.5,.12,.67),cream);ba.emit(.007)
    door('reserve', (3.55,4.8,.14),1.35,2.48,opening=math.radians(65))
    # Floor tile joints in real shallow strips, batched as one mesh.
    joints=Batch(b,shop,'Joints de sol boutique')
    for i in range(-6,7):joints.box((i,3.8,.125),(.006,7.0,.002),brown)
    for i in range(1,8):joints.box((0,i,.125),(12.9,.006,.002),brown)
    joints.emit(0)
    counter=module('comptoir boutique',(.8,2.8,.14));co=Batch(b,counter,'Comptoir')
    co.box((0,0,.47),(3.6,.68,.94),blue);co.box((0,0,.98),(3.76,.84,.075),wood)
    for x in (-1.55,-.55,.55,1.55):co.box((x,-.35,.47),(.035,.025,.78),brown)
    co.box((1.43,.78,.47),(.72,1.3,.94),blue);co.box((1.43,.78,.98),(.86,1.4,.075),wood);co.emit(.008)
    b.box('Caisse ancienne',(-.95,0,1.20),(.42,.42,.36),cream,counter,.035)
    b.box('Afficheur caisse',(-.95,-.22,1.27),(.31,.018,.10),dark,counter,.005)
    for i in range(6):b.box('Touches caisse',(-1.08+i*.05,-.24,1.10),(.03,.025,.025),dark,counter,.003)
    shelves=module('rayonnages boutique',(-4.2,4.50,.14));bb=Batch(b,shelves,'Rayonnages muraux')
    for x in (-1.7,-.57,.57,1.7):bb.box((x,0,1.12),(.045,.46,2.24),metal)
    for z in (.20,.72,1.24,1.76,2.25):bb.box((0,0,z),(3.45,.48,.035),wood)
    bb.emit(.004)
    carton=weather('INTERIEUR · cartons detrempes',(.16,.12,.075),rough=.9,peeling=.1)
    for x,z,ww in [(-1.2,.93,.46),(.1,1.47,.35),(1.15,.39,.6),(-.4,.39,.44)]:b.box('Carton abandonne',(x,-.04,z),(ww,.32,.35),carton,shelves,.015)
    # Small visible practical lights, warm but restrained. Cold daylight comes through openings.
    lum=material('INTERIEUR · verre applique chaud',(.62,.38,.16),.35,emission=2)
    lights=module('appliques et gaines')
    for i,y in enumerate((-3.3,-.1,2.15)):
        b.box('Socle applique',(-10.85,y,2.28),(.08,.16,.25),brown,lights,.025)
        b.cylinder('Globe applique',(-10.75,y,2.28),.075,.22,lum,lights,vertices=16)
        for a in range(4):
            yy=y+math.sin(a*math.pi/2)*.08;xx=-10.75+math.cos(a*math.pi/2)*.08
            b.pipe('Cage applique',[(xx,yy,2.16),(xx,yy,2.40)],.005,metal,lights,0)
        ld=bpy.data.lights.new('Applique couloir','POINT');ld.energy=4 if i!=1 else 3;ld.color=(1,.84,.65);ld.shadow_soft_size=.10;lo=bpy.data.objects.new('INTERIEUR · applique',ld);b.collection.objects.link(lo);lo.parent=lights;lo.location=(-10.63,y,2.28)
    for x in (-10.82,-9.15):b.pipe('Gaine electrique',[(x,-4.2,2.75),(x,3.4,2.75)],.013,brown,lights,1)
    # Diffuse sky contribution at the front windows; remains an editable light.
    for name,loc,target,power,size in [('Jour boutique',(0,.55,2.3),(0,3,1.4),180,4),('Jour annexe',(-7.85,-4.42,2.1),(-7.8,-1,1.2),45,1.0),('Jour fond couloir',(-10.05,3.49,1.9),(-10,-2,1.4),45,1.0),('Rebond boutique',(0,2,3.18),(0,2,0),85,5),('Jour entree couloir',(-9.8,-4.3,2.25),(-10,1,1.3),65,1.1)]:
        ld=bpy.data.lights.new(name,'AREA');ld.energy=power;ld.color=(.57,.75,1);ld.shape='DISK';ld.size=size;lo=bpy.data.objects.new('INTERIEUR · '+name,ld);b.collection.objects.link(lo);lo.parent=lights;lo.location=loc;lo.rotation_euler=(Vector(target)-Vector(loc)).to_track_quat('-Z','Y').to_euler()
        lo.visible_glossy=False;lo.visible_transmission=False;lo.visible_camera=False;ld.specular_factor=0
    for name,loc,target,lens in [('CAM_07 · couloir',(-9.95,-3.95,1.63),(-10.0,2.7,1.53),22),('CAM_08 · atelier',(-7.75,-3.85,1.62),(-7.9,.10,1.40),20),('CAM_09 · boutique',(-5.8,4.1,1.72),(1.3,1.6,1.5),25),('CAM_10 · vers auvent',(-10.4,-3.95,1.65),(-3.6,-9,2.8),22)]:
        c=camera(b,name,loc,target,lens,1800,1200);c.data.clip_end=1200
    bpy.context.view_layer.update()
    for o in b.collection.objects:
        if o.type=='MESH' and any(s.material and s.material.get('pa_gas_procedural_paint') for s in o.material_slots):coordinates(o)
    sc['pa_gas_interior']=True
    return {'modules':[p.name for p in roots],'placeholders_hidden':hidden,'shells_opened':affected,'layout':'Annex corridor, two service rooms, connection to front shop and rear storeroom; estimated from reference interiors.'}
