"""Photo-led modular cockpit. Standalone reproducible Blender build; originals untouched.

Landmarks describe visible design intent, not a depth-mesh or generative artefacts.
Every module has a movable root; all mapped details use mesh UVs.
"""
import bpy, math, json, random, sys
from pathlib import Path
from mathutils import Vector, Matrix, Euler

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'output/cockpit-photo-modulaire-v1'; MAPS=OUT/'maps'
OUT.mkdir(parents=True,exist_ok=True)
PREVIEW='--preview' in sys.argv
bpy.ops.wm.read_factory_settings(use_empty=True)
sc=bpy.context.scene; sc.name='Cockpit photo — décor modulaire'
sc.unit_settings.system='METRIC'
groups={}
def coll(name):
    if name not in groups:
        c=bpy.data.collections.new(name); sc.collection.children.link(c); groups[name]=c
    return groups[name]
def link(obj,group):
    for c in list(obj.users_collection): c.objects.unlink(obj)
    coll(group).objects.link(obj); return obj
def module(name,loc=(0,0,0),group='01 · Architecture'):
    o=bpy.data.objects.new(name,None); coll(group).objects.link(o); o.location=loc
    o.empty_display_type='CUBE'; o.empty_display_size=.12
    o['module']=True; o['usage']='Déplacer ce parent pour déplacer tout le module. Alt+P pour détacher une pièce.'
    return o
def parent(o,p):
    if p:
        o.parent=p
    return o
def material(name,color,rough=.45,metal=0,emission=0):
    m=bpy.data.materials.new(name); m.diffuse_color=(*color,1); m.use_nodes=True
    bs=m.node_tree.nodes.get('Principled BSDF'); bs.inputs['Base Color'].default_value=(*color,1)
    bs.inputs['Roughness'].default_value=rough; bs.inputs['Metallic'].default_value=metal
    if emission:
        bs.inputs['Emission Color'].default_value=(*color,1); bs.inputs['Emission Strength'].default_value=emission
    return m
ivory=material('Coque · peinture ivoire satinée',(.40,.385,.34),.37)
light_ivory=material('Chants · ivoire clair',(.49,.47,.42),.3)
panelmat=material('Panneaux · gris chaud',(.37,.39,.36),.46)
dark=material('Joints · caoutchouc anthracite',(.024,.029,.027),.65)
chrome=material('Aluminium brossé',(.36,.39,.38),.3,.8)
wood=material('Porte · brun tabac',(.095,.038,.013),.4)
seatmat=material('Siège · vinyle olive grisé',(.29,.30,.235),.6)
red=material('Commandes · rouge brique',(.21,.033,.016),.38)
lampmat=material('Abat-jour · textile écru',(.73,.63,.46),.8,.0,.12)
brass=material('Lampe · laiton patiné',(.26,.19,.075),.28,.65)
floor=material('Sol · résine taupe satinée',(.28,.27,.235),.28)
glow=material('Plafonniers · blanc opalin',(.85,.89,1),.28,0,5)
glass=material('Vitrage · transparent IOR 1.45',(.98,.99,1),.006)
bs=glass.node_tree.nodes.get('Principled BSDF'); bs.inputs['Transmission Weight'].default_value=1; bs.inputs['IOR'].default_value=1.45
frost=material('Oculus · verre dépoli',(.64,.71,.79),.42,0,2.0)
bs=frost.node_tree.nodes.get('Principled BSDF'); bs.inputs['Transmission Weight'].default_value=.55
def image_mat(name,path,emission=0,rough=.45):
    m=material(name,(.5,.5,.5),rough); nt=m.node_tree
    im=bpy.data.images.load(str(path),check_existing=True); im.pack()
    t=nt.nodes.new('ShaderNodeTexImage'); t.image=im; t.label=path.name
    bs=nt.nodes.get('Principled BSDF'); nt.links.new(t.outputs['Color'],bs.inputs['Base Color'])
    if emission:
        nt.links.new(t.outputs['Color'],bs.inputs['Emission Color']); bs.inputs['Emission Strength'].default_value=emission
    return m
crt=[image_mat(f'CRT {i+1:02d} · phosphore vert',MAPS/f'crt-{i+1:02d}.png',2.4,.23) for i in range(6)]
plates=[image_mat(f'Instrumentation {i+1:02d}',MAPS/f'panel-{i+1:02d}.png',0,.48) for i in range(4)]
schematic=image_mat('Table · schéma technique',MAPS/'table-schematic.png',0,.36)
space=image_mat('Cyclorama · espace GPT Image',MAPS/'espace-gpt-image.png',.7,1)
# Modest microtexture is object-local, so it follows modules when moved.
for m in [ivory,light_ivory,panelmat,seatmat,floor,wood]:
    nt=m.node_tree; bs=nt.nodes.get('Principled BSDF'); n=nt.nodes.new('ShaderNodeTexNoise')
    n.inputs['Scale'].default_value=85; n.inputs['Detail'].default_value=2
    bump=nt.nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value=.12; bump.inputs['Distance'].default_value=.0015
    nt.links.new(n.outputs['Fac'],bump.inputs['Height']); nt.links.new(bump.outputs['Normal'],bs.inputs['Normal'])

def bevel(o,w=.015,segments=2):
    if w:
        for poly in o.data.polygons:poly.use_smooth=True
        md=o.modifiers.new('Petits chanfreins réels','BEVEL'); md.width=w; md.segments=segments;md.harden_normals=True
        md=o.modifiers.new('Normales des faces','WEIGHTED_NORMAL'); md.keep_sharp=True; md.weight=30
    return o
def mesh(name,verts,faces,mat,p=None,group=None,bevel_width=0):
    me=bpy.data.meshes.new(name); me.from_pydata(verts,[],faces); me.update()
    o=bpy.data.objects.new(name,me); (p.users_collection[0] if p else coll(group or '01 · Architecture')).objects.link(o)
    if mat: me.materials.append(mat)
    parent(o,p); bevel(o,bevel_width); return o
def box(name,loc,size,mat,p=None,bev=.015,rot=None):
    x,y,z=[v*.5 for v in size]
    verts=[(-x,-y,-z),(x,-y,-z),(x,y,-z),(-x,y,-z),(-x,-y,z),(x,-y,z),(x,y,z),(-x,y,z)]
    o=mesh(name,verts,[(0,3,2,1),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)],mat,p,bevel_width=bev)
    o.location=loc
    if rot: o.rotation_euler=rot
    return o
def cylinder(name,loc,radius,depth,mat,p=None,vertices=24,rot=None):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,radius=radius,depth=depth,location=(0,0,0))
    o=bpy.context.object; o.name=name; link(o,p.users_collection[0].name if p else '01 · Architecture'); parent(o,p)
    o.location=loc; o.data.materials.append(mat)
    if rot:o.rotation_euler=rot
    bevel(o,.008,2); return o
def quad(name,pts,mat,p=None,thick=0):
    o=mesh(name,pts,[(0,1,2,3)],mat,p)
    uv=o.data.uv_layers.new(name='UV_locales')
    for i,v in enumerate([(0,0),(1,0),(1,1),(0,1)]): uv.data[i].uv=v
    if thick:
        s=o.modifiers.new('Épaisseur réelle','SOLIDIFY'); s.thickness=thick; s.offset=0
        bevel(o,.003,2)
    return o
def beam(name,a,b,width,depth,mat,p):
    a,b=Vector(a),Vector(b); o=box(name,(a+b)*.5,(width,depth,(b-a).length),mat,p,bev=min(width*.2,.025))
    o.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler(); return o

# Camera calibration: estimated focal, not a metric recovery from one photo.
W,H=1456,816; F=650.; eye=Vector((0,0,1.6)); R=Euler((math.radians(86),0,0)).to_matrix()
camdata=bpy.data.cameras.new('Photo · focale calibrée'); cam=bpy.data.objects.new('CAM_PHOTO',camdata); coll('06 · Caméras').objects.link(cam)
cam.location=eye; cam.rotation_euler=R.to_euler(); camdata.lens=36*F/W; camdata.sensor_width=36; camdata.clip_end=200; sc.camera=cam
def ray(uv): return R@Vector(((uv[0]-W/2)/F,(H/2-uv[1])/F,-1))
def at_y(uv,y):
    r=ray(uv); return eye+r*(y/r.y)
def at_z(uv,z):
    r=ray(uv); return eye+r*((z-eye.z)/r.z)
def plane_uv(uv,point,normal):
    n=Vector(normal); r=ray(uv); return eye+r*((Vector(point)-eye).dot(n)/r.dot(n))
def plane3(a,b,c): return a,(b-a).cross(c-a).normalized()
def from_photo(poly,plane): return [plane_uv(p,*plane) for p in poly]
def prism(name,front,offset,mat,p,bev=.012):
    front=[Vector(v) for v in front]; off=Vector(offset); n=len(front)
    verts=front+[v+off for v in front]
    faces=[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    return mesh(name,verts,faces,mat,p,bevel_width=bev)
def polygon_panel(name,poly,plane,mat,p,thick=.06):
    pts=from_photo(poly,plane); n=Vector(plane[1]).normalized()
    if n.dot(sum(pts,Vector())/len(pts)-eye)<0:n=-n
    return prism(name,pts,n*thick,mat,p)
def window(name,pts,depth=.18,width=.13,matglass=glass,p=None):
    pts=[Vector(x) for x in pts]; center=sum(pts,Vector())/len(pts)
    normal=(pts[1]-pts[0]).cross(pts[2]-pts[0]).normalized()
    if normal.dot(center-eye)<0:normal=-normal
    # A real extruded ring, open in its centre; glass is recessed behind the front lip.
    inner=[v+(center-v).normalized()*width for v in pts]
    n=len(pts); verts=pts+inner+[v+normal*depth for v in pts]+[v+normal*depth for v in inner]
    faces=[]
    for i in range(n):
        j=(i+1)%n; faces.extend([(i,j,n+j,n+i),(i,2*n+i,2*n+j,j),(n+i,n+j,3*n+j,3*n+i),(2*n+i,3*n+i,3*n+j,2*n+j)])
    mesh(name+' · cadre plein',verts,faces,ivory,p,bevel_width=.018)
    # Rubber gasket follows the aperture, not an opaque plane across it.
    ip=[v+(center-v).normalized()*.025+normal*(depth-.04) for v in inner]
    vv=[v+normal*(depth-.035) for v in inner]+ip
    mesh(name+' · joint',vv,[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)],dark,p)
    if n==4: pane=quad(name+' · vitre transparente',ip,matglass,p,.008)
    else:
        pane=mesh(name+' · vitrage',ip,[tuple(range(n))],matglass,p)
        so=pane.modifiers.new('Épaisseur verre','SOLIDIFY'); so.thickness=.008
    pane['window_glass']=True; pane['ior']=1.45
    return pane

# Floor is geometry, without projected chairs/shadows baked into it.
root=module('M_SOL',group='01 · Architecture'); box('Sol continu',(0,3,-.09),(13,11,.18),floor,root,bev=.02)
for x in [-4,-2,0,2,4]: box('Joint sol',(x,3,.002),(.006,10,.004),panelmat,root,bev=0)
for y in [0,2,4,6,8]: box('Joint sol',(0,y,.002),(12,.006,.004),panelmat,root,bev=0)

leftplane=(Vector((0,6.4,0)),Vector((-.55,1,0)))
rightplane=(Vector((0,6.4,0)),Vector((.55,1,0)))
windows=[('G1',[(-170,185),(220,251),(100,425),(-170,449)],leftplane),
         ('G2',[(215,250),(390,278),(318,418),(101,426)],leftplane),
         ('G3',[(389,278),(621,282),(623,415),(318,419)],leftplane),
         ('D1',[(824,281),(1065,272),(1208,418),(840,417)],rightplane),
         ('D2',[(1063,271),(1226,237),(1432,413),(1207,420)],rightplane),
         ('D3',[(1224,236),(1620,160),(1620,433),(1434,415)],rightplane)]
for name,poly,pl in windows:
    pts=from_photo(poly,pl); p=module('M_FENETRE_'+name)
    window(name,pts,.20,.17,p=p)
    # Lower wall individually follows each bay; leave the aperture genuinely empty.
    a,b=pts[3],pts[2]
    prism(name+' · allège',[a,b,Vector((b.x,b.y,0)),Vector((a.x,a.y,0))],Vector(pl[1]).normalized()*.15,ivory,p)
    beam(name+' · appui',a,b,.10,.15,light_ivory,p)

# Front bulkhead and recessed, independently movable door leaf.
doorroot=module('M_CLOISON_PORTE'); dp=(Vector((0,6.48,0)),Vector((0,1,0)))
for name,poly in [('Montant gauche',[(620,279),(697,279),(697,534),(622,534)]),('Montant droit',[(804,279),(842,279),(850,535),(803,535)]),('Linteau',[(697,280),(804,280),(804,312),(697,312)])]:
    polygon_panel(name,poly,dp,ivory,doorroot,.25)
opening=from_photo([(696,310),(804,310),(804,528),(696,528)],dp)
for i in [0,1,3]:
    a=opening[i]; b=opening[(i+1)%4]
    prism('Ébrasement porte', [a,b,b+Vector((0,.36,0)),a+Vector((0,.36,0))],Vector((.01,0,0)),panelmat,doorroot,.008)
dc=at_y((750,421),6.83); door=module('M_PORTE_FEUILLE',loc=(dc.x-.40,6.81,.02),group='02 · Mobilier')
box('Porte · panneau principal',(.40,0,1.0),(.80,.10,2.0),wood,door,bev=.025)
for x in [-.075,.875]:box('Porte · dormant',(x,.035,1.04),(.15,.17,2.12),ivory,doorroot,bev=.016).location+=door.location
box('Porte · traverse dormant',(.40,.035,2.10),(1.10,.17,.14),ivory,doorroot,bev=.016).location+=door.location
for x in [.06,.74]:box('Porte · moulure',(x,-.062,1.05),(.035,.026,1.76),wood,door,bev=.007)
for z in [.20,1.90]:box('Porte · moulure',(.40,-.062,z),(.69,.026,.035),wood,door,bev=.006)
box('Porte · panneau haut',(.40,-.060,1.35),(.58,.024,.69),wood,door,.015)
cylinder('Poignée · rosace',(.11,-.09,.92),.048,.035,chrome,door,rot=(math.pi/2,0,0))
box('Poignée · levier',(.17,-.13,.92),(.16,.035,.03),chrome,door,.01)
for z in [.23,1.77]: cylinder('Charnière',(0,-.005,z),.018,.16,chrome,door,vertices=12)
for side,u in [('G',655),('D',824)]:
    cp=at_y((u,382),6.42)
    box('Coffret '+side,cp,(.31,.08,.75),light_ivory,doorroot)
    q=[(-.11,-.046,-.23),(.11,-.046,-.23),(.11,-.046,.23),(-.11,-.046,.23)]
    quad('Coffret · détails '+side,[cp+Vector(v) for v in q],plates[2],doorroot)

# Roof annulus: real roof bays with recessed transparent trapezoid windows.
outer_uv=[(-180,-100),(250,-95),(1200,-95),(1630,-100),(1530,216),(1010,279),(490,279),(-80,224)]
inner_uv=[(501,48),(575,25),(885,25),(958,46),(925,105),(835,142),(600,142),(540,108)]
inner=[at_z(p,3.12) for p in inner_uv]
outer=[at_z(p,2.78 if i>=4 else 3.02) for i,p in enumerate(outer_uv)]
for i in range(8):
    p=module(f'M_TOIT_{i+1:02d}'); j=(i+1)%8
    subdivisions=3 if i==5 else (2 if i in [3,4,6,7] else 1)
    for k in range(subdivisions):
        t0=k/subdivisions;t1=(k+1)/subdivisions
        pts=[inner[i].lerp(inner[j],t0),inner[i].lerp(inner[j],t1),outer[i].lerp(outer[j],t1),outer[i].lerp(outer[j],t0)]
        pane=window(f'Toit {i+1}.{k+1}',pts,.16,.18,p=p,matglass=ivory if i in [0,1,2] else glass)
        if i in [0,1,2]:pane['window_glass']=False
    beam('Traverse extérieure',outer[i],outer[j],.20,.25,ivory,p)
oc=module('M_OCULUS'); window('Oculus central',inner,.12,.15,matglass=frost,p=oc)

# Console builders use calibrated photo-plane faces plus volumetric side panels.
def console(name,poly,ys,index):
    a,b,c=[at_y(poly[i],ys[i]) for i in range(3)]
    plane=plane3(a,b,c); pts=from_photo(poly,plane)
    center=sum(pts,Vector())/4
    p=module('M_CONSOLE_'+name,group='02 · Mobilier')
    p['photo_landmarks']=json.dumps(poly)
    # Photo coordinates order TL TR BR BL. Lower front lip is horizontal and volumetric.
    a,b,c,d=pts
    normal=(b-a).cross(d-a).normalized()
    if normal.dot(eye-center)<0:normal=-normal
    prism(name+' · corps',[a,b,c,d],-normal*.12,ivory,p,.025)
    front_d=d+Vector((0,-.26,-.075)); front_c=c+Vector((0,-.26,-.075))
    prism(name+' · tablette clavier',[d,c,front_c,front_d],(0,0,-.12),light_ivory,p,.035)
    # Closed base with inset toe kick; independent true 3D cabinetry.
    lo=[Vector((v.x,v.y,.12)) for v in [front_d,front_c,b,a]]
    hi=[front_d,front_c,b,a]
    mesh(name+' · caisson',hi+lo,[(0,1,2,3),(7,6,5,4),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)],ivory,p,bevel_width=.018)
    beam(name+' · plinthe',lo[0]+Vector((0,.03,.04)),lo[1]+Vector((0,.03,.04)),.10,.12,dark,p)
    def surf(u,v,offset=.012):return a*(1-u)*(1-v)+b*u*(1-v)+c*u*v+d*(1-u)*v+normal*offset
    def tile(label,u0,u1,v0,v1,mat,offset=.025):
        return quad(label,[surf(u0,v1,offset),surf(u1,v1,offset),surf(u1,v0,offset),surf(u0,v0,offset)],mat,p)
    # Alternating real bezel/recess and dense flat instrumentation maps.
    columns=[(.025,.235,'panel'),(.255,.445,'screen'),(.465,.655,'screen'),(.68,.975,'panel')]
    for k,(u0,u1,kind) in enumerate(columns):
        v0,v1=.12,.80
        if kind=='screen':
            tile(name+' · joint CRT',u0,u1,v0,v1,dark,.028)
            tile(name+' · CRT lumineux',u0+.018,u1-.018,v0+.055,v1-.055,crt[(index+k)%6],.036)
            # raised rim around the four edges
            corners=[surf(u0,v0,.04),surf(u1,v0,.04),surf(u1,v1,.04),surf(u0,v1,.04)]
            for e in range(4):beam('CRT · encadrement',corners[e],corners[(e+1)%4],.025,.025,panelmat,p)
        else:
            tile(name+' · plaque instruments',u0,u1,.07,.91,plates[(index+k)%4],.025)
            for j in range(3):
                q=surf(u0+(u1-u0)*(j+1)/4,.75,.05)
                o=box('Interrupteur',q,(.024,.024,.035),red if j==0 else dark,p,bev=.004)
    # Keys on the real horizontal ledge, kept light and independently editable.
    for j in range(14):
        t=.20+j*.044; pt=d.lerp(c,t)+Vector((0,-.13,.006))
        box('Touche clavier',pt,(.045,.06,.013),panelmat,p,bev=.003)
    return p

console('ARRIERE_G',[(246,464),(620,442),(642,514),(269,554)],[3.8,5.05,4.2],0)
console('ARRIERE_D',[(853,443),(1253,463),(1199,548),(830,517)],[5.05,3.8,3.15],2)
console('LATERALE_G',[(-180,514),(242,465),(264,570),(-180,679)],[1.95,3.7,2.9],1)
console('LATERALE_D',[(1255,464),(1610,516),(1600,693),(1222,571)],[3.7,1.8,1.4],3)

# Foreground desk surfaces: real closed polygons with rounded bevels, no photo billboards.
def foreground(name,uv,z):
    pts=[at_z(q,z) for q in uv]; p=module('M_'+name,group='02 · Mobilier')
    prism(name+' · plateau',pts,(0,0,-.12),light_ivory,p,.045)
    center=sum(pts,Vector())/len(pts)
    inner=[center+(v-center)*.87-Vector((0,0,.15)) for v in pts]
    bottom=[Vector((v.x,v.y,.08)) for v in inner]; n=len(pts)
    mesh(name+' · caisson',inner+bottom,[tuple(range(n)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)],ivory,p,bevel_width=.018)
    for i in range(n):
        a,b=inner[i],inner[(i+1)%n]
        beam('Bandeau armoire',a,b,.045,.035,panelmat,p)
        if (b-a).length>.35:
            mid=(a+b)*.5;out=(Vector((mid.x,mid.y,0))-Vector((center.x,center.y,0))).normalized()*.012
            aa=a.lerp(b,.08)+out;bb=a.lerp(b,.92)+out
            pts=[Vector((aa.x,aa.y,.15)),Vector((bb.x,bb.y,.15)),Vector((bb.x,bb.y,.60)),Vector((aa.x,aa.y,.60))]
            prism('Porte de rangement',pts,out*.4,light_ivory,p,.006)
            hh=aa.lerp(bb,.18);hh.z=.53
            beam('Poignée encastrée rouge',hh,hh+(bb-aa).normalized()*.075,.016,.018,red,p)
    return p,center
fg,fgc=foreground('BUREAU_PREMIER_PLAN_G',[(-160,581),(180,610),(441,641),(475,665),(433,690),(95,714),(-180,691)],.78)
fd,fdc=foreground('BUREAU_PREMIER_PLAN_D',[(1052,630),(1323,602),(1620,622),(1620,794),(1123,711),(1000,679),(1007,649)],.78)

# Central plinth matches its footprint and layered construction, no stretched image.
tablecorners=[at_z(p,.88) for p in [(636,540),(821,540),(872,620),(598,620)]]
tablepos=sum(tablecorners,Vector())/4
table=module('M_TABLE_CENTRALE',(tablepos.x,tablepos.y,0),'02 · Mobilier')
tw=(tablecorners[2]-tablecorners[3]).length; td=(tablecorners[0].y-tablecorners[3].y)
box('Socle inférieur',(0,.38,.09),(tw*.62,td*.48,.18),panelmat,table,.025)
box('Pied central',(0,.29,.34),(tw*.64,td*.50,.45),ivory,table,.025)
box('Caisson médian',(0,.10,.56),(tw*.85,td*.86,.20),light_ivory,table,.025)
box('Joint sous plateau',(0,0,.705),(tw*.92,td*.92,.05),panelmat,table,.015)
box('Plateau chanfreiné',(0,0,.79),(tw,td,.18),light_ivory,table,.045)
quad('Schéma du plateau',[(-tw*.45,-td*.44,.884),(tw*.45,-td*.44,.884),(tw*.45,td*.44,.884),(-tw*.45,td*.44,.884)],schematic,table)

def chair(name,pos,angle=0,scale=1):
    p=module('M_SIEGE_'+name,pos,'02 · Mobilier'); p.rotation_euler.z=angle; p.scale=(scale,)*3
    cylinder('Embase pivot',(0,0,.1),.29,.12,dark,p,vertices=16)
    cylinder('Vérin',(0,0,.31),.055,.38,chrome,p,vertices=12)
    for i in range(4):
        a=i*math.pi/2; beam('Branche pied',(0,0,.11),(.4*math.cos(a),.4*math.sin(a),.08),.055,.065,panelmat,p)
    box('Coque assise',(0,0,.48),(.68,.62,.12),ivory,p,.06)
    box('Coussin assise',(0,-.01,.57),(.66,.60,.13),seatmat,p,.065)
    box('Dossier bas',(0,.23,.78),(.68,.17,.35),seatmat,p,.07,rot=(math.radians(-9),0,0))
    box('Dossier haut',(0,.28,1.04),(.67,.18,.25),seatmat,p,.08,rot=(math.radians(-9),0,0))
    for x in [-.38,.38]:
        box('Support accoudoir',(x,.02,.67),(.055,.11,.28),ivory,p,.025)
        box('Accoudoir',(x,-.03,.82),(.14,.48,.12),seatmat,p,.055)
    return p
ch=chair('DROIT',(1.45,2.63,0),math.radians(-60));ch.scale=(1.1,1.1,.81)
ch=chair('GAUCHE',(-.58,5.17,0),math.radians(-65));ch.scale=(.86,.86,.55)

# Lamp: plausible shade, stem and bulb, independently movable on the right ledge.
lp=at_z((1329,550),.85); lamp=module('M_LAMPE',lp,'03 · Accessoires')
lamp.scale=(.68,.68,.68)
cylinder('Lampe · socle',(0,0,.025),.15,.05,brass,lamp)
cylinder('Lampe · tige',(0,0,.27),.025,.50,brass,lamp,vertices=16)
bpy.ops.mesh.primitive_cone_add(vertices=32,radius1=.23,radius2=.14,depth=.29,location=(0,0,0))
o=bpy.context.object;o.name='Lampe · abat-jour';link(o,'03 · Accessoires');parent(o,lamp);o.location=(0,0,.59);o.data.materials.append(lampmat)
so=o.modifiers.new('Épaisseur toile','SOLIDIFY');so.thickness=.003
for z,r in [(.445,.23),(.735,.14)]:
    # Thin rolled rims.
    bpy.ops.mesh.primitive_torus_add(major_radius=r,minor_radius=.008,major_segments=32,minor_segments=6)
    o=bpy.context.object;o.name='Abat-jour · bord';link(o,'03 · Accessoires');parent(o,lamp);o.location=(0,0,z);o.data.materials.append(lampmat)

# A few readable physical props: papers, cups, bottle. Ambiguous photo marks become sensible props.
paper=material('Papier usé',(.58,.59,.52),.9)
for k,(x,y) in enumerate([(-.08,.02),(.13,-.08),(-.12,-.14)]):
    box('Feuille de travail',(fgc.x+x,fgc.y+y,.789+k*.002),(.15,.20,.002),paper,fg,0,rot=(0,0,k*.22))
for p,c in [(fg,fgc),(fd,fdc)]:
    x,y=c.x,c.y+.12
    quad('Pupitre · plaque de commandes',[(x-.17,y-.08,.789),(x+.17,y-.08,.789),(x+.17,y+.16,.789),(x-.17,y+.16,.789)],plates[2],p)
    for k in range(4):box('Pupitre · sélecteur',(x-.12+k*.07,y+.19,.802),(.022,.035,.024),red if k==0 else dark,p,.004)
cup=module('M_GOBELET',(fgc.x+.65,fgc.y+.12,.78),'03 · Accessoires')
cylinder('Gobelet',(0,0,.075),.055,.15,ivory,cup,vertices=20)
bot=module('M_BOUTEILLE',(fgc.x-.7,fgc.y-.03,.78),'03 · Accessoires')
cylinder('Bouteille',(0,0,.12),.047,.24,dark,bot,vertices=16)
cylinder('Bouchon',(0,0,.255),.025,.045,red,bot,vertices=12)

# User-requested 180 degree cyclorama; curved mesh with UV image projection.
cyc=module('M_CYCLORAMA_ESPACE',group='04 · Extérieur spatial')
verts=[]; faces=[]; N=64
for i in range(N+1):
    a=-math.pi/2+math.pi*i/N
    for z in [-5,18]: verts.append((18*math.sin(a),3+18*math.cos(a),z))
for i in range(N):faces.append((i*2,i*2+2,i*2+3,i*2+1))
o=mesh('Cyclorama demi-cercle · 180°',verts,faces,space,cyc)
uv=o.data.uv_layers.new(name='Projection cylindrique espace')
for poly in o.data.polygons:
    for li in poly.loop_indices:
        vi=o.data.loops[li].vertex_index; uv.data[li].uv=((vi//2)/N,vi%2)
for p in o.data.polygons:p.use_smooth=True
o['arc_degrees']=180; o['radius_m']=18
# Roof starfield also needs a backing above glazing. A separate horizontal extension belongs to the same cyclorama module.
quad('Cyclorama · retour supérieur',[(-18,-3,17),(18,-3,17),(18,21,17),(-18,21,17)],space,cyc)

# Lighting is real and editable. Diffuse ceiling bounce + broad frontal fill, luminous CRTs.
def area(name,loc,target,power,size,color=(1,1,1),p=None):
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size;data.color=color
    data.specular_factor=.1
    o=bpy.data.objects.new(name,data);coll('05 · Éclairage').objects.link(o);o.location=loc;o.rotation_euler=(Vector(target)-Vector(loc)).to_track_quat('-Z','Y').to_euler()
    # Keep studio bounce helpers out of mirror/transmission paths. Practical
    # fixtures remain real emissive meshes and still appear in the glazing.
    o.visible_glossy=False; o.visible_transmission=False
    if p:parent(o,p)
    return o
area('Oculus · grande source diffuse',(0,3.4,2.98),(0,3,0),180,2.4,(.88,.93,1))
area('Remplissage frontal doux',(0,-1.2,2.7),(0,4,1.2),95,4.5,(1,.95,.85))
area('Rebond latéral gauche',(-3,2.6,2.4),(0,3.5,.8),55,2.5,(.86,.91,1))
area('Rebond latéral droit',(3,2.6,2.4),(0,3.5,.8),50,2.5,(.96,.96,1))
fixtures=[(-3.2,2.6,2.65),(-2,4.8,2.50),(-.85,5.9,2.42),(0,6.2,2.42),(.85,5.9,2.42),(2,4.8,2.5),(3.2,2.6,2.65)]
for i,pt in enumerate(fixtures):
    p=module(f'M_PLAFONNIER_{i+1:02d}',pt,'05 · Éclairage')
    cylinder('Plafonnier · cerclage',(0,0,0),.105,.035,chrome,p)
    cylinder('Plafonnier · diffuseur',(0,0,-.023),.084,.012,glow,p)
    area('Plafonnier · lumière',(0,0,-.03),(0,0,-1),12,.17,(.9,.93,1),p)
data=bpy.data.lights.new('Lampe · ampoule','POINT');data.energy=8;data.color=(1,.76,.48);data.shadow_soft_size=.10
o=bpy.data.objects.new('Lampe · ampoule',data);coll('05 · Éclairage').objects.link(o);parent(o,lamp);o.location=(0,0,.49)
sc.world=bpy.data.worlds.new('Environnement très sombre');sc.world.use_nodes=True
sc.world.node_tree.nodes['Background'].inputs[0].default_value=(.12,.14,.18,1)
sc.world.node_tree.nodes['Background'].inputs[1].default_value=.12

sc.render.engine='CYCLES'; sc.cycles.samples=24 if PREVIEW else 96; sc.cycles.use_denoising=True
sc.cycles.preview_samples=24;sc.cycles.use_preview_denoising=True
sc.cycles.max_bounces=8;sc.cycles.transmission_bounces=8;sc.cycles.transparent_max_bounces=8
try:
    prefs=bpy.context.preferences.addons['cycles'].preferences; prefs.compute_device_type='OPTIX';prefs.get_devices()
    for dev in prefs.devices:dev.use=dev.type!='CPU'
    sc.cycles.device='GPU'
except Exception as exc:print('GPU fallback',exc)
sc.render.resolution_x=W;sc.render.resolution_y=H;sc.render.resolution_percentage=60 if PREVIEW else 100
sc.render.image_settings.file_format='PNG';sc.view_settings.view_transform='AgX';sc.view_settings.look='AgX - Medium Low Contrast';sc.view_settings.exposure=-1.2
sc.render.film_transparent=False
sc['source_photo']='022-cockpit-hexagonal-minimal_base.webp'
sc['scope']='Reconstruction manuelle guidée par photo. Arrière non visible à compléter ensuite.'
sc['workflow']='Modules physiques, UV locales, matériaux PBR, vitres transparentes, cyclorama 180 degrés.'
sc['calibration']='Estimation artistique: F=650px, hauteur=1.6m, inclinaison=-4 degrés.'
# Secondary cameras prove actual volume and support mouse navigation.
for name,loc,target in [('CAM_LATERALE',(.8,.35,1.6),(0,4,1.15)),('CAM_DETAIL',(.6,2.35,1.65),(2.6,4.5,1.3)),('CAM_VOLUME',(-3,-2,4),(0,3,1))]:
    d=camdata.copy();o=bpy.data.objects.new(name,d);coll('06 · Caméras').objects.link(o);o.location=loc;o.rotation_euler=(Vector(target)-Vector(loc)).to_track_quat('-Z','Y').to_euler()
    d.lens=21
for screen in bpy.data.screens:
    for ar in screen.areas:
        if ar.type=='VIEW_3D':
            ar.spaces.active.region_3d.view_perspective='CAMERA';ar.spaces.active.region_3d.view_camera_zoom=0
            ar.spaces.active.shading.type='RENDERED';ar.spaces.active.shading.use_scene_world=True;ar.spaces.active.shading.use_scene_lights=True
            ar.spaces.active.overlay.show_extras=False
bpy.ops.object.select_all(action='DESELECT')
bpy.context.view_layer.update()
# Individual mesh pivots and module roots are local to the physical parts.
for obj in list(sc.objects):
    if obj.type=='MESH' and len(obj.data.vertices):
        center=sum((Vector(v) for v in obj.bound_box),Vector())/8
        obj.data.transform(Matrix.Translation(-center)); obj.location+=obj.matrix_basis.to_3x3()@center
bpy.context.view_layer.update()
for obj in list(sc.objects):
    if obj.get('module') and obj.location.length<.001 and obj.children:
        child_matrices={c:c.matrix_world.copy() for c in obj.children}
        corners=[c.matrix_world@Vector(v) for c in obj.children if c.type=='MESH' for v in c.bound_box]
        if corners:
            low=Vector(tuple(min(v[i] for v in corners) for i in range(3))); high=Vector(tuple(max(v[i] for v in corners) for i in range(3)))
            obj.location=((low.x+high.x)/2,(low.y+high.y)/2,low.z)
            bpy.context.view_layer.update()
            for c,m in child_matrices.items():c.matrix_world=m
bpy.context.view_layer.update()
report={'modules':len([o for o in sc.objects if o.get('module')]),'mesh_objects':len([o for o in sc.objects if o.type=='MESH']),
        'triangles_base':0,'triangles_with_modifiers':0,'windows':len([o for o in sc.objects if o.get('window_glass')]),
        'materials':len(bpy.data.materials),'images_packed':len([im for im in bpy.data.images if im.packed_file]),
        'camera_focal_mm':camdata.lens,'calibration_estimated':True,'scope':sc['scope']}
dg=bpy.context.evaluated_depsgraph_get()
for o in sc.objects:
    if o.type=='MESH':
        o.data.calc_loop_triangles();report['triangles_base']+=len(o.data.loop_triangles)
        e=o.evaluated_get(dg);me=e.to_mesh();me.calc_loop_triangles();report['triangles_with_modifiers']+=len(me.loop_triangles);e.to_mesh_clear()
(OUT/'scene-report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'cockpit-photo-modulaire.blend'))
sc.render.filepath=str(OUT/('preview-photo.png' if PREVIEW else 'rendu-photo.png'));bpy.ops.render.render(write_still=True)
print('COCKPIT_BUILD_OK',json.dumps(report),flush=True)
