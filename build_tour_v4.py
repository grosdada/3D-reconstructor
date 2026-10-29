"""Ground contact, economical botaniq grass and a packed Pure-sky environment."""
import bpy, math, random, json, shutil, hashlib
from pathlib import Path
from mathutils import Vector
R=Path(__file__).parent; O=R/'output/tour-belvedere-v4'; T=O/'textures'; T.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(R/'output/tour-belvedere-v3/tour-belvedere-foret-360-v3.blend'))
sc=bpy.context.scene
def fingerprint(o):
    return hashlib.sha256(str((o.parent.name if o.parent else None,list(map(tuple,o.matrix_world)),[tuple(v.co) for v in o.data.vertices] if o.type=='MESH' else None)).encode()).hexdigest()
before={o.name:fingerprint(o) for o in sc.objects if not o.name.startswith('Dalle soubassement')}
coll=bpy.data.collections.new('10 · Terrain vivant et herbes');sc.collection.children.link(coll)
root=bpy.data.objects.new('HERBE · assemblage deplacable',None);coll.objects.link(root)
def mesh_obj(name,verts,faces):
    me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update()
    ob=bpy.data.objects.new(name,me);coll.objects.link(ob);ob.parent=root;return ob
def node(nt,kind,name):
    n=nt.nodes.new(kind);n.name=n.label=name;return n
def calc(nt,op,a,b=0):
    n=node(nt,'ShaderNodeMath',op);n.operation=op
    for i,v in enumerate((a,b)):
        if isinstance(v,(int,float)):n.inputs[i].default_value=v
        else:nt.links.new(v,n.inputs[i])
    return n.outputs[0]
atlas=next(i for i in bpy.data.images if i.name.startswith('material-atlas-albedo'))
def texture_material(name,quadrant,scales,tint):
    m=bpy.data.materials.new(name);m.use_nodes=True;nt=m.node_tree;bs=nt.nodes.get('Principled BSDF');bs.inputs['Roughness'].default_value=.92
    coord=node(nt,'ShaderNodeTexCoord','Coordonnees locales');outs=[]
    for i,meters in enumerate(scales):
        mapping=node(nt,'ShaderNodeMapping','Variation atlas '+str(i));mapping.inputs['Scale'].default_value=(1/meters,1/meters,1/meters);mapping.inputs['Rotation'].default_value[2]=i*1.173;mapping.inputs['Location'].default_value=(i*3.17,i*1.87,0);nt.links.new(coord.outputs['Object'],mapping.inputs['Vector'])
        sep=node(nt,'ShaderNodeSeparateXYZ','Axes atlas');nt.links.new(mapping.outputs[0],sep.inputs[0]);uv=node(nt,'ShaderNodeCombineXYZ','Quart atlas')
        for j,axis in enumerate('XY'):
            v=calc(nt,'ADD',calc(nt,'MULTIPLY',calc(nt,'PINGPONG',sep.outputs[axis],1),.482),quadrant[j]+.009);nt.links.new(v,uv.inputs[j])
        im=node(nt,'ShaderNodeTexImage','Detail photographique '+str(i));im.image=atlas;im.extension='EXTEND';nt.links.new(uv.outputs[0],im.inputs[0]);outs.append(im.outputs['Color'])
    color=outs[0]
    for i,out in enumerate(outs[1:]):
        mix=node(nt,'ShaderNodeMixRGB','Moyenne anti repetition');mix.inputs[0].default_value=1/(i+2);nt.links.new(color,mix.inputs[1]);nt.links.new(out,mix.inputs[2]);color=mix.outputs[0]
    mix=node(nt,'ShaderNodeMixRGB','Teinte terre naturelle');mix.inputs[0].default_value=.52;mix.inputs[2].default_value=(*tint,1);nt.links.new(color,mix.inputs[1]);nt.links.new(mix.outputs[0],bs.inputs['Base Color'])
    bump=node(nt,'ShaderNodeBump','Microrelief sol');bump.inputs['Strength'].default_value=.18;bump.inputs['Distance'].default_value=.022;nt.links.new(color,bump.inputs['Height']);nt.links.new(bump.outputs[0],bs.inputs['Normal'])
    return m
soil=texture_material('V4 · terre herbacee sans grille',(.5,0),(2.7,4.13,6.71),(.19,.17,.10))
plinth=texture_material('V4 · soubassement beton',(.5,.5),(1.7,2.93),(.29,.28,.24))
# Fine concrete grain avoids a stretched planar map on the vertical plinth.
pnt=plinth.node_tree;pbs=pnt.nodes.get('Principled BSDF')
for socket in ('Base Color','Normal'):
    for link in list(pbs.inputs[socket].links):pnt.links.remove(link)
pbs.inputs['Base Color'].default_value=(.32,.31,.275,1)
noise=node(pnt,'ShaderNodeTexNoise','Grain fin du beton');noise.inputs['Scale'].default_value=65
pc=node(pnt,'ShaderNodeTexCoord','Coordonnees grain');pnt.links.new(pc.outputs['Object'],noise.inputs['Vector'])
pb=node(pnt,'ShaderNodeBump','Relief fin du soubassement');pb.inputs['Distance'].default_value=.003;pb.inputs['Strength'].default_value=.22;pnt.links.new(noise.outputs['Fac'],pb.inputs['Height']);pnt.links.new(pb.outputs[0],pbs.inputs['Normal'])
foundations=[]
for ob in sc.objects:
    if ob.name.startswith('Dalle soubassement'):
        for v in ob.data.vertices:
            for k in (0,1):v.co[k]+=math.copysign(.16,v.co[k])
            v.co.z=math.copysign(.25,v.co.z)
        ob.location.z=.04
        for mod in list(ob.modifiers):
            if mod.type=='NODES':ob.modifiers.remove(mod)
        ob.data.materials.clear();ob.data.materials.append(plinth);foundations.append(ob)
# Exact holes in the new surface: asphalt, forecourt, pavement and buildings.
rects=[(-15.5,-8.5,-85,65),(2.5,9.5,-62.5,42.5),(-16,32,-29,-21),(-7,7,-8.5,8.5),(10.9,12.9,-14.5,14.5),(12.84,23.16,-36.16,12.16),(13.84,22.16,11.84,18.16)]
def inside(x,y,margin=0):return any(a-margin<=x<=b+margin and c-margin<=y<=d+margin for a,b,c,d in rects)
def distance(x,y):return min(math.hypot(max(a-x,0,x-b),max(c-y,0,y-d)) for a,b,c,d in rects)
def height(x,y):return .038+.024*min(1,distance(x,y)/.7)+.003*math.sin(x*.41)*math.sin(y*.27)*min(1,distance(x,y))
xs=sorted(set([float(x) for x in range(-126,127,4)]+[v for a,b,c,d in rects for v in (a,b,a-.5,b+.5)]))
ys=sorted(set([float(y) for y in range(-226,199,4)]+[v for a,b,c,d in rects for v in (c,d,c-.5,d+.5)]))
verts=[];faces=[];lookup={}
def vert(x,y):
    key=(x,y)
    if key not in lookup:lookup[key]=len(verts);verts.append((x,y,height(x,y)))
    return lookup[key]
for a,b in zip(xs,xs[1:]):
    for c,d in zip(ys,ys[1:]):
        x=(a+b)/2;y=(c+d)/2
        if inside(x,y) or (x/123)**2+((y+15)/208)**2>1:continue
        faces.append(tuple(vert(x,y) for x,y in ((a,c),(b,c),(b,d),(a,d))))
ground=mesh_obj('SOL · terre relevee avec decoupes voirie',verts,faces);ground.data.materials.append(soil)
# The original ground remains underneath; the same unobtrusive material covers its edge.
for ob in sc.objects:
    if ob.name in ('Terrain','SOL · disque foret peripherique'):
        ob.data.materials.clear();ob.data.materials.append(soil)
AS=Path(r'K:\Connector-Blender\Blender-asset-lib-VDB\botaniq_full-Assets')
sources=bpy.data.collections.new('SOURCES V4 · herbes botaniq');sources.use_fake_user=True
source_names=['Grass_Basic-Strands_B_spring-summer','Grass_Wild_C_spring-summer','Grass_Basic-dry_D_spring-summer']
source_report=[]
for i,name in enumerate(source_names):
    with bpy.data.libraries.load(str(AS/'blends_280/grass'/(name+'.blend')),link=False) as (a,b):b.objects=a.objects
    ob=next(o for o in b.objects if o and o.type=='MESH')
    ob.name='V4_GRASS_%02d'%i;ob.location=(0,0,0);ob.rotation_euler=(0,0,0);ob.scale=(1,1,1)
    for mod in list(ob.modifiers):ob.modifiers.remove(mod)
    sources.objects.link(ob)
    source_report.append({'source':name,'object':ob.name,'triangles':sum(len(p.vertices)-2 for p in ob.data.polygons),'color':list(ob.color)})
for _ in range(3):
    for kind in ('collections','objects','meshes','materials','node_groups','images'):
        for item in list(getattr(bpy.data,kind)):
            if item.library:item.make_local()
for im in bpy.data.images:
    if im.source=='FILE' and not im.packed_file:
        p=Path(bpy.path.abspath(im.filepath))
        if not p.exists():p=AS/'textures'/Path(im.filepath.replace('\\','/')).name
        if not p.exists():raise FileNotFoundError(p)
        im.filepath=str(p);im.reload();im.pack()
# Deterministic point scatter; no realized geometry or per-tuft Blender objects.
rng=random.Random(2610264);points=[];rotations=[];scales=[];variants=[]
def add(x,y,far=False):
    if inside(x,y,.26) or (x/119)**2+((y+15)/202)**2>1:return
    dist=distance(x,y)
    probability=.045 if far else (.92 if dist<5 else (.40 if dist<16 else .16))
    if rng.random()>probability:return
    variant=rng.choices((0,1,2),(.68,.24,.08))[0]
    h=rng.uniform(.055,.13) if variant==0 else rng.uniform(.08,.20)
    sourceheight=(.0572,.3698,.1993)[variant]
    sz=h/sourceheight;sxy=rng.uniform(1.7,2.8) if variant==0 else rng.uniform(.9,1.5)
    points.append((x,y,height(x,y)+.003));rotations.append((0,0,rng.uniform(0,math.tau)));scales.append((sxy,sxy*rng.uniform(.8,1.2),sz));variants.append(variant)
for ix in range(385):
    for iy in range(577):
        x=-50+(ix+rng.random())*.26;y=-90+(iy+rng.random())*.26;add(x,y)
for ix in range(120):
    for iy in range(205):
        x=-120+(ix+rng.random())*2;y=-220+(iy+rng.random())*2
        if -50<x<50 and -90<y<60:continue
        add(x,y,True)
ob=mesh_obj('HERBE · instances botaniq · 25 pourcent viewport',points,[])
for name,typ,values in [('grass_rotation','FLOAT_VECTOR',rotations),('grass_scale','FLOAT_VECTOR',scales),('grass_variant','INT',variants)]:
    attr=ob.data.attributes.new(name,typ,'POINT')
    for item,value in zip(attr.data,values):
        if typ=='FLOAT_VECTOR':item.vector=value
        else:item.value=value
ng=bpy.data.node_groups.new('V4 · herbe instanciee economique','GeometryNodeTree')
ng.interface.new_socket(name='Geometry',in_out='INPUT',socket_type='NodeSocketGeometry');ng.interface.new_socket(name='Geometry',in_out='OUTPUT',socket_type='NodeSocketGeometry')
inp=node(ng,'NodeGroupInput','Points');out=node(ng,'NodeGroupOutput','Instances non realisees')
ci=node(ng,'GeometryNodeCollectionInfo','Trois touffes botaniq');ci.inputs['Collection'].default_value=sources;ci.inputs['Separate Children'].default_value=True;ci.inputs['Reset Children'].default_value=True
inst=node(ng,'GeometryNodeInstanceOnPoints','Instances herbe');inst.inputs['Pick Instance'].default_value=True;ng.links.new(ci.outputs['Instances'],inst.inputs['Instance'])
delete=node(ng,'GeometryNodeDeleteGeometry','Alleger viewport a 25 pourcent');delete.domain='POINT';ng.links.new(inp.outputs['Geometry'],delete.inputs['Geometry'])
idx=node(ng,'GeometryNodeInputIndex','Index');mod=calc(ng,'MODULO',idx.outputs[0],4);keep=calc(ng,'GREATER_THAN',mod,.5)
view=node(ng,'GeometryNodeIsViewport','Viewport uniquement');sel=node(ng,'FunctionNodeBooleanMath','Selection viewport');sel.operation='AND';ng.links.new(keep,sel.inputs[0]);ng.links.new(view.outputs[0],sel.inputs[1]);ng.links.new(sel.outputs[0],delete.inputs['Selection']);ng.links.new(delete.outputs[0],inst.inputs['Points'])
for name,typ,socket in [('grass_rotation','FLOAT_VECTOR','Rotation'),('grass_scale','FLOAT_VECTOR','Scale'),('grass_variant','INT','Instance Index')]:
    attr=node(ng,'GeometryNodeInputNamedAttribute',name);attr.data_type=typ;attr.inputs['Name'].default_value=name;ng.links.new(attr.outputs['Attribute'],inst.inputs[socket])
ng.links.new(inst.outputs['Instances'],out.inputs['Geometry']);ob.modifiers.new('Herbe · instances sans subdivision','NODES').node_group=ng
ob['render_instances']=len(points);ob['viewport_instances_approx']=len(points)//4;ob['note']='Trois touffes botaniq, aucune realisation, 25% visible dans le viewport; render 100%.'
hdri='kloppenheim_05_puresky_4k.exr';src=Path(r'K:\Connector-Blender\HDR\HDRI-Haven\Pure-sky')/hdri;shutil.copy2(src,T/hdri)
sc.world=sc.world.copy();sc.world.name='V4 · ciel seul · Kloppenheim 05';sc.world.use_nodes=True;nt=sc.world.node_tree;nt.nodes.clear()
env=node(nt,'ShaderNodeTexEnvironment','HDRI Pure-sky');env.image=bpy.data.images.load(str(T/hdri));env.image.pack()
co=node(nt,'ShaderNodeTexCoord','Direction ciel');ma=node(nt,'ShaderNodeMapping','Orientation ciel');ma.inputs['Rotation'].default_value[2]=math.radians(105);nt.links.new(co.outputs['Generated'],ma.inputs[0]);nt.links.new(ma.outputs[0],env.inputs[0])
bg=node(nt,'ShaderNodeBackground','Lumiere HDRI');bg.inputs['Strength'].default_value=.8;nt.links.new(env.outputs[0],bg.inputs['Color']);wo=node(nt,'ShaderNodeOutputWorld','World');nt.links.new(bg.outputs[0],wo.inputs[0])
for light in sc.objects:
    if light.type=='LIGHT':light.hide_render=True
sc.render.engine='CYCLES';sc.cycles.samples=64;sc.cycles.use_denoising=True;sc.view_settings.exposure=.4
sc.name='Tour belvedere · herbe et ciel HDRI · V4';sc.camera=bpy.data.objects['CAM_02 · ensemble frontal'];sc.render.resolution_x=1440;sc.render.resolution_y=960;sc.render.resolution_percentage=100
bpy.context.view_layer.update()
preserved=all(fingerprint(bpy.data.objects[n])==v for n,v in before.items());assert preserved
assert all(not inside(x,y,.25) for x,y,z in points)
contacts=[]
for f in foundations:
    z=[(f.matrix_world@Vector(p)).z for p in f.bound_box];assert min(z)<0 and max(z)>.25
    contacts.append({'name':f.name,'bottom':min(z),'top':max(z),'wall_bottom':.25})
old=root.location.copy();oldpos=ob.matrix_world.translation.copy();root.location.x+=2;bpy.context.view_layer.update();movable=abs(ob.matrix_world.translation.x-oldpos.x-2)<.001;root.location=old;bpy.context.view_layer.update();assert movable
report={'geometry_other_than_foundations_preserved':preserved,'foundations':contacts,'grass_sources':source_report,'grass_instances':len(points),'viewport_instances':(len(points)+3)//4,'grass_unique_triangles':sum(s['triangles'] for s in source_report),'grass_virtual_triangles':sum(source_report[i]['triangles'] for i in variants),'terrain_faces':len(faces),'grass_outside_pavements':True,'assembly_movable':movable,'hdri':hdri,'hdri_source':str(src),'hdri_strength':.8,'hdri_rotation_degrees':105,'images_unpacked':[i.name for i in bpy.data.images if i.source=='FILE' and not i.packed_file]}
assert not report['images_unpacked'];(O/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
bpy.ops.wm.save_as_mainfile(filepath=str(O/'tour-belvedere-herbe-hdri-v4.blend'))
print('V4_BUILD_DONE',json.dumps(report),flush=True)
