"""Reusable, object-local primitives and curated KitBash import for modular scenes."""
import math
from pathlib import Path
import bpy,bmesh
from mathutils import Vector,Matrix

class Builder:
    def __init__(self,scene,name):
        self.scene=scene;self.collection=bpy.data.collections.new(name);scene.collection.children.link(self.collection)
        self.assets={};self.asset_report=[];self.modules=[]
    def root(self,name,location=(0,0,0),parent=None):
        o=bpy.data.objects.new(name,None);self.collection.objects.link(o);o.location=location;o.parent=parent;o.empty_display_size=.22;self.modules.append(o);return o
    def mesh(self,name,vertices,faces,mat,parent=None,bevel=0):
        me=bpy.data.meshes.new(name);me.from_pydata(vertices,[],faces);me.update()
        ob=bpy.data.objects.new(name,me);self.collection.objects.link(ob);ob.parent=parent
        if mat:me.materials.append(mat)
        if bevel:
            mod=ob.modifiers.new('Chanfreins physiques','BEVEL');mod.width=bevel;mod.segments=2
            no=ob.modifiers.new('Normales ponderees','WEIGHTED_NORMAL');no.keep_sharp=True
        return ob
    def box(self,name,loc,size,mat,parent=None,bevel=.008):
        x,y,z=(v/2 for v in size)
        ob=self.mesh(name,[(-x,-y,-z),(x,-y,-z),(x,y,-z),(-x,y,-z),(-x,-y,z),(x,-y,z),(x,y,z),(-x,y,z)],[(3,2,1,0),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)],mat,parent,bevel);ob.location=loc;return ob
    def pipe(self,name,points,radius,mat,parent=None,resolution=2):
        cu=bpy.data.curves.new(name,'CURVE');cu.dimensions='3D';cu.bevel_depth=radius;cu.bevel_resolution=resolution;cu.resolution_u=2
        s=cu.splines.new('POLY');s.points.add(len(points)-1)
        for p,v in zip(s.points,points):p.co=(*v,1)
        o=bpy.data.objects.new(name,cu);self.collection.objects.link(o);o.parent=parent;cu.materials.append(mat);return o
    def cylinder(self,name,loc,radius,depth,mat,parent=None,axis=(0,0,1),vertices=16):
        vs=[(radius*math.cos(i*math.tau/vertices),radius*math.sin(i*math.tau/vertices),z) for z in (-depth/2,depth/2) for i in range(vertices)]
        fs=[tuple(range(vertices-1,-1,-1)),tuple(range(vertices,vertices*2))]+[(i,(i+1)%vertices,(i+1)%vertices+vertices,i+vertices) for i in range(vertices)]
        o=self.mesh(name,vs,fs,mat,parent,.001 if radius<.03 else .004);o.location=loc;o.rotation_euler=Vector(axis).to_track_quat('Z','Y').to_euler();return o
    def ring(self,name,loc,inner,outer,depth,mat,parent=None,segments=96):
        # Axis Y. Four loops form an actual solid annulus with an open centre.
        vs=[(r*math.cos(i*math.tau/segments),y,r*math.sin(i*math.tau/segments)) for r,y in ((inner,-depth/2),(outer,-depth/2),(outer,depth/2),(inner,depth/2)) for i in range(segments)]
        fs=[]
        for k in range(4):
            for i in range(segments):j=(i+1)%segments;fs.append((k*segments+i,k*segments+j,((k+1)%4)*segments+j,((k+1)%4)*segments+i))
        o=self.mesh(name,vs,fs,mat,parent,.003);o.location=loc
        for p in o.data.polygons:p.use_smooth=True
        return o
    def asset(self,library,filename,object_name,mat=None):
        key=(filename,object_name,mat.name if mat else '')
        if key in self.assets:return self.assets[key]
        path=Path(library)/filename
        if not path.is_file():raise FileNotFoundError(path)
        with bpy.data.libraries.load(str(path),link=False) as (a,b):
            if object_name not in a.objects:raise ValueError('Asset absent : '+object_name)
            b.objects=[object_name]
        src=b.objects[0]
        if src.type!='MESH':raise ValueError('Asset mesh requis')
        # Source is never linked into the scene. Normalize its local bounds for predictable placement.
        me=src.data.copy();xs=[v.co.x for v in me.vertices];ys=[v.co.y for v in me.vertices];zs=[v.co.z for v in me.vertices]
        lo=Vector((min(xs),min(ys),min(zs)));hi=Vector((max(xs),max(ys),max(zs)));center=(lo+hi)/2;dims=hi-lo
        for v in me.vertices:v.co-=center
        me.materials.clear()
        if mat:me.materials.append(mat)
        me.use_fake_user=True
        self.assets[key]=(me,dims);self.asset_report.append({'file':filename,'object':object_name,'base_triangles':sum(len(p.vertices)-2 for p in me.polygons),'normalization':'Local bounds centered; instances share mesh; originals untouched.'})
        bpy.data.objects.remove(src,do_unlink=True)
        return me,dims
    def place_asset(self,name,source,loc,size,parent=None,rotation=(0,0,0)):
        me,dims=source;o=bpy.data.objects.new(name,me);self.collection.objects.link(o);o.parent=parent;o.location=loc;o.rotation_euler=rotation;o.scale=tuple(s/max(d,1e-8) for s,d in zip(size,dims));o['pa_asset_instance']=True;return o

def material(name,color,rough=.45,metal=0,emission=0):
    m=bpy.data.materials.new(name);m.use_nodes=True;bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Roughness'].default_value=rough;bs.inputs['Metallic'].default_value=metal
    if emission:bs.inputs['Emission Color'].default_value=(*color,1);bs.inputs['Emission Strength'].default_value=emission
    return m

def camera(builder,name,loc,target,lens=26,w=1440,h=960):
    d=bpy.data.cameras.new(name);o=bpy.data.objects.new(name,d);builder.collection.objects.link(o);o.location=loc;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();d.lens=lens;d.clip_start=.03;d.clip_end=150;o['pa_resolution_x']=w;o['pa_resolution_y']=h;return o
