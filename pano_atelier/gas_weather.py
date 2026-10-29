"""Image-free peeling paint, rain runs and roof dirt in metric local space.

Art-directed imitation of the GPT albedo's structure, not an image-to-shader fit.
The two reusable paint assets contain no bitmap dependency.
"""
import bpy,hashlib
from mathutils import Vector
from .station_procedural import node,feed,noise,mapped,mix,math as calc

def vmath(t,op,a,b):
    n=node(t,'ShaderNodeVectorMath',op);n.operation=op;feed(t,n.inputs[0],a);feed(t,n.inputs['Scale'] if op=='SCALE' else n.inputs[1],b);return n.outputs[0]

def paint_group(blue=False):
    name='PA · Peinture bleue usee' if blue else 'PA · Enduit blanc ecaille'
    g=bpy.data.node_groups.new(name,'ShaderNodeTree')
    for label,typ,default in [('Coordonnees metres','NodeSocketVector',None),('Bandes hauteur','NodeSocketVector',None),('Ecaillage','NodeSocketFloat',.57 if blue else .56),('Crasse','NodeSocketFloat',.78),('Echelle','NodeSocketFloat',1.0)]:
        s=g.interface.new_socket(name=label,in_out='INPUT',socket_type=typ)
        if default is not None:s.default_value=default;s.min_value=.01;s.max_value=2 if label=='Echelle' else 1
    for label,typ in [('Couleur','NodeSocketColor'),('Rugosite','NodeSocketFloat'),('Normale','NodeSocketVector'),('Metal','NodeSocketFloat')]:g.interface.new_socket(name=label,in_out='OUTPUT',socket_type=typ)
    inp=node(g,'NodeGroupInput','Reglages');out=node(g,'NodeGroupOutput','Matiere physique')
    co=vmath(g,'MULTIPLY',inp.outputs['Coordonnees metres'],inp.outputs['Echelle'])
    warp=node(g,'ShaderNodeTexNoise','Contour irregulier des ecailles');feed(g,warp.inputs['Vector'],co);warp.inputs['Scale'].default_value=11;warp.inputs['Detail'].default_value=3
    co2=vmath(g,'ADD',co,vmath(g,'SCALE',warp.outputs['Color'],.10))
    broad=noise(g,'Plaques de peinture decollee',co2,3.2 if blue else 2.1,4)
    threshold=calc(g,'SUBTRACT',.76,calc(g,'MULTIPLY',inp.outputs['Ecaillage'],.28))
    chips=mapped(g,'Bords francs irreguliers',broad,threshold,calc(g,'ADD',threshold,.026),0,1)
    rim=mapped(g,'Sous couche aux bords',broad,calc(g,'SUBTRACT',threshold,.022),threshold,0,1)
    grain=noise(g,'Grain fin du support',co,190,2)
    tone=(.055,.135,.185,1) if blue else (.52,.535,.48,1)
    subtle=tuple(c*.88 if i<3 else c for i,c in enumerate(tone))
    color=mix(g,'Peinture legerement passee',mapped(g,'Nuance fine',noise(g,'Pigment',co,22,2),0,1,0,.5),tone,subtle)
    primer=(.235,.19,.11,1) if blue else (.35,.345,.29,1)
    bare=(.105,.050,.020,1) if blue else (.205,.215,.19,1)
    color=mix(g,'Liseres de sous couche',rim,color,primer);color=mix(g,'Support expose',chips,color,bare)
    bands=node(g,'ShaderNodeSeparateXYZ','Hauteur au pied / sous rive');feed(g,bands.inputs[0],inp.outputs['Bandes hauteur'])
    streak_co=vmath(g,'MULTIPLY',co,(6,6,.20))
    streak=noise(g,'Ruissellement vertical discontinu',streak_co,2.2,3)
    threads=mapped(g,'Filets de pluie',streak,.48,.73,0,1)
    run_length=mapped(g,'Longueur variable',noise(g,'Departs de coulures',vmath(g,'MULTIPLY',co,(1,1,0)),3,2),.25,.75,.18,1.8)
    top=mapped(g,'Coulees sous rive',bands.outputs['Y'],.03,run_length,1,0)
    foot=mapped(g,'Humidite ascendante',bands.outputs['X'],.08,.95,1,0)
    mottled=mapped(g,'Depots irreguliers au pied',noise(g,'Mousse rare',co2,8,3),.25,.70,.12,1)
    dirt=calc(g,'MAXIMUM',calc(g,'MULTIPLY',threads,top),calc(g,'MULTIPLY',foot,mottled))
    dirt=calc(g,'MULTIPLY',dirt,inp.outputs['Crasse'])
    color=mix(g,'Depots noirs et verdatres',dirt,color,(.027,.035,.025,1))
    micro=node(g,'ShaderNodeBump','Grain mineral 0.4 mm');micro.inputs['Distance'].default_value=.0004;micro.inputs['Strength'].default_value=.35;feed(g,micro.inputs['Height'],grain)
    bump=node(g,'ShaderNodeBump','Epaisseur de peinture 1 mm');bump.inputs['Distance'].default_value=.0012;bump.inputs['Strength'].default_value=.65;feed(g,bump.inputs['Height'],calc(g,'SUBTRACT',1,chips));feed(g,bump.inputs['Normal'],micro.outputs[0])
    rough=calc(g,'ADD',.53 if blue else .73,calc(g,'MULTIPLY',chips,.20 if blue else .12))
    feed(g,out.inputs['Couleur'],color);feed(g,out.inputs['Rugosite'],rough);feed(g,out.inputs['Normale'],bump.outputs[0]);feed(g,out.inputs['Metal'],calc(g,'MULTIPLY',chips,.55 if blue else 0))
    for i,n in enumerate(g.nodes):n.location=((i//7)*230,-(i%7)*165)
    return g

def add_layer(mat,group,keep=.0,attribute=True):
    t=mat.node_tree;bs=t.nodes.get('Principled BSDF');old=bs.inputs['Base Color'].links[0].from_socket if bs.inputs['Base Color'].is_linked else tuple(bs.inputs['Base Color'].default_value)
    gr=node(t,'ShaderNodeGroup','Peinture procedurale reglable');gr.node_tree=group
    if attribute:
        a=node(t,'ShaderNodeAttribute','Metres lies au module');a.attribute_name='PA_WeatherMeters'
        h=node(t,'ShaderNodeAttribute','Pied et rive du panneau');h.attribute_name='PA_WeatherBands';feed(t,gr.inputs[0],a.outputs['Vector']);feed(t,gr.inputs[1],h.outputs['Vector'])
    else:
        a=node(t,'ShaderNodeTexCoord','Coordonnees locales');feed(t,gr.inputs[0],a.outputs['Object'])
        sep=node(t,'ShaderNodeSeparateXYZ','Hauteur');feed(t,sep.inputs[0],a.outputs['Object']);bands=node(t,'ShaderNodeCombineXYZ','Panneau 3m');feed(t,bands.inputs[0],sep.outputs['Z']);feed(t,bands.inputs[1],calc(t,'SUBTRACT',3,sep.outputs['Z']));feed(t,gr.inputs[1],bands.outputs[0])
    final=mix(t,'Procedural + rappel GPT',keep,gr.outputs['Couleur'],old) if keep else gr.outputs['Couleur']
    feed(t,bs.inputs['Base Color'],final);feed(t,bs.inputs['Normal'],gr.outputs['Normale']);feed(t,bs.inputs['Roughness'],gr.outputs['Rugosite']);feed(t,bs.inputs['Metallic'],gr.outputs['Metal'])
    mat['pa_gas_procedural_paint']=True;mat['pa_gpt_reminder']=keep
    return gr

def coordinates(o):
    if o.type!='MESH':return
    root=o.parent
    while root and not root.get('pa_module'):root=root.parent
    mx=(root.matrix_world.inverted()@o.matrix_world) if root else o.matrix_local
    coords=[mx@v.co for v in o.data.vertices]
    if not coords:return
    lo=min(v.z for v in coords);hi=max(v.z for v in coords)
    seed=int(hashlib.sha1((root.name if root else o.name).encode()).hexdigest()[:4],16)/65535*23
    for name in ('PA_WeatherMeters','PA_WeatherBands'):
        if name in o.data.attributes:o.data.attributes.remove(o.data.attributes[name])
    a=o.data.attributes.new('PA_WeatherMeters','FLOAT_VECTOR','POINT');a.data.foreach_set('vector',[q for v in coords for q in (v.x+seed,v.y+seed,v.z)])
    a=o.data.attributes.new('PA_WeatherBands','FLOAT_VECTOR','POINT');a.data.foreach_set('vector',[q for v in coords for q in (v.z-lo,hi-v.z,seed)])

def install(scene):
    if scene.get('pa_gas_proc_weather'):raise ValueError('Peintures procedurales deja installees.')
    groups=[paint_group(False),paint_group(True)];pure=[]
    for blue,g in enumerate(groups):
        m=bpy.data.materials.new('PA · BLEU patine procedural' if blue else 'PA · BLANC patine procedural');m.use_nodes=True;add_layer(m,g,attribute=False);m.use_fake_user=True;m.asset_mark();m.asset_data.description='Procedural sans image : ecaillage, sous couche, ruissellement et humidite. Coordonnees locales en metres.';pure.append(m)
    used={s.material for o in scene.objects for s in o.material_slots if s.material}
    changed=[]
    for m in used:
        blue=m.name.startswith('STATION · tole bleu desature');white=m.name.startswith('STATION · enduit ivoire ancien')
        if not (white or blue):continue
        add_layer(m,groups[1 if blue else 0],keep=.25 if 'detail projete' in m.name else 0,attribute=True);changed.append(m.name)
    bpy.context.view_layer.update()
    for o in scene.objects:
        if o.type=='MESH' and any(s.material and s.material.get('pa_gas_procedural_paint') for s in o.material_slots):coordinates(o)
    scene['pa_gas_proc_weather']=True
    return groups,pure,changed

def roof_material():
    m=bpy.data.materials.new('PA · Toiture depots et oxydation');m.use_nodes=True;t=m.node_tree;bs=t.nodes.get('Principled BSDF');tc=node(t,'ShaderNodeTexCoord','Toiture locale');co=tc.outputs['Object']
    sep=node(t,'ShaderNodeSeparateXYZ','Bords de toiture');feed(t,sep.inputs[0],tc.outputs['Generated'])
    edge=calc(t,'MINIMUM',calc(t,'MINIMUM',sep.outputs['X'],calc(t,'SUBTRACT',1,sep.outputs['X'])),calc(t,'MINIMUM',sep.outputs['Y'],calc(t,'SUBTRACT',1,sep.outputs['Y'])))
    border=mapped(t,'Salissure accumulee en peripherie',edge,.015,.14,1,0)
    n=noise(t,'Taches de sediments',co,4.5,5);mask=mapped(t,'Iles de depots',n,.52,.68,0,1)
    dirt=calc(t,'MAXIMUM',calc(t,'MULTIPLY',border,mapped(t,'Bords heterogenes',n,0,1,.3,1)),calc(t,'MULTIPLY',mask,.55))
    color=mix(t,'Membrane usee',mapped(t,'Nuance discrete',n,0,1,0,.3),(.16,.17,.145,1),(.11,.12,.095,1));color=mix(t,'Sediments noir verdatre',dirt,color,(.025,.032,.022,1));feed(t,bs.inputs['Base Color'],color)
    feed(t,bs.inputs['Roughness'],mapped(t,'Humidite des sediments',n,.35,.7,.86,.49));micro=node(t,'ShaderNodeBump','Grain toiture');micro.inputs['Distance'].default_value=.002;micro.inputs['Strength'].default_value=.35;feed(t,micro.inputs['Height'],noise(t,'Granulat toiture',co,110,2));feed(t,bs.inputs['Normal'],micro.outputs[0]);return m
