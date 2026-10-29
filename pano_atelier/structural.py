"""Editable low-poly cockpit template and fixed-camera texture projection.

This is an explicit architectural template, not inferred arbitrary geometry.
The image generator supplies appearance; it must preserve the guide geometry.
"""
import json
import math
from pathlib import Path
import bpy
import numpy as np
from mathutils import Matrix, Vector
from . import engine


ORDER = ('front', 'right', 'back', 'left', 'up', 'down')


def cameras(origin=(0, 0, 1.6)):
    directions = ((0,1,0),(1,0,0),(0,-1,0),(-1,0,0),(0,0,1),(0,0,-1))
    result = []
    for name, direction in zip(ORDER, directions):
        forward = Vector(direction)
        up = Vector((0,1,0)) if name in ('up','down') else Vector((0,0,1))
        right = forward.cross(up).normalized()
        up = right.cross(forward).normalized()
        matrix = Matrix((right, up, -forward)).transposed().to_4x4()
        matrix.translation = Vector(origin)
        result.append((name, matrix))
    return result


def build(scene, folder, atlas_size=4096, architecture=False):
    folder = Path(folder); folder.mkdir(parents=True, exist_ok=True)
    meshes = []
    def mesh(name, vertices, faces, color):
        data = bpy.data.meshes.new(name)
        data.from_pydata(vertices, [], faces); data.update()
        obj = bpy.data.objects.new('PA '+name, data)
        engine.collection(scene).objects.link(obj)
        obj.color = (*color, 1)
        meshes.append(obj)
        return obj
    def quad(name, vertices, color=(.58,.58,.55)):
        return mesh(name, vertices, [(0,1,2,3)], color)
    def box(name, center, size, angle=0, color=(.48,.48,.44)):
        x,y,z = center; sx,sy,sz = (v/2 for v in size)
        c,s = math.cos(angle),math.sin(angle)
        vertices = [(x+c*a-s*b,y+s*a+c*b,z+d) for a,b,d in
                    [(-sx,-sy,-sz),(sx,-sy,-sz),(sx,sy,-sz),(-sx,sy,-sz),
                     (-sx,-sy,sz),(sx,-sy,sz),(sx,sy,sz),(-sx,sy,sz)]]
        return mesh(name,vertices,[(3,2,1,0),(0,1,5,4),(1,2,6,5),
                                 (2,3,7,6),(3,0,4,7),(4,5,6,7)],color)
    def window(name,a,b):
        a,b=Vector(a),Vector(b)
        outward=Vector(((a.x+b.x)/2,(a.y+b.y)/2-1.6,0)).normalized()
        outer=[(a.x,a.y,1.25),(b.x,b.y,1.25),(b.x,b.y,2.8),(a.x,a.y,2.8)]
        opening=[]
        for u,z in ((.09,1.38),(.91,1.38),(.84,2.66),(.16,2.66)):
            p=a.lerp(b,u); opening.append(Vector((p.x,p.y,z)))
        recessed=[p+outward*.22 for p in opening]
        for k in range(4):
            n=(k+1)%4
            quad(name+' frame %d'%k,[outer[k],outer[n],opening[n],opening[k]],(.69,.68,.62))
            quad(name+' reveal %d'%k,[opening[k],opening[n],recessed[n],recessed[k]],(.43,.43,.39))
        quad(name+' glass',recessed,(.12,.15,.17))
    def doorway(name,a,b):
        a,b=Vector((*a,0)),Vector((*b,0)); middle=(a+b)/2
        tangent=(b-a).normalized(); outward=Vector((middle.x,middle.y-1.6,0)).normalized()
        def point(u,z,d=0):
            p=middle+tangent*u+outward*d
            return (p.x,p.y,z)
        # Real recess, side returns and pocket close the room behind the leaf.
        quad(name+' left jamb',[point(-.83,0),point(-.68,0),point(-.68,2.65),point(-.83,2.8)])
        quad(name+' right jamb',[point(.68,0),point(.83,0),point(.83,2.8),point(.68,2.65)])
        quad(name+' lintel',[point(-.83,2.8),point(-.68,2.65),point(.68,2.65),point(.83,2.8)])
        quad(name+' header',[point(-.83,2.8),point(.83,2.8),point(.83,3.15),point(-.83,3.15)])
        for label,verts in [('left reveal',[point(-.68,0),point(-.68,0,.7),point(-.68,2.65,.7),point(-.68,2.65)]),
                            ('right reveal',[point(.68,0,.7),point(.68,0),point(.68,2.65),point(.68,2.65,.7)]),
                            ('pocket back',[point(-.68,0,.7),point(.68,0,.7),point(.68,2.65,.7),point(-.68,2.65,.7)]),
                            ('threshold',[point(-.68,0),point(.68,0),point(.68,0,.7),point(-.68,0,.7)]),
                            ('ceiling',[point(-.68,2.65),point(-.68,2.65,.7),point(.68,2.65,.7),point(.68,2.65)])]:
            quad(name+' '+label,verts,(.15,.14,.12))
        hinge=middle-tangent*.64+outward*.12
        direction=tangent*math.cos(.21)-outward*math.sin(.21)
        center=hinge+direction*.64
        box(name+' leaf ajar',(center.x,center.y,1.31),(1.28,.09,2.60),math.atan2(direction.y,direction.x),(.32,.22,.12))
    cy = 1.6; radius = 5.1
    ring = [(radius*math.cos(i*math.pi/3),cy+radius*math.sin(i*math.pi/3)) for i in range(6)]
    inner = [(x*.46,cy+(y-cy)*.46) for x,y in ring]
    # Six triangles each close the floor and central skylight without concave n-gons.
    for i in range(6):
        j = (i+1)%6; a,b = ring[i],ring[j]; ia,ib=inner[i],inner[j]
        mesh('Floor %d'%i,[(0,cy,0),(*b,0),(*a,0)],[(0,1,2)],(.34,.34,.31))
        if architecture:
            length=(Vector(b)-Vector(a)).length
            gap=.83/length
            segments=[(0,.5-gap),(.5+gap,1)] if i in (1,4) else [(0,.5),(.5,1)]
            for k,(u0,u1) in enumerate(segments):
                p=Vector(a).lerp(Vector(b),u0); q=Vector(a).lerp(Vector(b),u1)
                window('Window %d %d'%(i,k),p,q)
                quad('Lower wall %d %d'%(i,k),[(*p,0),(*q,0),(*q,1.25),(*p,1.25)])
                quad('Frieze %d %d'%(i,k),[(*p,2.8),(*q,2.8),(*q,3.15),(*p,3.15)])
            if i in (1,4): doorway('Door %d'%i,a,b)
        else:
            for label,z0,z1,col in [('Lower wall',0,1.25,(.60,.60,.56)),
                                   ('Windows',1.25,2.8,(.14,.17,.18)),
                                   ('Frieze',2.8,3.15,(.62,.62,.58))]:
                quad(label+' %d'%i,[(*a,z0),(*b,z0),(*b,z1),(*a,z1)],col)
        quad('Canopy %d'%i,[(*a,3.15),(*b,3.15),(*ib,4.05),(*ia,4.05)],(.31,.34,.34))
        mesh('Skylight %d'%i,[(0,cy,4.05),(*ia,4.05),(*ib,4.05)],[(0,1,2)],(.75,.76,.74))
        # Narrow radial architectural ribs and wall posts stay actual geometry.
        box('Pillar %d'%i,(*a,1.6),(.18,.18,3.2),color=(.7,.7,.66))
        mid=((a[0]+b[0])/2,(a[1]+b[1])/2)
        angle=math.atan2(b[1]-a[1],b[0]-a[0])
        inward=Vector((-mid[0],cy-mid[1])).normalized()
        length=(Vector(a)-Vector(b)).length
        # Leave the central front door and back circulation open.
        segments=[(-1.55,1.6),(1.55,1.6)] if i in (1,4) else [(0,length-.45)]
        for k,(along,width) in enumerate(segments):
            center=(mid[0]+inward.x*.55+math.cos(angle)*along,
                    mid[1]+inward.y*.55+math.sin(angle)*along,.55)
            box('Console base %d %d'%(i,k),center,(width,.85,1.1),angle)
            # Sloping top control surface, thickness kept as a clean wedge.
            x,y,_=center; c,s=math.cos(angle),math.sin(angle)
            verts=[]
            for u,v,z in [(-width/2,-.48,1.05),(width/2,-.48,1.05),
                          (width/2,.48,1.05),(-width/2,.48,1.05),
                          (-width/2,-.48,1.38),(width/2,-.48,1.38),
                          (width/2,.48,1.10),(-width/2,.48,1.10)]:
                verts.append((x+c*u-s*v,y+s*u+c*v,z))
            mesh('Control deck %d %d'%(i,k),verts,[(0,1,5,4),(1,2,6,5),
                (2,3,7,6),(3,0,4,7),(4,5,6,7)],(.42,.43,.4))
    box('Central pedestal',(0,2.6,.43),(1.25,.95,.86))
    box('Central table',(0,2.6,.94),(1.7,1.35,.22),color=(.66,.65,.6))
    for side in (-1,1):
        x=side*2.4
        box('Seat base '+str(side),(x,2.8,.29),(.38,.38,.58))
        box('Seat cushion '+str(side),(x,2.8,.61),(.75,.8,.18),color=(.42,.43,.35))
        box('Seat back '+str(side),(x,2.43,.94),(.75,.16,.65),color=(.42,.43,.35))
        if architecture:
            for arm in (-1,1):
                box('Seat arm %d %d'%(side,arm),(x+arm*.36,2.8,.82),(.12,.8,.13),color=(.42,.43,.35))
            box('Seat foot '+str(side),(x,2.8,.035),(.6,.6,.07))
    # Nonoverlapping face cells keep geometry simple even after camera projection.
    face_count=sum(len(o.data.polygons) for o in meshes)
    cols=math.ceil(math.sqrt(face_count)); cell=atlas_size/cols
    blank=np.ones((atlas_size,atlas_size,4),np.float32); blank[...,:3]=.35
    engine.write_image(folder/'untextured.png',blank)
    source=bpy.data.images.load(str(folder/'untextured.png')); source.pack()
    index=0
    for obj in meshes:
        layer=obj.data.uv_layers.new(name='PA Atlas')
        for poly in obj.data.polygons:
            x,y=index%cols,index//cols; index+=1
            points=[(x*cell+3,y*cell+3),((x+1)*cell-3,y*cell+3),
                    ((x+1)*cell-3,(y+1)*cell-3),(x*cell+3,(y+1)*cell-3)]
            for li,(u,v) in zip(poly.loop_indices,points): layer.data[li].uv=(u/atlas_size,1-v/atlas_size)
        mat=bpy.data.materials.new(obj.name+' projection'); mat.use_nodes=True
        nodes=mat.node_tree.nodes; nodes.clear()
        tex=nodes.new('ShaderNodeTexImage'); tex.name='PA Texture'; tex.image=source
        emission=nodes.new('ShaderNodeEmission'); out=nodes.new('ShaderNodeOutputMaterial')
        mat.node_tree.links.new(tex.outputs['Color'],emission.inputs['Color'])
        mat.node_tree.links.new(emission.outputs[0],out.inputs['Surface'])
        obj.data.materials.append(mat)
        obj['pa_owned']=True; obj['pa_structural']=True; obj['pa_panorama']=True; obj['pa_fov']=90.
        obj['pa_source_matrix']=[v for row in engine.base_matrix() for v in row]
        obj['pa_image']=source.name; obj['pa_original_image']=source.name
    scene['pa_structural']=True; scene['pa_template']='hexagonal_cockpit_v2' if architecture else 'hexagonal_cockpit_v1'
    scene['pa_atlas_size']=atlas_size
    scene['pa_projection_origin']=[0.,0.,1.6]
    scene.pa_settings.radius=1.0; scene.pa_settings.fov=90; scene.pa_settings.width=256
    scene.pa_settings.output=str(folder/'inspections')
    engine.create_path(scene,meshes[0],1.0)
    return meshes


def export_guides(scene, folder, size=512):
    folder=Path(folder); folder.mkdir(parents=True,exist_ok=True)
    scene.render.engine='BLENDER_WORKBENCH'
    scene.render.resolution_x=size; scene.render.resolution_y=size; scene.render.resolution_percentage=100
    scene.display.shading.light='STUDIO'; scene.display.shading.color_type='OBJECT'
    scene.display.shading.show_shadows=True; scene.display.shading.show_cavity=True
    scene.display.shading.cavity_type='BOTH'
    scene.view_settings.view_transform='Standard'
    camera_data=bpy.data.cameras.new('PA Fixed projector'); camera=bpy.data.objects.new('PA Fixed projector',camera_data)
    engine.collection(scene).objects.link(camera)
    camera_data.sensor_fit='HORIZONTAL'; camera_data.angle=math.pi/2; camera_data.clip_start=.03
    previous=scene.camera; scene.camera=camera
    atlas=np.ones((size*2,size*3,4),np.float32); manifest=[]
    for index,(name,matrix) in enumerate(cameras(scene['pa_projection_origin'])):
        camera.matrix_world=matrix
        scene.render.filepath=str(folder/(name+'.png'))
        bpy.ops.render.render(write_still=True,scene=scene.name)
        atlas[index//3*size:(index//3+1)*size,index%3*size:(index%3+1)*size]=engine.load_pixels(folder/(name+'.png'))
        data=camera_data.copy(); obj=bpy.data.objects.new('PA Projector '+name,data)
        engine.collection(scene).objects.link(obj); obj.matrix_world=matrix; obj.hide_set(True)
        obj['pa_projector']=True
        manifest.append({'name':name,'matrix':[list(r) for r in matrix],'fov':90,'tile':[index%3,index//3]})
    engine.write_image(folder/'guide-atlas.png',atlas)
    (folder/'projectors.json').write_text(json.dumps(manifest,indent=2))
    scene.camera=previous
    bpy.data.objects.remove(camera,do_unlink=True)
    return folder/'guide-atlas.png'


def project_atlas(scene, path, folder):
    """Bake fixed views per surface texel; geometry never depends on viewer pose.

    Coverage records distinguish visible projection from occluded fallback. The
    fallback is also camera mapped but must be repaired from a displaced view.
    """
    folder=Path(folder); folder.mkdir(parents=True,exist_ok=True)
    image=engine.load_pixels(path); h,w=image.shape[:2]
    if abs(w/h-1.5)>.02: raise ValueError('Atlas requis : 3 colonnes × 2 lignes carrées, sans marges.')
    side=min(w//3,h//2)
    tiles=[engine.resize(image[round(i//3*h/2):round((i//3+1)*h/2),round(i%3*w/3):round((i%3+1)*w/3)],side,side) for i in range(6)]
    surface=engine.Surface(scene); poses=cameras(scene['pa_projection_origin'])
    # Depth maps make visibility evaluation practical for millions of atlas texels.
    shots=[]
    for name,matrix in poses:
        print('Projection visibility: '+name,flush=True)
        shots.append(engine.scan(surface,matrix,90,384,384))
    size=int(scene['pa_atlas_size']); result=np.ones((size,size,4),np.float32)
    result[...,:3]=.05; coverage=np.zeros((size,size),np.float32); occupied=np.zeros((size,size),bool)
    for tid,(obj,poly,uv) in enumerate(surface.records):
        pts=uv*np.array((size,size)); pts[:,1]=size-pts[:,1]
        x0=max(0,int(np.floor(pts[:,0].min()))); x1=min(size,int(np.ceil(pts[:,0].max())))
        y0=max(0,int(np.floor(pts[:,1].min()))); y1=min(size,int(np.ceil(pts[:,1].max())))
        xx,yy=np.meshgrid(np.arange(x0,x1),np.arange(y0,y1)); samples=np.column_stack((xx.ravel()+.5,yy.ravel()+.5))
        basis=np.stack((pts[1]-pts[0],pts[2]-pts[0]),-1)
        if abs(np.linalg.det(basis))<1e-8: continue
        bc=(samples-pts[0])@np.linalg.inv(basis).T; weights=np.column_stack((1-bc.sum(1),bc))
        inside=np.all(weights>=-1e-5,axis=1)
        if not np.any(inside): continue
        ax=xx.ravel()[inside]; ay=yy.ravel()[inside]
        world=weights[inside]@np.array([surface.vertices[v][:] for v in surface.triangles[tid]])
        best=np.full(len(world),-1e9); colors=np.zeros((len(world),4)); visible_best=np.zeros(len(world),bool)
        for i,((name,matrix),shot) in enumerate(zip(poses,shots)):
            inv=np.array(matrix.inverted()); p=world@inv[:3,:3].T+inv[:3,3]; z=-p[:,2]
            u=.5+.5*p[:,0]/np.maximum(z,1e-8); v=.5-.5*p[:,1]/np.maximum(z,1e-8)
            valid=(z>0)&(u>=0)&(u<=1)&(v>=0)&(v<=1)
            sx=np.clip(u*384,0,383).astype(int); sy=np.clip(v*384,0,383).astype(int)
            depth=shot['depth'][sy,sx]
            visible=valid&(np.abs(depth-z)<np.maximum(.035,z*.018))
            score=np.where(valid,1-np.maximum(abs(u-.5),abs(v-.5)),-1e8)+visible*10
            choose=score>best; best[choose]=score[choose]
            fx=np.clip(u*side-.5,0,side-1); fy=np.clip(v*side-.5,0,side-1)
            tx=fx.astype(int); ty=fy.astype(int); nx=np.minimum(tx+1,side-1); ny=np.minimum(ty+1,side-1)
            wx=(fx-tx)[:,None]; wy=(fy-ty)[:,None]
            sampled=(tiles[i][ty,tx]*(1-wx)+tiles[i][ty,nx]*wx)*(1-wy)+(tiles[i][ny,tx]*(1-wx)+tiles[i][ny,nx]*wx)*wy
            colors[choose]=sampled[choose]; visible_best[choose]=visible[choose]
        result[ay,ax]=colors; occupied[ay,ax]=True; coverage[ay,ax]=visible_best
    # Pad UV islands by 3 texels to avoid dark bilinear seams.
    filled=occupied.copy()
    for _ in range(3):
        old=filled.copy()
        for dy,dx in ((0,1),(0,-1),(1,0),(-1,0)):
            candidate=np.roll(old,(dy,dx),(0,1)); take=candidate&~filled
            result[take]=np.roll(result,(dy,dx),(0,1))[take]; filled[take]=True
    texture=folder/'camera-mapped-atlas.png'; engine.write_image(texture,result)
    engine.write_image(folder/'projection-coverage.png',coverage,True)
    packed=bpy.data.images.load(str(texture)); packed.pack()
    for obj in engine.owned(scene):
        engine.set_texture(obj,packed)
        obj['pa_original_image']=packed.name
    report={'technique':'fixed_camera_projection_baked_per_surface_texel','source_atlas':str(path),
        'uv_texels':int(occupied.sum()),'visible_projection_texels':int(coverage[occupied].sum()),
        'occluded_fallback_texels':int((coverage[occupied]==0).sum()),
        'limitation':'Occluded fallback texels need additional displaced-camera masked repairs; multi-view visual consistency is not guaranteed.'}
    (folder/'projection-report.json').write_text(json.dumps(report,indent=2))
    scene['pa_projection_report']=str(folder/'projection-report.json')
    return report
