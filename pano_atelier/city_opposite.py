"""Art-directed opposite frontage for the approved A1 city, batched by building."""
import bpy,math,random,json
from mathutils import Vector
from .modular_scene import Builder,material,camera
from .city_scene import Batch
from .city_optimize import freeze_coordinates,metrics
from .station_procedural import node,feed,math as smath


def add_street_background(scene):
    """Low-detail distant blocks keep the street from ending against an empty horizon."""
    if bpy.data.objects.get('VIS · fond de rue est'):return []
    b=Builder(scene,'VIS-A-VIS · fonds de rue');ensemble=bpy.data.objects.get('VIS-A-VIS · ensemble');made=[]
    wall=bpy.data.materials['VIS · beton gris'];glass=bpy.data.materials['VILLE · vitrage vert gris'];dark=bpy.data.materials['VIS · beton abrite']
    for name,loc,w,d,h,n in [('fond de rue est',(275,-43,0),38,28,45,13),('fond nord est',(180,-8,0),48,30,38,11),('fond sud est',(175,-90,0),56,32,29,8)]:
        p=b.root('VIS · '+name,loc,ensemble);p['pa_module']=True;p['pa_opposite']=True;p['pa_background_lod']=True
        q=Batch(b,p,name);q.box((0,0,h/2),(w,d,h),wall)
        for axis,span,half in [(0,w,d/2),(1,d,w/2)]:
            cols=max(3,int(span/3.4));step=span/cols
            for sign in (-1,1):
                for row in range(n):
                    z=3+row*(h-4)/n
                    for col in range(cols):
                        u=-span/2+(col+.5)*step
                        q.box((u,sign*(half+.025),z) if axis==0 else (sign*(half+.025),u,z),(step*.69,.08,1.55) if axis==0 else (.08,step*.69,1.55),glass)
                    if row%3==0:q.box((0,sign*(half+.08),z-1) if axis==0 else (sign*(half+.08),0,z-1),(w+.15,.22,.18) if axis==0 else (.22,d+.15,.18),dark)
        for o in q.emit(0):o['pa_opposite']=True;made.append(o)
    bpy.context.view_layer.update()
    for o in made:freeze_coordinates(o,o.parent)
    ground=b.box('VIS · prolongement sol est',(440,30,-.3),(520,360,.6),bpy.data.materials['VILLE · asphalte humide'],ensemble,0);ground['pa_opposite']=True;bpy.context.view_layer.update();freeze_coordinates(ground,ensemble)
    fog=bpy.data.materials.new('VIS · brume fond est');fog.use_nodes=True;t=fog.node_tree;t.nodes.clear();v=node(t,'ShaderNodeVolumePrincipled','Brume lointaine est');v.inputs['Color'].default_value=(.90,.94,.84,1);v.inputs['Density'].default_value=.009;v.inputs['Anisotropy'].default_value=.15;v.inputs['Emission Color'].default_value=(.68,.75,.53,1);v.inputs['Emission Strength'].default_value=.003
    out=node(t,'ShaderNodeOutputMaterial','Volume');feed(t,out.inputs['Volume'],v.outputs[0])
    vol=b.box('VIS · atmosphere est',(400,-44,75),(400,600,150),fog,ensemble,0);vol['pa_noncolliding']=True;vol['pa_opposite']=True;vol.hide_select=True;vol.display_type='WIRE'
    return [o.name for o in made]


def soften_new_fog_boundaries(scene):
    # Keep V2's volume/material intact but use a feathered copy for the expanded views.
    if not bpy.data.objects.get('VIS · atmosphere nord raccordee'):
        src=scene.objects.get('ATMOSPHERE · brume')
        if src:
            m=src.material_slots[0].material.copy();m.name='VIS · brume nord raccordee'
            ob=src.copy();ob.data=src.data.copy();ob.name='VIS · atmosphere nord raccordee';scene.collection.objects.link(ob)
            ob.data.materials.clear();ob.data.materials.append(m);ob['pa_opposite']=True
            ob.hide_render=False;ob.hide_viewport=False;src.hide_render=True;src.hide_viewport=True
    for name in ('VIS · brume vers le sud','VIS · brume fond est','VIS · brume nord raccordee'):
        m=bpy.data.materials.get(name)
        if not m or m.get('pa_soft_edges'):continue
        t=m.node_tree;v=next(n for n in t.nodes if n.type=='PRINCIPLED_VOLUME')
        tc=node(t,'ShaderNodeTexCoord','Limites progressives');sep=node(t,'ShaderNodeSeparateXYZ','Volume normalise');feed(t,sep.inputs[0],tc.outputs['Generated'])
        fade=1
        for axis in ('X','Y'):
            dist=smath(t,'MINIMUM',sep.outputs[axis],smath(t,'SUBTRACT',1,sep.outputs[axis]))
            fade=smath(t,'MULTIPLY',fade,smath(t,'MINIMUM',smath(t,'MULTIPLY',dist,10),1))
        fade=smath(t,'MULTIPLY',fade,smath(t,'MINIMUM',smath(t,'MULTIPLY',smath(t,'SUBTRACT',1,sep.outputs['Z']),4),1))
        for field in ('Density','Emission Strength'):
            s=v.inputs[field];old=s.links[0].from_socket if s.is_linked else s.default_value;feed(t,s,smath(t,'MULTIPLY',old,fade))
        m['pa_soft_edges']=True
    # Explicit local-space normalization also works for evaluated volume meshes.
    for ob in scene.objects:
        if not ob.get('pa_opposite') or not ob.get('pa_noncolliding'):continue
        for slot in ob.material_slots:
            m=slot.material
            if not m or not m.get('pa_soft_edges') or m.get('pa_explicit_fog_coordinates'):continue
            t=m.node_tree;tc=t.nodes.get('Limites progressives');sep=t.nodes.get('Volume normalise')
            lo=[min(v.co[i] for v in ob.data.vertices) for i in range(3)];hi=[max(v.co[i] for v in ob.data.vertices) for i in range(3)]
            add=node(t,'ShaderNodeVectorMath','Volume · origine locale');add.operation='ADD';feed(t,add.inputs[0],tc.outputs['Object']);add.inputs[1].default_value=tuple(-x for x in lo)
            mul=node(t,'ShaderNodeVectorMath','Volume · normalisation explicite');mul.operation='MULTIPLY';feed(t,mul.inputs[0],add.outputs[0]);mul.inputs[1].default_value=tuple(1/(h-l) for h,l in zip(hi,lo));feed(t,sep.inputs[0],mul.outputs[0]);m['pa_explicit_fog_coordinates']=True


def continuous_city_haze(scene):
    """One broad envelope avoids crossing several local fog box boundaries in reverse shots."""
    if scene.get('pa_continuous_city_haze'):return
    soften_new_fog_boundaries(scene)
    for name in ('ATMOSPHERE · brume','VIS · atmosphere sud','VIS · atmosphere est','VIS · atmosphere nord raccordee'):
        o=scene.objects.get(name)
        if o:o.hide_render=True;o.hide_viewport=True
    b=Builder(scene,'VIS-A-VIS · atmosphere continue');m=bpy.data.materials.new('VIS · atmosphere urbaine continue');m.use_nodes=True;t=m.node_tree;t.nodes.clear()
    v=node(t,'ShaderNodeVolumePrincipled','Brume continue');v.inputs['Color'].default_value=(.90,.94,.84,1);v.inputs['Density'].default_value=.0012;v.inputs['Anisotropy'].default_value=.15;v.inputs['Emission Color'].default_value=(.68,.75,.53,1);v.inputs['Emission Strength'].default_value=.00028
    out=node(t,'ShaderNodeOutputMaterial','Volume');feed(t,out.inputs['Volume'],v.outputs[0])
    o=b.box('VIS · atmosphere urbaine continue',(0,0,150),(1600,1600,400),m,None,0);o.display_type='WIRE';o.hide_select=True;o['pa_noncolliding']=True;o['pa_opposite']=True
    scene['pa_continuous_city_haze']=True


def build(scene):
    if not scene.get('pa_city_recipe'):raise ValueError('Ouvrir une ville A1 avant cette extension.')
    if scene.get('pa_city_opposite'):raise ValueError('Le vis-a-vis existe deja.')
    required=['VILLE · beton brut gris sauge','VILLE · beton clair erode','VILLE · enduit gris brun','VILLE · cadres aluminium terni','VILLE · vitrage vert gris','VILLE · interieur profond','VILLE · beton humide sombre','VILLE · etancheite vieillie','VILLE · vitrage poussiereux','VILLE · trottoir use','VILLE · asphalte humide']
    if any(n not in bpy.data.materials for n in required):raise ValueError('Materiaux de la ville A1 manquants.')
    b=Builder(scene,'VIS-A-VIS · quartier sud');rng=random.Random(7119);old=set(scene.objects);root=b.root('VIS-A-VIS · ensemble');root['pa_module']=True
    # Copy only the procedural substrates, never the already projected A1 materials.
    def clone(src,name):
        m=bpy.data.materials[src].copy();m.name='VIS · '+name;return m
    cement=clone(required[0],'beton gris');pale=clone(required[1],'beton clair');oldwall=clone(required[2],'enduit ancien')
    dark=clone('VILLE · beton humide sombre','beton abrite');roof=clone('VILLE · etancheite vieillie','toiture')
    metal=bpy.data.materials[required[3]];glass=bpy.data.materials[required[4]];inside=bpy.data.materials[required[5]];dust=bpy.data.materials['VILLE · vitrage poussiereux']
    ox=material('VIS · acier patine',(.105,.08,.054),.72,.5);store=material('VIS · stores gris beige',(.26,.25,.20),.9)
    shop=material('VIS · enseigne vert oxyde',(.07,.115,.105),.7,.25);letters=material('VIS · lettres ivoire',(.54,.53,.42),.85)
    dirt=material('VIS · terre humide',(.032,.038,.026),.98);paint=material('VIS · marquage use',(.34,.35,.28),.87)
    projected={cement,pale,oldwall,dark};roots=[];made=[]
    def module(name,loc):
        p=b.root('VIS · '+name,loc,root);p['pa_module']=True;p['pa_opposite']=True;roots.append(p);return p
    def emit(batch):
        for o in batch.emit(0):
            o['pa_opposite']=True;o['pa_city_project']=o.data.materials[0] in projected;made.append(o)
    def rooftop(batch,w,d,z):
        batch.box((0,0,z),(w,d,.18),roof)
        for y in (-d/2,d/2):batch.box((0,y,z+.30),(w+.2,.25,.65),cement)
        for x in (-w/2,w/2):batch.box((x,0,z+.30),(.25,d,.65),cement)
        for x,y in [(-w*.25,0),(w*.20,-d*.20)]:
            batch.box((x,y,z+.75),(2.2,1.5,1.4),metal)
            for k in range(5):batch.box((x,y+.78,z+.25+k*.22),(1.9,.06,.065),inside)
            batch.box((x+.8,y-.7,z+1.5),(.3,.35,2.6),metal)
    def text(p,txt,loc,size=.32):
        cu=bpy.data.curves.new(txt,'FONT');cu.body=txt;cu.size=size;cu.align_x='CENTER';cu.extrude=.008
        o=bpy.data.objects.new('Enseigne · '+txt,cu);b.collection.objects.link(o);o.parent=p;o.location=loc;o.rotation_euler=(math.pi/2,0,math.pi);cu.materials.append(letters);o['pa_opposite']=True
    def building(name,loc,w,d,h,floors,cols,style='housing',background=False):
        p=module(name,loc);p['pa_footprint']=json.dumps([w,d,h]);batch=Batch(b,p,name);ground=4.1 if not background else 3.4;fh=(h-ground)/floors
        wall=oldwall if style=='old' else cement
        for side,span,extent in [('front',w,d/2),('back',w,-d/2),('left',d,-w/2),('right',d,w/2)]:
            horizontal=side in ('front','back');sign=1 if side in ('front','right') else -1;count=cols if horizontal else max(3,round(cols*d/w));step=span/count
            def box(u,z,width,height,depth,mat,offset=0):
                batch.box((u,extent+sign*offset,z) if horizontal else (extent+sign*offset,u,z),(width,depth,height) if horizontal else (depth,width,height),mat)
            # Street level: actual recessed shopfronts, heavy lintel and supporting piers.
            box(0,ground-.35,span,.7,.65,wall)
            for j in range(count+1):box(-span/2+j*step,ground/2,.42,ground,.72,dark)
            for j in range(count):
                u=-span/2+(j+.5)*step
                box(u,1.78,step-.50,3.10,.10,inside,-1.05)
                box(u,1.7,step-.63,2.85,.06,glass,-.30)
                box(u,.23,step-.44,.46,.65,dark)
                box(u,1.7,.075,2.85,.15,metal,-.21)
                for dz in (.35,3.12):box(u,dz,step-.55,.09,.15,metal,-.21)
            for row in range(floors):
                z0=ground+row*fh
                wh=fh*(.59 if style=='office' else .49);sill=(fh-wh)*.47;ww=step*(.83 if style=='office' else .67)
                box(0,z0+sill/2,span,sill,.42,wall)
                box(0,z0+sill+wh+(fh-wh-sill)/2,span,fh-wh-sill,.42,wall)
                for j in range(count+1):
                    pw=(step-ww)*(1 if 0<j<count else .5);u=-span/2+j*step
                    if j==0:u+=pw/2
                    if j==count:u-=pw/2
                    box(u,z0+sill+wh/2,pw,wh,.42,wall)
                for j in range(count):
                    u=-span/2+(j+.5)*step;z=z0+sill+wh/2
                    solid=(style=='housing' and side=='front' and j==count//2) or (style=='office' and side in ('left','right') and j==1)
                    if solid:
                        box(u,z,ww+.05,wh+.04,.45,pale)
                        if row%3==0:
                            box(u,z,ww*.4,wh*.35,.08,inside,.25)
                            for k in range(4):box(u,z-wh*.12+k*wh*.08,ww*.37,.055,.10,metal,.31)
                        continue
                    box(u,z,ww+.02,wh+.02,.08,inside,-.70)
                    box(u,z,ww-.12,wh-.10,.045,dust if rng.random()<.22 else glass,-.28)
                    for xx in (-ww/2+.045,ww/2-.045):box(u+xx,z,.07,wh,.13,metal,-.12)
                    for zz in (-wh/2+.04,wh/2-.04):box(u,z+zz,ww,.07,.13,metal,-.12)
                    box(u,z,.065,wh,.10,metal,-.12);box(u,z0+sill-.045,ww+.2,.09,.75,pale,.06)
                    if rng.random()<.19:
                        bh=wh*rng.uniform(.3,.8);box(u,z+wh/2-bh/2,ww-.15,bh,.03,store,-.25)
                    if side=='front' and style=='housing' and j in (1,2,cols-2) and row in (0,1,3,4,6):
                        # Real projecting loggias with side walls, not dark painted rectangles.
                        batch.box((u,d/2+.74,z0+.10),(step-.16,1.8,.22),dark)
                        batch.box((u,d/2+1.60,z0+.72),(step-.14,.18,1.10),pale)
                        for xx in (-step/2+.12,step/2-.12):batch.box((u+xx,d/2+.82,z0+.72),(.18,1.72,1.10),pale)
                        batch.box((u,d/2+1.61,z0+1.30),(step-.08,.24,.06),ox)
                    if not background and side=='front' and rng.random()<.11:
                        box(u+ww*.27,z0+sill-.4,.75,.48,.35,metal,.38)
                        for k in range(4):box(u+ww*.27,z0+sill-.55+k*.10,.65,.035,.04,inside,.57)
                if style=='office' or row in (1,floors-1):box(0,z0+fh-.08,span+.18,.20,.70,dark,.10)
            if style=='old':
                for j in (0,2,count-2,count):box(-span/2+j*step,h/2,.34,h,.78,pale,.14)
        rooftop(batch,w,d,h)
        if style=='old':
            batch.box((0,-2,h+1.8),(w*.64,d*.63,3.3),dark)
            batch.box((0,-2,h+3.5),(w*.68,d*.67,.20),roof)
        if not background:
            for x in (-w*.44,w*.42):
                batch.box((x,d/2+.36,h/2),(.10,.12,h),metal)
                for z in range(2,int(h),3):batch.box((x,d/2+.34,z),(.24,.16,.045),metal)
            # Enamel signs and small awnings over the shop doors.
            for j,label in enumerate(['LIBRAIRIE','ATELIER'] if style=='housing' else ['DEPOT']):
                x=-w*.23+j*w*.46;batch.box((x,d/2+.50,3.28),(min(5,w*.38),.15,.52),shop)
                batch.box((x,d/2+1.12,3.55),(min(5.8,w*.42),2.2,.14),ox)
                text(p,label,(x,d/2+.59,3.16),.29)
        emit(batch);return p

    housing=building('logements et commerces',(-16,-72,0),44,18,27,7,10,'housing')
    office=building('bureaux et noyau vertical',(20,-78,0),16,20,34,9,4,'office')
    corner=building('immeuble ancien angle',(71,-77,0),28,24,24,6,7,'old')
    civic=building('annexe sur cour',(-15,-108,0),43,18,13,3,9,'office')
    far1=building('fond sud tour A',(-34,-152,0),23,24,55,16,7,'office',True)
    far2=building('fond sud tour B',(62,-175,0),27,28,67,19,8,'housing',True)
    building('fond avenue sud',(43,-243,0),57,24,31,9,12,'office',True)
    building('fond quartier ouest',(-82,-206,0),47,26,39,11,11,'housing',True)

    # Opposite sidewalk and continuous cross street. The existing V2 roadway is kept.
    street=module('trottoirs et mobilier',(0,0,0));batch=Batch(b,street,'Trottoir sud');sidewalk=bpy.data.materials['VILLE · trottoir use'];asphalt=bpy.data.materials['VILLE · asphalte humide']
    batch.box((0,-475,-.30),(900,650,.60),asphalt)
    batch.box((-16,-56.5,.065),(98,13,.13),sidewalk);batch.box((79,-56.5,.065),(52,13,.13),sidewalk)
    for x in range(-64,106,2):
        if 33<x<53:continue
        batch.box((x,-50,.10),(1.98,.32,.20),pale)
    for y in range(-64,-195,-2):
        for x in (33,53):batch.box((x,y,.10),(.32,1.98,.2),pale)
    for y in range(-63,-200,-9):batch.box((43,y,.012),(.12,4,.012),paint)
    for x in range(35,52,2):batch.box((x,-54,.013),(1.1,4,.014),paint)
    # Tree beds and practical street furniture, grouped in one editable street module.
    for x in (-39,5,57,90):
        batch.box((x,-54,.145),(2.6,2.5,.03),dirt)
        for dx in (-1.4,1.4):batch.box((x+dx,-54,.2),(.15,2.8,.13),pale)
    for x in (-48,-12,27,67,100):
        batch.box((x,-50.8,4.1),(.12,.13,8.2),metal)
        batch.box((x,-49.7,8.15),(.13,2.3,.13),metal)
        batch.box((x,-48.8,8.07),(.46,.95,.16),metal)
    # Bus shelter: thin structural steel and real glass panels.
    for x in (-23,-18):
        for y in (-53.8,-52.2):batch.box((x,y,1.48),(.07,.07,2.7),metal)
    batch.box((-20.5,-53,2.85),(5.4,2.0,.13),ox)
    batch.box((-20.5,-53.8,1.5),(4.9,.035,2.35),glass)
    for z in (.55,.95):batch.box((-20.5,-53.2,z),(3.5,.42,.08),ox)
    for x in (-22,-19):batch.box((x,-53.2,.33),(.10,.4,.55),metal)
    emit(batch)
    # Share the already imported, packed automobile meshes and Botaniq trees.
    car_sources={o.get('pa_asset_model'):o for o in old if o.type=='MESH' and o.get('pa_asset_model')};keys=sorted(car_sources)
    for i,(x,y) in enumerate([(-43,-48),(-29,-48),(-8,-48),(12,-48),(63,-48),(91,-48)]):
        if not keys:break
        src=car_sources[keys[i%len(keys)]];p=module('voiture sud %02d'%i,(x,y,.015));o=bpy.data.objects.new(src.get('pa_asset_model')+' · instance sud',src.data);b.collection.objects.link(o);o.parent=p;o.rotation_euler.z=-math.pi/2+rng.uniform(-.025,.025);o['pa_asset_instance']=True;o['pa_asset_model']=src.get('pa_asset_model');o['pa_opposite']=True
    trees=list({o.data.name:o for o in sorted(old,key=lambda x:x.name) if o.type=='MESH' and o.name.startswith('Botaniq')}.values())
    for i,(x,y,h) in enumerate([(-39,-54,11),(5,-54,12),(57,-54,10),(90,-54,13),(-45,-100,14),(78,-114,15)]):
        if not trees:break
        src=trees[i%len(trees)];p=module('arbre sud %02d'%i,(x,y,.17));o=bpy.data.objects.new('Botaniq · sud partage',src.data);b.collection.objects.link(o);o.parent=p
        lo=min(v.co.z for v in o.data.vertices);hi=max(v.co.z for v in o.data.vertices);s=h/(hi-lo);o.scale=(s,s,s);o.location.z=-lo*s;o.rotation_euler.z=rng.random()*math.tau;o['pa_opposite']=True
    bpy.context.view_layer.update()
    for o in made:freeze_coordinates(o,o.parent)
    # Separate southern haze volume, adjacent to the existing volume with no overlap.
    fog=bpy.data.materials.new('VIS · brume vers le sud');fog.use_nodes=True;t=fog.node_tree;t.nodes.clear();v=node(t,'ShaderNodeVolumePrincipled','Brume sud');v.inputs['Color'].default_value=(.90,.94,.84,1);v.inputs['Anisotropy'].default_value=.2
    tc=node(t,'ShaderNodeTexCoord','Volume local');sep=node(t,'ShaderNodeSeparateXYZ','Profondeur sud');feed(t,sep.inputs[0],tc.outputs['Generated']);mr=node(t,'ShaderNodeMapRange','Brume · distance au fond');mr.clamp=True;mr.inputs['From Min'].default_value=0;mr.inputs['From Max'].default_value=1;mr.inputs['To Min'].default_value=.008;mr.inputs['To Max'].default_value=.00025;feed(t,mr.inputs['Value'],sep.outputs['Y']);feed(t,v.inputs['Density'],mr.outputs[0]);v.inputs['Emission Color'].default_value=(.68,.75,.53,1);feed(t,v.inputs['Emission Strength'],smath(t,'MULTIPLY',mr.outputs[0],.45));out=node(t,'ShaderNodeOutputMaterial','Volume');feed(t,out.inputs['Volume'],v.outputs[0])
    volume=b.box('VIS · atmosphere sud',(0,-170,75),(380,190,150),fog,root,0);volume['pa_noncolliding']=True;volume.hide_select=True;volume.display_type='WIRE';volume['pa_opposite']=True
    ld=bpy.data.lights.new('VIS · rebond du ciel sur la rue','AREA');ld.energy=16000;ld.shape='DISK';ld.size=75;ld.color=(.75,.82,.78);lo=bpy.data.objects.new(ld.name,ld);b.collection.objects.link(lo);lo.parent=root;lo.location=(0,-25,42);lo.rotation_euler=(Vector((0,-77,15))-lo.location).to_track_quat('-Z','Y').to_euler();lo['pa_opposite']=True
    cameras=[]
    for args in [('CAM_09 · vis-a-vis depuis le parvis',(26,-25,8),(12,-76,17),19),('CAM_10 · avenue et deux rives',(-49,-43,2.4),(45,-56,13),29),('CAM_11 · commerces et loggias',(-9,-46,4.5),(-17,-64,13),26),('CAM_12 · rue transversale et cour',(43,-114,5),(13,-78,14),26),('CAM_13 · retour vers A1',(39,-49,4),(2,12,32),22)]:
        cam=camera(b,*args,2000,1100);cam.data.clip_end=1500;cam['pa_opposite']=True;cameras.append(cam)
    scene.camera=cameras[0];scene.render.resolution_x=2000;scene.render.resolution_y=1100;scene.render.resolution_percentage=100
    scene['pa_city_opposite']='South frontage, art-directed continuation of A1. Not a surveyed reference.'
    add_street_background(scene)
    soften_new_fog_boundaries(scene)
    continuous_city_haze(scene)
    return {'buildings':8,'distant_lod_blocks':3,'new_objects':len(set(scene.objects)-old),'roots':[o.name for o in roots],'cameras':[c.name for c in cameras],'metrics':metrics(scene),'assumptions':['Opposite frontage inferred from the city language, not surveyed.','Shop interiors are shallow sets; apartments are not furnished.','Existing A1 buildings, geometry, projection coordinates and materials retained.']}
