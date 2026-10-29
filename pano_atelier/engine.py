"""Blender scene operations; called on the main thread only."""
import json
import math
import hashlib
from pathlib import Path
import bpy
import numpy as np
from mathutils import Matrix, Vector, Euler
from mathutils.bvhtree import BVHTree
from . import core


def pixels(image):
    w,h = image.size
    a = np.empty(w*h*4,np.float32)
    image.pixels.foreach_get(a)
    a=a.reshape(h,w,4)[::-1].copy()
    # Byte image buffers expose encoded values; float buffers are already linear.
    # All calculations here use scene-linear RGB, masks remain Non-Color.
    if not image.is_float and image.colorspace_settings.name=='sRGB':
        c=a[...,:3]
        a[...,:3]=np.where(c<=.04045,c/12.92,((c+.055)/1.055)**2.4)
    return a


def load_pixels(path, data=False):
    image = bpy.data.images.load(str(path),check_existing=False)
    try:
        if data: image.colorspace_settings.name='Non-Color'
        return pixels(image)
    finally: bpy.data.images.remove(image)


def write_image(path, array, data=False):
    a = np.asarray(array,dtype=np.float32)
    if a.ndim==2: a=np.stack((a,a,a,np.ones_like(a)),-1)
    if a.shape[-1]==3: a=np.concatenate((a,np.ones((*a.shape[:2],1),np.float32)),-1)
    path = Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    im = bpy.data.images.new('PA temporary',width=a.shape[1],height=a.shape[0],alpha=True,float_buffer=True)
    try:
        if data: im.colorspace_settings.name='Non-Color'
        im.pixels.foreach_set(a[::-1].astype(np.float32).ravel())
        im.filepath_raw=str(path); im.file_format='PNG'; im.save()
    finally: bpy.data.images.remove(im)


def resize(a,w,h):
    yy=np.minimum((np.arange(h)+.5)*a.shape[0]/h,a.shape[0]-1).astype(int)
    xx=np.minimum((np.arange(w)+.5)*a.shape[1]/w,a.shape[1]-1).astype(int)
    return a[yy[:,None],xx[None,:]]


def base_matrix():
    return Matrix.Translation((0,0,1.6)) @ Euler((math.pi/2,0,0)).to_matrix().to_4x4()


def collection(scene):
    name='PA_'+scene.name
    c=bpy.data.collections.get(name)
    if c is None:
        c=bpy.data.collections.new(name); scene.collection.children.link(c)
    return c


def set_texture(obj, image):
    # All materials belong solely to this add-on's generated objects.
    mat=obj.data.materials[0]
    mat.node_tree.nodes['PA Texture'].image=image
    obj['pa_image']=image.name


def build(scene, image_path, depth_path, panorama=False, fov=70, resolution=180, scale=1., edge=.15):
    rgba=load_pixels(image_path)
    if panorama and abs(rgba.shape[1]/rgba.shape[0]-2)>.05:
        raise ValueError('Un panorama équirectangulaire complet doit être au format 2:1.')
    if str(depth_path).lower().endswith('.npy'):
        depth=np.load(str(depth_path),allow_pickle=False)
        if depth.ndim!=2: raise ValueError('La profondeur NPY doit être un tableau H x W.')
    else: depth=load_pixels(depth_path,True)[...,0]
    w=resolution; h=max(8,round(w*rgba.shape[0]/rgba.shape[1]))
    depth=resize(depth,w,h)*scale
    verts,faces,uv=core.grid_mesh(depth,fov,panorama,edge)
    if not faces: raise ValueError('Aucune surface valide : vérifier profondeur, échelle et seuil.')
    mesh=bpy.data.meshes.new('PA Geometry'); mesh.from_pydata(verts.tolist(),[],faces); mesh.update()
    layer=mesh.uv_layers.new(name='PA Atlas')
    for p in mesh.polygons:
        for li in p.loop_indices: layer.data[li].uv=uv[mesh.loops[li].vertex_index]
    obj=bpy.data.objects.new('PA Decor',mesh); collection(scene).objects.link(obj)
    obj.matrix_world=base_matrix()
    obj['pa_owned']=True; obj['pa_panorama']=panorama; obj['pa_fov']=fov
    obj['pa_source_matrix']=[x for row in obj.matrix_world for x in row]
    image=bpy.data.images.load(str(image_path),check_existing=False)
    image.pack()
    mat=bpy.data.materials.new('PA Projected texture'); mat.use_nodes=True
    nodes=mat.node_tree.nodes; nodes.clear()
    tex=nodes.new('ShaderNodeTexImage'); tex.name='PA Texture'; tex.image=image; tex.interpolation='Linear'
    emission=nodes.new('ShaderNodeEmission'); out=nodes.new('ShaderNodeOutputMaterial')
    mat.node_tree.links.new(tex.outputs['Color'],emission.inputs['Color'])
    mat.node_tree.links.new(emission.outputs[0],out.inputs['Surface'])
    mesh.materials.append(mat); obj['pa_image']=image.name; obj['pa_original_image']=image.name
    return obj


def owned(scene):
    return [o for o in scene.objects if o.type=='MESH' and o.get('pa_owned') and not o.hide_render]


def geometry_signature(scene):
    digest=hashlib.sha256()
    for obj in owned(scene):
        digest.update(obj.name.encode())
        digest.update(np.array(obj.matrix_world,dtype=np.float32).tobytes())
        for v in obj.data.vertices: digest.update(np.array(v.co,dtype=np.float32).tobytes())
        for p in obj.data.polygons: digest.update(np.array(p.vertices,dtype=np.int32).tobytes())
        if obj.data.uv_layers.active:
            for uv in obj.data.uv_layers.active.data: digest.update(np.array(uv.uv,dtype=np.float32).tobytes())
    return digest.hexdigest()


class Surface:
    def __init__(self,scene):
        self.vertices=[]; self.triangles=[]; self.records=[]; self.images={}; self.sources={}
        image_cache={}
        for obj in owned(scene):
            mesh=obj.data; mesh.calc_loop_triangles()
            start=len(self.vertices)
            self.vertices.extend([obj.matrix_world @ v.co for v in mesh.vertices])
            uv=mesh.uv_layers.active
            if uv is None: raise ValueError('UV manquants sur '+obj.name)
            image_name=obj['pa_image']
            if image_name not in image_cache: image_cache[image_name]=pixels(bpy.data.images[image_name])
            self.images[obj.name]=image_cache[image_name]
            self.sources[obj.name]=Vector(np.array(obj['pa_source_matrix']).reshape(4,4)[:3,3])
            for tri in mesh.loop_triangles:
                self.triangles.append(tuple(start+v for v in tri.vertices))
                self.records.append((obj,tri.polygon_index,np.array([uv.data[i].uv[:] for i in tri.loops])))
        if not self.triangles: raise ValueError('Construire ou charger un décor Pano Atelier avant inspection.')
        self.tree=BVHTree.FromPolygons(self.vertices,self.triangles,all_triangles=True)


def barycentric(point,a,b,c):
    v0=b-a; v1=c-a; v2=point-a
    d00=v0.dot(v0); d01=v0.dot(v1); d11=v1.dot(v1)
    den=d00*d11-d01*d01
    if abs(den)<1e-16: return np.array((1.,0.,0.))
    d20=v2.dot(v0); d21=v2.dot(v1)
    v=(d11*d20-d01*d21)/den; w=(d00*d21-d01*d20)/den
    return np.array((1-v-w,v,w))


def scan(surface,matrix,fov,width=192,height=108):
    rays=core.camera_rays(width,height,fov)
    rgb=np.zeros((height,width,4),np.float32); rgb[...,3]=1
    depth=np.zeros((height,width),np.float32); ids=np.full((height,width),-1,np.int32)
    incidence=np.zeros_like(depth); source_incidence=np.zeros_like(depth)
    origin=matrix.translation; rotation=matrix.to_3x3(); inverse=matrix.inverted()
    for y in range(height):
        for x in range(width):
            direction=rotation @ Vector(rays[y,x])
            hit,normal,index,distance=surface.tree.ray_cast(origin,direction)
            if index is None: continue
            obj,polygon,uvs=surface.records[index]
            a,b,c=(surface.vertices[i] for i in surface.triangles[index])
            uv=barycentric(hit,a,b,c) @ uvs
            tex=surface.images[obj.name]; th,tw=tex.shape[:2]
            tx=min(tw-1,max(0,int(uv[0]*tw))); ty=min(th-1,max(0,int((1-uv[1])*th)))
            rgb[y,x]=tex[ty,tx]
            depth[y,x]=-(inverse @ hit).z; ids[y,x]=index
            incidence[y,x]=abs(normal.dot(-direction))
            sd=(surface.sources[obj.name]-hit).normalized()
            source_incidence[y,x]=abs(normal.dot(sd))
    masks=core.detect(rgb,depth,incidence,source_incidence,ids>=0)
    return dict(rgb=rgb,depth=depth,ids=ids,masks=masks,matrix=matrix.copy(),fov=fov)


def object_mask(surface,shot,names):
    """Visible surface IDs, not image content, enforce the selected-object scope."""
    names=set(names)
    triangles=[i for i,record in enumerate(surface.records) if record[0].name in names]
    return np.isin(shot['ids'],triangles)


def save_scan(folder,shot):
    folder=Path(folder); folder.mkdir(parents=True,exist_ok=True)
    write_image(folder/'view.png',shot['rgb'])
    depth=shot['depth']; nz=depth[depth>0]
    write_image(folder/'depth.png',depth/max(float(np.percentile(nz,95)) if len(nz) else 1,.001),True)
    np.save(folder/'depth.npy',depth)
    write_image(folder/'mask-texture.png',shot['masks']['texture'].astype(np.float32),True)
    write_image(folder/'mask-geometry.png',shot['masks']['holes'].astype(np.float32),True)
    overlay=shot['rgb'].copy()
    for mask,col in [(shot['masks']['texture'],(1,.28,0)),(shot['masks']['holes'],(.8,0,.65))]:
        overlay[mask,:3]=overlay[mask,:3]*.25+np.array(col)*.75
    write_image(folder/'diagnostic.png',overlay)
    (folder/'camera.json').write_text(json.dumps({'matrix':[list(r) for r in shot['matrix']],'fov':shot['fov']},indent=2))


def create_path(scene,obj,radius):
    root=Matrix(np.array(obj['pa_source_matrix']).reshape(4,4))
    data=bpy.data.cameras.new('PA Inspection'); cam=bpy.data.objects.new('PA Inspection',data)
    collection(scene).objects.link(cam); cam['pa_camera']=True
    data.type='PERSP'; data.lens_unit='FOV'; data.angle=math.radians(float(obj['pa_fov']))
    data.sensor_fit='HORIZONTAL'; cam.rotation_mode='QUATERNION'
    poses=[]
    for i,(offset,yaw,holdout) in enumerate(core.path_poses(radius,bool(obj['pa_panorama']))):
        mat=root @ Matrix.Translation(offset) @ Euler((0,math.radians(yaw),0)).to_matrix().to_4x4()
        frame=1+i*12
        cam.matrix_world=mat
        cam.keyframe_insert(data_path='location',frame=frame)
        cam.keyframe_insert(data_path='rotation_quaternion',frame=frame)
        poses.append((mat,holdout))
    curve=bpy.data.curves.new('PA Camera path','CURVE'); curve.dimensions='3D'
    spline=curve.splines.new('POLY'); spline.points.add(len(poses)-1)
    for p,(mat,_) in zip(spline.points,poses): p.co=(*mat.translation,1)
    path=bpy.data.objects.new('PA Camera path',curve); collection(scene).objects.link(path); path.hide_render=True
    scene.camera=cam; scene.frame_end=1+(len(poses)-1)*12; scene.frame_set(1)
    return cam,poses


def bake_patch(surface,shot,generated,mask,folder,score_buffer=None):
    """Back-project into the original UV atlas with depth + triangle visibility.

    Rasterize each visible triangle in atlas space. Patches never reach hidden
    surfaces and no screen-space decal remains tied to the navigation camera.
    """
    h,w=shot['depth'].shape
    generated=resize(generated,w,h)
    mask=np.clip(mask,0,1)*(shot['ids']>=0)
    inv=np.array(shot['matrix'].inverted()); t=math.tan(math.radians(shot['fov'])/2)
    face_keys={}; triangle_faces=[]
    for obj,poly,_ in surface.records:
        key=(obj.name,poly)
        if key not in face_keys: face_keys[key]=len(face_keys)
        triangle_faces.append(face_keys[key])
    triangle_faces=np.asarray(triangle_faces)
    touched=np.unique(shot['ids'][mask>.001]); touched=touched[touched>=0]
    target_names={surface.records[int(i)][0].name for i in touched}
    buffers={}; changed={}; groups={}
    for name,a in surface.images.items():
        obj=bpy.data.objects[name]
        group=('structural',obj['pa_image']) if obj.get('pa_structural') else ('object',name)
        groups.setdefault(group,[]).append(name)
    active=[]
    for names in groups.values():
        if not target_names.intersection(names): continue
        a=surface.images[names[0]].copy(); change=np.zeros(a.shape[:2],bool)
        for name in names: buffers[name]=a; changed[name]=change
        active.append(names)
    for index in touched:
        obj,poly,uv=surface.records[int(index)]; atlas=buffers[obj.name]; ah,aw=atlas.shape[:2]
        pts=uv*np.array((aw,ah)); pts[:,1]=ah-pts[:,1]
        x0=max(0,int(np.floor(min(pts[:,0])))); x1=min(aw,int(np.ceil(max(pts[:,0]))))
        y0=max(0,int(np.floor(min(pts[:,1])))); y1=min(ah,int(np.ceil(max(pts[:,1]))))
        if x1<=x0 or y1<=y0: continue
        xx,yy=np.meshgrid(np.arange(x0,x1),np.arange(y0,y1)); samples=np.stack((xx.ravel()+.5,yy.ravel()+.5),-1)
        basis=np.stack((pts[1]-pts[0],pts[2]-pts[0]),-1)
        if abs(np.linalg.det(basis))<1e-9: continue
        bc=(samples-pts[0]) @ np.linalg.inv(basis).T; weights=np.column_stack((1-bc.sum(1),bc))
        inside=np.all(weights>=-1e-5,axis=1)
        vertices=np.array([surface.vertices[i][:] for i in surface.triangles[int(index)]])
        world=weights @ vertices; local=world @ inv[:3,:3].T+inv[:3,3]; z=-local[:,2]
        sx=(local[:,0]/np.maximum(z,1e-6)/t*.5+.5)*w
        sy=(.5-local[:,1]/np.maximum(z,1e-6)/t*w/h*.5)*h
        ix=np.clip(sx,0,w-1).astype(int); iy=np.clip(sy,0,h-1).astype(int)
        visible=inside & (z>0) & (sx>=0)&(sx<w)&(sy>=0)&(sy<h)
        # Both triangles of the same planar quad are one surface. Matching the
        # polygon prevents a spurious unpainted diagonal without crossing objects.
        sampled=shot['ids'][iy,ix]
        visible &= (sampled>=0)&(triangle_faces[np.maximum(sampled,0)]==triangle_faces[index])
        alpha=mask[iy,ix]*visible
        choose=alpha>.001
        if score_buffer is not None:
            normal=np.cross(vertices[1]-vertices[0],vertices[2]-vertices[0])
            normal=normal/max(np.linalg.norm(normal),1e-12)
            view=np.asarray(shot['matrix'].translation)-world
            distance2=np.maximum(np.sum(view*view,axis=1),1e-8)
            quality=(view@normal)**2/(distance2*distance2)
            previous=score_buffer[yy.ravel(),xx.ravel()]
            choose &= quality>np.maximum(previous*(1+1e-5),previous+1e-10)
        if not np.any(choose): continue
        ax=xx.ravel()[choose]; ay=yy.ravel()[choose]; weight=alpha[choose,None]
        if score_buffer is not None: score_buffer[ay,ax]=quality[choose]
        atlas[ay,ax,:3]=atlas[ay,ax,:3]*(1-weight)+generated[iy[choose],ix[choose],:3]*weight
        changed[obj.name][ay,ax]=True
    old={}; new={}; old_paths={}; count=0
    for names in active:
        name=names[0]; array=buffers[name]
        n=int(changed[name].sum())
        if not n: continue
        count+=n
        path=Path(folder)/(name.replace('/','_')+'-texture.png')
        write_image(path,array)
        image=bpy.data.images.load(str(path),check_existing=False); image.pack()
        for member in names:
            obj=bpy.data.objects[member]; old[member]=obj['pa_image']
            old_paths[member]=bpy.path.abspath(bpy.data.images[obj['pa_image']].filepath)
            set_texture(obj,image); new[member]=image.name
    return {'old':old,'old_paths':old_paths,'new':new,'texels':count}


def restore(patch):
    replacements={}
    for name,image in patch['old'].items():
        if name not in bpy.data.objects: continue
        restored=bpy.data.images.get(image)
        if restored is None:
            path=patch.get('old_paths',{}).get(name,'')
            if not path or not Path(path).is_file(): raise ValueError('Texture précédente introuvable : '+image)
            if path not in replacements:
                replacements[path]=bpy.data.images.load(path,check_existing=True); replacements[path].pack()
            restored=replacements[path]
        replacements[name]=restored
    for name in patch['old']:
        if name in replacements: set_texture(bpy.data.objects[name],replacements[name])
    for name in patch.get('added_objects',[]):
        if name in bpy.data.objects:
            bpy.data.objects[name].hide_render=True
            bpy.data.objects[name].hide_set(True)


def add_missing_surface(scene,shot,generated_path,depth_path,folder):
    predicted=load_pixels(depth_path,True)[...,0] if not str(depth_path).endswith('.npy') else np.load(depth_path,allow_pickle=False)
    predicted=resize(predicted,shot['depth'].shape[1],shot['depth'].shape[0])
    missing,alignment=core.align_missing_depth(predicted,shot['depth'],shot['masks']['holes'])
    folder=Path(folder); folder.mkdir(parents=True,exist_ok=True)
    np.save(folder/'aligned-missing-depth.npy',missing)
    obj=build(scene,generated_path,folder/'aligned-missing-depth.npy',fov=shot['fov'],resolution=shot['depth'].shape[1])
    obj.name='PA Generated surface'; obj.matrix_world=shot['matrix']
    obj['pa_source_matrix']=[x for row in shot['matrix'] for x in row]
    obj['pa_generated_geometry']=True
    return obj,alignment


def fixture(scene,folder):
    """Analytic test set, deliberately includes foreground disocclusion and seam."""
    folder=Path(folder); folder.mkdir(parents=True,exist_ok=True)
    w,h=640,360
    y,x=np.mgrid[0:h,0:w]; u=x/w; v=y/h
    depth=np.full((h,w),5.,np.float32)
    rgb=np.ones((h,w,4),np.float32)
    rgb[...,:3]=np.stack((.36+.09*u,.44+.06*v,.5+.05*u),-1)
    grid=((x%80)<2)|((y%80)<2); rgb[grid,:3]*=.75
    # Coloured foreground block, backed by a genuinely unobserved region.
    fg=(u>.28)&(u<.45)&(v>.35)&(v<.88)
    depth[fg]=2.6; rgb[fg,:3]=(.46,.20,.075)
    seam=(u>.67)&(u<.69)&(v>.15)&(v<.85)
    rgb[seam,:3]=(.95,.8,.65)
    write_image(folder/'source.png',rgb); np.save(folder/'depth.npy',depth)
    obj=build(scene,folder/'source.png',folder/'depth.npy',resolution=160)
    scene.render.resolution_x=w; scene.render.resolution_y=h; scene.render.resolution_percentage=100
    return obj
