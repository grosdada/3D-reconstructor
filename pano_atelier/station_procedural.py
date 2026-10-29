"""Local procedural finish and low-poly machined plate ends, station recipe.

Own node implementation inspired by inspecting the user's layered materials.
No library material or external image is shipped with the add-on.
"""
import bpy, bmesh
from mathutils import Vector


def node(t,typ,name):
    n=t.nodes.new(typ);n.name=n.label=name;return n

def feed(t,s,value):
    if isinstance(value,bpy.types.NodeSocket):t.links.new(value,s)
    else:s.default_value=value

def math(t,op,a,b=0):
    n=node(t,'ShaderNodeMath',op);n.operation=op;feed(t,n.inputs[0],a);feed(t,n.inputs[1],b);return n.outputs[0]

def mix(t,name,fac,a,b):
    n=node(t,'ShaderNodeMixRGB',name);feed(t,n.inputs[0],fac);feed(t,n.inputs[1],a);feed(t,n.inputs[2],b);return n.outputs[0]

def mapped(t,name,x,lo,hi,a,b):
    n=node(t,'ShaderNodeMapRange',name);n.clamp=True;n.interpolation_type='SMOOTHERSTEP'
    for s,v in [('Value',x),('From Min',lo),('From Max',hi),('To Min',a),('To Max',b)]:feed(t,n.inputs[s],v)
    return n.outputs[0]

def noise(t,name,co,scale,detail=2):
    n=node(t,'ShaderNodeTexNoise',name);feed(t,n.inputs['Vector'],co);n.inputs['Scale'].default_value=scale;n.inputs['Detail'].default_value=detail;return n.outputs['Fac']

def finish(mat,color,rough=.42,metal=.04,keep_projection=False,floor=False):
    """Rebuild generic paint; preserve approved camera albedo on mapped walls."""
    t=mat.node_tree;bs=t.nodes.get('Principled BSDF')
    old=bs.inputs['Base Color'].links[0].from_socket if keep_projection and bs.inputs['Base Color'].is_linked else (*color,1)
    if not keep_projection and not floor:
        t.nodes.clear();bs=node(t,'ShaderNodeBsdfPrincipled','Principled BSDF');out=node(t,'ShaderNodeOutputMaterial','Material Output');t.links.new(bs.outputs[0],out.inputs['Surface'])
    tc=node(t,'ShaderNodeTexCoord','Procedural · coordonnees objet');info=node(t,'ShaderNodeObjectInfo','Procedural · variation par piece')
    offset=node(t,'ShaderNodeVectorMath','Procedural · decalage du grain');offset.operation='ADD';t.links.new(tc.outputs['Object'],offset.inputs[0]);t.links.new(info.outputs['Random'],offset.inputs[1]);co=offset.outputs[0]
    grain=noise(t,'Procedural · grain fin 0.8 mm',co,1250)
    dirt=noise(t,'Procedural · patine 15 mm',co,65,3)
    chipped=mapped(t,'Eclats · fraction discontinue',noise(t,'Eclats · bruit 3 mm',co,320,2),.48,.68,0,1)
    # Compare real normal and a ray-traced bevel normal, as in All edges.
    geo=node(t,'ShaderNodeNewGeometry','Usure · geometrie reelle')
    bevel=node(t,'ShaderNodeBevel','Usure · voisinage des aretes');bevel.samples=4;bevel.inputs['Radius'].default_value=.004 if floor else .006
    dif=node(t,'ShaderNodeVectorMath','Usure · difference de normales');dif.operation='DISTANCE';t.links.new(geo.outputs['Normal'],dif.inputs[0]);t.links.new(bevel.outputs['Normal'],dif.inputs[1])
    edge=mapped(t,'Usure · masque des bords',dif.outputs['Value'],.012,.15,0,1)
    wear=math(t,'MULTIPLY',math(t,'MULTIPLY',edge,chipped),.42 if not keep_projection else .18)
    ao=node(t,'ShaderNodeAmbientOcclusion','Crasse · creux proches');ao.samples=4;ao.only_local=True;ao.inputs['Distance'].default_value=.045
    crevice=math(t,'MULTIPLY',math(t,'SUBTRACT',1,ao.outputs['AO']),mapped(t,'Crasse · variation locale',dirt,0,1,.15,.40))
    tint=mapped(t,'Patine · amplitude contenue',dirt,0,1,.94,1.01)
    n=node(t,'ShaderNodeMixRGB','Peinture · variation douce');n.blend_type='MULTIPLY';n.inputs[0].default_value=1;feed(t,n.inputs[1],old);feed(t,n.inputs[2],tint)
    painted=mix(t,'Creux · depot fin',crevice,n.outputs[0],(.13,.115,.08,1))
    final=mix(t,'Aretes · metal decouvert',wear,painted,(.29,.31,.29,1));feed(t,bs.inputs['Base Color'],final)
    feed(t,bs.inputs['Metallic'],math(t,'ADD',metal,math(t,'MULTIPLY',wear,max(0,.82-metal))))
    feed(t,bs.inputs['Roughness'],math(t,'ADD',mapped(t,'Rugosite · grain',dirt,0,1,rough,rough+.10),math(t,'MULTIPLY',crevice,.2)))
    micro=node(t,'ShaderNodeBump','Procedural · micrograin');micro.inputs['Strength'].default_value=.16;micro.inputs['Distance'].default_value=.00008;feed(t,micro.inputs['Height'],grain)
    if floor:
        # Retain V2.1 analytic anti-slip dots, remove their former bitmap normal input.
        relief=t.nodes['Normal · relief antiderapant fin'];feed(t,relief.inputs['Normal'],micro.outputs[0]);feed(t,bs.inputs['Normal'],relief.outputs[0])
        for n in list(t.nodes):
            if n.type=='TEX_IMAGE':t.nodes.remove(n)
    else:feed(t,bs.inputs['Normal'],micro.outputs[0])
    # Clean obsolete atlas micro-bump on retained wall materials without changing color mapping.
    mat['pa_procedural_finish']=True;mat['pa_finish_scope']='local grain, geometry edge chips, short-range crevice dirt';mat['pa_keep_projection']=keep_projection
    # Readable node columns, without modifying external library data.
    for i,n in enumerate(t.nodes):
        if not keep_projection:n.location=((i//8)*230,-(i%8)*170)


def plate_mesh(o,ramp=False):
    w,l=(.42,.88) if ramp else (.66,.38);c=.024;r=.020;d=.030;a=w*.61
    bottom=[(-w+c,-l),(-a-r,-l),(-a-r,-l+d),(-a+r,-l+d),(-a+r,-l),(a-r,-l),(a-r,-l+d),(a+r,-l+d),(a+r,-l),(w-c,-l),(w,-l+c)]
    bottom=[(-w,-l+c)]+bottom
    outline=bottom+[(x,-y) for x,y in reversed(bottom)]
    bm=bmesh.new();vs=[bm.verts.new((x,y,0)) for x,y in outline];bm.faces.new(vs)
    if ramp:
        for y in (-.2,.2):
            bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-7,plane_co=(0,y,0),plane_no=(0,1,0))
    for v in bm.verts:v.co.z=(-1.21-max(0,abs(v.co.y)-.2)*(.38/.68)) if ramp else .008
    bm.verts.index_update();bm.verts.ensure_lookup_table();verts=[tuple(v.co) for v in bm.verts];faces=[tuple(v.index for v in f.verts) for f in bm.faces]
    # Explicit lower skin and closed side walls, no Boolean or subdivision modifier.
    boundary=[(e.verts[0].index,e.verts[1].index) for e in bm.edges if e.is_boundary];N=len(verts);thick=.009 if ramp else .016
    verts += [(x,y,z-thick) for x,y,z in verts[:N]]
    faces += [tuple(v+N for v in reversed(f)) for f in faces[:]]
    faces += [(i,j,j+N,i+N) for i,j in boundary];bm.free()
    mats=[s.material for s in o.material_slots]
    me=bpy.data.meshes.new(o.name+' · tole usinee');me.from_pydata(verts,[],faces);me.update()
    bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
    o.data=me
    for m in mats:me.materials.append(m)
    for mod in list(o.modifiers):
        if mod.type in {'BEVEL','WEIGHTED_NORMAL'}:o.modifiers.remove(mod)
    bevel=o.modifiers.new('Petits chanfreins usines','BEVEL');bevel.width=.0018;bevel.segments=2
    norm=o.modifiers.new('Normales ponderees','WEIGHTED_NORMAL');norm.keep_sharp=True
    o['pa_machined_plate']=True;o['pa_notch_width_m']=2*r;o['pa_notch_depth_m']=d
    return {'name':o.name,'vertices':len(me.vertices),'triangles':sum(len(p.vertices)-2 for p in me.polygons),'notches':4,'thickness_m':thick}


def apply(scene):
    if scene.get('pa_station_procedural'):raise ValueError('Passe procedurale deja appliquee.')
    if not scene.get('pa_surface_repair'):raise ValueError('Cette passe attend la station V2.1 avec raccord valide.')
    specs=[('V2 · email use des sas',(.61,.585,.48),.34,.04),('V2 · brides peinture ecailee',(.28,.29,.24),.46,.25),('V2 · acier nickel terni',(.26,.28,.26),.36,.78),('V2 · ocre securite use',(.49,.32,.05),.44,.03),('V2 · plaques de sol use fine',(.235,.28,.30),.43,.26)]
    for name,color,rough,metal in specs:
        if name not in bpy.data.materials:raise ValueError('Materiau requis absent: '+name)
    report={'procedural_materials':[],'hybrid_materials':[],'plates':[]}
    for name,color,rough,metal in specs:
        finish(bpy.data.materials[name],color,rough,metal,floor='plaques de sol' in name);report['procedural_materials'].append(name)
    for name in ['ST · panneaux ivoire vieilli','ST · sol resine creme','ST · coffrets gris']:
        m=bpy.data.materials.get(name)
        if m:finish(m,(.5,.48,.37),rough=.43,metal=.02,keep_projection=True);report['hybrid_materials'].append(name)
    for o in list(scene.objects):
        if o.type=='MESH' and o.name.startswith(('Plaque de passage antiderapante','Sas · seuil franchissable')):report['plates'].append(plate_mesh(o,'seuil' in o.name))
    scene['pa_station_procedural']=True
    return report
