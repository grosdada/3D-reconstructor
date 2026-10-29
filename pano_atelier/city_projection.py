"""Optional low-weight albedo detail projection over procedural city surfaces.

Depth, normal and eligibility gating; frozen rest coordinates follow moved modules.
"""
import bpy,json
from pathlib import Path
from mathutils import Vector,Matrix
from .multiview_albedo import node,mathn,vec,transform,scale


def apply(scene,folder,strength=.28,incidence_exponent=3,append=False,scope='ALL'):
    if scope not in ('ALL','OPPOSITE'):raise ValueError('Cible de projection inconnue.')
    folder=Path(folder);meta=json.loads((folder/'projection.json').read_text(encoding='utf8'))
    for filename in ('detail-albedo.png','guide-depth.exr','guide-mask.png'):
        if not (folder/filename).exists():raise FileNotFoundError(folder/filename)
    if scene.get('pa_city_projection') and not append:raise ValueError('Projection deja appliquee.')
    layers=json.loads(scene.get('pa_city_projection_layers','[]'))
    if not layers and scene.get('pa_city_projection'):layers=[{'folder':scene['pa_city_projection']}]
    if any(x['folder']==str(folder) for x in layers):raise ValueError('Cette vue est deja projetee.')
    suffix='' if not layers else '_%02d'%(len(layers)+1)
    pos_name='PA_CityRest'+suffix;normal_name='PA_CityNormal'+suffix
    targets=[o for o in scene.objects if o.type=='MESH' and o.get('pa_city_project') and (scope=='ALL' or o.get('pa_opposite'))]
    if not targets:raise ValueError('Aucune facade cible de projection.')
    ng=bpy.data.node_groups.new('VILLE · details albedo camera','ShaderNodeTree')
    for name,typ in [('Color','NodeSocketColor'),('Coverage','NodeSocketFloat')]:ng.interface.new_socket(name=name,in_out='OUTPUT',socket_type=typ)
    po=node(ng,'ShaderNodeAttribute','Position de repos');po.attribute_name=pos_name
    no=node(ng,'ShaderNodeAttribute','Normale de repos');no.attribute_name=normal_name
    matrix=Matrix(meta['matrix']);p=transform(ng,po.outputs['Vector'],matrix.inverted());xyz=node(ng,'ShaderNodeSeparateXYZ','Camera locale');ng.links.new(p,xyz.inputs[0]);z=mathn(ng,'MULTIPLY',xyz.outputs['Z'],-1)
    fr=[Vector(x) for x in meta['frame']];xmin=min(a.x/-a.z for a in fr);xmax=max(a.x/-a.z for a in fr);ymin=min(a.y/-a.z for a in fr);ymax=max(a.y/-a.z for a in fr)
    u=mathn(ng,'DIVIDE',mathn(ng,'SUBTRACT',mathn(ng,'DIVIDE',xyz.outputs['X'],z),xmin),xmax-xmin)
    v=mathn(ng,'DIVIDE',mathn(ng,'SUBTRACT',mathn(ng,'DIVIDE',xyz.outputs['Y'],z),ymin),ymax-ymin)
    uv=node(ng,'ShaderNodeCombineXYZ','Projection fixe');ng.links.new(u,uv.inputs[0]);ng.links.new(v,uv.inputs[1]);tex={}
    for f in ('detail-albedo.png','guide-depth.exr','guide-mask.png'):
        im=bpy.data.images.load(str(folder/f),check_existing=True)
        if f!='detail-albedo.png':im.colorspace_settings.name='Non-Color'
        im.pack();n=node(ng,'ShaderNodeTexImage',f);n.image=im;n.extension='CLIP';ng.links.new(uv.outputs[0],n.inputs[0]);tex[f]=n.outputs['Color']
    diff=mathn(ng,'ABSOLUTE',mathn(ng,'SUBTRACT',z,tex['guide-depth.exr']))
    depth=mathn(ng,'LESS_THAN',diff,.14)
    incidence=mathn(ng,'POWER',mathn(ng,'MAXIMUM',vec(ng,'DOT_PRODUCT',vec(ng,'NORMALIZE',no.outputs['Vector']),vec(ng,'NORMALIZE',vec(ng,'SUBTRACT',tuple(matrix.translation),po.outputs['Vector']))),0),incidence_exponent)
    edge=mathn(ng,'MINIMUM',mathn(ng,'MINIMUM',u,mathn(ng,'SUBTRACT',1,u)),mathn(ng,'MINIMUM',v,mathn(ng,'SUBTRACT',1,v)))
    fade=mathn(ng,'MINIMUM',mathn(ng,'MAXIMUM',mathn(ng,'MULTIPLY',edge,18),0),1)
    coverage=mathn(ng,'MULTIPLY',mathn(ng,'MULTIPLY',depth,tex['guide-mask.png']),mathn(ng,'MULTIPLY',incidence,fade))
    out=node(ng,'NodeGroupOutput','Detail sans eclairage');ng.links.new(tex['detail-albedo.png'],out.inputs['Color']);ng.links.new(coverage,out.inputs['Coverage'])
    mats={}
    for o in targets:
        if o.data.users>1:o.data=o.data.copy()
        me=o.data
        for name in (pos_name,normal_name):
            if name in me.attributes:me.attributes.remove(me.attributes[name])
        me.attributes.new(pos_name,'FLOAT_VECTOR','POINT');me.attributes.new(normal_name,'FLOAT_VECTOR','CORNER')
        pos=me.attributes[pos_name];normal=me.attributes[normal_name];nm=o.matrix_world.inverted().transposed().to_3x3()
        for vertex,entry in zip(me.vertices,pos.data):entry.vector=o.matrix_world@vertex.co
        for face in me.polygons:
            n=(nm@face.normal).normalized()
            for li in face.loop_indices:normal.data[li].vector=n
        for slot in o.material_slots:
            src=slot.material
            if not src:continue
            if src.name not in mats:
                m=src.copy();m.name=src.name+' · detail projete';nt=m.node_tree;bs=nt.nodes.get('Principled BSDF')
                if not bs:continue
                old=bs.inputs['Base Color'].links[0].from_socket;gr=node(nt,'ShaderNodeGroup','Details photographiques localises');gr.node_tree=ng
                mx=node(nt,'ShaderNodeMixRGB','Procedural majoritaire / albedo detail');nt.links.new(old,mx.inputs[1]);nt.links.new(gr.outputs['Color'],mx.inputs[2]);nt.links.new(mathn(nt,'MULTIPLY',gr.outputs['Coverage'],strength),mx.inputs[0]);nt.links.new(mx.outputs[0],bs.inputs['Base Color'])
                m['pa_projection_strength']=strength;mats[src.name]=m
            slot.link='OBJECT';slot.material=mats[src.name]
    scene['pa_city_projection']=str(folder)
    layers.append({'folder':str(folder),'strength':strength,'incidence_exponent':incidence_exponent,'position_attribute':pos_name,'normal_attribute':normal_name,'target_scope':scope})
    scene['pa_city_projection_layers']=json.dumps(layers)
    return {'targets':len(targets),'materials':len(mats),'max_strength':strength,'incidence_exponent':incidence_exponent,'scope':'Albedo detail only. Procedural roughness, bump, general dirt and lighting preserved.','guards':['frozen rest coordinates','depth tolerance 14 cm','front-facing incidence','eligible concrete mask','image border fade']}
