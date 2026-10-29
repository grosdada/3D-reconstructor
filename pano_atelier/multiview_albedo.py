"""Depth-gated albedo projection with object-attached rest attributes.

Generated colors feed Base Color only. Lighting, emission and metal stay physical.
"""
import json,math
from pathlib import Path
import bpy
from mathutils import Vector,Matrix

def node(nt,t,name):
    n=nt.nodes.new(t);n.name=n.label=name;return n
def mathn(nt,op,a,b=0):
    n=node(nt,'ShaderNodeMath',op);n.operation=op
    for i,v in enumerate((a,b)):
        if isinstance(v,(int,float)):n.inputs[i].default_value=v
        else:nt.links.new(v,n.inputs[i])
    return n.outputs[0]
def vec(nt,op,a,b=None):
    n=node(nt,'ShaderNodeVectorMath',op);n.operation=op
    for i,v in enumerate((a,b)):
        if v is None:continue
        if isinstance(v,(tuple,list,Vector)):n.inputs[i].default_value=v
        else:nt.links.new(v,n.inputs[i])
    return n.outputs['Value'] if op=='DOT_PRODUCT' else n.outputs['Vector']
def scale(nt,a,s):
    n=node(nt,'ShaderNodeVectorMath','Poids');n.operation='SCALE';nt.links.new(a,n.inputs[0])
    if isinstance(s,(int,float)):n.inputs['Scale'].default_value=s
    else:nt.links.new(s,n.inputs['Scale'])
    return n.outputs[0]
def transform(nt,value,matrix):
    co=node(nt,'ShaderNodeCombineXYZ','Coordonnees camera')
    for i,axis in enumerate('XYZ'):nt.links.new(vec(nt,'DOT_PRODUCT',value,tuple(matrix[i][:3])),co.inputs[axis])
    return vec(nt,'ADD',co.outputs[0],tuple(matrix.translation))

def atlas_material(mat,image,quadrant,meters=1.5,strength=1):
    nt=mat.node_tree;bs=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED')
    tc=node(nt,'ShaderNodeTexCoord','Coordonnees locales atlas');geo=node(nt,'ShaderNodeNewGeometry','Normale')
    tr=node(nt,'ShaderNodeVectorTransform','Normale locale');tr.vector_type='NORMAL';tr.convert_from='WORLD';tr.convert_to='OBJECT';nt.links.new(geo.outputs['Normal'],tr.inputs[0])
    sep=node(nt,'ShaderNodeSeparateXYZ','Axes normaux');nt.links.new(tr.outputs[0],sep.inputs[0])
    weights=[mathn(nt,'POWER',mathn(nt,'ABSOLUTE',sep.outputs[a]),8) for a in 'XYZ'];total=mathn(nt,'MAXIMUM',mathn(nt,'ADD',mathn(nt,'ADD',weights[0],weights[1]),weights[2]),.00001)
    info=node(nt,'ShaderNodeObjectInfo','Variation par objet');offset=node(nt,'ShaderNodeCombineXYZ','Decalage matiere')
    for k,m in enumerate((13.1,7.7,19.3)):nt.links.new(mathn(nt,'MULTIPLY',info.outputs['Random'],m),offset.inputs[k])
    coord=vec(nt,'ADD',tc.outputs['Object'],offset.outputs[0]);xyz=node(nt,'ShaderNodeSeparateXYZ','Axes texture');nt.links.new(coord,xyz.inputs[0]);colors=[]
    for i,axes in enumerate(('YZ','XZ','XY')):
        uv=node(nt,'ShaderNodeCombineXYZ','Quart atlas')
        for j,axis in enumerate(axes):nt.links.new(mathn(nt,'ADD',mathn(nt,'MULTIPLY',mathn(nt,'PINGPONG',mathn(nt,'DIVIDE',xyz.outputs[axis],meters),1),.482),quadrant[j]+.009),uv.inputs[j])
        tex=node(nt,'ShaderNodeTexImage','GPT · albedo matiere');tex.image=image;tex.extension='EXTEND';nt.links.new(uv.outputs[0],tex.inputs[0]);colors.append(scale(nt,tex.outputs['Color'],mathn(nt,'DIVIDE',weights[i],total)))
    color=vec(nt,'ADD',vec(nt,'ADD',colors[0],colors[1]),colors[2]);mix=node(nt,'ShaderNodeMixRGB','Albedo matiere / teinte');mix.inputs[0].default_value=strength;mix.inputs[1].default_value=bs.inputs['Base Color'].default_value;nt.links.new(color,mix.inputs[2]);nt.links.new(mix.outputs[0],bs.inputs['Base Color'])
    bump=node(nt,'ShaderNodeBump','Microrelief discret');bump.inputs['Distance'].default_value=.0008;bump.inputs['Strength'].default_value=.15;nt.links.new(color,bump.inputs['Height']);nt.links.new(bump.outputs[0],bs.inputs['Normal']);mat['pa_albedo_only']=True

def apply(scene,manifest_path):
    manifest_path=Path(manifest_path);folder=manifest_path.parent;views=json.loads(manifest_path.read_text(encoding='utf8'))
    # Preflight: a partially generated manifest must not produce a half-wired scene.
    for v in views:
        for suffix in ('-albedo.png','-depth.exr','-protection.png'):
            if not (folder/(v['name']+suffix)).is_file():raise FileNotFoundError(folder/(v['name']+suffix))
    targets=[o for o in scene.objects if o.type=='MESH' and o.get('pa_albedo_target') and not o.get('pa_asset_instance')]
    if not targets:raise ValueError('Aucun objet marque pa_albedo_target')
    if scene.get('pa_multiview_applied'):raise ValueError('Projections deja appliquees; repartir de la base de projection.')
    mats={m for o in targets for m in o.data.materials if m and m.name.startswith('ST ·')}
    mats={m for m in mats if any(key in m.name for key in ('panneaux','sas email','sol resine','plaques circulation','coffrets'))}
    ng=bpy.data.node_groups.new('PA · albedos multivues station','ShaderNodeTree')
    for name,typ in [('Color','NodeSocketColor'),('Coverage','NodeSocketFloat')]:ng.interface.new_socket(name=name,in_out='OUTPUT',socket_type=typ)
    po=node(ng,'ShaderNodeAttribute','Rest position');po.attribute_name='PA_RestWorld'
    no=node(ng,'ShaderNodeAttribute','Rest normal');no.attribute_name='PA_RestNormal';normal=vec(ng,'NORMALIZE',no.outputs['Vector'])
    cs=[];ws=[];images=[]
    for v in views:
        mat=Matrix(v['matrix']);p=transform(ng,po.outputs['Vector'],mat.inverted());sp=node(ng,'ShaderNodeSeparateXYZ',v['name']);ng.links.new(p,sp.inputs[0]);z=mathn(ng,'MULTIPLY',sp.outputs['Z'],-1)
        fr=[Vector(a) for a in v['frame']];xmin=min(a.x/-a.z for a in fr);xmax=max(a.x/-a.z for a in fr);ymin=min(a.y/-a.z for a in fr);ymax=max(a.y/-a.z for a in fr)
        u=mathn(ng,'DIVIDE',mathn(ng,'SUBTRACT',mathn(ng,'DIVIDE',sp.outputs['X'],z),xmin),xmax-xmin);vv=mathn(ng,'DIVIDE',mathn(ng,'SUBTRACT',mathn(ng,'DIVIDE',sp.outputs['Y'],z),ymin),ymax-ymin)
        uv=node(ng,'ShaderNodeCombineXYZ',v['name']+' UV');ng.links.new(u,uv.inputs[0]);ng.links.new(vv,uv.inputs[1]);textures={}
        for suffix in ('albedo.png','depth.exr','protection.png'):
            im=bpy.data.images.load(str(folder/(v['name']+'-'+suffix)),check_existing=True)
            if suffix!='albedo.png':im.colorspace_settings.name='Non-Color'
            im.pack();images.append(im);tex=node(ng,'ShaderNodeTexImage',v['name']+' '+suffix);tex.image=im;tex.extension='EXTEND';ng.links.new(uv.outputs[0],tex.inputs[0]);textures[suffix]=tex.outputs['Color']
        depdiff=mathn(ng,'ABSOLUTE',mathn(ng,'SUBTRACT',z,textures['depth.exr']));mask=mathn(ng,'LESS_THAN',depdiff,mathn(ng,'ADD',.025,mathn(ng,'MULTIPLY',z,.001)))
        mask=mathn(ng,'MULTIPLY',mask,mathn(ng,'GREATER_THAN',z,.02))
        edge=mathn(ng,'MINIMUM',mathn(ng,'MINIMUM',u,mathn(ng,'SUBTRACT',1,u)),mathn(ng,'MINIMUM',vv,mathn(ng,'SUBTRACT',1,vv)))
        fade=mathn(ng,'MINIMUM',mathn(ng,'MAXIMUM',mathn(ng,'MULTIPLY',edge,14),0),1)
        angle=mathn(ng,'POWER',mathn(ng,'MAXIMUM',vec(ng,'DOT_PRODUCT',normal,vec(ng,'NORMALIZE',vec(ng,'SUBTRACT',tuple(mat.translation),po.outputs['Vector']))),0),4)
        w=mathn(ng,'MULTIPLY',mathn(ng,'MULTIPLY',mathn(ng,'MULTIPLY',mask,fade),angle),textures['protection.png']);ws.append(w);cs.append(scale(ng,textures['albedo.png'],w))
    sumw=ws[0];sumc=cs[0]
    for w,c in zip(ws[1:],cs[1:]):sumw=mathn(ng,'ADD',sumw,w);sumc=vec(ng,'ADD',sumc,c)
    result=scale(ng,sumc,mathn(ng,'DIVIDE',1,mathn(ng,'MAXIMUM',sumw,.00001)));coverage=mathn(ng,'MINIMUM',mathn(ng,'MULTIPLY',sumw,4),1)
    out=node(ng,'NodeGroupOutput','Albedos seulement');ng.links.new(result,out.inputs['Color']);ng.links.new(coverage,out.inputs['Coverage'])
    bpy.context.view_layer.update()
    for o in targets:
        if not any(m in mats for m in o.data.materials):continue
        if o.data.users>1:o.data=o.data.copy()
        me=o.data
        for name in ('PA_RestWorld','PA_RestNormal'):
            if name in me.attributes:me.attributes.remove(me.attributes[name])
        a=me.attributes.new('PA_RestWorld','FLOAT_VECTOR','POINT');n=me.attributes.new('PA_RestNormal','FLOAT_VECTOR','CORNER');normalmat=o.matrix_world.inverted().transposed().to_3x3()
        # Retrieve attributes after both allocations: adding an attribute can invalidate RNA wrappers.
        a=me.attributes['PA_RestWorld'];n=me.attributes['PA_RestNormal']
        for vertex,entry in zip(me.vertices,a.data):entry.vector=o.matrix_world@vertex.co
        for poly in me.polygons:
            norm=(normalmat@poly.normal).normalized()
            for li in poly.loop_indices:n.data[li].vector=norm
    for m in mats:
        nt=m.node_tree;bs=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED');old=bs.inputs['Base Color'].links[0].from_socket if bs.inputs['Base Color'].is_linked else None
        gr=node(nt,'ShaderNodeGroup','PA · albedo camera');gr.node_tree=ng;mix=node(nt,'ShaderNodeMixRGB','Albedo projete / matiere locale');weight=mathn(nt,'MULTIPLY',gr.outputs['Coverage'],.45 if 'sol resine' in m.name else .85);nt.links.new(weight,mix.inputs[0]);nt.links.new(gr.outputs['Color'],mix.inputs[2])
        if old:nt.links.new(old,mix.inputs[1])
        else:mix.inputs[1].default_value=bs.inputs['Base Color'].default_value
        nt.links.new(mix.outputs[0],bs.inputs['Base Color']);m['pa_albedo_only']=True
    scene['pa_multiview_applied']=str(manifest_path)
    return {'views':len(views),'objects':len(targets),'materials':len(mats),'images':len(images),'method':'base-color-only; fixed rest attributes; depth gating; incidence; border blend; protected silhouettes'}
