"""Second, additive station pass: local wear, service hardware and practical light.

This is a reference-specific recipe. Texture generation is external. No API calls.
"""
import math, random, json
from pathlib import Path
import bpy
from mathutils import Vector
from .modular_scene import Builder, material


def surface(name, color, rough, metal=0, image=None, tile=.70, wear=.5):
    m=material(name,color,rough,metal); nt=m.node_tree; n=nt.nodes; l=nt.links
    bs=n.get('Principled BSDF'); tc=n.new('ShaderNodeTexCoord')
    if image:
        mapping=n.new('ShaderNodeVectorMath'); mapping.operation='SCALE'; mapping.inputs[3].default_value=1/tile
        l.new(tc.outputs['Object'],mapping.inputs[0])
        info=n.new('ShaderNodeObjectInfo'); offset=n.new('ShaderNodeVectorMath');offset.operation='ADD'
        l.new(mapping.outputs[0],offset.inputs[0]);l.new(info.outputs['Random'],offset.inputs[1])
        tex=n.new('ShaderNodeTexImage');tex.image=image;tex.projection='BOX';tex.projection_blend=.18;tex.interpolation='Linear'
        l.new(offset.outputs[0],tex.inputs[0]);mix=n.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=wear;mix.inputs[1].default_value=(*color,1)
        l.new(tex.outputs['Color'],mix.inputs[2]);l.new(mix.outputs[0],bs.inputs['Base Color'])
        bw=n.new('ShaderNodeRGBToBW');l.new(tex.outputs['Color'],bw.inputs[0])
        ramp=n.new('ShaderNodeMapRange');ramp.inputs['From Min'].default_value=.15;ramp.inputs['From Max'].default_value=.88;ramp.inputs['To Min'].default_value=min(.85,rough+.22);ramp.inputs['To Max'].default_value=rough
        l.new(bw.outputs[0],ramp.inputs[0]);l.new(ramp.outputs[0],bs.inputs['Roughness'])
        bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.13;bump.inputs['Distance'].default_value=.00035
        l.new(bw.outputs[0],bump.inputs['Height']);l.new(bump.outputs[0],bs.inputs['Normal'])
    else:
        noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=1100;noise.inputs['Detail'].default_value=2
        l.new(tc.outputs['Object'],noise.inputs[0]);bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.12;bump.inputs['Distance'].default_value=.00006
        l.new(noise.outputs['Fac'],bump.inputs['Height']);l.new(bump.outputs[0],bs.inputs['Normal'])
    m['pa_local_texture']=True;return m


def smooth_pipe(b,name,points,radius,mat,parent):
    cu=bpy.data.curves.new(name,'CURVE');cu.dimensions='3D';cu.resolution_u=10;cu.render_resolution_u=12;cu.bevel_depth=radius;cu.bevel_resolution=3
    sp=cu.splines.new('BEZIER');sp.bezier_points.add(len(points)-1)
    for p,co in zip(sp.bezier_points,points):p.co=co;p.handle_left_type='AUTO';p.handle_right_type='AUTO'
    cu.materials.append(mat);o=bpy.data.objects.new(name,cu);b.collection.objects.link(o);o.parent=parent;o['pa_detail_pass']='v2';return o


def assign(o,mat):
    # Per-object assignment preserves shared KitBash geometry.
    if not o.data.materials:o.data.materials.append(mat)
    for slot in o.material_slots:slot.link='OBJECT';slot.material=mat


def text_label(b,parent,name,text,loc,size,mat,rotation=(math.pi/2,0,0)):
    cu=bpy.data.curves.new(name,'FONT');cu.body=text;cu.size=size;cu.extrude=0;cu.align_x='CENTER';cu.materials.append(mat)
    o=bpy.data.objects.new(name,cu);b.collection.objects.link(o);o.parent=parent;o.location=loc;o.rotation_euler=rotation;return o


def apply(scene,asset_root,texture_path,seed=48):
    if scene.get('pa_station_refinement'):raise ValueError('La passe V2 est deja appliquee; repartir de la V1 pour la reconstruire.')
    if scene.get('pa_modular_recipe')!='station-habitat':raise ValueError('Cette recette demande la station modulaire.')
    texture_path=Path(texture_path);asset_root=Path(asset_root)
    sources=[('hatches-and-cover.blend','jro_cover_018'),('hatches-and-cover.blend','jro_cover_027'),('hatches-and-cover.blend','jro_cover_011'),('KitBash_control_panel_industrial.blend','switch_3')]
    if not texture_path.is_file():raise FileNotFoundError(texture_path)
    for file,obj in sources:
        if not (asset_root/file).is_file():raise FileNotFoundError(asset_root/file)
        with bpy.data.libraries.load(str(asset_root/file),link=False) as (a,d):
            if obj not in a.objects:raise ValueError('Asset absent: '+obj)
    rng=random.Random(seed);image=bpy.data.images.load(str(texture_path),check_existing=True);image.pack()
    b=Builder(scene,'STATION V2 · cables ferrures et maintenance')
    ivory=surface('V2 · email use des sas',(.72,.69,.58),.31,.08,image,.72,.62)
    flange=surface('V2 · brides peinture ecailee',(.39,.40,.34),.48,.32,image,.46,.85)
    metal=surface('V2 · acier nickel terni',(.30,.32,.30),.38,.78,image,.40,.35)
    rubber=surface('V2 · gaine caoutchouc vieilli',(.032,.035,.028),.67)
    cloth=surface('V2 · cable tresse beige',(.29,.27,.20),.72)
    grey=surface('V2 · gaine grise souple',(.22,.25,.24),.58)
    tape=surface('V2 · ruban toile maintenance',(.39,.36,.25),.84)
    red=surface('V2 · bakelite rouge passe',(.20,.058,.038),.48)
    yellow=surface('V2 · ocre securite use',(.55,.36,.055),.46,.03,image,.30,.3)
    walk=surface('V2 · plaques de sol use fine',(.25,.30,.32),.39,.26,image,.46,.18)
    black=material('V2 · encre graphite',(.018,.020,.016),.8)
    assets=[b.asset(asset_root,f,n,metal if i==3 else flange) for i,(f,n) in enumerate(sources)]
    existing=list(scene.objects);oldcurves=[]
    for o in existing:
        if o.type=='CURVE' and o.data.splines and o.data.splines[0].type=='POLY':
            # Smooth the broad original cable bends; true straight conduits remain straight.
            if len(o.data.splines[0].points)>2 and any(s in o.name for s in ('cable','alimentation','boucle')):
                points=[p.co[:3] for p in o.data.splines[0].points]
                new=smooth_pipe(b,o.name+' · courbe continue',points,o.data.bevel_depth,grey if 'alimentation' in o.name else rubber,o.parent)
                new.matrix_basis=o.matrix_basis.copy();o.hide_render=True;o.hide_viewport=True;oldcurves.append(o.name)
            else:o.data.bevel_resolution=3
        if o.type=='MESH':
            if o.name.startswith(('Sas · couronne','Sas · levre','Sas · tunnel','Porte terminale fermee')):assign(o,ivory)
            elif o.name.startswith('Sas · bride'):assign(o,flange)
            elif o.name.startswith(('Sas · seuil','Plaque de passage')):assign(o,walk)
            elif o.name.startswith(('Ferrure ·','Charniere ·','Verrou · axe')):assign(o,metal)
            elif o.name.startswith('Commande · bouton rouge'):
                assign(o,red);o.scale*=.83
            elif o.name.startswith(('Verrou · embase','Verrou · levier','Commande · voyant','Flexible · segment')):
                if any(s.material and 'jaune' in s.material.name for s in o.material_slots):assign(o,yellow)
    roots=sorted([o for o in existing if o.type=='EMPTY' and o.name.startswith('SAS ')],key=lambda o:o.name)
    for index,p in enumerate(roots):
        for side in (-1,1):
            service=b.root('V2 · harnais sas %02d %s'%(index+1,side),(0,0,0),p)
            service['role']='Faisceaux, colliers et raccords du sas; deplacable avec son parent'
            # Concentric harnesses track the pressure frame, with distinct endpoints and routes.
            count=3+(index%3)
            for j in range(count):
                r=1.515+j*.021;start=math.radians(-12-(index%3)*9);end=math.radians(200+(index%2)*15)
                points=[]
                for k in range(81):
                    a=start+(end-start)*k/80;points.append((r*math.cos(a),side*(.265+.015*math.sin(a*3+j)+rng.uniform(-.001,.001)),r*math.sin(a)))
                ob=b.pipe('V2 · faisceau annulaire',points,.007 if j%2 else .009,(grey,cloth,rubber)[(j+index)%3],service,3)
                for aa in (25,67,112,155,192):
                    a=math.radians(aa);r2=r
                    c=b.cylinder('V2 · collier sur faisceau',(r2*math.cos(a),side*.267,r2*math.sin(a)),.011,.021,tape,service,(-math.sin(a),0,math.cos(a)),12)
            for lr in (-1,1):
                # Asymmetric junction boxes replace the mirrored "button on a box" repetition.
                z=.76 if (index+(lr==1))%2 else -.45
                source=assets[(index+(lr==1))%3]
                ob=b.place_asset('V2 KITBASH · boitier maintenance',source,(lr*1.83,side*.19,z),(.27,.39,.095),service,(-side*math.pi/2,0,0))
                for j in range(3 if lr==1 else 2):
                    x=lr*(1.76+j*.035);zz=z-.15
                    points=[(x,side*.22,zz),(x+lr*.035,side*.26,zz-.23),(lr*(1.90+j*.027),side*.18,-1.14),(lr*(1.87+j*.035),side*.22,-1.46)]
                    smooth_pipe(b,'V2 · descente souple',points,.008+(j%2)*.003,(cloth,grey,rubber)[j%3],service)
                    b.cylinder('V2 · presse etoupe',(x,side*.22,zz),.021,.052,metal,service,(0,0,1),12)
                # Secured small service loop, away from the circular passage.
                if (index+lr)%2==0:
                    smooth_pipe(b,'V2 · boucle maintenance',[(lr*1.79,side*.22,z+.15),(lr*1.67,side*.29,z+.33),(lr*1.77,side*.29,z+.44),(lr*1.93,side*.27,z+.37),(lr*1.91,side*.22,z+.16)],.012,rubber,service)
                if (index+lr)%3==0:
                    b.place_asset('V2 KITBASH · commande protegee',assets[3],(lr*1.90,side*.24,.17),(.18,.14,.25),service,(-side*math.pi/2,0,0))
                plate=b.box('V2 · plaque gravure',(lr*1.78,side*.29,-.18),(.19,.009,.07),flange,service,.003)
                text_label(b,service,'V2 · repere maintenance','P%02d / %s'%(index+1,'A' if lr<0 else 'B'),(lr*1.78,side*.297,-.19),.019,ivory,(math.pi/2,0,math.pi if side>0 else 0))
            # Segmented worn flange faces / actual mechanical seats, not uniformly spaced noise.
            for k,a0 in enumerate((18,54,108,153,211,259,304,335)):
                a=math.radians(a0+(index%3-1)*4);r=1.47
                o=b.box('V2 · cale mecanique',(r*math.cos(a),side*.244,r*math.sin(a)),(.16,.026,.057),flange,service,.004);o.rotation_euler.y=-a
                for sign in (-1,1):
                    rr=r+sign*.047
                    b.cylinder('V2 · fixation cale',(rr*math.cos(a),side*.264,rr*math.sin(a)),.008,.008,metal,service,(0,1,0),8)
            # Original mirrored buttons shifted/reduced, while all children still follow.
            controls=[o for o in p.children_recursive if o.type=='EMPTY' and o.name.startswith('Commande · boitier') and o.location.y*side>0]
            for c in controls:
                c.location.z+=(-.25 if c.location.x<0 else .26)+(index%3)*.06
                if (index+side)%3==0 and c.location.x<0:
                    for child in c.children_recursive:child.hide_render=True;child.hide_viewport=True
    bays=sorted([o for o in existing if o.type=='EMPTY' and o.name.startswith('MODULE ')],key=lambda o:o.name)
    for index,p in enumerate(bays):
        rack=b.root('V2 · reseaux cabine %02d'%(index+1),(0,0,0),p)
        for side in (-1,1):
            # Bundles sit against the wall, with sag and visible fixing straps.
            for j in range(4+(index+side)%3):
                x=side*(2.005+j*.018);z=.15+j*.020
                points=[(x,.12,z),(x-side*.025,1.4,z-.025),(x,2.7,z),(x-side*.018,4.0,z-.035),(x,5.85,z)]
                smooth_pipe(b,'V2 · cables en goulotte',points,.006+(j%3)*.002,(cloth,grey,rubber)[j%3],rack)
            for yy in (.4,1.9,3.5,5.4):b.box('V2 · bride goulotte',(side*2.05,yy,.22),(.16,.024,.018),metal,rack,.002)
            # Alternate ceiling bundles instead of duplicating them on both sides of every room.
            if (index+(side==1))%2==0:
                for j in range(3):
                    smooth_pipe(b,'V2 · cables hauts',[(side*(1.88+j*.026),.12,2.72),(side*(1.90+j*.026),2.7,2.68),(side*(1.89+j*.026),5.85,2.73)],.009,(grey,cloth,rubber)[j],rack)
        # Local optional service access and a loose tethered cable. Source library mesh shared.
        side=-1 if index%2 else 1;y=1.25+(index%3)*1.35
        hatch=b.root('V2 · acces inspection',(side*2.08,y,1.17),p)
        b.place_asset('V2 KITBASH · trappe inspection',assets[index%3],(0,0,0),(.37,.48,.08),hatch,(0,-side*math.pi/2,0))
        if index in (1,2,4):
            smooth_pipe(b,'V2 · liaison inspection',[(side*2.03,y,1.0),(side*1.95,y+.22,.74),(side*2.01,y+.32,.24)],.013,grey,rack)
        # Different workstation locations, preserving their internal modular hierarchy.
        for o in p.children:
            if o.name.startswith('COFFRET '):o.location.y+=(-.45,.6,0,.30,-.7,.15)[index]
            if o.name.startswith('SECURITE '):o.location.y+=(-.3,.12,-.15,-.65,.25,-.4)[index]
        for o in p.children_recursive:
            if o.type=='LIGHT':
                o.data=o.data.copy();local_y=o.parent.location.y
                powers=((36,20,43),(58,32,47),(28,16,40),(90,63,80),(42,70,35),(45,30,55))
                i=min(2,int(local_y//2));o.data.energy=powers[index][i];o.data.color=((1,.93,.79),(1,.98,.91),(.91,.96,1))[(index+i)%3]
            if o.name.startswith('Luminaire · diffuseur'):
                mat=o.active_material.copy();mat.name='V2 · diffuseur cabine %02d'%index
                bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Emission Strength'].default_value=(1.05,1.3,.95,2.2,1.2,1.15)[index];assign(o,mat)
    # Panel variation remains subtle, no broad procedural dirt.
    for name in ('ST · panneaux ivoire vieilli','ST · sol resine creme'):
        m=bpy.data.materials.get(name)
        if not m:continue
        nt=m.node_tree;bs=nt.nodes.get('Principled BSDF');old=bs.inputs['Base Color'].links[0].from_socket
        info=nt.nodes.new('ShaderNodeObjectInfo');r=nt.nodes.new('ShaderNodeMapRange');r.inputs['To Min'].default_value=.90;r.inputs['To Max'].default_value=1.025;nt.links.new(info.outputs['Random'],r.inputs[0])
        mix=nt.nodes.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=1;nt.links.new(old,mix.inputs[1]);nt.links.new(r.outputs[0],mix.inputs[2]);nt.links.new(mix.outputs[0],bs.inputs['Base Color'])
    scene.view_settings.exposure=-.65
    scene['pa_station_refinement']='v2';scene['pa_detail_texture']=str(texture_path)
    report={'version':2,'seed':seed,'added_objects':len(b.collection.objects),'new_asset_sources':b.asset_report,'replaced_angular_curves':oldcurves,'texture_native_pixels':list(image.size),'texture_tile_m':.72,'texture_density_px_m':image.size[0]/.72,'note':'Dedicated regenerated albedo; no artificial resolution claim. Existing multiview maps retained for broad panels. Wear is local material color, not emitted light.'}
    scene['pa_station_refinement_report']=json.dumps(report,ensure_ascii=False);return report
