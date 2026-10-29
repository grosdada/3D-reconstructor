"""Reference A1 brutalist district: editable buildings, real facade recesses.

Explicit art-directed recipe with estimated dimensions, not photogrammetry.
Procedural surfaces stay local to every module. No downloaded dependencies.
"""
import bpy,math,random,json,bmesh
from pathlib import Path
from mathutils import Vector
from .modular_scene import Builder,material,camera
from .station_procedural import node,feed,math as smath,mapped,noise,mix


def concrete(name,color,seed=0):
    m=material(name,color,.79);t=m.node_tree;bs=t.nodes.get('Principled BSDF')
    tc=node(t,'ShaderNodeTexCoord','Coordonnees locales en metres');info=node(t,'ShaderNodeObjectInfo','Variation par module')
    off=node(t,'ShaderNodeVectorMath','Origine du grain');off.operation='ADD';feed(t,off.inputs[0],tc.outputs['Object']);feed(t,off.inputs[1],info.outputs['Random']);co=off.outputs[0]
    broad=noise(t,'Nuances du ciment',co,.38,3);fine=noise(t,'Granulat mineral',co,95,2)
    v=node(t,'ShaderNodeVectorMath','Ruissellement vertical');v.operation='MULTIPLY';feed(t,v.inputs[0],co);v.inputs[1].default_value=(3.8,3.8,.085)
    rain=noise(t,'Coulees fines',v.outputs[0],3.5,3);mask=mapped(t,'Patine · pluie',rain,.46,.74,0,.29)
    base=mix(t,'Beton · nuances discretes',mapped(t,'Nuance',broad,0,1,.05,.32),(*color,1),(*(c*.60 for c in color),1))
    base=mix(t,'Beton · coulures',mask,base,(*(c*.32 for c in color),1))
    ao=node(t,'ShaderNodeAmbientOcclusion','Depots sous les corniches');ao.samples=4;ao.only_local=True;ao.inputs['Distance'].default_value=.36
    base=mix(t,'Beton · creux',smath(t,'MULTIPLY',smath(t,'SUBTRACT',1,ao.outputs['AO']),.30),base,(.055,.065,.052,1));feed(t,bs.inputs['Base Color'],base)
    feed(t,bs.inputs['Roughness'],mapped(t,'Rugosite minerale',fine,0,1,.65,.91))
    bump=node(t,'ShaderNodeBump','Grain · 0.8 mm');bump.inputs['Distance'].default_value=.0008;bump.inputs['Strength'].default_value=.34;feed(t,bump.inputs['Height'],fine);feed(t,bs.inputs['Normal'],bump.outputs[0])
    m['pa_procedural']=True;m['pa_coordinate_space']='Object local metres'
    from .city_material_detail import refine
    refine(m)
    return m


class Batch:
    """Batch little boxes by material, keep each facade/storey independently movable."""
    def __init__(self,b,parent,name):self.b=b;self.parent=parent;self.name=name;self.parts={}
    def box(self,loc,size,mat):
        vs,fs=self.parts.setdefault(mat.name,([],[]));n=len(vs);x,y,z=(s/2 for s in size);a,c,d=loc
        vs.extend([(a+xx,c+yy,d+zz) for xx,yy,zz in [(-x,-y,-z),(x,-y,-z),(x,y,-z),(-x,y,-z),(-x,-y,z),(x,-y,z),(x,y,z),(-x,y,z)]])
        fs.extend([tuple(n+j for j in f) for f in [(3,2,1,0),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)]])
    def emit(self,bevel=.025):
        out=[]
        for name,(vs,fs) in self.parts.items():
            o=self.b.mesh(self.name+' · '+name,vs,fs,bpy.data.materials[name],self.parent,bevel);o['pa_city_part']=True;out.append(o)
        return out


def build(scene,output,asset_root,reference,seed=407):
    rng=random.Random(seed);out=Path(output);out.mkdir(parents=True,exist_ok=True)
    if scene.get('pa_city_recipe'):raise ValueError('Ville deja presente; construire dans une scene vide.')
    if any(s.get('pa_city_recipe') for s in bpy.data.scenes if s!=scene):raise ValueError('Une ville A1 existe deja dans ce fichier; utiliser un nouveau fichier.')
    if any(o.type=='MESH' for o in scene.objects):raise ValueError('Choisir une scene vide pour cette recette de ville.')
    b=Builder(scene,'VILLE · architecture A1');roots=[];targets=[]
    city=b.root('VILLE · ensemble');city['pa_module']=True
    def root(name,loc=(0,0,0),parent=city):
        o=b.root(name,loc,parent);o['pa_module']=True;roots.append(o);return o
    cement=concrete('VILLE · beton brut gris sauge',(.285,.305,.255))
    light=concrete('VILLE · beton clair erode',(.40,.405,.33))
    dark=concrete('VILLE · beton humide sombre',(.16,.19,.16))
    old=concrete('VILLE · enduit gris brun',(.265,.265,.21))
    trim=material('VILLE · cadres aluminium terni',(.13,.16,.145),.52,.45)
    glass=material('VILLE · vitrage vert gris',(.035,.058,.052),.29,.35);glass.node_tree.nodes['Principled BSDF'].inputs['Transmission Weight'].default_value=.15
    glass2=material('VILLE · vitrage poussiereux',(.10,.135,.12),.48,.20)
    inside=material('VILLE · interieur profond',(.008,.014,.013),.88)
    rubber=material('VILLE · joints noirs',(.025,.033,.027),.87)
    roof=concrete('VILLE · etancheite vieillie',(.095,.103,.09))
    rust=concrete('VILLE · tuiles et tole oxydee',(.16,.095,.065))
    concrete_mats=[cement,light,dark,old]
    def box(name,loc,size,m,p,bevel=.025,project=False):
        o=b.box(name,loc,size,m,p,bevel)
        if project:o['pa_city_project']=True;targets.append(o)
        return o
    def roof_detail(p,w,d,h):
        box('Toiture · membrane',(0,0,h+.03),(w,d,.12),roof,p,.02)
        for y in (-d/2,d/2):box('Acrotere',(0,y,h+.30),(w+.18,.24,.62),cement,p,.03,True)
        for x in (-w/2,w/2):box('Acrotere',(x,0,h+.30),(.24,d,.62),cement,p,.03,True)
        for k in range(3):
            x=rng.uniform(-w*.35,w*.35);y=rng.uniform(-d*.3,d*.3)
            box('Equipement de toit',(x,y,h+.45),(1.2,.75,.8),trim,p,.06)
            b.cylinder('Conduit toiture',(x+.8,y,h+1.0),.16,1.7,trim,p,vertices=10)
        for k in range(2):
            x=rng.uniform(-w*.38,w*.38);y=rng.uniform(-d*.38,d*.38);z=rng.uniform(2,4.5)
            b.cylinder('Antenne fine',(x,y,h+z/2),.035,z,trim,p,vertices=8)
    def facade(p,w,d,h,floors,cols,mat,mode='regular',project=True):
        # Every storey consists of spandrels/piers around actual empty window recesses.
        fh=h/floors
        for side,span,norm in [('front',w,(0,-1,0)),('right',d,(1,0,0)),('back',w,(0,1,0)),('left',d,(-1,0,0))]:
            count=cols if side in ('front','back') else max(2,round(cols*d/w));step=span/count
            for row in range(floors):
                floor=root(f'Etage {row+1:02d} · {side}',(0,0,row*fh),p);batch=Batch(b,floor,'Facade')
                yface=-d/2 if side=='front' else d/2
                xface=w/2 if side=='right' else -w/2
                def cell(u,z,ww,hh,depth,material,offset=0):
                    if side in ('front','back'):batch.box((u,yface+norm[1]*offset,z),(ww,depth,hh),material)
                    else:batch.box((xface+norm[0]*offset,u,z),(depth,ww,hh),material)
                wh=fh*(.39 if mode=='holes' else .52);sill=fh*.31
                ww=step*(.30 if mode=='holes' else .73)
                cell(0,sill/2,span,sill,.42,mat)
                cell(0,(sill+wh+fh)/2,span,fh-sill-wh,.42,mat)
                for j in range(count+1):
                    piw=(step-ww) if 0<j<count else (step-ww)/2
                    u=-span/2+j*step
                    if j==0:u+=piw/2
                    if j==count:u-=piw/2
                    cell(u,sill+wh/2,piw,wh,.42,mat)
                for j in range(count):
                    u=-span/2+(j+.5)*step;z=sill+wh/2
                    cell(u,z,ww+.03,wh+.03,.08,inside,offset=-.52)
                    gm=glass2 if rng.random()<.18 else glass
                    cell(u,z,ww-.08,wh-.10,.045,gm,offset=-.24)
                    for du in (-ww/2+.045,ww/2-.045):cell(u+du,z,.07,wh,.12,trim,offset=-.14)
                    for dz in (-wh/2+.04,wh/2-.04):cell(u,z+dz,ww,.07,.12,trim,offset=-.14)
                    if ww>1.8:cell(u,z,.055,wh,.09,trim,offset=-.14)
                    cell(u,sill-.045,ww+.16,.09,.64,mat,offset=.06)
                parts=batch.emit(.012 if mode=='holes' else .018)
                if project:
                    for o in parts:
                        if o.data.materials[0] in concrete_mats:o['pa_city_project']=True;targets.append(o)
        roof_detail(p,w,d,h)
    def block(name,loc,w,d,h,floors,cols,mat=cement,mode='regular',project=True):
        p=root(name,loc);facade(p,w,d,h,floors,cols,mat,mode,project);return p
    # Main A1 silhouette: narrow perforated shaft and offset top-heavy tower.
    mainA=block('A1 · tour mince perforee',(-8,12,0),12,16,70,18,4,cement,'holes')
    # Recessed balconies on the visible shaft side, independent slabs and parapets.
    for z in range(8,66,7):
        box('Loggia · dalle',(-6.65,-3,z),(1.5,4.0,.22),dark,mainA,.035)
        box('Loggia · garde-corps plein',(-7.25,-3,z+.55),(.18,4.0,1.1),cement,mainA,.02,True)
    core=block('A1 · noyau porteur tour droite',(10,17,0),12,15,53,13,3,cement,'holes')
    crown=block('A1 · couronne en porte-a-faux',(10,13,48),25,21,14,3,5,cement,'holes')
    cap=block('A1 · noyau haut',(12,17,62),10,12,11,3,3,cement,'holes')
    bridge=block('A1 · liaison verticale',(0,22,0),10,12,64,16,2,dark,'holes')
    # Asymmetric side service cantilever, prominent on the left in the photograph.
    leftcore=block('A1 · aile gauche haute',(-24,14,0),9,13,47,12,2,dark,'regular')
    leftcap=block('A1 · boite suspendue gauche',(-25,11,36),13,17,16,4,3,cement,'regular')
    wing=block('A1 · aile droite ajouree',(36,14,0),19,19,40,10,5,cement,'holes')
    fin=root('A1 · nervure verticale droite',(46,12,0));box('Voile vertical',(0,0,20),(2.4,20,40),cement,fin,.06,True)
    # Foreground stepped podium. Deep set black ribbon windows, projecting decks.
    podium=block('A1 · podium haut',(2,-5,0),31,21,24,6,6,cement,'regular')
    terrace=root('A1 · terrasses basses',(-10,-15,0))
    for level,(w,d,z) in enumerate([(40,22,3.4),(37,20,6.8),(34,18,10.2)]):
        box('Terrasse · dalle debordante',(0,0,z),(w,d,.65),light,terrace,.06,True)
        box('Terrasse · interieur en retrait',(0,.5,z-1.65),(w-2.7,d-2.8,2.5),inside,terrace,.02)
        for x in [-w/2+2,0,w/2-2]:box('Terrasse · poteau',(x,-d/2+1.1,z-1.5),(.52,.62,3.0),dark,terrace,.025)
        for x in range(-int(w/2)+2,int(w/2)-1,2):box('Terrasse · meneau',(x,-d/2+1.15,z-1.6),(.085,.12,2.1),trim,terrace,.006)
    # Massive vertical blade gives the podium its distinctive facade division.
    box('Podium · voile monumental',(8,-11.2,12.2),(4.5,1.6,24.4),light,podium,.04,True)
    # Low pre-existing city fabric, different architectural rhythm.
    low=block('A1 · batiment bas longitudinal',(-36,-14,0),31,13,14,4,11,old,'regular')
    corner=block('A1 · immeuble ancien angle',(-55,-4,0),15,19,24,6,5,old,'regular')
    box('Ancien · couronnement oxyde',(0,0,24.8),(16,20,1.3),rust,corner,.10)
    # Skyline behind main building, simplified repeated bays but actual relief.
    background=[('BG · tour sombre',(-130,52,0),26,25,96,29,10,dark),('BG · tour claire',(-100,77,0),33,25,90,28,12,light),('BG · tour droite',(38,85,0),30,28,88,27,11,light),('BG · lointain gauche',(-160,140,0),24,23,82,23,9,cement),('BG · lointain droite',(75,140,0),32,26,105,30,10,light)]
    for (name,loc,w,d,h,f,c,m),factor in zip(background,(84/96,77/90,78/88,1,95/105)):
        bg=block(name,loc,w,d,h,f,c,m,project=False);bg.scale.z=factor
    # Off-camera continuation, logically inferred rather than claiming surveyed agreement.
    for idx,(x,y,w,d,h) in enumerate([(-70,-55,23,24,30),(66,-24,22,18,28),(-64,37,20,22,39),(70,43,21,26,32)]):block('EXT · ilot %02d'%idx,(x,y,0),w,d,h,round(h/3.6),6,old,project=False)
    ground=root('VOIRIE · quartier')
    asphalt=concrete('VILLE · asphalte humide',(.052,.064,.059));bs=asphalt.node_tree.nodes['Principled BSDF'];t=asphalt.node_tree;tc=node(t,'ShaderNodeTexCoord','Asphalte local');n=noise(t,'Zones humides',tc.outputs['Object'],.24,3);feed(t,bs.inputs['Roughness'],mapped(t,'Humidite',n,.2,.8,.16,.60))
    sidewalk=concrete('VILLE · trottoir use',(.23,.25,.22));line=material('VILLE · peinture route usee',(.43,.44,.35),.72)
    box('Sol urbain',(0,30,-.30),(360,360,.6),asphalt,ground,.03)
    box('Parvis',(0,-4,.08),(112,65,.16),sidewalk,ground,.03)
    # Local streets, stepped curb stones and sparse worn road markings.
    for x in range(-130,131,2):
        box('Bordure de trottoir',(x,-36,.10),(1.98,.35,.20),light,ground,.02)
        if x%8==0:box('Marquage discontinu',(x,-44,.014),(3,.12,.014),line,ground,0)
    for y in range(-95,120,2):box('Bordure voie laterale',(-62,y,.10),(.35,1.98,.20),light,ground,.02)
    # Podium support piers, roof pipes and antennas break the blockout silhouette.
    for p in [mainA,core,wing]:
        for x in (-3,3):b.pipe('Descente eaux pluviales',[(x,-8.3,1),(x,-8.3,14),(x+.25,-8.3,14.4),(x+.25,-8.3,32)],.055,trim,p,1)
    # Street furniture assembled as independent editable modules.
    for i,x in enumerate(range(-60,61,20)):
        p=root('MOBILIER · lampadaire %02d'%i,(x,-35,.1))
        b.cylinder('Mat', (0,0,4.3),.085,8.6,trim,p,vertices=10)
        b.pipe('Bras',[(0,0,8.5),(0,0,9),(0,-1.8,9.2)],.07,trim,p,1)
        box('Luminaire',(0,-1.8,9.13),(.42,1.05,.16),trim,p,.045)
    benchmat=material('VILLE · banc bois brun',(.095,.075,.052),.8)
    for x in (-34,-18,30):
        p=root('MOBILIER · banc',(x,-32,.1))
        for y in (-.23,0,.23):box('Latte',(0,y,.46),(1.8,.18,.06),benchmat,p,.02)
        for xx in (-.65,.65):box('Pied',(xx,0,.23),(.07,.45,.46),trim,p,.015)
    # Lightweight editable sedans, a minor scale cue, not hero car assets.
    carpaint=[material('VILLE · carrosserie '+str(i),c,.29,.5) for i,c in enumerate([(.11,.14,.13),(.29,.29,.25),(.08,.10,.10),(.27,.23,.18)])]
    for i in range(13):
        p=root('VEHICULE · voiture %02d'%i,(-54+i*8.5,-38.5,.1));p.rotation_euler.z=math.pi/2
        box('Carrosserie',(0,0,.66),(1.72,4.2,.72),carpaint[i%4],p,.18)
        box('Habitacle',(0,-.05,1.16),(1.48,2.0,.70),glass,p,.22)
        box('Toit',(0,-.05,1.51),(1.5,1.58,.09),carpaint[i%4],p,.08)
        for x in (-.84,.84):
            for y in (-1.28,1.28):b.cylinder('Roue',(x,y,.40),.34,.18,rubber,p,(1,0,0),14)
    # Assets from user's library: two winter species, shared mesh instances.
    assets=[];base=Path(asset_root)/'botaniq_full-Assets/blends_280/deciduous'
    tree_specs=['Tree_Tilia-europaea_A_winter.blend','Tree_Ulmus-minor_B_winter.blend']
    sources=[]
    for file in tree_specs:
        path=base/file
        if not path.exists():continue
        with bpy.data.libraries.load(str(path),link=False) as(a,d):d.objects=[n for n in a.objects if n.startswith('Tree_')]
        meshes=[o for o in d.objects if o and o.type=='MESH']
        for o in meshes:
            o.data.use_fake_user=True;sources.append(o.data);assets.append({'file':str(path),'object':o.name,'vertices':len(o.data.vertices)})
            bpy.data.objects.remove(o,do_unlink=True)
    for i,(x,y,h) in enumerate([(54,-8,20),(57,3,22),(53,17,18),(51,30,21),(-59,-28,13),(-59,-10,14),(-59,18,16),(49,-27,15),(-50,34,17),(72,17,20),(-74,-33,14)]):
        if not sources:break
        p=root('VEGETATION · arbre hiver %02d'%i,(x,y,.18));me=sources[i%len(sources)];o=bpy.data.objects.new('Botaniq · arbre partage',me);b.collection.objects.link(o);o.parent=p
        zs=[v.co.z for v in me.vertices];height=max(zs)-min(zs);s=h/max(height,.1);o.scale=(s,s,s);o.location.z=-min(zs)*s;o.rotation_euler.z=rng.random()*math.tau
    # Diffuse overcast light and bounded atmospheric depth; no photographed sky buildings.
    world=bpy.data.worlds.new('VILLE · ciel couvert vert pale');world.use_nodes=True;world.node_tree.nodes['Background'].inputs['Color'].default_value=(.67,.72,.53,1);world.node_tree.nodes['Background'].inputs['Strength'].default_value=.65;scene.world=world
    wt=world.node_tree;sky=node(wt,'ShaderNodeBackground','Ciel visible pale');sky.inputs['Color'].default_value=(.76,.82,.57,1);sky.inputs['Strength'].default_value=1.8
    path=node(wt,'ShaderNodeLightPath','Ciel / ambiance');mx=node(wt,'ShaderNodeMixShader','Ciel visible et eclairage diffus');wt.links.new(path.outputs['Is Camera Ray'],mx.inputs[0]);wt.links.new(wt.nodes['Background'].outputs[0],mx.inputs[1]);wt.links.new(sky.outputs[0],mx.inputs[2]);wt.links.new(mx.outputs[0],wt.nodes['World Output'].inputs[0])
    ld=bpy.data.lights.new('Soleil diffus derriere les nuages','SUN');ld.energy=1.0;ld.angle=math.radians(32);lo=bpy.data.objects.new(ld.name,ld);b.collection.objects.link(lo);lo.rotation_euler=(math.radians(28),math.radians(-20),math.radians(-25))
    fog=bpy.data.materials.new('VILLE · brume atmospherique');fog.use_nodes=True;fog.node_tree.nodes.clear();t=fog.node_tree;v=node(t,'ShaderNodeVolumeScatter','Brume douce');v.inputs['Color'].default_value=(.70,.74,.61,1);v.inputs['Density'].default_value=.0036;v.inputs['Anisotropy'].default_value=.15;vo=node(t,'ShaderNodeOutputMaterial','Volume uniquement');t.links.new(v.outputs[0],vo.inputs['Volume'])
    o=box('ATMOSPHERE · brume', (0,90,67),(400,330,135),fog,city,0);o.display_type='WIRE';o.hide_select=True;o['pa_noncolliding']=True
    cam=camera(b,'CAM_01 · A1 reference',(82,-135,8),(-4,12,35),46,1800,1000);scene.camera=cam
    camera(b,'CAM_02 · place et contre-angle',(-66,-80,5),(4,12,31),35,1800,1100)
    camera(b,'CAM_03 · pied des tours',(27,-29,2.0),(2,13,38),21,1600,1200)
    camera(b,'CAM_04 · facades rapprochees',(44,-9,14),(17,11,24),35,1600,1100)
    camera(b,'CAM_05 · quartier et skyline',(106,-115,51),(0,16,38),35,1600,1000)
    camera(b,'CAM_06 · arriere invente',(-44,60,14),(3,13,35),21,1600,1000)
    camera(b,'CAM_07 · promenade au sol',(35,-32,1.7),(18,-10,8),24,1800,1100)
    for o in scene.objects:
        if o.type=='CAMERA':o.data.clip_end=1500;o.data.clip_start=.15
    scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True;scene.cycles.max_bounces=8;scene.cycles.volume_bounces=1
    scene.render.resolution_x=1800;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
    scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast';scene.view_settings.exposure=-.3
    scene.unit_settings.system='METRIC';scene['pa_city_recipe']='brutalist-A1';scene['pa_output']=str(out)
    scene['pa_reference']=str(reference);scene['pa_assumption']='Estimated scale. A1 is the sole geometric anchor; other panels are inconsistent and not treated as survey views.'
    bpy.context.view_layer.update()
    calibrate(scene)
    for _ in range(4):
        for seq in (bpy.data.objects,bpy.data.meshes,bpy.data.materials,bpy.data.node_groups,bpy.data.images):
            for datablock in list(seq):
                if datablock.library:
                    try:datablock.make_local()
                    except RuntimeError:pass
    # Pack dependencies and store the source reference separately from material lighting.
    for im in bpy.data.images:
        if im.source=='FILE' and not im.packed_file:
            try:im.pack()
            except RuntimeError:pass
    report={'reference':str(reference),'anchor':'A1','modules':len(roots),'objects':len(scene.objects),'projection_targets':len(targets),'assets':assets,'assumptions':['Building proportions estimated in metres, not surveyed.','Back elevations and street continuity inferred logically.','Other grid panels not assumed to share exact geometry.'],'materials':'Procedural concrete, rain streaks, aggregate, local grime, wet asphalt; dedicated projection detail pass follows geometry review.'}
    (out/'reconstruction.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    return scene,report


def calibrate(scene):
    """Final A1 composition and depth calibration, reused by the build operator."""
    cam=next(o for o in scene.objects if o.name.startswith('CAM_01'));cam.data.lens=42
    cam.rotation_euler=(Vector((-4,12,37))-cam.location).to_track_quat('-Z','Y').to_euler()
    bpy.data.objects['EXT · ilot 01'].location=(100,35,0)
    for o in scene.objects:
        if o.type=='MESH' and o.parent and o.parent.parent and o.parent.parent.name in ('A1 · noyau porteur tour droite','A1 · liaison verticale') and 'vitrage poussiereux' in o.name:
            o.data.materials.clear();o.data.materials.append(bpy.data.materials['VILLE · beton humide sombre'])
    for prefix,label in [('A1 ·','ILOT · ensemble principal A1'),('BG ·','SKYLINE · arriere plan'),('EXT ·','ILOTS · prolongement invente'),('VEGETATION ·','VEGETATION · arbres mobiles'),('VEHICULE ·','VEHICULES · stationnement'),('MOBILIER ·','MOBILIER · voirie')]:
        root=bpy.data.objects.new(label,None);scene.collection.objects.link(root);root.parent=bpy.data.objects['VILLE · ensemble'];root['pa_module']=True
        for o in list(scene.objects):
            if o is not root and o.name.startswith(prefix) and o.parent==bpy.data.objects['VILLE · ensemble']:
                mw=o.matrix_world.copy();o.parent=root;o.matrix_world=mw
    fog=bpy.data.materials['VILLE · brume atmospherique'];t=fog.node_tree;t.nodes.clear();v=node(t,'ShaderNodeVolumePrincipled','Brume douce');v.inputs['Color'].default_value=(.90,.94,.84,1);v.inputs['Anisotropy'].default_value=.2
    tc=node(t,'ShaderNodeTexCoord','Brume · coordonnees locales');sep=node(t,'ShaderNodeSeparateXYZ','Brume · axe profondeur');t.links.new(tc.outputs['Object'],sep.inputs[0]);density=mapped(t,'Brume · faible devant dense derriere',smath(t,'ADD',sep.outputs['Y'],90),0,100,.0006,.008)
    feed(t,v.inputs['Density'],density);v.inputs['Emission Color'].default_value=(.68,.75,.53,1);feed(t,v.inputs['Emission Strength'],smath(t,'MULTIPLY',density,.22));out=node(t,'ShaderNodeOutputMaterial','Volume uniquement');t.links.new(v.outputs[0],out.inputs['Volume'])
    bpy.context.view_layer.update()
