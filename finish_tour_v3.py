"""Add generated fallback maps, a modular forest belt, and editable shot cameras."""
import bpy,json,math,random,hashlib,importlib.util
from pathlib import Path
from mathutils import Vector
R=Path(__file__).parent;O=R/'output/tour-belvedere-v3'
bpy.ops.wm.open_mainfile(filepath=str(O/'tour-belvedere-projections-v3.blend'))
sc=bpy.context.scene

def signature():
    return {o.name:hashlib.sha256(str((o.parent.name if o.parent else None,list(map(tuple,o.matrix_world)),[tuple(v.co) for v in o.data.vertices] if o.type=='MESH' else None)).encode()).hexdigest() for o in sc.objects if o.type not in {'CAMERA','LIGHT'}}
before=signature()
def node(nt,kind,name):
    n=nt.nodes.new(kind);n.name=n.label=name;return n
def mathn(nt,op,a,b=0):
    n=node(nt,'ShaderNodeMath',op);n.operation=op
    for i,v in enumerate((a,b)):
        if isinstance(v,(float,int)):n.inputs[i].default_value=v
        else:nt.links.new(v,n.inputs[i])
    return n.outputs[0]
atlas=bpy.data.images.load(str(O/'material-atlas-albedo.png'),check_existing=True);atlas.pack()

def fallback_texture(mat,quadrant,meters=2,rest=False,tint=None):
    nt=mat.node_tree
    if rest:
        co=node(nt,'ShaderNodeAttribute','Coordonnees figees · complement');co.attribute_name='GPT_RestWorld';coord=co.outputs['Vector']
        no=node(nt,'ShaderNodeAttribute','Normales figees · complement');no.attribute_name='GPT_RestNormal';normal=no.outputs['Vector']
    else:
        co=node(nt,'ShaderNodeTexCoord','Coordonnees objet · complement');coord=co.outputs['Object']
        no=node(nt,'ShaderNodeNewGeometry','Normale complement')
        tr=node(nt,'ShaderNodeVectorTransform','Normale locale');tr.vector_type='NORMAL';tr.convert_from='WORLD';tr.convert_to='OBJECT';nt.links.new(no.outputs['Normal'],tr.inputs[0]);normal=tr.outputs[0]
    xyz=node(nt,'ShaderNodeSeparateXYZ','Position complement');nt.links.new(coord,xyz.inputs[0])
    nxyz=node(nt,'ShaderNodeSeparateXYZ','Axes complement');nt.links.new(normal,nxyz.inputs[0])
    weights=[mathn(nt,'POWER',mathn(nt,'ABSOLUTE',nxyz.outputs[a]),6) for a in 'XYZ']
    total=mathn(nt,'MAXIMUM',mathn(nt,'ADD',mathn(nt,'ADD',weights[0],weights[1]),weights[2]),.00001)
    outputs=[]
    # Axis selection blends three local planar mappings; atlas quadrants are guarded.
    for i,(a,b) in enumerate((('Y','Z'),('X','Z'),('X','Y'))):
        uv=node(nt,'ShaderNodeCombineXYZ','Atlas UV '+str(i))
        for j,axis in enumerate((a,b)):
            tiled=mathn(nt,'PINGPONG',mathn(nt,'DIVIDE',xyz.outputs[axis],meters),1)
            value=mathn(nt,'ADD',mathn(nt,'MULTIPLY',tiled,.492),quadrant[j]+.004)
            nt.links.new(value,uv.inputs[j])
        im=node(nt,'ShaderNodeTexImage','GPT · matiere de complement '+str(i));im.image=atlas;im.extension='EXTEND';nt.links.new(uv.outputs[0],im.inputs[0])
        m=node(nt,'ShaderNodeVectorMath','Poids triplanaire');m.operation='SCALE';nt.links.new(im.outputs['Color'],m.inputs[0]);nt.links.new(mathn(nt,'DIVIDE',weights[i],total),m.inputs['Scale']);outputs.append(m.outputs[0])
    out=outputs[0]
    for val in outputs[1:]:
        m=node(nt,'ShaderNodeVectorMath','Somme triplanaire');m.operation='ADD';nt.links.new(out,m.inputs[0]);nt.links.new(val,m.inputs[1]);out=m.outputs[0]
    if tint:
        gray=node(nt,'ShaderNodeRGBToBW','Detail matiere neutre');nt.links.new(out,gray.inputs[0])
        factor=mathn(nt,'MINIMUM',mathn(nt,'MAXIMUM',mathn(nt,'DIVIDE',gray.outputs[0],.48),.65),1.22)
        m=node(nt,'ShaderNodeMixRGB','Teinte materiau conservee');m.blend_type='MULTIPLY';m.inputs[0].default_value=1;m.inputs[1].default_value=(*tint[:3],1);nt.links.new(factor,m.inputs[2]);out=m.outputs[0]
    mat['GPT_fallback_texture']=True
    return out

updated=[]
for m in list(bpy.data.materials):
    nt=m.node_tree
    if not nt:continue
    bs=next((n for n in nt.nodes if n.type=='BSDF_PRINCIPLED'),None)
    if not bs:continue
    mix=nt.nodes.get('Materiau initial / patine GPT')
    if mix:
        is_mint=m.name.startswith(('Batiments','Beton · celadon'))
        road=m.name.startswith(('Voirie','Etancheite'))
        q=(0,.5) if is_mint else ((0,0) if road else (.5,.5))
        color=fallback_texture(m,q,1.8 if is_mint else (1.2 if road else 2.2),True,None if is_mint or road else tuple(mix.inputs[1].default_value))
        nt.links.new(color,mix.inputs[1]);updated.append(m.name)
    elif m.name.startswith('Massifs ·'):
        nt.links.new(fallback_texture(m,(.5,0),3.5),bs.inputs['Base Color']);updated.append(m.name)
    elif m.name.startswith(('Bordures ·','Equipements ·','Menuiseries ·')):
        nt.links.new(fallback_texture(m,(.5,.5),1.2,False,tuple(bs.inputs['Base Color'].default_value)),bs.inputs['Base Color']);updated.append(m.name)

# Reuse the packed botaniq sources and append three more silhouettes.
ASSETS=Path(r'K:\Connector-Blender\Blender-asset-lib-VDB\botaniq_full-Assets')
extra=['Tree_Acer-pseudoplatanus_B_summer.blend','Tree_Alnus-glutinosa_A_summer.blend','Tree_Carpinus-betulus_C_summer.blend']
for f in extra:
    with bpy.data.libraries.load(str(ASSETS/'blends_280/deciduous'/f),link=False) as (a,b):b.objects=a.objects
    c=bpy.data.collections.new('SOURCE BOTANIQ · '+Path(f).stem);c.use_fake_user=True
    for o in b.objects:
        if o:c.objects.link(o)
bpy.ops.object.make_local(type='ALL')
for _ in range(3):
    for kind in ('collections','objects','meshes','curves','materials','node_groups','images'):
        for item in list(getattr(bpy.data,kind)):
            if item.library:item.make_local()
for im in bpy.data.images:
    if im.source=='FILE' and not im.packed_file:
        p=Path(bpy.path.abspath(im.filepath))
        if not p.exists():p=ASSETS/'textures'/Path(im.filepath.replace('\\','/')).name
        if not p.exists():raise FileNotFoundError(p)
        im.filepath=str(p);im.reload();im.pack()
trees=sorted([c for c in bpy.data.collections if c.name.startswith('SOURCE BOTANIQ · Tree_')],key=lambda c:c.name)
shrubs=next(c for c in bpy.data.collections if c.name.startswith('SOURCE BOTANIQ · Shrub_'))
forest=bpy.data.collections.new('08 · Foret peripherique 360');sc.collection.children.link(forest)
def empty(name,parent=None):
    o=bpy.data.objects.new(name,None);forest.objects.link(o);o.parent=parent;return o
root=empty('FORET · ceinture 360');root['note']='Instances botaniq, 12 secteurs deplacables, 3 rangees decalees.'
sectors=[empty('FORET · secteur %02d'%(i+1),root) for i in range(12)]
rng=random.Random(261026)
heights={c:max((o.matrix_world@Vector(v)).z for o in c.objects if o.type=='MESH' for v in o.bound_box) for c in trees+[shrubs]}
instances=[]
def plant(c,x,y,height,sector):
    o=empty(('ARBRE' if c!=shrubs else 'SOUS-BOIS')+' · FORET %03d'%len(instances),sectors[sector]);o.instance_type='COLLECTION';o.instance_collection=c
    scale=height/max(.1,heights[c]);o.scale=(scale*rng.uniform(.88,1.12),scale*rng.uniform(.88,1.12),scale)
    o.location=(x,y,-.045);o.rotation_euler=(rng.uniform(-.035,.035),rng.uniform(-.035,.035),rng.uniform(0,math.tau))
    o['source_asset']=c.name;o['instance']=True;o['forest_height']=height;instances.append(o)
for row,(rx,ry,count) in enumerate(((60,145,84),(77,162,104),(95,180,124))):
    for i in range(count):
        a=math.tau*(i+.33*row+rng.uniform(-.23,.23))/count
        c=trees[(i+row*3)%len(trees)]
        plant(c,(rx+rng.uniform(-3,3))*math.cos(a),-15+(ry+rng.uniform(-3,3))*math.sin(a),rng.uniform(13,21)+row, int((a%math.tau)/math.tau*12))
for i in range(144):
    a=math.tau*(i+rng.uniform(-.2,.2))/144
    plant(shrubs,(55+rng.uniform(-2,3))*math.cos(a),-15+(139+rng.uniform(-2,3))*math.sin(a),rng.uniform(2.6,4.8),int(a%math.tau/math.tau*12))
for i in range(160):
    a=math.tau*(i+.5+rng.uniform(-.2,.2))/160
    plant(shrubs,(65+rng.uniform(-2,3))*math.cos(a),-15+(150+rng.uniform(-2,3))*math.sin(a),rng.uniform(4.0,6.0),int(a%math.tau/math.tau*12))

# Lightweight surrounding ground disc, below the approved ground; no alteration to V2.
vs=[(0,-15,-.085)]+[(125*math.cos(i*math.tau/128),-15+210*math.sin(i*math.tau/128),-.085) for i in range(128)]
fs=[(0,i+1,(i+1)%128+1) for i in range(128)]
me=bpy.data.meshes.new('Disque terrain peripherique');me.from_pydata(vs,[],fs);me.update()
o=bpy.data.objects.new('SOL · disque foret peripherique',me);forest.objects.link(o);o.parent=root;me.materials.append(bpy.data.materials['Massifs · terre'])

shots=bpy.data.collections.new('09 · Shots inspection 360');sc.collection.children.link(shots)
def camera(name,loc,target,lens=32,w=1440,h=960):
    d=bpy.data.cameras.new(name);o=bpy.data.objects.new(name,d);shots.objects.link(o);o.location=loc;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();d.lens=lens;d.clip_end=600
    o['pa_resolution_x']=w;o['pa_resolution_y']=h;return o
camera('CAM_06 · facade est',(32,-28,2.1),(22,-10,2.4),28)
camera('CAM_07 · arriere annexe',(23.8,21.8,2.0),(18,14,2.2),23)
camera('CAM_08 · pied rapproche',(-17,12,5),(0,0,6),40)
camera('CAM_09 · face ouest',(-15,22,4),(13,-6,3),32)
for i,(name,direction) in enumerate([('nord',(0,1,0)),('est',(1,0,0)),('sud',(0,-1,0)),('ouest',(-1,0,0))]):
    loc=Vector((6,-30,1.7));camera('CAM_%02d · horizon %s'%(10+i,name),loc,loc+Vector(direction)*40,24)
pan=camera('CAM_14 · panorama 360',(6,-30,1.7),(6,-10,1.7),24,2400,1200);pan.data.type='PANO';pan.data.panorama_type='EQUIRECTANGULAR'
camera('CAM_15 · ensemble foret',(110,-190,120),(0,-15,5),40,1440,960)
for o in sc.objects:
    if o.type=='CAMERA' and o.name.startswith('PROJ_'):o['pa_projection_only']=True
for name,w,h in [('CAM_01 · reference portrait',1000,1200),('CAM_02 · ensemble frontal',1440,960),('CAM_03 · approche pieton',1000,1200),('CAM_04 · vue aerienne',1200,1200),('CAM_05 · controle lateral',1440,960)]:
    c=bpy.data.objects[name];c['pa_resolution_x']=w;c['pa_resolution_y']=h

# Camera browser runtime validation: complete cycle and no camera transform mutation.
bpy.context.view_layer.update()
spec=importlib.util.spec_from_file_location('pa_navigation_v3',R/'pano_atelier/camera_navigation.py');nav=importlib.util.module_from_spec(spec);spec.loader.exec_module(nav);nav.register()
cams=nav.cameras(sc);saved=sc.camera;transforms={o.name:o.matrix_world.copy() for o in cams}
sc.camera=cams[0]
for i in range(len(cams)):
    assert bpy.ops.pa.camera_step(direction=1)=={'FINISHED'}
    assert sc.camera==cams[(i+1)%len(cams)]
assert sc.camera==cams[0]
assert bpy.ops.pa.camera_step(direction=-1)=={'FINISHED'} and sc.camera==cams[-1]
camera_ok=all(o.matrix_world==transforms[o.name] for o in cams)
sc.camera=saved;nav.unregister()

# Existing architecture and modules are untouched by the forest stage.
after=signature();preserved=all(after[n]==v for n,v in before.items());assert preserved
old=root.location.copy();child=instances[0];p=child.matrix_world.translation.copy();root.location.x+=3;bpy.context.view_layer.update()
forest_movable=abs(child.matrix_world.translation.x-p.x-3)<1e-4
root.location=old;bpy.context.view_layer.update();assert forest_movable and camera_ok
sc.name='Tour belvedere · mapping complet et foret 360 · V3'
sc['phase']='03 · dix projections, complements textures, foret 360 en instances'
sc.camera=bpy.data.objects['CAM_02 · ensemble frontal'];sc.render.resolution_x=1440;sc.render.resolution_y=960;sc.render.resolution_percentage=100
sc.cycles.samples=64;sc.cycles.use_denoising=True;sc.render.use_persistent_data=True;sc.cycles.device='GPU';sc.cycles.transparent_max_bounces=16
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.region_3d.view_perspective='CAMERA';area.spaces.active.clip_end=700;area.spaces.active.shading.type='MATERIAL';area.spaces.active.shading.use_scene_world=True
text=bpy.data.texts.new('Pano Atelier · navigation cameras.py');text.write((R/'pano_atelier/camera_navigation.py').read_text(encoding='utf8')+'\nregister()\n')
report={'checks':{'existing_objects_unchanged':preserved,'forest_parent_move':forest_movable,'camera_cycle_forward_backward_wrap':camera_ok,'all_images_packed':all(im.packed_file for im in bpy.data.images if im.source=='FILE'),'all_asset_data_local':all(not x.library for kind in ('collections','objects','meshes','curves','materials','node_groups','images') for x in getattr(bpy.data,kind))},'new_tree_instances':312,'new_shrub_instances':304,'tree_species':[c.name for c in trees],'forest_sectors':12,'forest_center':[0,-15],'forest_bands_m':[[60,145],[77,162],[95,180]],'texture_complement_materials':updated,'projection_views':10,'camera_shots':[o.name for o in cams],'notes':['Forest extent is an artistic extension, not a survey of the reference location.','Six broadleaf tree types plus shrub understory; geometries and image resources shared.','Fallback albedo textures fill unobserved surface regions; not every point is directly camera-projected.','No UV bake, no complete collision validation.']}
assert all(report['checks'].values()),report
(O/'validation-v3.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
bpy.ops.wm.save_as_mainfile(filepath=str(O/'tour-belvedere-foret-360-v3.blend'))
print('TOUR_V3_FINISHED',json.dumps(report['checks']),flush=True)
