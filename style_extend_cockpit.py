"""V2: generated surface materials + invented modular rear. V1 remains untouched."""
import bpy,math,json,ast,sys,hashlib
from pathlib import Path
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'output/cockpit-photo-modulaire-v2';MAPS=OUT/'maps'
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'output/cockpit-photo-modulaire-v1/cockpit-photo-modulaire.blend'))
sc=bpy.context.scene;sc.name='Cockpit patiné — extension arrière'
eye=Vector((0,0,1.6));groups={c.name:c for c in sc.collection.children}
aliases={'ivory':'Coque · peinture ivoire satinée','light_ivory':'Chants · ivoire clair','panelmat':'Panneaux · gris chaud',
         'dark':'Joints · caoutchouc anthracite','chrome':'Aluminium brossé','wood':'Porte · brun tabac',
         'seatmat':'Siège · vinyle olive grisé','red':'Commandes · rouge brique','glass':'Vitrage · transparent IOR 1.45',
         'glow':'Plafonniers · blanc opalin','space':'Cyclorama · espace GPT Image','floor':'Sol · résine taupe satinée'}
for var,name in aliases.items():globals()[var]=bpy.data.materials[name]
plates=[bpy.data.materials[f'Instrumentation {i+1:02d}'] for i in range(4)]
# Reuse only pure modeling helpers, never execute the V1 builder or its file writes.
tree=ast.parse((ROOT/'build_photo_cockpit.py').read_text(encoding='utf-8'))
needed={'coll','link','module','parent','material','image_mat','bevel','mesh','box','cylinder','quad','beam','prism','window','area'}
defs=ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in needed],type_ignores=[])
exec(compile(defs,'cockpit_modeling_helpers','exec'),globals())
crt=[bpy.data.materials.get(f'CRT {i+1:02d} · phosphore vert') or image_mat(f'CRT {i+1:02d} · phosphore vert',ROOT/f'output/cockpit-photo-modulaire-v1/maps/crt-{i+1:02d}.png',2.4,.23) for i in range(6)]
originals=set(sc.objects)
def geometry_digest(objects):
    h=hashlib.sha256()
    for o in sorted(objects,key=lambda x:x.name):
        if o.type=='MESH':
            h.update(o.name.encode());h.update(str([round(v,6) for row in o.matrix_world for v in row]).encode())
            h.update(str([[round(c,6) for c in v.co] for v in o.data.vertices]).encode())
    return h.hexdigest()
front_before=geometry_digest(originals)
def load_image(path):
    im=bpy.data.images.load(str(path),check_existing=True);im.pack();return im
paintimg=load_image(MAPS/'ivoire-patine.png');floorimg=load_image(MAPS/'sol-resine-usee.png');instimg=load_image(MAPS/'instruments-atlas.png')

def surface(m,im,scale,tint,roughness,bump_distance):
    nt=m.node_tree;bs=nt.nodes.get('Principled BSDF')
    for link_ in list(nt.links):
        if link_.to_node==bs and link_.to_socket.name in ['Base Color','Roughness','Normal']:nt.links.remove(link_)
    tc=nt.nodes.new('ShaderNodeTexCoord');tc.label='Coordonnées locales : suivent le module'
    v=nt.nodes.new('ShaderNodeVectorMath');v.operation='SCALE';v.inputs[3].default_value=scale;nt.links.new(tc.outputs['Object'],v.inputs[0])
    tex=nt.nodes.new('ShaderNodeTexImage');tex.image=im;tex.projection='BOX';tex.projection_blend=.15;tex.label='Albédo généré — sans reflet de lampe'
    nt.links.new(v.outputs['Vector'],tex.inputs['Vector'])
    mix=nt.nodes.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=1;mix.inputs[2].default_value=(*tint,1)
    nt.links.new(tex.outputs['Color'],mix.inputs[1]);nt.links.new(mix.outputs[0],bs.inputs['Base Color'])
    ramp=nt.nodes.new('ShaderNodeValToRGB');ramp.label='Rugosité variable, reflets calculés'
    ramp.color_ramp.elements[0].position=.14;ramp.color_ramp.elements[0].color=(roughness+.10,)*3+(1,)
    ramp.color_ramp.elements[1].position=.75;ramp.color_ramp.elements[1].color=(roughness-.035,)*3+(1,)
    nt.links.new(tex.outputs['Color'],ramp.inputs[0]);nt.links.new(ramp.outputs[0],bs.inputs['Roughness'])
    bump=nt.nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.16;bump.inputs['Distance'].default_value=bump_distance
    nt.links.new(tex.outputs['Color'],bump.inputs['Height']);nt.links.new(bump.outputs[0],bs.inputs['Normal'])
    m['generated_albedo']=im.name;m['texture_coordinates']='local object, metric scale'
surface(ivory,paintimg,1.1,(.77,.80,.83),.34,.0013)
surface(light_ivory,paintimg,1.3,(.88,.89,.90),.30,.001)
surface(panelmat,paintimg,1.5,(.56,.60,.61),.40,.001)
surface(floor,floorimg,.85,(.92,.91,.89),.115,.00025)
bs=floor.node_tree.nodes.get('Principled BSDF');bs.inputs['Coat Weight'].default_value=.18;bs.inputs['Coat Roughness'].default_value=.24
nt=floor.node_tree;previous=bs.inputs['Base Color'].links[0].from_socket
soft=nt.nodes.new('ShaderNodeMixRGB');soft.blend_type='MIX';soft.inputs[0].default_value=.40;soft.inputs[1].default_value=(.22,.215,.205,1)
nt.links.new(previous,soft.inputs[2]);nt.links.new(soft.outputs[0],bs.inputs['Base Color'])
for i,m in enumerate(plates):
    nt=m.node_tree;bs=nt.nodes.get('Principled BSDF');tex=next(n for n in nt.nodes if n.type=='TEX_IMAGE');tex.image=instimg
    tc=nt.nodes.new('ShaderNodeTexCoord');mul=nt.nodes.new('ShaderNodeVectorMath');mul.operation='MULTIPLY';mul.inputs[1].default_value=(.492,.492,1)
    add=nt.nodes.new('ShaderNodeVectorMath');add.operation='ADD';add.inputs[1].default_value=(.004+(i%2)*.5,.004+(1-i//2)*.5,0)
    nt.links.new(tc.outputs['UV'],mul.inputs[0]);nt.links.new(mul.outputs[0],add.inputs[0]);nt.links.new(add.outputs[0],tex.inputs[0])
    bs.inputs['Roughness'].default_value=.36
    bump=nt.nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.12;bump.inputs['Distance'].default_value=.0006
    nt.links.new(tex.outputs['Color'],bump.inputs['Height']);nt.links.new(bump.outputs[0],bs.inputs['Normal'])
    m['atlas_quadrant']=i;m['note']='Image atlas generated; knobs in the print are small details, not deep geometry.'
amber=material('Voyants · ambre',(.95,.23,.025),.23,0,3)
ledred=material('Voyants · rouge',(.6,.025,.008),.25,0,1.5)
labelmat=material('Marquages · graphite',(.04,.043,.036),.8)

# Add real grille detail to the original closed cabinets, attached to their existing modules.
def vent(name,a,b,z0,z1,p,normal):
    a,b=Vector(a),Vector(b);normal=Vector(normal).normalized();a.z=z0;b.z=z0
    inv=p.matrix_world.inverted();off=normal*.018
    pts=[a+off,b+off,Vector((b.x,b.y,z1))+off,Vector((a.x,a.y,z1))+off]
    quad(name+' · fond',[inv@v for v in pts],dark,p)
    for k in range(9):
        aa=a+normal*.025;bb=b+normal*.025;aa.z=bb.z=z0+.018+k*(z1-z0-.035)/8
        beam(name+' · lamelle',inv@aa,inv@bb,.012,.022,panelmat,p)
for obj in list(originals):
    if obj.type=='MESH' and '· caisson' in obj.name and obj.parent and obj.parent.name.startswith('M_CONSOLE_'):
        a=obj.matrix_world@obj.data.vertices[0].co;b=obj.matrix_world@obj.data.vertices[1].co
        n=(b-a).cross(Vector((0,0,1))).normalized()
        if n.dot(eye-(a+b)*.5)<0:n=-n
        vent('Ventilation '+obj.name,a.lerp(b,.12),a.lerp(b,.33),.21,.43,obj.parent,n)
        vent('Ventilation '+obj.name,a.lerp(b,.72),a.lerp(b,.9),.21,.43,obj.parent,n)

# Rear footprint joins the photographed side-window termination precisely.
def front_edge(name,indices):
    ob=bpy.data.objects[name];return [ob.matrix_world@ob.data.vertices[i].co for i in indices]
lt,lb=front_edge('G1 · cadre plein',[0,3]);rt,rb=front_edge('D3 · cadre plein',[1,2])
rear_group='07 · Extension arrière modulaire'
p=module('M_ARR_MONTANTS_TRANSITION',group=rear_group)
for title,top,bottom in [('G',lt,lb),('D',rt,rb)]:
    beam('Jonction avant-arrière '+title,Vector((bottom.x,bottom.y,0)),Vector((top.x,top.y,3.15)),.32,.34,ivory,p)
def wall_bay(name,bl,br,tl,tr):
    p=module('M_ARR_'+name,group=rear_group)
    bl,br,tl,tr=map(Vector,[bl,br,tl,tr])
    window(name+' · fenêtre',[tl,tr,br,bl],.18,.13,p=p)
    n=(br-bl).cross(Vector((0,0,1))).normalized()
    if n.dot((bl+br)*.5-eye)<0:n=-n
    prism(name+' · allège',[bl,br,Vector((br.x,br.y,0)),Vector((bl.x,bl.y,0))],n*.14,ivory,p)
    prism(name+' · frise supérieure',[tl,tr,Vector((tr.x,tr.y,3.13)),Vector((tl.x,tl.y,3.13))],n*.14,ivory,p)
    beam(name+' · appui',bl,br,.09,.16,light_ivory,p)
    beam(name+' · traverse',tl,tr,.16,.20,ivory,p)
    for a in [bl,br]:beam(name+' · montant bas',(a.x,a.y,.04),a,.06,.06,panelmat,p)
    return p
# Two long side bays on each side, then angled corners and rear glazing.
for side,top,bottom,sgn in [('GAUCHE',lt,lb,-1),('DROIT',rt,rb,1)]:
    endb=Vector((sgn*5,-1.35,1.1));endt=Vector((sgn*5,-1.35,2.82))
    for k in range(2):
        t0=k/2;t1=(k+1)/2
        wall_bay(f'COTE_{side}_{k+1}',bottom.lerp(endb,t0),bottom.lerp(endb,t1),top.lerp(endt,t0),top.lerp(endt,t1))
    cb=Vector((sgn*3.6,-3.4,1.1));ct=Vector((sgn*3.6,-3.4,2.82))
    wall_bay('ANGLE_'+side,endb,cb,endt,ct)
    db=Vector((sgn*.95,-3.4,1.1));dt=Vector((sgn*.95,-3.4,2.82))
    wall_bay('FOND_'+side,cb,db,ct,dt)

# Floor extension is separate and aligned with the original slab.
p=module('M_ARR_SOL',group=rear_group);box('Sol arrière',(0,-3.05,-.09),(13,1.1,.18),floor,p,.015)
# Side skylights and central ceiling cassettes, leaving the original front roof unchanged.
for side in [-1,1]:
    for j,(y0,y1) in enumerate([(-3.4,-1.25),(-1.25,1.55)]):
        p=module(f'M_ARR_TOIT_{side}_{j}',group=rear_group)
        x0,x1=sorted([side*1.65,side*5.02])
        z0=2.95+(y0+3.4)/4.95*.09;z1=2.95+(y1+3.4)/4.95*.09
        window('Toit arrière',[(x0,y0,z0),(x1,y0,z0),(x1,y1,z1),(x0,y1,z1)],.12,.21,p=p)
for j,(y0,y1) in enumerate([(-3.4,-1.75),(-1.75,-.1),(-.1,1.55)]):
    p=module('M_ARR_PLAFOND_'+str(j),group=rear_group)
    box('Cassette plafond',(0,(y0+y1)/2,3.02),(3.32,y1-y0+.015,.12),ivory,p,.012)
    box('Plafonnier linéaire',(0,(y0+y1)/2,2.94),(1.45,.14,.035),glow,p,.02)
    area('Éclairage arrière',(0,(y0+y1)/2,2.88),(0,(y0+y1)/2,0),65,1.4,(1,.80,.57))
    for x in [-1.5,1.5]:box('Rainure technique',(x,(y0+y1)/2,2.95),(.035,y1-y0-.14,.02),dark,p,.004)
# Narrow roof junction caps across the side transition.
def roof_reference(pixel,z):
    direction=Matrix.Rotation(math.radians(86),3,'X')@Vector(((pixel[0]-728)/650,(408-pixel[1])/650,-1))
    return eye+direction*((z-eye.z)/direction.z)
for s in [-1,1]:
    p=module('M_ARR_RACCORD_TOIT_'+str(s),group=rear_group)
    box('Raccord latéral supérieur',(s*4.82,2.35,2.96),(.44,1.65,.15),ivory,p,.025)
    corner=roof_reference((-180,-100) if s<0 else (1630,-100),3.02)
    far=roof_reference((-80,224) if s<0 else (1530,216),2.78)
    near=roof_reference((250,-95) if s<0 else (1200,-95),3.02)
    inner=corner.lerp(near,(s*1.65-corner.x)/(near.x-corner.x))
    outer=corner.lerp(far,(s*5.05-corner.x)/(far.x-corner.x))
    profile=[inner,corner,outer]
    for k in range(2):
        a,b=profile[k:k+2]
        window('Jonction verrière ajustée',[(a.x,1.55,3.04),(b.x,1.55,3.04),b,a],.10,.10,p=p)
p=module('M_ARR_JONCTION_CENTRALE',group=rear_group)
box('Jonction plafond avant-arrière',(0,1.76,3.03),(3.34,.42,.12),ivory,p,.015)

# Central rear pressure-door and its functional frame; separate pivoted leaf.
p=module('M_ARR_CLOISON_SAS',group=rear_group)
for x in [-.835,.835]:box('Sas · montant',(x,-3.43,1.56),(.23,.22,3.12),ivory,p,.025)
box('Sas · linteau',(0,-3.43,2.68),(1.46,.22,.84),ivory,p,.025)
box('Sas · seuil',(0,-3.33,.025),(1.50,.38,.05),chrome,p,.01)
door=module('M_ARR_PORTE_SAS',(-.70,-3.45,0),rear_group)
box('Sas · porte bas',(.70,0,.68),(1.38,.12,1.36),ivory,door,.055)
for x in [.16,1.24]:box('Sas · porte bord hublot',(x,0,1.78),(.30,.12,.84),ivory,door,.028)
box('Sas · porte haut',(.70,0,2.16),(1.38,.12,.12),ivory,door,.025)
quad('Sas · vitrage hublot',[(.31,.015,1.38),(1.09,.015,1.38),(1.09,.015,2.10),(.31,.015,2.10)],glass,door,.01)['window_glass']=True
for x in [.32,1.08]:box('Sas · joint hublot',(x,.072,1.75),(.018,.02,.72),dark,door,.005)
for z in [1.39,2.1]:box('Sas · joint hublot',(.70,.072,z),(.77,.02,.018),dark,door,.005)
box('Sas · poignée',(.20,.11,.97),(.035,.08,.27),chrome,door,.015)
for z in [.28,1.8]:cylinder('Sas · charnière',(.0,0,z),.025,.20,chrome,door,vertices=12)
# An enclosed lit vestibule is visible through the real door glazing.
airlock=module('M_ARR_VESTIBULE',group=rear_group)
box('Vestibule · fond',(0,-4.65,1.35),(1.70,.15,2.70),panelmat,airlock,.02)
for x in [-.82,.82]:box('Vestibule · paroi',(x,-4.02,1.35),(.12,1.30,2.70),ivory,airlock,.02)
box('Vestibule · toit',(0,-4.02,2.72),(1.76,1.35,.12),ivory,airlock,.02)
box('Vestibule · sol',(0,-4.02,-.06),(1.76,1.35,.12),floor,airlock,.02)
area('Veilleuse vestibule',(0,-4.03,2.55),(0,-4,0),18,.6,(1,.78,.52))

def rear_console(name,loc,width=2.2,rotation=0):
    p=module('M_ARR_CONSOLE_'+name,loc,rear_group);p.rotation_euler.z=rotation
    w=width/2
    box('Console arrière · caisson',(0,0,.37),(width,.78,.74),ivory,p,.045)
    box('Console arrière · plinthe',(0,0,.08),(width-.07,.72,.13),dark,p,.015)
    pts=[(-w,.40,.76),(w,.40,.76),(w,-.30,1.12),(-w,-.30,1.12)]
    prism('Console arrière · plan incliné',pts,(0,0,-.08),light_ivory,p,.025)
    def point(u,v):return Vector(pts[0]).lerp(Vector(pts[1]),u)*(1-v)+Vector(pts[3]).lerp(Vector(pts[2]),u)*v+Vector((0,.005,.013))
    for k,(u0,u1) in enumerate([(.02,.29),(.32,.65),(.68,.98)]):
        q=[point(u0,.08),point(u1,.08),point(u1,.92),point(u0,.92)]
        quad('Console arrière · plaque',q,dark if k==1 else plates[(k+len(name))%4],p)
        if k==1:
            quad('Console arrière · écran CRT',[point(u0+.018,.15),point(u1-.018,.15),point(u1-.018,.85),point(u0+.018,.85)],crt[len(name)%6],p)
        for u in [u0+.04,u1-.04]:
            pos=point(u,.1);o=cylinder('Console arrière · voyant',pos,.014,.008,amber,p,vertices=12);o.rotation_euler.x=math.radians(-62)
    # Two recessed access doors, grilles and real fasteners on the cabinet front.
    for x in [-width*.25,width*.25]:
        box('Console arrière · porte technique',(x,.405,.40),(width*.47,.022,.50),light_ivory,p,.012)
        box('Console arrière · prise encastrée',(x+.13,.425,.56),(.08,.016,.018),red,p,.004)
        box('Console arrière · grille noire',(x,.43,.29),(.30,.018,.18),dark,p,.008)
        for j in range(7):box('Console arrière · persienne',(x,.445,.22+j*.024),(.28,.018,.009),panelmat,p,.002)
    return p
rear_console('COMMUNICATIONS',(-2.26,-2.86,0),2.35)
rear_console('SYSTEMES',(2.26,-2.86,0),2.35)
rear_console('GAUCHE',(-4.57,.4,0),2.65,-math.pi/2)
rear_console('DROIT',(4.57,.4,0),2.65,math.pi/2)

# Freestanding storage/rack modules at the diagonal corners, keeping the central path empty.
for s in [-1,1]:
    p=module('M_ARR_RANGEMENT_'+str(s),(s*3.85,-1.75,0),rear_group);p.rotation_euler.z=s*math.radians(34)
    box('Armoire technique',(0,0,.65),(.85,.55,1.30),ivory,p,.035)
    for z in [.30,.70,1.10]:
        box('Tiroir',(0,.291,z),(.77,.025,.32),light_ivory,p,.012)
        box('Poignée de tiroir',(0,.327,z+.10),(.20,.045,.024),chrome,p,.008)
    quad('Armoire · étiquette',[(-.18,.311,1.2),(.18,.311,1.2),(.18,.311,1.29),(-.18,.311,1.29)],plates[3],p)

# Complete the spatial backdrop with a second independent 180-degree cyclorama.
p=module('M_CYCLORAMA_ESPACE_ARRIERE',group='04 · Extérieur spatial')
vs=[];fs=[];N=64
for i in range(N+1):
    a=math.pi/2+math.pi*i/N
    for z in [-5,18]:vs.append((18*math.sin(a),3+18*math.cos(a),z))
for i in range(N):fs.append((2*i,2*i+2,2*i+3,2*i+1))
o=mesh('Cyclorama arrière · 180°',vs,fs,space,p);uv=o.data.uv_layers.new(name='UV_espace')
for poly in o.data.polygons:
    poly.use_smooth=True
    for li in poly.loop_indices:
        vi=o.data.loops[li].vertex_index;uv.data[li].uv=((vi//2)/N,vi%2)
o['arc_degrees']=180
quad('Cyclorama · retour ciel arrière',[(-18,-18,17),(18,-18,17),(18,3,17),(-18,3,17)],space,p)

# Warm practical light, neutral skylight, and actual movable specular reflections.
for o in list(originals):
    if o.type=='LIGHT':
        if 'Oculus' in o.name:o.data.energy=240;o.data.color=(.92,.95,1)
        elif 'Remplissage' in o.name:o.data.energy=155;o.data.color=(1,.88,.72)
        elif 'Rebond' in o.name:o.data.energy*=1.35;o.data.color=(1,.87,.72)
        elif 'Plafonnier' in o.name:o.data.energy=24;o.data.color=(1,.79,.54)
bs=glow.node_tree.nodes.get('Principled BSDF');bs.inputs['Emission Color'].default_value=(1,.79,.52,1);bs.inputs['Emission Strength'].default_value=8
# Retain the fixture reflections, but keep the large invisible helper disks out of glass.
for i,x in enumerate([-4.65,4.65]):
    for j,y in enumerate([-1.1,1.2]):
        p=module(f'M_ARR_LAMPE_{i}_{j}',(x,y,2.68),'05 · Éclairage')
        cylinder('Plafonnier arrière · bague',(0,0,0),.12,.035,chrome,p)
        cylinder('Plafonnier arrière · opale',(0,0,-.022),.105,.015,glow,p)
        area('Plafonnier arrière',(0,0,-.04),(0,0,-1),18,.20,(1,.79,.54),p)

# Supplemental cameras; original source camera remains unchanged.
def camera(name,loc,target,lens=18):
    d=bpy.data.cameras.new(name);o=bpy.data.objects.new(name,d);coll('06 · Caméras').objects.link(o)
    o.location=loc;o.rotation_euler=(Vector(target)-Vector(loc)).to_track_quat('-Z','Y').to_euler();d.lens=lens;d.clip_end=200;return o
camera('CAM_ARRIERE',(0,.35,1.6),(0,-3.0,1.4),17)
camera('CAM_ARRIERE_OBLIQUE',(1.7,1.0,1.6),(-1.6,-2.5,1.2),19)
camera('CAM_RACCORD_GAUCHE',(0,1.8,1.6),(-4.8,1.8,1.6),18)
camera('CAM_360',(0,.0,1.6),(0,1,1.6),18)
sc.camera=bpy.data.objects['CAM_PHOTO']
sc.view_settings.exposure=-.85;sc.view_settings.look='AgX - Medium High Contrast'
sc.render.use_persistent_data=True
sc.cycles.samples=48 if '--preview' in sys.argv else 96;sc.cycles.use_denoising=True
sc.cycles.preview_samples=24;sc.cycles.max_bounces=10;sc.cycles.transmission_bounces=8
try:
    prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
    for dev in prefs.devices:dev.use=dev.type!='CPU'
    sc.cycles.device='GPU'
except Exception as e:print(e)
sc.render.resolution_percentage=65 if '--preview' in sys.argv else 100
sc['scope']='Front photographié conservé et texturé ; extension arrière inventée et modulaire.'
sc['texture_provenance']='3 textures générées avec GPT Image intégré, projection locale, roughness et bump procéduraux dérivés.'

# Recenter only NEW mesh pivots and new zero-position module roots. Do not modify the original front geometry.
bpy.context.view_layer.update();new_objects=set(sc.objects)-originals
for o in new_objects:
    if o.type=='MESH':
        c=sum((Vector(v) for v in o.bound_box),Vector())/8;o.data.transform(Matrix.Translation(-c));o.location+=o.matrix_basis.to_3x3()@c
bpy.context.view_layer.update()
for o in new_objects:
    if o.get('module') and o.location.length<.001 and o.children:
        mats={c:c.matrix_world.copy() for c in o.children};corners=[c.matrix_world@Vector(v) for c in o.children if c.type=='MESH' for v in c.bound_box]
        if corners:
            lo=Vector(tuple(min(v[i] for v in corners) for i in range(3)));hi=Vector(tuple(max(v[i] for v in corners) for i in range(3)))
            o.location=((lo.x+hi.x)*.5,(lo.y+hi.y)*.5,lo.z);bpy.context.view_layer.update()
            for c,m in mats.items():c.matrix_world=m
bpy.context.view_layer.update()
report={'modules':len([o for o in sc.objects if o.get('module')]),'meshes':len([o for o in sc.objects if o.type=='MESH']),
        'front_geometry_before':front_before,'front_geometry_after':geometry_digest(originals),'generated_maps':[paintimg.name,floorimg.name,instimg.name],
        'new_modules':[o.name for o in new_objects if o.get('module')],'base_triangles':0,'evaluated_triangles':0}
dg=bpy.context.evaluated_depsgraph_get()
for o in sc.objects:
    if o.type=='MESH':
        o.data.calc_loop_triangles();report['base_triangles']+=len(o.data.loop_triangles)
        ev=o.evaluated_get(dg);me=ev.to_mesh();me.calc_loop_triangles();report['evaluated_triangles']+=len(me.loop_triangles);ev.to_mesh_clear()
assert report['front_geometry_before']==report['front_geometry_after'],'Original front geometry changed'
(OUT/'scene-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'cockpit-patine-360.blend'))
if '--no-render' not in sys.argv:
    for name,f in [('CAM_PHOTO','avant'),('CAM_ARRIERE','arriere'),('CAM_ARRIERE_OBLIQUE','arriere-oblique')]:
        sc.camera=bpy.data.objects[name];sc.render.filepath=str(OUT/(f+'.png'));bpy.ops.render.render(write_still=True)
print('V2_BUILD_OK',json.dumps(report,ensure_ascii=False),flush=True)
