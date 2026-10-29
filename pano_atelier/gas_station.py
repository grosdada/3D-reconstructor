"""Reference-directed abandoned filling station, exterior only.

Dimensions are artistic estimates; true modules, openings and movable props.
Procedural substrates remain independent of optional GPT albedo projections.
"""
import bpy,math,random,json
from mathutils import Vector
from .modular_scene import Builder,material,camera
from .city_scene import Batch
from .station_procedural import node,feed,math as smath,noise,mapped,mix
from .city_optimize import freeze_coordinates

def weather(name,color,metal=0,rough=.72,peeling=.28):
    m=material(name,color,rough,metal);t=m.node_tree;bs=t.nodes.get('Principled BSDF')
    tc=node(t,'ShaderNodeTexCoord','Coordonnees locales metres');co=tc.outputs['Object']
    n=noise(t,'Nuances lentes',co,.9,3);base=mix(t,'Nuances de peinture',mapped(t,'Nuance moderee',n,0,1,0,.16),(*color,1),(*(c*.60 for c in color),1))
    v=node(t,'ShaderNodeVectorMath','Ruissellement vertical');v.operation='MULTIPLY';feed(t,v.inputs[0],co);v.inputs[1].default_value=(6,6,.16)
    streak=noise(t,'Coulees et condensation',v.outputs[0],1.5,3);dirt=mapped(t,'Depots de pluie',streak,.53,.78,0,.54)
    base=mix(t,'Traces sombres',dirt,base,(.038,.046,.044,1))
    chips=noise(t,'Peinture eclatee',co,5.5,3);mask=mapped(t,'Ecailles discontinues',chips,.63,.77,0,peeling)
    base=mix(t,'Fond de peinture expose',mask,base,(.105,.095,.073,1));feed(t,bs.inputs['Base Color'],base)
    fine=noise(t,'Grain du support',co,160,2);feed(t,bs.inputs['Roughness'],mapped(t,'Rugosite locale',fine,0,1,max(.18,rough-.12),min(1,rough+.13)))
    bump=node(t,'ShaderNodeBump','Relief de peinture');bump.inputs['Distance'].default_value=.0018;bump.inputs['Strength'].default_value=.4
    feed(t,bump.inputs['Height'],smath(t,'ADD',smath(t,'MULTIPLY',fine,.18),mask));feed(t,bs.inputs['Normal'],bump.outputs[0]);m['pa_procedural']=True;return m

def build(scene):
    if any(o.type=='MESH' for o in scene.objects):raise ValueError('Construire dans une scene vide.')
    b=Builder(scene,'STATION · exterieur');rng=random.Random(35027);roots=[]
    whole=b.root('STATION · ensemble')
    def root(name,loc=(0,0,0)):
        o=b.root('STATION · '+name,loc,whole);o['pa_module']=True;roots.append(o);return o
    white=weather('STATION · enduit ivoire ancien',(.53,.55,.49),peeling=.8)
    blue=weather('STATION · tole bleu desature',(.055,.14,.19),metal=.15,rough=.6,peeling=.35)
    grey=weather('STATION · acier peint gris',(.18,.22,.22),metal=.55,rough=.54,peeling=.4)
    rust=weather('STATION · acier oxyde',(.115,.058,.027),metal=.55,rough=.77,peeling=.5)
    concrete=weather('STATION · beton de structure',(.23,.25,.235),peeling=.35)
    black=weather('STATION · caoutchouc ancien',(.012,.015,.014),rough=.81,peeling=.03)
    red=weather('STATION · lettres rouges passees',(.21,.041,.034),rough=.68,peeling=.30)
    yellow=weather('STATION · liseres ocre pale',(.36,.28,.09),rough=.68,peeling=.2)
    dark=material('STATION · obscurite des ouvertures',(.007,.010,.012),.94)
    glass=material('STATION · vitrage poussiereux',(.055,.10,.115),.28,.08);glass.node_tree.nodes['Principled BSDF'].inputs['Transmission Weight'].default_value=.30
    mats={'white':white,'blue':blue,'grey':grey,'rust':rust,'concrete':concrete,'black':black,'red':red,'yellow':yellow,'dark':dark,'glass':glass}
    def box(name,loc,size,mat,p,bevel=.018,project=False):
        o=b.box(name,loc,size,mat,p,bevel)
        if project:o['pa_city_project']=True;o['pa_albedo_target']=True
        return o
    def batch_finish(batch,p,project=False):
        obs=batch.emit(.006);bpy.context.view_layer.update()
        for o in obs:
            freeze_coordinates(o,p)
            if project:o['pa_city_project']=True;o['pa_albedo_target']=True
        return obs
    # Shell has real door/window gaps. Interior furnishing is intentionally deferred.
    main=root('boutique',(0,3.8,0));w=13.4;d=7.6;h=4.8
    shell=Batch(b,main,'Boutique · murs')
    shell.box((0,d/2,h/2),(w,.32,h),white)
    shell.box((-w/2,0,h/2),(.32,d,h),white)
    # East wall: steel service door and recessed vent in separate wall spans.
    shell.box((w/2,-2.6,h/2),(.32,2.4,h),white);shell.box((w/2,2.35,h/2),(.32,2.9,h),white)
    shell.box((w/2,-.85,3.65),(.32,1.1,2.3),white);shell.box((w/2,.45,h/2),(.32,1.5,h),white)
    # Front broad service windows + entrance, all below canopy.
    for x,ww in [(-5.85,1.7),(-2.65,.38),(2.1,.4),(5.7,2.0)]:shell.box((x,-d/2,h/2),(ww,.36,h),white)
    shell.box((0,-d/2,3.85),(w,.36,1.9),white)
    shell.box((-.25,-d/2,.56),(10.9,.36,1.12),blue)
    batch_finish(shell,main,True)
    box('Boutique · toit',(0,0,h+.1),(w+.5,d+.5,.25),concrete,main,.02,True)
    box('Boutique · reserve sombre',(0,1.6,1.7),(12,.06,3.3),dark,main,0)
    box('Boutique · sol',(0,0,.06),(w,d,.12),concrete,main,.015)
    for x,width in [(-4.1,2.6),(-.3,4.3),(3.5,2.35)]:
        z=2.0
        for xx in (x-width/2,x+width/2):box('Menuiserie verticale',(xx,-3.85,z),(.075,.10,1.70),grey,main,.007)
        for zz in (1.16,2.83):box('Menuiserie horizontale',(x,-3.85,zz),(width,.10,.075),grey,main,.006)
        for j in range(3):
            xx=x-width/2+(j+.5)*width/3;box('Vitre en retrait',(xx,-3.75,z),(width/3-.06,.016,1.58),glass,main,.002)
            if j<2:box('Petit bois',(xx+width/6,-3.84,z),(.035,.09,1.65),grey,main,.002)
    box('Bandeau jaune',(0,-4.005,2.98),(13.2,.045,.10),yellow,main,.002)
    box('Bandeau bleu sous vitrines',(0,-4.01,.85),(12.9,.05,.45),blue,main,.008,True)
    # East doorway; opening through wall, frame and recessed closed leaf.
    door=b.root('STATION · porte technique',(6.72,-.85,0),main);door['pa_module']=True
    for y in (-.6,.6):box('Chambranle technique',(0,y,1.3),(.12,.09,2.6),grey,door,.006)
    box('Linteau technique',(0,0,2.62),(.12,1.28,.1),grey,door,.006)
    box('Porte acier',(0.015,0,1.28),(.045,1.1,2.5),grey,door,.009,True)
    box('Poignee porte',(.065,-.4,1.2),(.08,.035,.18),rust,door,.008)
    # Left attached service annex, visibly lower and more damaged.
    annex=root('annexe technique',(-8.9,-.5,0));aw=4.4;ad=8.6;ah=4.05
    walls=Batch(b,annex,'Annexe · enduit')
    walls.box((-aw/2,0,ah/2),(.3,ad,ah),white);walls.box((aw/2,0,ah/2),(.3,ad,ah),white);walls.box((0,ad/2,ah/2),(aw,.3,ah),white)
    for x,ww in [(-1.65,1.1),(.2,.8),(1.8,.8)]:walls.box((x,-ad/2,ah/2),(ww,.32,ah),white)
    walls.box((-.7,-ad/2,3.35),(1.2,.32,1.4),white);walls.box((1.05,-ad/2,3.4),(.85,.32,1.3),white)
    walls.box((1.05,-ad/2,.6),(.85,.32,1.2),white);batch_finish(walls,annex,True)
    box('Annexe · toit',(0,0,ah+.06),(aw+.3,ad+.3,.22),concrete,annex,.025,True)
    for x,y,sz in [(0,-4.4,(4.5,.2,.48)),(-2.25,0,(.2,8.8,.43)),(2.25,0,(.2,8.8,.34))]:box('Acrotere ebreche',(x,y,4.35),sz,white,annex,.025,True)
    box('Annexe · fond porte',(-.65,-4.05,1.35),(1.05,.07,2.65),dark,annex,.001)
    box('Annexe · porte condamnee',(-.65,-4.23,1.3),(.95,.06,2.5),rust,annex,.009,True)
    box('Annexe · fenetre sombre',(1.05,-4.18,2.02),(.78,.03,1.55),dark,annex,.002)
    for x in (.64,1.46):box('Cadre annexe',(x,-4.30,2.02),(.06,.09,1.63),grey,annex,.005)
    # Roof canopy: independent structural supports, broken edge reveals the steel grid.
    canopy=root('auvent et charpente',(0,-4.6,0));cw=14.7;cd=8.8;roofz=5.25
    structure=Batch(b,canopy,'Charpente apparente')
    for x in (-6.7,-3.5,0,3.5,6.7):
        structure.box((x,0,4.96),(.12,cd,.22),rust)
        for z in (4.84,5.08):structure.box((x,0,z),(.27,cd,.045),grey)
    for y in (-4.2,-1.7,.8,3.3):structure.box((0,y,5.02),(cw,.12,.20),rust)
    batch_finish(structure,canopy)
    sheets=Batch(b,canopy,'Tole de couverture et nervures')
    for j in range(33):
        x=-7.1+j*.44
        length=cd-1.5 if j<5 else cd
        yy=.75 if j<5 else 0
        sheets.box((x,yy,roofz),(.435,length,.045),grey)
        sheets.box((x-.20,yy,roofz+.028),(.035,length,.055),grey)
    batch_finish(sheets,canopy)
    for x in (-cw/2,cw/2):box('Auvent · fascia laterale',(x,0,5.45),(.15,cd,.93),blue,canopy,.025,True)
    box('Auvent · fascia avant',(0,-cd/2,5.45),(cw,.17,.93),blue,canopy,.025,True)
    box('Auvent · rive arriere',(0,cd/2,5.45),(cw,.17,.93),blue,canopy,.025,True)
    # Vertical seams remain actual geometry, not generated lines.
    joints=Batch(b,canopy,'Joints du bandeau')
    for x in range(-6,7,2):joints.box((x,-cd/2-.091,5.45),(.015,.012,.90),grey)
    batch_finish(joints,canopy)
    for x,y in [(-5.2,-7),(5.65,-7),(-5.2,-.6),(5.65,-.6)]:
        col=root('pilier',(x,y,0));box('Socle pilier',(0,0,.12),(.94,.94,.24),concrete,col,.06)
        box('Pilier beton',(0,0,2.6),(.58,.58,4.98),white,col,.025,True)
        box('Peinture bleue basse',(0,-.002,.56),(.60,.60,.85),blue,col,.012,True)
        for z in (1.3,3.4):box('Bride metallique',(.30,0,z),(.035,.63,.08),rust,col,.004)
    # Movable sign with genuine raised lettering, clear interpretation of the reference.
    sign=root('enseigne',(1.1,-9.12,5.65));box('Caisson enseigne',(0,0,0),(7.8,.22,1.16),white,sign,.035,True)
    for x in (-3.88,3.88):box('Cadre enseigne',(x,-.13,0),(.035,.035,1.14),rust,sign,.003)
    for z in (-.56,.56):box('Cadre enseigne',(0,-.13,z),(7.8,.035,.035),rust,sign,.003)
    font=bpy.data.curves.new('Lettres de l enseigne','FONT');font.body='plecienda TV';font.align_x='CENTER';font.align_y='CENTER';font.size=.84;font.extrude=.014;font.bevel_depth=.003
    text=bpy.data.objects.new('STATION · lettres en relief',font);b.collection.objects.link(text);text.parent=sign;text.location=(0,-.14,0);text.rotation_euler=(math.pi/2,0,0);font.materials.append(red)
    bpy.context.view_layer.update()
    if text.dimensions.x>7.2:text.scale.x*=7.2/text.dimensions.x
    logo=root('totem sur enseigne',(1.6,-8.8,7.08));box('Embleme ivoire',(0,0,0),(.93,.30,1.42),white,logo,.16,True)
    box('Embleme ligne rouge',(0,-.17,.35),(.76,.035,.16),red,logo,.02);box('Embleme ligne ocre',(0,-.17,.05),(.76,.035,.12),yellow,logo,.02)
    # Three old dispensers; one front cover is genuinely missing.
    for k,(x,y) in enumerate([(-2.6,-4.0),(2.0,-4.2),(5.0,-1.7)]):
        p=root('pompe %02d'%(k+1),(x,y,0));p['pa_gas_pump']=True
        box('Ilot de pompe',(0,0,.10),(1.35,1.0,.20),concrete,p,.10)
        box('Pompe · caisse',(0,0,.73),(.73,.56,1.16),white if k!=1 else blue,p,.045,True)
        box('Pompe · tete',(0,0,1.64),(.91,.62,.64),grey,p,.035,True)
        for side in (-1,1):
            box('Compteur noir',(0,side*.319,1.73),(.72,.018,.29),dark,p,.01)
            for zz in (1.64,1.81):
                for xx in (-.23,-.11,.01,.13,.25):box('Rouleaux de compteur',(xx,side*.333,zz),(.065,.008,.055),white,p,.001)
            box('Etiquette carburant',(0,side*.324,1.46),(.36,.016,.07),yellow,p,.002)
        box('Bandeau pompe',(0,-.292,1.16),(.64,.018,.15),red if k==0 else yellow,p,.002)
        if k==1:
            box('Trappe ouverte · fond sombre',(0,-.296,.66),(.53,.015,.76),dark,p,.002)
            for xx in (-.19,.0,.19):b.pipe('Mecanique visible',[(xx,-.33,.34),(xx,-.33,.82),(xx+.06,-.34,1.0)],.025,rust,p,1)
            hatch=box('Trappe posee au sol',(.64,-.55,.37),(.6,.045,.75),white,p,.015,True);hatch.rotation_euler=(.25,.15,-.35)
        for side in (-1,1):
            pts=[(side*.49,.10,1.82),(side*.78,.10,1.38),(side*.89,-.02,.45),(side*.71,-.08,.25),(side*.56,-.18,.42),(side*.58,-.20,1.18)]
            b.pipe('Flexible pompe',pts,.026,black,p,2)
            nozzle=box('Pistolet', (side*.57,-.20,1.23),(.08,.07,.30),grey,p,.012);nozzle.rotation_euler.y=side*.28
    # Tall external maintenance ladder, interpreted as a displaced service stair.
    ladder=root('echelle de maintenance',(8.6,-6.1,.06));ladder.rotation_euler.x=math.radians(-29)
    steel=Batch(b,ladder,'Echelle · montants et barreaux')
    for x in (-.52,.52):
        steel.box((x,0,5.2),(.09,.16,10.4),grey)
        steel.box((x,.38,5.4),(.055,.055,10.5),rust)
    for j in range(33):
        z=.20+j*.31;steel.box((0,0,z),(1.11,.17,.035),grey)
        if j%4==0:
            for x in (-.52,.52):steel.box((x,.19,z),(.045,.42,.045),rust)
    batch_finish(steel,ladder)
    for z in (3,6,9):b.pipe('Cable de maintien',[(-.5,.4,z),(-.5,.65,z+.3),(.5,.65,z+.3),(.5,.4,z)],.014,rust,ladder,1)
    # Exterior service equipment and rainwater routing.
    tech=root('equipements arriere',(0,0,0));batch=Batch(b,tech,'Equipements techniques')
    for x in (-5,3.5):
        batch.box((x,6.4,5.06),(1.1,.9,.35),grey)
        for j in range(8):batch.box((x-.45+j*.12,6.4,5.25),(.04,.85,.03),rust)
    batch.box((6.9,5.8,1.6),(.25,.95,1.25),grey)
    for z in (1.2,1.35,1.5,1.65,1.8):batch.box((7.04,5.8,z),(.025,.78,.035),dark)
    batch_finish(batch,tech)
    for x,y in [(-6.8,7.1),(6.8,7.1),(-11.2,3.1)]:b.pipe('Descente pluviale',[(x,y,4.4),(x,y,.45),(x+.18,y,.16)],.065,rust,tech,1)
    for x,y in [(-10.3,2.4),(-9.8,2.5)]:b.pipe('Antenne toiture',[(x,y,4.35),(x+.12,y,6.2)],.014,grey,tech,0)
    # Ground: foreground details have real silhouette, distant terrain stays cheap.
    ground=root('terrain et decombres');asphalt=weather('STATION · asphalte mouille',(.055,.063,.064),rough=.57,peeling=.45)
    box('Terrain continu',(0,0,-.23),(1800,1800,.4),asphalt,ground,0)
    paving=Batch(b,ground,'Dalles fendues du parvis')
    for ix in range(9):
        for iy in range(7):
            if rng.random()<.15:continue
            x=-13+ix*3;y=-14+iy*3;z=-.069
            paving.box((x,y,z),(2.996,2.996,.08),asphalt)
    batch_finish(paving,ground)
    # Flat irregular water patches; reflective roughness is physical, not painted light.
    water=material('STATION · flaques',(.022,.036,.041),.11,.05);water.node_tree.nodes['Principled BSDF'].inputs['IOR'].default_value=1.333
    puddles=Batch(b,ground,'Flaques')
    for j in range(17):
        x=rng.uniform(-17,17);y=rng.uniform(-18,12);r=rng.uniform(.35,1.4);vs=[(x,y,-.027)]
        for i in range(14):a=i*math.tau/14;rr=r*rng.uniform(.7,1.1);vs.append((x+rr*math.cos(a),y+rr*.5*math.sin(a),-.027))
        b.mesh('Flaque irreguliere',vs,[(0,i+1,(i+1)%14+1) for i in range(14)],water,ground)
    debris=Batch(b,ground,'Gravats regroupes')
    for j in range(230):
        if j<120:x=rng.uniform(-12,9);y=rng.choice([-5.0,7.8])+rng.uniform(-.45,.45)
        else:x=rng.uniform(-18,18);y=rng.uniform(-17,13)
        sx=rng.uniform(.025,.19);sy=rng.uniform(.025,.14);sz=rng.uniform(.015,.10)
        debris.box((x,y,-.025+sz/2),(sx,sy,sz),concrete if j%4 else white)
    batch_finish(debris,ground)
    for j in range(27):
        x=rng.uniform(-15,16);y=rng.uniform(-15,10)
        pts=[(x,y,-.024)]
        for k in range(rng.randint(3,6)):x+=rng.uniform(-.45,.45);y+=rng.uniform(.15,.55);pts.append((x,y,-.024))
        b.pipe('Fissure du sol',pts,rng.uniform(.0015,.0035),dark,ground,0)
    # Sparse dead weeds, grouped into one curve object to keep the scene light.
    weeds=bpy.data.curves.new('Herbes seches','CURVE');weeds.dimensions='3D';weeds.bevel_depth=.004;weeds.bevel_resolution=0
    for j in range(150):
        x=rng.uniform(-16,15);y=rng.choice([-5.2,8.2,12])+rng.uniform(-.35,.35);h=rng.uniform(.12,.5)
        s=weeds.splines.new('POLY');s.points.add(2)
        for p,v in zip(s.points,[(x,y,.04),(x+.03,y+.04,h*.6),(x+.11,y+.08,h)]):p.co=(*v,1)
    o=bpy.data.objects.new('STATION · vegetaux secs',weeds);b.collection.objects.link(o);o.parent=ground;weeds.materials.append(rust)
    # Far silhouettes fade into fog; deliberately no detailed interior.
    distant=root('silhouettes lointaines');sil=Batch(b,distant,'Volumes de fond')
    for x,y,w,d,h in [(-105,142,18,13,5),(92,155,26,15,6),(12,171,30,12,4),(-82,175,20,17,6)]:sil.box((x,y,h/2),(w,d,h),concrete)
    batch_finish(sil,distant)
    for x,y in [(-28,24),(32,33),(-38,-10)]:
        b.cylinder('Poteau lointain',(x,y,4.5),.09,9,grey,distant,vertices=8)
        box('Traverse poteau',(x,y,8.3),(2.1,.10,.1),grey,distant,.002)
    # Cold overcast. Large soft source gives a legible sky-facing roof and dark soffit.
    world=bpy.data.worlds.new('STATION · ciel bleu gris');world.use_nodes=True;world.node_tree.nodes['Background'].inputs['Color'].default_value=(.48,.65,.73,1);world.node_tree.nodes['Background'].inputs['Strength'].default_value=.75;scene.world=world
    ld=bpy.data.lights.new('Ciel diffus','AREA');lo=bpy.data.objects.new('STATION · ciel diffus',ld);b.collection.objects.link(lo);lo.location=(-10,-4,24);ld.energy=10000;ld.shape='DISK';ld.size=24;lo.rotation_euler=(Vector((0,0,0))-lo.location).to_track_quat('-Z','Y').to_euler()
    fill=bpy.data.lights.new('Rebond ciel frontal','AREA');fo=bpy.data.objects.new('STATION · lumiere diffuse frontale',fill);b.collection.objects.link(fo);fo.location=(0,-19,8);fill.energy=1700;fill.shape='DISK';fill.size=18;fo.rotation_euler=(Vector((0,-1,2))-fo.location).to_track_quat('-Z','Y').to_euler()
    fogmat=bpy.data.materials.new('STATION · brouillard froid');fogmat.use_nodes=True;nt=fogmat.node_tree;nt.nodes.clear();v=node(nt,'ShaderNodeVolumePrincipled','Brume froide');v.inputs['Density'].default_value=.009;v.inputs['Color'].default_value=(.60,.74,.79,1);v.inputs['Anisotropy'].default_value=.15;v.inputs['Emission Color'].default_value=(.25,.40,.47,1);v.inputs['Emission Strength'].default_value=.0048;gp=node(nt,'ShaderNodeNewGeometry','Distance au decor');xy=node(nt,'ShaderNodeVectorMath','Distance horizontale');xy.operation='MULTIPLY';xy.inputs[1].default_value=(1,1,0);nt.links.new(gp.outputs['Position'],xy.inputs[0]);length=node(nt,'ShaderNodeVectorMath','Rayon');length.operation='LENGTH';nt.links.new(xy.outputs[0],length.inputs[0]);density=node(nt,'ShaderNodeMapRange','Brume progressive');density.inputs['From Min'].default_value=23;density.inputs['From Max'].default_value=100;density.inputs['To Min'].default_value=.0015;density.inputs['To Max'].default_value=.035;nt.links.new(length.outputs['Value'],density.inputs[0]);nt.links.new(density.outputs[0],v.inputs['Density']);em=node(nt,'ShaderNodeMath','Diffusion lointaine');em.operation='MULTIPLY';em.inputs[1].default_value=.22;nt.links.new(density.outputs[0],em.inputs[0]);nt.links.new(em.outputs[0],v.inputs['Emission Strength']);out=node(nt,'ShaderNodeOutputMaterial','Sortie');nt.links.new(v.outputs[0],out.inputs['Volume'])
    f=box('STATION · atmosphere',(0,0,70),(700,700,200),fogmat,None,0);f['pa_noncolliding']=True;f.display_type='WIRE';f.hide_select=True
    cams=[]
    for name,loc,target,lens in [('CAM_01 · reference avant',(-18,-24,3.1),(-.5,-.7,3),33),('CAM_02 · sous auvent',(-.4,-14.6,1.65),(-.5,-1,2.45),29),('CAM_03 · cote technique',(20,-17,4.0),(1.0,0,3.15),35),('CAM_04 · toiture',(21,-23,22),(0,-.3,1.8),40),('CAM_05 · arriere',(18,19,3.0),(0,2,2.6),36),('CAM_06 · controle intermediaire',(-10,-21,2.2),(0,-2,2.7),36)]:
        c=camera(b,name,loc,target,lens,1800,1200);c.data.clip_end=1200;cams.append(c)
    scene.camera=cams[0];scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True;scene.render.resolution_x=1800;scene.render.resolution_y=1200;scene.render.resolution_percentage=100
    scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast';scene.view_settings.exposure=.4
    scene['pa_gas_station']=True;scene['pa_reference_interpretation']='Exterior-only interpretation: main shop, lower annex, blue damaged canopy, three old pumps, leaning maintenance ladder, raised fictional sign, damp forecourt and cold mist. Dimensions estimated. Interior deferred.'
    bpy.context.view_layer.update()
    return {'modules':[r.name for r in roots],'cameras':[c.name for c in cams],'objects':len(scene.objects),'projection_targets':sum(bool(o.get('pa_city_project')) for o in scene.objects),'interpretation':scene['pa_reference_interpretation']}
