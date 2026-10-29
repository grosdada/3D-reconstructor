"""Reference-guided habitat corridor recipe. Explicit reconstruction, not automatic inference."""
import math,json
from pathlib import Path
import bpy
from mathutils import Vector
from .modular_scene import Builder,material,camera

PROJECTION_SPECS=[('avant',(0,-1.2,1.6),(0,1,0)),('droite',(0,-1.0,1.6),(1,0,0)),('arriere',(0,-.6,1.6),(0,-1,0)),('gauche',(0,-1.0,1.6),(-1,0,0)),('plafond',(0,-1,1.55),(0,0,1)),('sol',(0,-1,2.2),(0,0,-1)),('couloir',(0,4.5,1.6),(0,1,0)),('retour',(0,-6.2,1.6),(0,-1,0))]

def build(scene,asset_root,output,reference=''):
    if scene.get('pa_station_collection'):raise ValueError('Un decor station existe deja dans cette scene; utiliser une nouvelle scene pour une autre construction.')
    b=Builder(scene,'STATION · sas modulaires');top=b.root('STATION · ensemble');out=Path(output);out.mkdir(parents=True,exist_ok=True)
    mats={
      'ivory':material('ST · panneaux ivoire vieilli',(.53,.48,.32),.38),
      'trim':material('ST · sas email blanc chaud',(.73,.73,.63),.29,.12),
      'floor':material('ST · sol resine creme',(.46,.43,.31),.3),
      'walk':material('ST · plaques circulation gris bleu',(.29,.35,.37),.37,.28),
      'metal':material('ST · aluminium brosse',(.46,.49,.48),.27,.83),
      'dark':material('ST · joints anthracite',(.018,.022,.018),.62),
      'green':material('ST · joint vert sombre',(.025,.075,.042),.42),
      'yellow':material('ST · securite jaune',(.83,.57,.022),.33),
      'red':material('ST · boutons rouges',(.48,.025,.014),.32),
      'box':material('ST · coffrets gris',(.36,.4,.39),.4,.15),
      'light':material('ST · diffuseur opalin',(.92,.94,.84),.32,0,3),
      'blue':material('ST · plaques signaletiques bleues',(.018,.045,.10),.55),
    }
    A=asset_root
    cover=b.asset(A,'hatches-and-cover.blend','jro_cover_032',mats['box'])
    circular=b.asset(A,'hatches-and-cover.blend','jro_cover_030',mats['metal'])
    panel=b.asset(A,'SCI-FI-PANEL-VOL-01.blend','Cube.012',mats['trim'])
    wallpanel=b.asset(A,'SCI-FI-PANEL-VOL-01.blend','Cube.003',mats['box'])
    wheel=b.asset(A,'KitBash_control_panel_industrial.blend','handwheel_9',mats['yellow'])
    valve=b.asset(A,'KitBash_control_panel_industrial.blend','valve_8',mats['metal'])
    # Full solid surfaces; thin joints and seams are geometry, not baked silhouettes.
    bay_starts=(-16,-10,-4,2,8,14)
    for bay,y0 in enumerate(bay_starts):
        p=b.root('MODULE %02d · cabine pressurisee'%(bay+1),(0,y0,0),top)
        p['role']='Cabine avec plancher, plafond, cloisons, conduites et accessoires';p['dimensions_m']='4.30 x 6.00 x 3.20'
        b.box('Plancher · support continu',(0,3,-.11),(4.42,6,.10),mats['dark'],p,0)
        b.box('Plafond · enveloppe',(0,3,3.30),(4.42,6,.08),mats['dark'],p,0)
        for side in (-1,1):b.box('Cloison · support continu',(side*2.25,3,1.56),(.08,6,3.52),mats['dark'],p,0)
        # Local room spans y=0..6. Floor subdivision produces readable maintenance joints.
        for i in range(6):
            y=i+.5
            for j,x in enumerate((-1.56,-.52,.52,1.56)):
                b.box('Plancher · panneau', (x,y,-.045),(1.026,.986,.09),mats['floor'],p,.009)
            if i%2==0:
                b.box('Plaque de passage antiderapante',(0,y,.008),(1.32,.76,.016),mats['walk'],p,.015)
            for side in (-1,1):
                b.box('Goulotte · embase',(side*1.98,y,.035),(.20,.99,.07),mats['metal'],p,.004)
                # Horizontal seams alternate broad panels and a lower service strip.
                for z,h in ((.56,.80),(1.63,1.31),(2.45,.30)):
                    b.box('Cloison · panneau demontable',(side*2.17,y,z),(.12,.984,h),mats['ivory'],p,.012)
                # Small actual fasteners, intentionally sparse rather than every switch modelled.
                if i%2==0:
                    for z in (.22,2.58):b.cylinder('Fixation quart de tour',(side*2.101,y-.38,z),.017,.009,mats['metal'],p,(1,0,0),12)
                # Curved ceiling shoulder, segmented lightweight surface with thickness.
                for k in range(8):
                    a=k*math.pi/16;aa=(k+1)*math.pi/16
                    x1=side*(1.60+.55*math.cos(a));z1=2.65+.55*math.sin(a)
                    x2=side*(1.60+.55*math.cos(aa));z2=2.65+.55*math.sin(aa)
                    ob=b.mesh('Voute · panneau courbe',[(x1,i+.009,z1),(x1,i+.991,z1),(x2,i+.991,z2),(x2,i+.009,z2)],[(0,1,2,3)] if side==-1 else [(3,2,1,0)],mats['ivory'],p)
                    sol=ob.modifiers.new('Epaisseur voute','SOLIDIFY');sol.thickness=.045
            # Roof is split around true luminaire opening; no surface covers the luminous panel.
            for side in (-1,1):b.box('Plafond · bande laterale',(side*1.15,y,3.23),(.90,.986,.06),mats['ivory'],p,.007)
            if i%2==0:
                lamp=b.root('LUMINAIRE · cassette',(0,y,3.17),p)
                b.box('Luminaire · cadre',(0,0,.015),(1.43,.89,.085),mats['metal'],lamp,.018)
                lm=mats['light']
                if bay==2:
                    lm=lm.copy();lm.name='ST · opalin cabine de reference';lm.node_tree.nodes.get('Principled BSDF').inputs['Emission Strength'].default_value=.75
                b.box('Luminaire · diffuseur',(0,0,-.034),(1.32,.79,.018),lm,lamp,.012)
                d=bpy.data.lights.new('Tube fluorescent · blanc chaud','AREA');d.energy=48 if bay==2 else 110;d.color=(1,.96,.88);d.shape='RECTANGLE';d.size=1.25;d.size_y=.72
                ob=bpy.data.objects.new(d.name,d);b.collection.objects.link(ob);ob.parent=lamp;ob.location=(0,0,-.07)
                # Vent alongside lamp, actual slots.
                vent=b.root('VENTILATION · grille',(1.23,y,3.185),p)
                b.box('Grille · fond',(0,0,0),(.43,.65,.018),mats['dark'],vent,.008)
                for k in range(10):b.box('Grille · lamelle',(-.18+k*.04,0,-.014),(.018,.60,.025),mats['metal'],vent,.002)
            else:b.box('Plafond · panneau central',(0,y,3.23),(1.39,.986,.06),mats['ivory'],p,.009)
        # Continuous visible pipe runs are below the roof and above floor service covers.
        for side in (-1,1):
            for n in range(3):
                x=side*(1.88+n*.06);z=.11+n*.035
                b.pipe('Faisceau · cables bas',[(x,.06,z),(x,5.94,z)],.014,mats['metal'] if n!=1 else mats['dark'],p)
            for n in range(2):
                x=side*(1.65+n*.15);z=2.87+n*.10
                b.pipe('Conduite · plafond',[(x,.03,z),(x,5.97,z)],.035 if n else .065,mats['metal'],p)
                for y in (.35,2.2,4.3,5.65):
                    b.cylinder('Collier de conduite',(x,y,z),.074 if not n else .045,.055,mats['box'],p,(0,1,0),20)
            for y in (1.6,4.6):
                # Sci-Fi panel pack is oriented X-thin, Y-wide, Z-high.
                b.place_asset('KITBASH · rail technique',panel,(side*2.075,y,2.53),(.08,1.5,.18),p,(0,0,math.pi if side==1 else 0))
        # Main electrical box matches the conspicuous reference box, not a generic greeble.
        side=1 if bay%2==0 else -1
        cabinet=b.root('COFFRET · distribution',(side*2.05,3.4,1.76),p)
        b.box('Coffret · caisson',(-side*.08,0,0),(.22,.88,.65),mats['box'],cabinet,.02)
        b.box('Coffret · porte',(-side*.202,0,0),(.028,.84,.61),mats['box'],cabinet,.012)
        b.cylinder('Coffret · verrou',(-side*.224,.22,-.08),.037,.016,mats['metal'],cabinet,(1,0,0),24)
        b.place_asset('KITBASH · trappe service',cover,(-side*.225,-.23,.12),(.21,.30,.045),cabinet,(0,-side*math.pi/2,0))
        b.pipe('Coffret · alimentation',[(side*1.91,3.42,1.40),(side*2.025,3.42,.32),(side*1.96,3.42,.14)],.018,mats['dark'],p)
        # Additional lower service panel and circular valve cover use actual user-library meshes.
        b.place_asset('KITBASH · panneau service',wallpanel,(-side*2.06,4.1,.68),(.10,.95,.42),p,(0,0,math.pi if side==-1 else 0))
        b.place_asset('KITBASH · trappe circulaire',circular,(-side*2.07,1.65,1.77),(.36,.36,.07),p,(0,side*math.pi/2,0))
        b.place_asset('KITBASH · vanne',valve,(side*1.88,1.10,2.70),(.16,.18,.23),p,(0,0,0))
        b.place_asset('KITBASH · volant',wheel,(side*1.86,1.10,2.83),(.22,.22,.14),p)
        # Yellow/black emergency hose cradles, geometry-stripes, restrained accents.
        for side in (-1,1):
            cradle=b.root('SECURITE · flexible jaune',(side*1.76,5.35,.18),p)
            for j in range(9):
                z=.0;y=(j-4)*.11
                b.cylinder('Flexible · segment',(0,y,z),.075,.11,mats['yellow'] if j%3 else mats['dark'],cradle,(0,1,0),16)
            b.pipe('Flexible · boucle',[(-.04,-.48,0),(-.17,-.55,.04),(-.24,-.47,.06),(-.24,.50,.06),(-.10,.57,.02),(.02,.48,0)],.018,mats['yellow'],cradle)
            for y in (-.4,.4):b.box('Flexible · support',(0,y,-.08),(.24,.06,.06),mats['metal'],cradle,.005)
        # Individual wall rails / frames leave dark inset bays in forward cabins.
        if bay in (3,4):
            for side in (-1,1):
                rack=b.root('BAIE · equipements en retrait',(side*2.035,3.1,1.5),p)
                b.box('Baie · fond',(-side*.005,0,0),(.08,1.18,2.15),mats['dark'],rack,.005)
                for y in (-.62,.62):b.box('Baie · montant',(-side*.13,y,0),(.19,.065,2.22),mats['trim'],rack,.008)
                for z in (-1.09,0,1.09):b.box('Baie · traverse',(-side*.13,0,z),(.19,1.28,.065),mats['trim'],rack,.008)
                for j in range(4):b.box('Baie · tiroir technique',(-side*.07,0,-.78+j*.49),(.14,1.10,.40),mats['box'],rack,.012)
    # Bulkheads on every joint, open to actual neighbouring geometry.
    for index,y in enumerate((-16,-10,-4,2,8,14,20)):
        p=b.root('SAS %02d · anneau et cloison'%(index+1),(0,y,1.60),top);p['role']='Sas circulaire ouvert; passage libre de 2.68 m au diametre'
        N=96;inner=1.55;vs=[]
        for k in range(N):
            a=k*math.tau/N;dx=math.cos(a);dz=math.sin(a);lim=min(2.18/max(abs(dx),1e-8),(1.64 if dz>0 else 1.60)/max(abs(dz),1e-8))
            vs.extend([(inner*dx,0,inner*dz),(lim*dx,0,lim*dz)])
        fs=[(2*i,2*i+1,2*((i+1)%N)+1,2*((i+1)%N)) for i in range(N)]
        ob=b.mesh('Cloison · ouverture circulaire',vs,fs,mats['ivory'],p);sol=ob.modifiers.new('Cloison epaisse','SOLIDIFY');sol.thickness=.12
        for side in (-1,1):
            b.ring('Sas · bride exterieure',(0,side*.085,0),1.43,1.565,.10,mats['box'],p)
            b.ring('Sas · couronne emaillee',(0,side*.145,0),1.35,1.49,.085,mats['trim'],p)
            b.ring('Sas · gorge polie',(0,side*.19,0),1.335,1.36,.025,mats['metal'],p)
            b.ring('Sas · joint vert',(0,side*.205,0),1.305,1.335,.028,mats['green'],p)
            b.ring('Sas · levre interieure',(0,side*.21,0),1.29,1.306,.022,mats['trim'],p)
            for j in range(24):
                a=(j+.5)*math.tau/24;x=1.465*math.cos(a);z=1.465*math.sin(a)
                b.cylinder('Sas · boulon',(x,side*.20,z),.018,.018,mats['metal'],p,(0,1,0),8)
            for lr in (-1,1):
                latch=b.root('Sas · verrou lateral',(lr*1.45,side*.21,.05),p)
                b.box('Verrou · embase',(0,0,0),(.14,.10,.31),mats['yellow'],latch,.012)
                b.box('Verrou · levier',(-lr*.08,side*.08,0),(.24,.055,.075),mats['yellow'],latch,.012)
                b.cylinder('Verrou · axe',(0,side*.06,0),.04,.06,mats['metal'],latch,(0,1,0),16)
        b.ring('Sas · tunnel metallique',(0,0,0),1.29,1.35,.40,mats['trim'],p)
        # Broad threshold ramp joins floor to the circular aperture's lower lip.
        verts=[(-.42,-.88,-1.59),(.42,-.88,-1.59),(.42,-.20,-1.21),(-.42,-.20,-1.21),(-.42,.20,-1.21),(.42,.20,-1.21),(.42,.88,-1.59),(-.42,.88,-1.59)]
        b.mesh('Sas · seuil franchissable',verts,[(0,1,2,3),(3,2,5,4),(4,5,6,7)],mats['walk'],p)
        if y in (-16,20):
            # Clearly invented terminal pressure doors prevent an empty black horizon.
            b.cylinder('Porte terminale fermee',(0,0,0),1.28,.16,mats['trim'],p,(0,1,0),96)
            b.ring('Porte terminale · hublot',(0,-.10,.25),.30,.38,.06,mats['metal'],p,64)
            b.cylinder('Porte terminale · verre sombre',(0,-.135,.25),.30,.018,mats['dark'],p,(0,1,0),64)
    # Labels are real small plates, their lettering is assigned in the map pass.
    for i,(side,y,z) in enumerate([(1,-1.1,1.95),(-1,.3,1.8),(1,5.3,1.8),(-1,-7,1.7),(1,11,1.8)]):
        p=b.root('SIGNAL %02d · plaque'%i,(side*2.09,y,z),top)
        b.box('Plaque instruction',(-side*.01,0,0),(.025,.25,.36),mats['blue'],p,.003)
        for j in range(7):b.box('Signal · ligne claire',(-side*.026,0,.12-j*.035),(.002,.19 if j else .13,.006),mats['trim'],p,0)
    cams=[camera(b,'CAM_01 · sas de reference',(0,-1.6,1.6),(0,4,1.6),22),camera(b,'CAM_02 · oblique avant',(-1.35,-1.5,1.6),(.25,2.7,1.55),23),camera(b,'CAM_03 · arriere raccorde',(.1,-.4,1.6),(0,-9,1.6),22),camera(b,'CAM_04 · couloir interieur',(.15,4.4,1.6),(0,13,1.6),22),camera(b,'CAM_05 · coffrets et cables',(-1.15,-2.8,1.55),(2.02,-.7,1.65),30),camera(b,'CAM_06 · sas rapproche',(-.75,.7,1.6),(.5,2.2,1.65),22),camera(b,'CAM_07 · circulation arriere',(0,-6.6,1.6),(0,-13,1.6),24)]
    pan=camera(b,'CAM_08 · panorama 360',(0,-.25,1.6),(0,3,1.6),22,2400,1200);pan.data.type='PANO';pan.data.panorama_type='EQUIRECTANGULAR';cams.append(pan)
    # A repeatable inspection path crosses the real hatch rather than rotating at one point.
    path=camera(b,'CAM_09 · parcours automatique',(0,-3,1.6),(0,5,1.6),23)
    for frame,y in ((1,-3),(120,.7),(180,3.0),(300,9.5)):
        path.location=(.15*math.sin(y),y,1.6);path.keyframe_insert(data_path='location',frame=frame)
    for name,loc,direction in PROJECTION_SPECS:
        o=camera(b,'PROJ_'+name,loc,Vector(loc)+Vector(direction),17,1024,1024);o['pa_projection_only']=True
    scene.frame_start=1;scene.frame_end=300;scene.frame_set(1)
    for o in b.collection.objects:
        if o.type=='MESH' and any(m in (mats['ivory'],mats['floor'],mats['trim'],mats['box'],mats['walk']) for m in o.data.materials):o['pa_albedo_target']=True
    scene.camera=cams[0];scene['pa_station_collection']=b.collection.name;scene['pa_modular_recipe']='station-habitat';scene['pa_reference_image']=reference;scene['pa_stage']='01 · geometrie modulaire et materiaux physiques';scene['pa_output']=str(out)
    scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True;scene.render.resolution_x=1440;scene.render.resolution_y=960;scene.render.resolution_percentage=100
    scene.world=bpy.data.worlds.new('ST · espace exterieur noir');scene.world.use_nodes=True;scene.world.node_tree.nodes.get('Background').inputs['Color'].default_value=(.02,.025,.03,1);scene.world.node_tree.nodes.get('Background').inputs['Strength'].default_value=.1
    scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast';scene.view_settings.exposure=-.6
    scene.unit_settings.system='METRIC';scene.render.image_settings.file_format='PNG'
    bpy.context.view_layer.update()
    report={'recipe':'station-habitat','version':1,'reference':reference,'asset_sources':b.asset_report,'modules':len(b.modules),'objects':len(b.collection.objects),'base_mesh_triangles':sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in b.collection.objects if o.type=='MESH'),'assumptions':['Source 3:1 treated as cropped horizontal panorama, not an exact calibrated sphere.','Duplicated seam hatch interpreted as one rear passage.','Six axial cabins, dimensions estimated from door clearance.','Terminal doors and far rooms are coherent extrapolations.'],'stage':'geometry-first'}
    (out/'scene-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    return b,report

def finish_details(scene):
    """Small physical fittings visible in the reference, added after large volumes settle."""
    if scene.get('pa_station_details'):return
    seal_backing(scene)
    b=Builder(scene,'STATION · ferrures et details physiques');metal=bpy.data.materials['ST · aluminium brosse'];dark=bpy.data.materials['ST · joints anthracite'];yellow=bpy.data.materials['ST · securite jaune'];red=bpy.data.materials.get('ST · boutons rouges') or material('ST · boutons rouges',(.48,.025,.014),.32);ivory=bpy.data.materials['ST · sas email blanc chaud'];boxmat=bpy.data.materials['ST · coffrets gris']
    for p in [o for o in scene.objects if o.type=='EMPTY' and o.name.startswith('SAS ' )]:
        for side in (-1,1):
            # Segmented latch plates and cable runs make the pressure frame less generic.
            for j in range(12):
                a=(j+.5)*math.tau/12;x=1.52*math.cos(a);z=1.52*math.sin(a)
                plate=b.box('Ferrure · platine radiale',(x,side*.22,z),(.115,.032,.068),metal,p,.005);plate.rotation_euler.y=-a
                b.cylinder('Ferrure · vis',(x,side*.245,z),.013,.013,dark,p,(0,1,0),8)
            for lr in (-1,1):
                hinge=b.root('Ferrure · charniere',(lr*1.51,side*.26,.36),p)
                for z in (-.08,0,.08):b.cylinder('Charniere · fut',(0,0,z),.041,.068,metal,hinge,(0,0,1),16)
                b.box('Charniere · attache',(-lr*.06,0,0),(.12,.065,.23),metal,hinge,.006)
                # Beside door, a real service box, red mushroom switch and electrical cable.
                control=b.root('Commande · boitier sas',(lr*1.84,side*.13,.24),p)
                b.box('Commande · boitier',(0,0,0),(.23,.13,.36),boxmat,control,.015)
                b.cylinder('Commande · bouton rouge',(0,side*.084,.06),.040,.035,red,control,(0,1,0),20)
                b.cylinder('Commande · voyant',(0,side*.082,-.06),.023,.016,yellow,control,(0,1,0),16)
                b.pipe('Commande · cable',[(lr*1.84,side*.1,.05),(lr*1.86,side*.14,-.90),(lr*1.96,side*.19,-1.42)],.012,dark,p)
    # Slight desaturation matches the reference's khaki paint under warm practical lights.
    for name in ('ST · panneaux ivoire vieilli','ST · sol resine creme'):
        nt=bpy.data.materials[name].node_tree;bs=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED');source=bs.inputs['Base Color'].links[0].from_socket
        n=nt.nodes.new('ShaderNodeHueSaturation');n.name=n.label='Peinture · accord khaki reference';n.inputs['Saturation'].default_value=.62;n.inputs['Value'].default_value=1.06;nt.links.new(source,n.inputs['Color']);nt.links.new(n.outputs[0],bs.inputs['Base Color'])
    scene['pa_station_details']=len(b.collection.objects)

def seal_backing(scene):
    """Overlap the hidden wall shell with the continuous subfloor and roof."""
    changed=[]
    for o in scene.objects:
        if o.type=='MESH' and o.name.startswith('Cloison · support continu'):
            o.location.z=1.56
            for v in o.data.vertices:v.co.z=math.copysign(1.76,v.co.z)
            changed.append(o.name)
    return changed
