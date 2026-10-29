"""Blender side of the photo → scene pipeline. Main thread only.

Builds the rough camera-mapped mesh, the editable modules, renders guides and
depth, writes atlases and assembles Principled materials, procedural detail,
lights, world and compositor. Numerical work lives in the pure photo_* modules.
"""
import math
from pathlib import Path
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree
from . import core, engine, photo_look as LOOK, photo_texture as T, photo_util as U

TAG='pa_photo'


def matrix(m):
    return Matrix([list(map(float,r)) for r in np.asarray(m)])


def nodes_on(mat):
    if hasattr(mat,'use_nodes') and not mat.use_nodes: mat.use_nodes=True
    return mat.node_tree


def socket(sockets,name,kind=None):
    for s in sockets:
        if s.name==name and (kind is None or s.type==kind): return s
    raise KeyError(name)


def new_scene(name,width,height):
    scene=bpy.data.scenes.new(name)
    scene.render.engine='CYCLES'
    scene.render.resolution_x=width; scene.render.resolution_y=height; scene.render.resolution_percentage=100
    scene.view_settings.view_transform='Standard'; scene.view_settings.look='None'; scene.view_settings.exposure=0
    scene.cycles.samples=64; scene.cycles.use_denoising=True
    prefs=bpy.context.preferences.addons.get('cycles')
    if prefs and getattr(prefs.preferences,'compute_device_type','NONE')!='NONE': scene.cycles.device='GPU'
    scene[TAG]=True
    return scene


def collection(scene,name,parent=None):
    c=bpy.data.collections.new(name)
    (parent.children if parent else scene.collection.children).link(c)
    return c


def mesh_object(name,verts,faces,coll,location=(0,0,0),smooth=False):
    me=bpy.data.meshes.new(name)
    loc=np.asarray(location,np.float64)
    me.from_pydata((np.asarray(verts,np.float64)-loc).tolist(),[],[tuple(int(i) for i in f) for f in faces]); me.validate(); me.update()
    if smooth:
        for p in me.polygons: p.use_smooth=True
    ob=bpy.data.objects.new(name,me); coll.objects.link(ob); ob.location=Vector(loc)
    return ob


def camera(scene,name,m,fov,coll,width=None,height=None):
    data=bpy.data.cameras.new(name); ob=bpy.data.objects.new(name,data); coll.objects.link(ob)
    data.type='PERSP'; data.sensor_fit='HORIZONTAL'; data.lens_unit='FOV'; data.angle=math.radians(fov)
    data.clip_start=.02; data.clip_end=2000
    ob.matrix_world=matrix(m)
    if width: ob['pa_resolution']=[int(width),int(height)]
    return ob


def emission_material(name,image=None,colour=(1,1,1,1),strength=1.):
    m=bpy.data.materials.new(name); nt=nodes_on(m); nt.nodes.clear()
    em=nt.nodes.new('ShaderNodeEmission'); out=nt.nodes.new('ShaderNodeOutputMaterial')
    em.inputs['Strength'].default_value=strength; em.inputs['Color'].default_value=colour
    if image is not None:
        tex=nt.nodes.new('ShaderNodeTexImage'); tex.image=image; tex.interpolation='Linear'; tex.extension='EXTEND'
        nt.links.new(tex.outputs['Color'],em.inputs['Color'])
    nt.links.new(em.outputs[0],out.inputs['Surface'])
    return m


def image(name,array,path,data=False):
    engine.write_image(path,array,data)
    im=bpy.data.images.load(str(path),check_existing=False); im.name=name
    if data: im.colorspace_settings.name='Non-Color'
    im.pack()
    return im


def replace_image(old,name,array,path,data=False):
    """New packed image for updated pixels; every node using the old one is redirected."""
    new=image(name+' ·',array,path,data)
    if old is not None:
        for tree in [m.node_tree for m in bpy.data.materials if m.node_tree]+list(bpy.data.node_groups):
            for n in tree.nodes:
                if getattr(n,'image',None)==old: n.image=new
        bpy.data.images.remove(old)
    new.name=name
    return new


# ---------------------------------------------------------------- phase 1 · camera mapping

def rough(scene,photo_image,depth,fov,cam_matrix,coll,resolution=200,edge=.08):
    """Dense depth mesh seen from the photo camera, photo projected by its UVs."""
    h0,w0=depth.shape; w=min(resolution,w0); h=max(8,round(w*h0/w0))
    d=U.nearest(depth,w,h).astype(np.float32)
    verts,faces,uv=core.grid_mesh(d,fov,False,edge)
    if not faces: raise ValueError('Profondeur inutilisable pour le camera mapping.')
    ob=mesh_object('Camera mapping · brut',verts,faces,coll)
    layer=ob.data.uv_layers.new(name='Photo')
    loops=np.empty(len(ob.data.loops),np.int64); ob.data.loops.foreach_get('vertex_index',loops)
    layer.data.foreach_set('uv',uv[loops].ravel())
    ob.matrix_world=matrix(cam_matrix)
    ob.data.materials.append(emission_material('PA Brut · projection caméra',photo_image))
    ob[TAG+'_rough']=True
    return ob


# ---------------------------------------------------------------- phase 2 · modules

GROUPS=('Architecture','Ouvertures','Objets','Fond')


def build_modules(scene,structure,coll):
    """Editable objects from the analysis; frames and glass follow their wall."""
    groups={g:collection(scene,g,coll) for g in GROUPS}
    objects={}
    for i,m in enumerate(structure['modules']):
        ob=mesh_object(m['name'],m['vertices'],m['faces'],groups[m['group']],m['pivot'],smooth=m['kind']=='object')
        ob[TAG+'_kind']=m['kind']; ob[TAG+'_index']=i
        if m.get('label'): ob[TAG+'_label']=m['label']
        if m.get('material_hint'): ob[TAG+'_hint']=m['material_hint']
        if m.get('bevel'):
            mod=ob.modifiers.new('Chanfreins','BEVEL'); mod.width=m['bevel']; mod.segments=2; mod.limit_method='ANGLE'
            wn=ob.modifiers.new('Normales pondérées','WEIGHTED_NORMAL'); wn.keep_sharp=True
        if m['kind']=='glass':
            ob.visible_shadow=False
        if m['kind']=='backdrop':
            ob.visible_diffuse=False; ob.visible_shadow=False; ob.visible_volume_scatter=False
        objects[m['name']]=ob
    # Frames / glass of an opening move with their wall. Objects only carry a
    # translation here, so the parent inverse is exact without evaluating the scene.
    for name,ob in objects.items():
        if ob[TAG+'_kind'] in ('frame','glass'):
            wall=objects.get('Mur '+name.split(' ')[-1].split('-')[0])
            if wall:
                ob.parent=wall; ob.matrix_parent_inverse=Matrix.Translation(wall.location).inverted()
    scene.view_layers[0].update()
    return objects


def unwrap(scene,objects,margin=.004):
    vl=scene.view_layers[0]
    for ob in objects:
        with bpy.context.temp_override(scene=scene,view_layer=vl,active_object=ob,object=ob,selected_objects=[ob],selected_editable_objects=[ob],edit_object=ob):
            vl.objects.active=ob
            bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.uv.smart_project(angle_limit=math.radians(60),island_margin=margin,area_weight=1.)
            bpy.ops.object.mode_set(mode='OBJECT')
        ob.data.uv_layers[0].name='Atlas'


def triangles(scene,ob):
    """Evaluated (modifiers applied) triangles: uv (T,3,2), world positions and normals (T,3,3)."""
    dg=scene.view_layers[0].depsgraph; dg.update(); ev=ob.evaluated_get(dg); me=ev.to_mesh()
    try:
        me.calc_loop_triangles(); n=len(me.loop_triangles)
        loops=np.empty(n*3,np.int64); me.loop_triangles.foreach_get('loops',loops)
        verts=np.empty(n*3,np.int64); me.loop_triangles.foreach_get('vertices',verts)
        co=np.empty(len(me.vertices)*3,np.float32); me.vertices.foreach_get('co',co); co=co.reshape(-1,3)
        uv=np.zeros(len(me.loops)*2,np.float32)
        if me.uv_layers.active: me.uv_layers.active.data.foreach_get('uv',uv)
        uv=uv.reshape(-1,2)
        normals=np.empty(len(me.loops)*3,np.float32); me.corner_normals.foreach_get('vector',normals) if hasattr(me,'corner_normals') else me.loops.foreach_get('normal',normals)
        normals=normals.reshape(-1,3)
        mw=np.array(ev.matrix_world); rot=mw[:3,:3]; nrm_m=np.linalg.inv(rot).T
        pos=co[verts]@rot.T+mw[:3,3]; nrm=normals[loops]@nrm_m.T
        nrm/=np.maximum(np.linalg.norm(nrm,axis=1,keepdims=True),1e-9)
        return uv[loops].reshape(n,3,2),pos.reshape(n,3,3),nrm.reshape(n,3,3)
    finally: ev.to_mesh_clear()


def samples(scene,objects,count,rng):
    """Area-weighted surface samples (positions, normals, area weights, owner index)."""
    tris=[triangles(scene,o)[1:] for o in objects]
    areas=[np.linalg.norm(np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0]),axis=1)/2 for p,_ in tris]
    total=sum(a.sum() for a in areas)
    P=[];N=[];A=[];O=[]
    for k,((pos,nrm),area) in enumerate(zip(tris,areas)):
        if not len(area) or area.sum()<=0: continue
        n=max(4,int(count*area.sum()/max(total,1e-9)))
        idx=rng.choice(len(area),n,p=area/area.sum())
        r1=np.sqrt(rng.random(n)); r2=rng.random(n)
        w=np.stack((1-r1,r1*(1-r2),r1*r2),1)
        P.append(np.einsum('ij,ijk->ik',w,pos[idx])); N.append(np.einsum('ij,ijk->ik',w,nrm[idx]))
        A.append(np.full(n,area.sum()/n)); O.append(np.full(n,k))
    N=np.concatenate(N); N/=np.maximum(np.linalg.norm(N,axis=1,keepdims=True),1e-9)
    return np.concatenate(P),N,np.concatenate(A),np.concatenate(O)


def bvh(scene,objects):
    V=[];F=[]
    for o in objects:
        _,pos,_=triangles(scene,o); base=len(V)
        V.extend(map(tuple,pos.reshape(-1,3))); F.extend((base+3*i,base+3*i+1,base+3*i+2) for i in range(len(pos)))
    return BVHTree.FromPolygons(V,F,all_triangles=True)


def visible(tree,origin,points,tolerance=.03):
    o=Vector(origin); out=np.zeros(len(points),bool)
    for i,p in enumerate(points):
        d=Vector(p)-o; dist=d.length
        if dist<1e-6: continue
        hit=tree.ray_cast(o,d/dist,dist+tolerance)
        out[i]=hit[0] is not None and abs(hit[3]-dist)<=tolerance+.01*dist
    return out


def free_position(tree,origin,target):
    d=Vector(target)-Vector(origin); dist=d.length
    if dist<1e-6: return True
    return tree.ray_cast(Vector(origin),d/dist,dist+.25)[0] is None


# ---------------------------------------------------------------- renders

def render(scene,cam,path,width,height,samples=32,exr=True,transparent=False,denoise=True,override=None,filter_size=1.5):
    r=scene.render; c=scene.cycles
    scene.camera=cam; r.resolution_x=int(width); r.resolution_y=int(height); r.resolution_percentage=100
    r.film_transparent=transparent; r.filter_size=filter_size
    c.samples=int(samples); c.use_denoising=denoise and samples>4
    r.image_settings.file_format='OPEN_EXR' if exr else 'PNG'
    r.image_settings.color_depth='32' if exr else '8'
    vl=scene.view_layers[0]; old=vl.material_override; vl.material_override=override
    compositing=r.use_compositing; r.use_compositing=False  # pipeline images stay raw scene-linear
    try:
        r.filepath=str(path)
        with bpy.context.temp_override(scene=scene,view_layer=vl):
            bpy.ops.render.render(write_still=True,scene=scene.name)
    finally: vl.material_override=old; r.use_compositing=compositing
    return engine.load_pixels(path)


def depth_material():
    m=bpy.data.materials.get('PA Photo · profondeur')
    if m: return m
    m=bpy.data.materials.new('PA Photo · profondeur'); nt=nodes_on(m); nt.nodes.clear()
    cd=nt.nodes.new('ShaderNodeCameraData'); em=nt.nodes.new('ShaderNodeEmission'); out=nt.nodes.new('ShaderNodeOutputMaterial')
    nt.links.new(cd.outputs['View Z Depth'],em.inputs['Color']); nt.links.new(em.outputs[0],out.inputs['Surface'])
    return m


def render_depth(scene,cam,path,width,height,exclude=()):
    hidden=[o for o in exclude if not o.hide_render]
    for o in hidden: o.hide_render=True
    bounces=scene.cycles.max_bounces; scene.cycles.max_bounces=0
    try: a=render(scene,cam,path,width,height,samples=1,transparent=True,denoise=False,override=depth_material(),filter_size=.01)
    finally:
        scene.cycles.max_bounces=bounces
        for o in hidden: o.hide_render=False
    return np.where(a[...,3]>.5,a[...,0]/np.maximum(a[...,3],1e-6),0).astype(np.float32)


def render_with(scene,cam,path,width,height,materials,samples=4):
    """Temporarily swap object materials (e.g. atlas emission / coverage) for one render."""
    saved={}
    for ob,mat in materials.items():
        saved[ob]=[s.material for s in ob.material_slots]
        if not ob.material_slots: ob.data.materials.append(None); saved[ob]=[None]
        for s in ob.material_slots: s.link='OBJECT'; s.material=mat
    bounces=scene.cycles.max_bounces; scene.cycles.max_bounces=0
    try: return render(scene,cam,path,width,height,samples=samples,transparent=True,denoise=False,filter_size=.01 if samples==1 else .5)
    finally:
        scene.cycles.max_bounces=bounces
        for ob,mats in saved.items():
            for s,m in zip(ob.material_slots,mats): s.material=None; s.link='DATA'
            if mats==[None] and len(ob.data.materials)==1 and ob.data.materials[0] is None: ob.data.materials.clear()


def render_ids(scene,cam,path,width,height,objects):
    """Object index per pixel (-1 = nothing), exact: one sample, no filtering."""
    mats={ob:emission_material('PA id · '+ob.name,colour=((i+1)/1024,0,0,1)) for i,ob in enumerate(objects)}
    try:
        a=render_with(scene,cam,path,width,height,mats,samples=1)
    finally:
        for m in mats.values(): bpy.data.materials.remove(m)
    return np.where(a[...,3]>.5,np.rint(a[...,0]/np.maximum(a[...,3],1e-6)*1024)-1,-1).astype(np.int32)


# ---------------------------------------------------------------- phase 4/5 · materials

def pixel_angle_group(scene,cam):
    """Shared value: world size of one pixel per metre of distance (2·tan(fov/2)/width).

    A driver follows the photo camera's field of view and the render width; the
    pipeline also writes the value explicitly. One group per generated scene.
    """
    name='PA Photo · angle pixel · '+scene.name
    ng=bpy.data.node_groups.get(name)
    if ng is None:
        ng=bpy.data.node_groups.new(name,'ShaderNodeTree')
        ng.interface.new_socket(name='Angle',in_out='OUTPUT',socket_type='NodeSocketFloat')
        v=ng.nodes.new('ShaderNodeValue'); v.name='Angle'; out=ng.nodes.new('NodeGroupOutput')
        ng.links.new(v.outputs[0],out.inputs[0])
        try:
            d=v.outputs[0].driver_add('default_value').driver; d.type='SCRIPTED'
            for var_name,id_type,target,path in (('a','CAMERA',cam.data,'angle'),('r','SCENE',scene,'render.resolution_x')):
                var=d.variables.new(); var.name=var_name; var.type='SINGLE_PROP'
                var.targets[0].id_type=id_type; var.targets[0].id=target; var.targets[0].data_path=path
            d.expression='2*tan(a/2)/max(r,1)'
        except Exception: pass
    set_pixel_angle(scene,cam)
    return ng


def set_pixel_angle(scene,cam):
    ng=bpy.data.node_groups.get('PA Photo · angle pixel · '+scene.name)
    if ng and cam: ng.nodes['Angle'].outputs[0].default_value=2*math.tan(cam.data.angle/2)/max(scene.render.resolution_x,1)


def _math(nt,op,a,b=0.,clamp=False):
    n=nt.nodes.new('ShaderNodeMath'); n.operation=op; n.use_clamp=clamp
    for i,v in enumerate((a,b)):
        if isinstance(v,(int,float)): n.inputs[i].default_value=v
        else: nt.links.new(v,n.inputs[i])
    return n.outputs[0]


def detail_group(kind):
    """Procedural micro-detail fading in when a pixel gets finer than an atlas texel.

    Inputs are metric, coordinates are object-local: the detail follows a moved module.
    Output colour = atlas × (1 + c·amplitude·pattern): the atlas mean is preserved.
    """
    name='PA Photo · détail '+kind
    ng=bpy.data.node_groups.get(name)
    if ng: return ng
    ng=bpy.data.node_groups.new(name,'ShaderNodeTree'); nt=ng
    for label,typ,default in (('Couleur','NodeSocketColor',None),('Amplitude','NodeSocketFloat',.08),('Echelle (m)','NodeSocketFloat',.004),
                              ('Texel (m)','NodeSocketFloat',.005),('Angle pixel','NodeSocketFloat',.0012),('Relief (m)','NodeSocketFloat',.0003),
                              ('Rugosite','NodeSocketFloat',.5),('Orientation','NodeSocketFloat',0.)):
        s=ng.interface.new_socket(name=label,in_out='INPUT',socket_type=typ)
        if default is not None: s.default_value=default
    for label,typ in (('Couleur','NodeSocketColor'),('Rugosite','NodeSocketFloat'),('Normale','NodeSocketVector'),('Proximite','NodeSocketFloat')):
        ng.interface.new_socket(name=label,in_out='OUTPUT',socket_type=typ)
    gi=nt.nodes.new('NodeGroupInput'); go=nt.nodes.new('NodeGroupOutput')
    tc=nt.nodes.new('ShaderNodeTexCoord')
    rot=nt.nodes.new('ShaderNodeVectorRotate'); rot.rotation_type='Z_AXIS'
    nt.links.new(tc.outputs['Object'],rot.inputs['Vector'])
    nt.links.new(_math(nt,'RADIANS',gi.outputs['Orientation']),rot.inputs['Angle'])
    inv=_math(nt,'DIVIDE',1.,gi.outputs['Echelle (m)'])
    sc=nt.nodes.new('ShaderNodeVectorMath'); sc.operation='SCALE'; nt.links.new(rot.outputs[0],sc.inputs[0]); nt.links.new(inv,sc.inputs['Scale'])
    co=sc.outputs[0]
    def noise(vec,scale=1.,detail=6.,rough=.6):
        n=nt.nodes.new('ShaderNodeTexNoise'); n.inputs['Scale'].default_value=scale; n.inputs['Detail'].default_value=detail
        n.inputs['Roughness'].default_value=rough; nt.links.new(vec,n.inputs['Vector']); return n.outputs['Fac']
    def stretch(vec,s):
        m=nt.nodes.new('ShaderNodeVectorMath'); m.operation='MULTIPLY'; m.inputs[1].default_value=s; nt.links.new(vec,m.inputs[0]); return m.outputs[0]
    if kind=='wood':
        wave=nt.nodes.new('ShaderNodeTexWave'); wave.wave_type='BANDS'; wave.bands_direction='X'
        wave.inputs['Scale'].default_value=.25; wave.inputs['Distortion'].default_value=6; wave.inputs['Detail'].default_value=3
        nt.links.new(stretch(co,(1,.15,1)),wave.inputs['Vector'])
        pattern=_math(nt,'ADD',_math(nt,'MULTIPLY',wave.outputs['Fac'],.65),_math(nt,'MULTIPLY',noise(stretch(co,(4,.3,4)),1.,4),.35))
    elif kind=='brushed':
        pattern=noise(stretch(co,(1,.03,1)),1.,8,.7)
    elif kind=='weave':
        a=nt.nodes.new('ShaderNodeTexWave'); a.bands_direction='X'; a.inputs['Scale'].default_value=1.; nt.links.new(co,a.inputs['Vector'])
        b=nt.nodes.new('ShaderNodeTexWave'); b.bands_direction='Y'; b.inputs['Scale'].default_value=1.; nt.links.new(co,b.inputs['Vector'])
        pattern=_math(nt,'ADD',_math(nt,'MULTIPLY',_math(nt,'MAXIMUM',a.outputs['Fac'],b.outputs['Fac']),.7),_math(nt,'MULTIPLY',noise(co,2.,2),.3))
    elif kind=='foliage':
        v=nt.nodes.new('ShaderNodeTexVoronoi'); v.inputs['Scale'].default_value=.6; nt.links.new(co,v.inputs['Vector'])
        pattern=_math(nt,'ADD',_math(nt,'MULTIPLY',_math(nt,'SUBTRACT',1.,v.outputs['Distance'],True),.6),_math(nt,'MULTIPLY',noise(co,1.5,4),.4))
    else:  # grain, tiles, brick: fine mineral/paint grain only; joints stay in the atlas
        pattern=noise(co,1.,6,.62)
    centred=_math(nt,'MULTIPLY',_math(nt,'SUBTRACT',pattern,.5),2.)
    cam=nt.nodes.new('ShaderNodeCameraData')
    footprint=_math(nt,'MAXIMUM',_math(nt,'MULTIPLY',cam.outputs['View Distance'],gi.outputs['Angle pixel']),1e-6)
    ratio=_math(nt,'DIVIDE',gi.outputs['Texel (m)'],footprint)
    mr=nt.nodes.new('ShaderNodeMapRange'); mr.clamp=True; mr.interpolation_type='SMOOTHSTEP'
    nt.links.new(ratio,mr.inputs['Value']); mr.inputs['From Min'].default_value=1.; mr.inputs['From Max'].default_value=4.
    close=mr.outputs['Result']
    gain=_math(nt,'ADD',1.,_math(nt,'MULTIPLY',_math(nt,'MULTIPLY',close,gi.outputs['Amplitude']),centred))
    col=nt.nodes.new('ShaderNodeVectorMath'); col.operation='SCALE'; nt.links.new(gi.outputs['Couleur'],col.inputs[0]); nt.links.new(gain,col.inputs['Scale'])
    rough=_math(nt,'ADD',gi.outputs['Rugosite'],_math(nt,'MULTIPLY',_math(nt,'MULTIPLY',close,centred),.12),True)
    bump=nt.nodes.new('ShaderNodeBump'); nt.links.new(pattern,bump.inputs['Height']); nt.links.new(gi.outputs['Relief (m)'],bump.inputs['Distance'])
    nt.links.new(_math(nt,'ADD',.15,_math(nt,'MULTIPLY',close,.6)),bump.inputs['Strength'])
    nt.links.new(col.outputs[0],go.inputs['Couleur']); nt.links.new(rough,go.inputs['Rugosite'])
    nt.links.new(bump.outputs['Normal'],go.inputs['Normale']); nt.links.new(close,go.inputs['Proximite'])
    return ng


def material(name,family,atlas=None,colour=(.5,.5,.5),roughness=None,metallic=None):
    """Principled material: atlas albedo in Base Color only, physical parameters from the family."""
    preset=LOOK.MATERIALS.get(family,LOOK.MATERIALS['paint'])
    m=bpy.data.materials.new(name); nt=nodes_on(m)
    bs=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED')
    bs.inputs['Roughness'].default_value=preset['roughness'] if roughness is None else roughness
    bs.inputs['Metallic'].default_value=preset.get('metallic',0.) if metallic is None else metallic
    bs.inputs['Specular IOR Level'].default_value=preset.get('specular',.5)
    bs.inputs['Coat Weight'].default_value=preset.get('coat',0.)
    bs.inputs['Sheen Weight'].default_value=preset.get('sheen',0.)
    bs.inputs['Transmission Weight'].default_value=preset.get('transmission',0.)
    bs.inputs['IOR'].default_value=preset.get('ior',1.5)
    bs.inputs['Base Color'].default_value=(*colour[:3],1)
    if preset.get('emission'): bs.inputs['Emission Strength'].default_value=0.
    if atlas is not None:
        uv=nt.nodes.new('ShaderNodeUVMap'); uv.uv_map='Atlas'
        tex=nt.nodes.new('ShaderNodeTexImage'); tex.name='PA Atlas'; tex.image=atlas; tex.interpolation='Linear'
        nt.links.new(uv.outputs['UV'],tex.inputs['Vector']); nt.links.new(tex.outputs['Color'],bs.inputs['Base Color'])
    m['pa_albedo_only']=True; m[TAG+'_family']=family
    return m


def add_detail(mat,recipe,pixel_group):
    """Insert the procedural detail group between the atlas and the Principled inputs."""
    if recipe['type']=='none': return None
    nt=nodes_on(mat); bs=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED')
    tex=nt.nodes.get('PA Atlas')
    g=nt.nodes.new('ShaderNodeGroup'); g.node_tree=detail_group(recipe['type']); g.name='PA Détail procédural'
    if tex: nt.links.new(tex.outputs['Color'],g.inputs['Couleur'])
    else: g.inputs['Couleur'].default_value=bs.inputs['Base Color'].default_value
    g.inputs['Amplitude'].default_value=recipe['detail']*2
    g.inputs['Echelle (m)'].default_value=recipe['detail_scale_m']
    g.inputs['Texel (m)'].default_value=recipe['texel_m']
    g.inputs['Relief (m)'].default_value=recipe['bump']
    g.inputs['Orientation'].default_value=recipe.get('angle',0.)
    g.inputs['Rugosite'].default_value=bs.inputs['Roughness'].default_value
    pa=nt.nodes.new('ShaderNodeGroup'); pa.node_tree=pixel_group
    nt.links.new(pa.outputs[0],g.inputs['Angle pixel'])
    nt.links.new(g.outputs['Couleur'],bs.inputs['Base Color']); nt.links.new(g.outputs['Rugosite'],bs.inputs['Roughness'])
    nt.links.new(g.outputs['Normale'],bs.inputs['Normal'])
    mat[TAG+'_procedural']=recipe['type']
    return g


def assign(ob,mat):
    ob.data.materials.clear(); ob.data.materials.append(mat)


# ---------------------------------------------------------------- phase 6 · light

def world(scene,sky=None,ambient=(.5,.5,.5),strength=1.):
    w=bpy.data.worlds.new('PA Photo · ciel'); scene.world=w; nt=nodes_on(w); nt.nodes.clear()
    bg=nt.nodes.new('ShaderNodeBackground'); out=nt.nodes.new('ShaderNodeOutputWorld'); bg.name='PA Ciel'
    bg.inputs['Strength'].default_value=strength
    if sky:
        tc=nt.nodes.new('ShaderNodeTexCoord'); sep=nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(tc.outputs['Generated'],sep.inputs[0])
        mr=nt.nodes.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value=-.05; mr.inputs['From Max'].default_value=.6
        nt.links.new(sep.outputs['Z'],mr.inputs['Value'])
        mix=nt.nodes.new('ShaderNodeMix'); mix.data_type='RGBA'
        nt.links.new(mr.outputs['Result'],mix.inputs['Factor'])
        socket(mix.inputs,'A','RGBA').default_value=(*sky['horizon'],1); socket(mix.inputs,'B','RGBA').default_value=(*sky['zenith'],1)
        nt.links.new(socket(mix.outputs,'Result','RGBA'),bg.inputs['Color'])
    else: bg.inputs['Color'].default_value=(*ambient[:3],1)
    nt.links.new(bg.outputs[0],out.inputs['Surface'])
    return w


def light(scene,coll,name,kind,location,direction=None,energy=1.,colour=(1,1,1),size=(.1,.1),glossy=True):
    """glossy=False for auxiliary sources: their large disc must not appear in glass, gloss or refraction."""
    data=bpy.data.lights.new(name,kind); data.energy=energy; data.color=colour[:3]
    if kind=='AREA': data.shape='RECTANGLE'; data.size=size[0]; data.size_y=size[1]
    if kind=='SUN': data.angle=math.radians(1.5)
    if kind=='POINT': data.shadow_soft_size=size[0]
    ob=bpy.data.objects.new(name,data); coll.objects.link(ob); ob.location=Vector(location)
    ob.visible_glossy=glossy; ob.visible_transmission=glossy
    ob.visible_camera=False  # a window or fill emitter must never be seen in place of the photo
    if direction is not None:  # lights emit along their local -Z
        ob.rotation_mode='QUATERNION'; ob.rotation_quaternion=(-Vector(direction)).to_track_quat('-Z','Y')
    ob[TAG+'_light']=kind
    return ob


def scale_lights(scene,factor):
    for ob in scene.objects:
        if ob.type=='LIGHT' and ob.get(TAG+'_light'): ob.data.energy*=factor
    if scene.world and scene.world.node_tree:
        bg=scene.world.node_tree.nodes.get('PA Ciel')
        if bg: bg.inputs['Strength'].default_value*=factor


def compositor(scene,look):
    """Mirror of photo_look.apply_look for interactive renders (best effort, Blender 5 trees).

    The scored image is produced by photo_look.apply_look on the EXR; this tree gives
    the same exposure, haze, glare and grade family when rendering with F12.
    """
    try:
        if not hasattr(scene,'compositing_node_group'): return False
        ng=bpy.data.node_groups.new('PA Photo · look','CompositorNodeTree')
        ng.interface.new_socket(name='Image',in_out='OUTPUT',socket_type='NodeSocketColor')
        scene.compositing_node_group=ng; scene.view_layers[0].use_pass_z=True
        rl=ng.nodes.new('CompositorNodeRLayers'); rl.scene=scene; out=ng.nodes.new('NodeGroupOutput')
        ex=ng.nodes.new('CompositorNodeExposure'); ex.inputs['Exposure'].default_value=look.get('exposure',0.)
        ng.links.new(rl.outputs['Image'],ex.inputs['Image']); img=ex.outputs['Image']
        beta=look.get('haze_beta',0.)
        if beta>0:
            m1=ng.nodes.new('ShaderNodeMath'); m1.operation='MULTIPLY'; m1.inputs[1].default_value=-beta; ng.links.new(rl.outputs['Depth'],m1.inputs[0])
            m2=ng.nodes.new('ShaderNodeMath'); m2.operation='EXPONENT'; ng.links.new(m1.outputs[0],m2.inputs[0])
            mix=ng.nodes.new('ShaderNodeMix'); mix.data_type='RGBA'
            inv=ng.nodes.new('ShaderNodeMath'); inv.operation='SUBTRACT'; inv.inputs[0].default_value=1; ng.links.new(m2.outputs[0],inv.inputs[1])
            ng.links.new(inv.outputs[0],mix.inputs['Factor']); ng.links.new(img,socket(mix.inputs,'A','RGBA'))
            socket(mix.inputs,'B','RGBA').default_value=(*look.get('airlight',(.7,.75,.8))[:3],1); img=socket(mix.outputs,'Result','RGBA')
        if look.get('glow_strength',0)>0:
            gl=ng.nodes.new('CompositorNodeGlare'); gl.inputs['Type'].default_value='Bloom'
            gl.inputs['Threshold'].default_value=look.get('glow_threshold',.8); gl.inputs['Strength'].default_value=min(1.,look['glow_strength']*3)
            ng.links.new(img,gl.inputs['Image']); img=gl.outputs['Image']
        g=look.get('grade')
        if g:
            cb=ng.nodes.new('CompositorNodeColorBalance')
            try:
                cb.inputs['Type'].default_value='Offset Power Slope (ASC-CDL)'
            except Exception: pass
            diag=[g['matrix'][i][i] for i in range(3)]
            for s in cb.inputs:
                if s.name=='Slope' and s.type=='RGBA': s.default_value=(*diag,1)
                if s.name=='Offset' and s.type=='RGBA': s.default_value=(*g['offset'],1)
            ng.links.new(img,cb.inputs['Image']); img=cb.outputs['Image']
        ng.links.new(img,out.inputs[0])
        return True
    except Exception:
        return False
