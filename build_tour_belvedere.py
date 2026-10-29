"""Reference-led tower study. Geometry first; no generated/projected textures.

Standalone scene; local assets appended without editing user's libraries.
Units are estimated metres, not surveyed dimensions. See reconstruction.json.
"""
import bpy, bmesh, math, random, json, sys
from pathlib import Path
from mathutils import Vector

OUT=Path(__file__).parent/'output/tour-belvedere-v1'
ASSETS=Path(r'K:\Connector-Blender\Blender-asset-lib-VDB\botaniq_full-Assets')
random.seed(241)
bpy.ops.wm.read_factory_settings(use_empty=True)
sc=bpy.context.scene; sc.name='Tour belvedere · reconstruction modulaire · passe 1'
sc.unit_settings.system='METRIC'
groups={}; roots=[]
def collection(name):
    if name not in groups:
        c=bpy.data.collections.new(name); sc.collection.children.link(c);groups[name]=c
    return groups[name]
def link(o,group):
    for c in list(o.users_collection):c.objects.unlink(o)
    collection(group).objects.link(o);return o
def module(name,loc=(0,0,0),group='01 · Tour'):
    o=bpy.data.objects.new(name,None);collection(group).objects.link(o);o.location=loc
    o.empty_display_type='PLAIN_AXES';o.empty_display_size=.45;o['module']=True
    o['instruction']='Deplacer ce parent : toutes les pieces de cet assemblage suivent.'
    roots.append(o);return o
def mat(name,color,rough=.7,metal=0):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
    s=m.node_tree.nodes.get('Principled BSDF');s.inputs['Base Color'].default_value=(*color,1)
    s.inputs['Roughness'].default_value=rough;s.inputs['Metallic'].default_value=metal
    return m
mint=mat('Beton · celadon pale',(.38,.48,.40))
cream=mat('Beton · pied beige',(.49,.46,.37))
pink=mat('Couverture · rose passe',(.57,.39,.40))
pink2=mat('Couverture · rose clair',(.64,.47,.47))
yellow=mat('Couverture · panneaux creme',(.62,.56,.39))
seam=mat('Joints creux',(.10,.13,.12))
trim=mat('Menuiseries · gris clair',(.53,.56,.50),.4,.25)
dark=mat('Interieurs et joints de vitrage',(.025,.037,.035),.8)
turquoise=mat('Batiments · peinture vert eau',(.26,.48,.43))
roofmat=mat('Etancheite · gris brun',(.20,.21,.19),.95)
asphalt=mat('Voirie · asphalte',(.19,.21,.21),.91)
pavement=mat('Trottoirs · beton',(.43,.44,.40),.88)
earth=mat('Massifs · terre',(.095,.12,.065),1)
red=mat('Bordures · rouge terre',(.37,.095,.06))
white=mat('Bordures · blanc casse',(.64,.63,.53))
metal=mat('Equipements · metal gris',(.27,.30,.28),.47,.6)
opal=mat('Lampadaires · globes opalins',(.72,.72,.65),.35)
glass=mat('Vitrages · verre gris vert',(.42,.59,.54),.16)
bs=glass.node_tree.nodes.get('Principled BSDF');bs.inputs['Transmission Weight'].default_value=.92;bs.inputs['IOR'].default_value=1.46
def mesh(name,verts,faces,m,p,group=None,smooth=False):
    me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update()
    o=bpy.data.objects.new(name,me);collection(group or p.users_collection[0].name).objects.link(o)
    if p:o.parent=p
    if m:me.materials.append(m)
    for f in me.polygons:f.use_smooth=smooth
    # Stable local UVs available before texturing.
    uv=me.uv_layers.new(name='UV_local')
    for f in me.polygons:
        for li in f.loop_indices:
            co=me.vertices[me.loops[li].vertex_index].co
            uv.data[li].uv=(co.x*.1,co.z*.1 if abs(f.normal.z)<.7 else co.y*.1)
    return o
def cube(name,loc,size,m,p,bevel=.025):
    x,y,z=[a*.5 for a in size]
    verts=[(-x,-y,-z),(-x,-y,z),(-x,y,-z),(-x,y,z),(x,-y,-z),(x,-y,z),(x,y,-z),(x,y,z)]
    # Outward winding; earlier V1 boxes were inverted and needed correction before projection.
    o=mesh(name,verts,[(2,6,4,0),(5,7,3,1),(4,5,1,0),(3,7,6,2),(1,3,2,0),(6,7,5,4)],m,p);o.location=loc
    if bevel:
        mod=o.modifiers.new('Chanfreins reels','BEVEL');mod.width=bevel;mod.segments=2
        n=o.modifiers.new('Normales ponderees','WEIGHTED_NORMAL')
    return o
def lathe(name,profile,m,p,n=96,theta0=0,theta1=2*math.pi,cap=False):
    closed=abs(theta1-theta0-2*math.pi)<1e-5
    count=n if closed else n+1
    vs=[(r*math.cos(theta0+(theta1-theta0)*i/n),r*math.sin(theta0+(theta1-theta0)*i/n),z) for r,z in profile for i in range(count)]
    fs=[]
    for j in range(len(profile)-1):
        for i in range(n):
            k=(i+1)%count;fs.append((j*count+i,j*count+k,(j+1)*count+k,(j+1)*count+i))
    if cap and closed:fs.extend([tuple(reversed(range(count))),tuple((len(profile)-1)*count+i for i in range(count))])
    o=mesh(name,vs,fs,m,p,smooth=True)
    uv=o.data.uv_layers.active
    for poly in o.data.polygons:
        for li in poly.loop_indices:
            vi=o.data.loops[li].vertex_index;j=vi//count;i=vi%count
            u=i/n
            if closed and any(o.data.loops[k].vertex_index%count==n-1 for k in poly.loop_indices) and i==0:u=1
            uv.data[li].uv=(u,j/max(1,len(profile)-1))
    return o
def tube(name,points,r,m,p):
    cu=bpy.data.curves.new(name,'CURVE');cu.dimensions='3D';cu.resolution_u=1
    cu.bevel_depth=r;cu.bevel_resolution=1
    sp=cu.splines.new('POLY');sp.points.add(len(points)-1)
    for v,co in zip(sp.points,points):v.co=(*co,1)
    o=bpy.data.objects.new(name,cu);p.users_collection[0].objects.link(o);o.parent=p;cu.materials.append(m);return o
def cyl(name,loc,r,depth,m,p,n=24):
    o=lathe(name,[(r,-depth/2),(r,depth/2)],m,p,n=n,cap=True);o.location=loc;return o

# Tower: three independently editable principal shells and a real glazed room.
tower=module('TOUR · assemblage complet')
pedestal=module('TOUR · pied evase');pedestal.parent=tower
baseprofile=[(4.1,.15),(4.0,.45),(3.7,1.1),(3.36,2.65),(3.3,2.8),(2.85,5.0),(2.5,7.1),(2.45,10.4)]
base=lathe('Fut inferieur · profil evase',baseprofile,cream,pedestal,cap=True)
# Cut a real sector opening at the foot so the shell cannot project through the door.
bm=bmesh.new();bm.from_mesh(base.data)
opening=[]
for f in bm.faces:
    c=f.calc_center_median();a=math.atan2(c.y,c.x)
    if len(f.verts)==4 and abs(a+math.pi/2)<.197 and max(v.co.z for v in f.verts)<2.651:opening.append(f)
bmesh.ops.delete(bm,geom=opening,context='FACES');bm.to_mesh(base.data);bm.free()
lathe('Plinthe du pied',[(4.25,.05),(4.25,.25),(4.0,.40)],pavement,pedestal)
for i in range(16):
    a=2*math.pi*i/16
    points=[(r*math.cos(a),r*math.sin(a),z) for r,z in baseprofile if i!=12 or z>=2.8]
    tube('Joint vertical du pied',points,.014,seam,pedestal)
collar=module('TOUR · collerette intermediaire');collar.parent=tower
lathe('Corniche intermediaire',[(2.45,10.35),(3.05,10.35),(3.05,10.85),(2.45,10.85)],cream,collar)
lathe('Bande rose collerette',[(3.065,10.40),(3.065,10.72)],pink,collar,theta0=math.pi,theta1=2*math.pi,n=48)
stem=module('TOUR · fut et sous-face');stem.parent=tower
stemprofile=[(2.45,10.85),(2.4,13),(2.35,16),(2.4,18.5),(2.65,20.3),(3.2,21.7),(4.15,23.0),(5.45,24.1),(7.2,24.8),(9,25.5),(10.55,26.5),(11.3,27.5),(11.65,28.7)]
lathe('Fut superieur et calice',stemprofile,mint,stem)
for i in range(32):
    a=2*math.pi*i/32
    tube('Joint rayonnant calice',[(r*math.cos(a),r*math.sin(a),z) for r,z in stemprofile],.012,seam,stem)
for z in (13.8,17.3):lathe('Joint horizontal fut',[(2.413,z-.018),(2.413,z+.018)],seam,stem)
ring=module('TOUR · galerie vitree');ring.parent=tower
lathe('Allège annulaire',[(11.67,28.60),(11.82,28.72),(11.82,28.95)],trim,ring)
lathe('Linteau annulaire',[(11.82,30.95),(11.95,31.10),(11.95,31.26)],trim,ring)
cyl('Dalle galerie', (0,0,28.84),11.65,.18,dark,ring,96)
cyl('Plafond galerie', (0,0,31.12),11.75,.14,dark,ring,96)
cyl('Noyau interieur galerie',(0,0,29.95),3.0,2.2,cream,ring,48)
for i in range(80):
    a=2*math.pi*i/80; da=2*math.pi/80
    pane=module(f'VITRE TOUR {i+1:02d}',group='01 · Tour');pane.parent=ring
    lathe('Verre courbe en retrait',[(11.685,28.98),(11.685,30.96)],glass,pane,n=2,theta0=a+.004,theta1=a+da-.004)
    tube('Montant vertical',[(11.77*math.cos(a),11.77*math.sin(a),28.94),(11.77*math.cos(a),11.77*math.sin(a),31.08)],.045,trim,pane)
    tube('Joint vitrage',[(11.70*math.cos(a+.005),11.70*math.sin(a+.005),28.97),(11.70*math.cos(a+.005),11.70*math.sin(a+.005),30.98)],.022,dark,pane)
caproot=module('TOUR · calotte et equipements');caproot.parent=tower
roofprofile=[(11.92,31.27),(11.78,32.1),(11.30,33.25),(10.4,34.35),(9.15,35.25),(7.65,36.0),(5.70,36.5),(3.7,36.8),(2.0,36.95)]
lathe('Sous-couche joints couverture',roofprofile,seam,caproot)
for i in range(40):
    a=i*2*math.pi/40;da=2*math.pi/40
    p=module(f'PANNEAU CALOTTE {i+1:02d}');p.parent=caproot
    lathe('Tole rose segmentee',[(r+.014,z+.014) for r,z in roofprofile],yellow if i%13==4 else (pink2 if i%4==0 else pink),p,n=3,theta0=a+.001,theta1=a+da-.001)
for r,z in [roofprofile[2],roofprofile[5]]:
    pts=[((r+.03)*math.cos(i*2*math.pi/160),(r+.03)*math.sin(i*2*math.pi/160),z+.025) for i in range(161)]
    tube('Joint circulaire calotte',pts,.018,seam,caproot)
cyl('Plateforme technique sommitale',(0,0,37.0),2.15,.24,roofmat,caproot,48)
cyl('Edicule technique central',(0,0,37.60),1.65,1.12,cream,caproot,48)
cyl('Couvertine edicule',(0,0,38.20),1.76,.12,trim,caproot,48)
for i in range(7):
    a=i*2*math.pi/7;x,y=2.75*math.cos(a),2.75*math.sin(a)
    o=cube('Armoire technique sommitale',(x,y,37.48),(.85,.85,1.20),trim,caproot);o.rotation_euler.z=a
for i,a in enumerate((.4,2.5,4.4)):
    x,y=2.5*math.cos(a),2.5*math.sin(a)
    cyl('Mat antenne',(x,y,38),.055,3.0,metal,caproot)
    cube('Antenne panneau',(x+.12,y,38.2),(.19,.34,1.35),trim,caproot)
    tube('Support antenne',[(x,y,36.8),(x,y,38.5)],.035,metal,caproot)

# A real inset service entrance, conservatively attached to the base.
entrance=module('TOUR · porte technique',(0,-3.90,.2));entrance.parent=tower
for x in (-.90,.90):cube('Jambage et ebrasement porte',(x,.18,1.24),(.18,1.05,2.48),trim,entrance)
cube('Linteau entree',(0,.18,2.44),(1.98,1.05,.18),trim,entrance)
cube('Porte metal en retrait', (0,.28,1.21),(1.62,.06,2.30),dark,entrance)
cube('Poignee',(.59,.19,1.15),(.045,.12,.28),metal,entrance)
cube('Marche porte',(0,-.35,.03),(2.15,.90,.16),pavement,entrance)
cube('Plaque signaletique',(-1.45,.2,2.2),(.55,.08,.70),yellow,entrance)

# Low administrative building east of the tower, derived from aerial footprint.
# Window openings are assembled from sill/lintel/piers, never textured onto a solid wall.
building=module('BATIMENT · aile principale',(18,0,0),'02 · Batiments')
def building_shell(parent,w,length,height=4.1,bays=8):
    cube('Dalle soubassement',(0,0,.16),(w,length,.32),roofmat,parent)
    cube('Plancher interieur',(0,0,.36),(w-.4,length-.4,.16),pavement,parent)
    cube('Toiture dalle porteuse',(0,0,height),(w+1,length+1,.22),trim,parent)
    cube('Toit etancheite',(0,0,height+.15),(w+.72,length+.72,.08),roofmat,parent,0)
    for x in (-w/2-.44,w/2+.44):cube('Acrotere longitudinal',(x,0,height+.36),(.14,length+1,.52),trim,parent)
    for y in (-length/2-.44,length/2+.44):cube('Acrotere transversal',(0,y,height+.36),(w+1,.14,.52),trim,parent)
    step=length/bays
    for side in (-1,1):
        x=side*w/2
        cube('Allege facade',(x,0,.93),(.30,length,1.36),turquoise,parent)
        cube('Linteau facade',(x,0,3.60),(.30,length,.66),turquoise,parent)
        for j in range(bays+1):cube('Trumeau facade',(x,-length/2+j*step,2.38),(.32,.54,1.84),turquoise,parent)
        for j in range(bays):
            y=-length/2+(j+.5)*step
            p=module(f'FENETRE · {parent.name} · {side:+d} {j+1}',(x,y,1.54),'02 · Batiments');p.parent=parent
            width=step-.54
            cube('Appui saillant',(0,0,-.02),(.47,width+.16,.12),trim,p)
            for yy in (-width/2,0,width/2):cube('Montant fenetre',(-side*.05,yy,.83),(.10,.055,1.66),trim,p,.008)
            for z in (0,.82,1.66):cube('Traverse fenetre',(-side*.05,0,z),(.10,width,.05),trim,p,.006)
            cube('Vitre distincte',(-side*.09,0,.83),(.015,width-.05,1.6),glass,p,0)
            if side==-1 and j%3==1:
                ac=module(f'CLIMATISEUR · {j+1}',(x-.41,y,.9),'02 · Batiments');ac.parent=parent
                cube('Caisson climatiseur',(0,0,0),(.62,.80,.57),trim,ac)
                for k in range(7):cube('Ailette climatiseur',(-.322,0,-.21+k*.07),(.025,.68,.022),dark,ac,.002)
                for yy in (-.27,.27):cube('Console fixation',(.10,yy,-.38),(.65,.045,.07),metal,ac,.006)
    for y in (-length/2,length/2):
        cube('Mur pignon gauche',(-w*.30,y,2.05),(w*.40,.30,3.8),turquoise,parent)
        cube('Mur pignon droit',(w*.30,y,2.05),(w*.40,.30,3.8),turquoise,parent)
        cube('Linteau porte',(0,y,3.48),(w*.20,.30,1.0),turquoise,parent)
        cube('Porte acces',(0,y+.02,1.62),(w*.20-.12,.08,2.70),dark,parent)
        for xx in (-w*.1,w*.1):cube('Huisserie porte',(xx,y-.08,1.65),(.09,.12,2.8),trim,parent)
    # Interior room dividers create plausible views through the glazing.
    cube('Cloison longitudinale',(0,0,2.0),(.15,length-.4,3.4),cream,parent)
    for y in (-length*.25,0,length*.25):cube('Cloison transversale',(0,y,2.0),(w-.3,.12,3.4),cream,parent)
    for y in (-length/2+.4,length/2-.4):tube('Descente pluviale',[(-w/2-.18,y,height),(-w/2-.24,y,.15)],.045,metal,parent)
building_shell(building,10,24,4.3,8)
wing=module('BATIMENT · annexe courte',(18,15,0),'02 · Batiments');building_shell(wing,8,6,3.9,2)
foreground=module('BATIMENT · prolongement premier plan',(18,-24,0),'02 · Batiments');building_shell(foreground,10,24,4.3,8)

# Ground, circulation and individually editable equipment.
site=module('SITE · plateforme',(0,0,0),'03 · Sols et voirie')
cube('Terrain',(0,0,-.24),(180,190,.4),earth,site,0)
cube('Route principale',(-12,-10,-.015),(7,150,.12),asphalt,site,0)
cube('Acces entre tour et batiment',(6,-10,-.01),(7,105,.12),asphalt,site,0)
cube('Route transversale',(8,-25,-.008),(48,8,.13),asphalt,site,0)
cube('Parvis tour',(0,0,.03),(14,17,.16),pavement,site,.03)
cube('Trottoir batiment',(11.9,0,.08),(2.0,29,.22),pavement,site,.03)
for x in (-16.0,-8.0):
    curb=module('BORDURE · route', (x,0,0),'03 · Sols et voirie')
    for j in range(55):cube('Bordure rouge blanc',(0,-44+j*1.3,.12),(.28,1.28,.28),red if j%2 else white,curb,.018)
for x in (2.3,9.8):
    curb=module('BORDURE · allee', (x,0,0),'03 · Sols et voirie')
    for j in range(32):cube('Bordure allee',(0,-21+j*1.3,.12),(.25,1.28,.28),red if j%2 else white,curb,.018)
for i,(x,y) in enumerate([(10,-18),(10,-4),(10,10),(-7,-26),(-7,15)]):
    p=module(f'LAMPADAIRE {i+1:02d}',(x,y,.1),'04 · Equipements')
    cyl('Socle lampadaire',(0,0,.2),.18,.40,pavement,p)
    tube('Fut courbe',[(0,0,.2),(.02,0,3.8),(.15,0,4.6),(.03,0,4.95),(-.28,0,5.22)],.065,metal,p)
    cyl('Douille globe',(-.28,0,5.19),.13,.35,metal,p)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16,ring_count=8,radius=.31)
    o=link(bpy.context.object,p.users_collection[0].name);o.name='Globe opalin';o.parent=p;o.location=(-.28,0,5.51);o.scale=(1,1,.78);o.data.materials.append(opal)
    for f in o.data.polygons:f.use_smooth=True
mast=module('MAT · projecteurs',(29,-20,0),'04 · Equipements')
cyl('Mat eclairage',(0,0,9),.10,18,metal,mast)
for i in range(4):
    a=i*math.pi/2
    tube('Bras projecteur',[(0,0,17.6),(math.cos(a)*.65,math.sin(a)*.65,17.6)],.04,metal,mast)
    o=cube('Projecteur',(math.cos(a)*.68,math.sin(a)*.68,17.7),(.42,.30,.30),metal,mast);o.rotation_euler.z=a

# Local botaniq prototypes, instanced rather than duplicated geometry.
botanicals=[]
files=['deciduous/Tree_Quercus-agrifolia_A_summer.blend','deciduous/Tree_Tilia-europaea_B_summer.blend','deciduous/Tree_Ficus-carica_A_summer.blend','shrubs/Shrub_Corylus-avellana_A_spring-summer.blend']
for f in files:
    path=ASSETS/'blends_280'/f
    with bpy.data.libraries.load(str(path),link=False) as (a,b):b.objects=a.objects
    c=bpy.data.collections.new('SOURCE BOTANIQ · '+Path(f).stem)
    for o in b.objects:
        if o:c.objects.link(o)
    c.use_fake_user=True
    botanicals.append(c)
for im in bpy.data.images:
    if im.source=='FILE':
        p=Path(bpy.path.abspath(im.filepath))
        if not p.exists():p=ASSETS/'textures'/Path(im.filepath.replace('\\','/')).name
        if not p.exists():raise FileNotFoundError(str(p))
        im.filepath=str(p);im.reload();im.pack()
bpy.ops.object.make_local(type='ALL')
def vegetation(kind,x,y,height,index):
    c=botanicals[kind];h=max(max(v[2] for v in o.bound_box) for o in c.objects if o.type=='MESH')
    o=module(('ARBRE' if kind<3 else 'ARBUSTE')+f' BOTANIQ {index:03d}',(x,y,.1),'05 · Vegetation botaniq')
    o.instance_type='COLLECTION';o.instance_collection=c;o.scale=(height/h,)*3;o.rotation_euler.z=random.uniform(0,2*math.pi)
    o['source_asset']=files[kind];o['instance']=True
    return o
positions=[(-23,-31,16),(-25,-20,17),(-23,-7,15),(-25,7,16),(-23,20,14),(-12,28,15),(0,26,13),(12,28,14),(25,27,13),(33,18,15),(34,4,12),(34,-10,13),(-34,-40,14),(-35,-28,15),(-36,-13,16),(-36,2,14),(-36,18,15),(-30,32,15),(-16,40,16),(0,42,15),(16,42,17),(32,39,13),(-30,-52,16),(-31,-64,17),(36,-35,13),(42,-18,14)]
for i,(x,y,h) in enumerate(positions):vegetation(i%3,x,y,h,i)
vegetation(1,-20,-72,21,70)
vegetation(0,-24,-51,18,71)
for i in range(38):
    if i<18:
        a=i*2*math.pi/18;x,y=5.2*math.cos(a),5.2*math.sin(a)
        if y<0 and abs(x)<2:continue
    else:x,y=random.choice([-19.1,26.2])+random.uniform(-.7,.7),random.uniform(-15,22)
    vegetation(3,x,y,random.uniform(.9,1.6),i)

# Broad overcast sky; no texture-driven shadows or procedural patina in this pass.
world=bpy.data.worlds.new('Ciel couvert neutre');world.use_nodes=True;sc.world=world
world.node_tree.nodes['Background'].inputs['Color'].default_value=(.78,.81,.85,1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value=.85
ld=bpy.data.lights.new('Ciel · grande source diffuse','AREA');lo=bpy.data.objects.new(ld.name,ld);collection('06 · Lumieres et cameras').objects.link(lo)
lo.location=(-28,-25,65);lo.rotation_euler=(Vector((0,0,12))-lo.location).to_track_quat('-Z','Y').to_euler();ld.energy=42000;ld.shape='DISK';ld.size=65
def camera(name,loc,target,lens=48):
    d=bpy.data.cameras.new(name);o=bpy.data.objects.new(name,d);collection('06 · Lumieres et cameras').objects.link(o)
    o.location=loc;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();d.lens=lens;d.clip_end=500;return o
camera('CAM_01 · reference portrait',(-9,-115,5.5),(1,0,19.7),88)
camera('CAM_02 · ensemble frontal',(-7,-87,5),(4,0,18),45)
camera('CAM_03 · approche pieton',(5.5,-31,1.7),(0,0,21),24)
camera('CAM_04 · vue aerienne',(4,-4,95),(4,-4,0),42)
camera('CAM_05 · controle lateral',(45,-67,25),(4,0,18),42)
sc.camera=bpy.data.objects['CAM_01 · reference portrait']
sc.render.engine='CYCLES';sc.cycles.samples=32;sc.cycles.use_denoising=True
sc.cycles.max_bounces=7;sc.cycles.transparent_max_bounces=12
try:
    pref=bpy.context.preferences.addons['cycles'].preferences;pref.compute_device_type='OPTIX';pref.get_devices()
    for d in pref.devices:d.use=d.type!='CPU'
    sc.cycles.device='GPU'
except Exception as e:print('GPU',str(e),flush=True)
sc.render.resolution_x=1000;sc.render.resolution_y=1200;sc.render.resolution_percentage=70
sc.render.image_settings.file_format='PNG';sc.render.use_persistent_data=True
sc.view_settings.view_transform='AgX';sc.view_settings.look='AgX - Medium High Contrast';sc.view_settings.exposure=0
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.region_3d.view_perspective='CAMERA';area.spaces.active.clip_end=500
            area.spaces.active.shading.type='MATERIAL';area.spaces.active.shading.use_scene_world=True
sc['phase']='01 · geometrie a valider avant texturing GPT'
sc['units_note']='Dimensions estimees depuis les photos, non releve metrique.'
bpy.context.view_layer.update()

# Actual parent/neighbor editability test, restored before saving.
test=bpy.data.objects['BATIMENT · aile principale'];children=list(test.children_recursive)
before={o.name:o.matrix_world.copy() for o in children};other=tower.matrix_world.copy();old=test.location.copy()
delta=Vector((2.3,-1.2,.4));test.location+=delta;bpy.context.view_layer.update()
move_ok=all((o.matrix_world.translation-before[o.name].translation-delta).length<1e-4 for o in children)
neighbor_ok=(tower.matrix_world.translation-other.translation).length<1e-6
test.location=old;bpy.context.view_layer.update()
arch=[o for o in sc.objects if o.type=='MESH' and not o.get('source_asset')]
base_tri=sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in arch)
dg=bpy.context.evaluated_depsgraph_get();eval_tri=0
for o in sc.objects:
    if o.type not in {'MESH','CURVE'}:continue
    e=o.evaluated_get(dg);me=e.to_mesh();eval_tri+=sum(len(p.vertices)-2 for p in me.polygons);e.to_mesh_clear()
unique_bot=sum(sum(len(p.vertices)-2 for p in o.data.polygons) for c in botanicals for o in c.objects if o.type=='MESH')
report={'phase':'geometry first; waiting for visual feedback before GPT texture pass','estimated_dimensions_m':{'tower_height':39.5,'globe_diameter':23.9,'main_building':[10,24,4.3]},'observed':['flared pedestal and narrow shaft','intermediate collar','radial curved underside','continuous glazed ring','segmented pink shallow dome','rooftop telecom equipment','mint low building east of tower','curved globe streetlamps','dense broadleaf vegetation'], 'assumptions':['Scale is estimated, not surveyed','Unseen building interiors, rear facades and entrance are logical interpretations','Front building prolongation inferred beyond aerial crop, not measured','Tree species chosen for silhouette, not botanically identified','Roof panel counts and antenna layout approximate the supplied pixels'], 'assets':files,'source_library':str(ASSETS),'modules':len(roots),'scene_objects':len(sc.objects),'architecture_base_triangles':base_tri,'architecture_evaluated_triangles':eval_tri,'vegetation_unique_source_triangles':unique_bot,'vegetation_instances':sum(o.instance_type=='COLLECTION' for o in sc.objects),'checks':{'building_children_follow':move_ok,'tower_unchanged_when_building_moves':neighbor_ok,'botaniq_images_packed':all(im.packed_file for im in bpy.data.images if im.source=='FILE'),'no_camera_projection':True},'limits':['First modelling pass, no generated albedo yet','Botaniq detailed vegetation is instanced, not a low-poly game export','No full collision validation or surveyed camera solve','Tower service door is a closed panel; interior access not reconstructed']}
(OUT/'reconstruction.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'tour-belvedere-geometrie-v1.blend'))
print('TOWER_BUILD_SAVED',json.dumps(report['checks']),flush=True)
if '--no-render' not in sys.argv:
    sc.render.filepath=str(OUT/'01-reference-preview.png');bpy.ops.render.render(write_still=True)
    sc.camera=bpy.data.objects['CAM_02 · ensemble frontal'];sc.render.resolution_x=1400;sc.render.resolution_y=900
    sc.render.filepath=str(OUT/'02-ensemble-preview.png');bpy.ops.render.render(write_still=True)
print('TOWER_DONE',flush=True)
