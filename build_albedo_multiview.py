"""Six depth-masked front projections into Base Color, with physical relighting and movable modules."""
import bpy,json,math,hashlib,sys
from pathlib import Path
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'output/cockpit-albedo-multivues-test'
bpy.ops.wm.open_mainfile(filepath=str(OUT/'base-v2-six-vues.blend'))
sc=bpy.context.scene;sc.name='Cockpit · albédos GPT multivues + matériaux physiques'
views=json.loads((OUT/'views.json').read_text(encoding='utf-8'))
def digest():
    return hashlib.sha256(str([(o.name,o.parent.name if o.parent else None,list(map(tuple,o.matrix_world)),[tuple(v.co) for v in o.data.vertices],[tuple(p.vertices) for p in o.data.polygons]) for o in sorted(sc.objects,key=lambda o:o.name) if o.type=='MESH']).encode()).hexdigest()
before=digest()
def node(nt,t,name):
    n=nt.nodes.new(t);n.name=n.label=name;return n
def math_(nt,op,a,b=0,label=''):
    n=node(nt,'ShaderNodeMath',label or op);n.operation=op
    for i,v in enumerate([a,b]):
        if isinstance(v,(float,int)):n.inputs[i].default_value=v
        else:nt.links.new(v,n.inputs[i])
    return n.outputs[0]
def vec(nt,op,a,b=None,label=''):
    n=node(nt,'ShaderNodeVectorMath',label or op);n.operation=op
    for i,v in enumerate([a,b]):
        if v is None:continue
        if isinstance(v,(tuple,list,Vector)):n.inputs[i].default_value=v
        else:nt.links.new(v,n.inputs[i])
    return n.outputs['Value'] if op=='DOT_PRODUCT' else n.outputs['Vector']
def scale(nt,a,s,label='Scale'):
    n=node(nt,'ShaderNodeVectorMath',label);n.operation='SCALE';nt.links.new(a,n.inputs[0])
    if isinstance(s,(int,float)):n.inputs['Scale'].default_value=s
    else:nt.links.new(s,n.inputs['Scale'])
    return n.outputs[0]
def transform(nt,value,mat,prefix,offset=True):
    combine=node(nt,'ShaderNodeCombineXYZ',prefix)
    for i,axis in enumerate('XYZ'):
        val=vec(nt,'DOT_PRODUCT',value,tuple(mat[i][:3]),prefix+' Row '+axis);nt.links.new(val,combine.inputs[axis])
    return vec(nt,'ADD',combine.outputs[0],tuple(mat.translation),prefix+' Offset') if offset else combine.outputs[0]

# Shared shader reads rest positions/normals produced AFTER existing modifiers.
ng=bpy.data.node_groups.new('GPT · 6 projections albédo avec raccords','ShaderNodeTree')
for name,typ in [('Color','NodeSocketColor'),('Coverage','NodeSocketFloat'),('Overlap','NodeSocketFloat')]:ng.interface.new_socket(name=name,in_out='OUTPUT',socket_type=typ)
pos=node(ng,'ShaderNodeAttribute','Position monde de référence');pos.attribute_name='GPT_RestWorld'
norm=node(ng,'ShaderNodeAttribute','Normale monde de référence');norm.attribute_name='GPT_RestNormal'
normal=vec(ng,'NORMALIZE',norm.outputs['Vector'])
colors=[];weights=[];rawweights=[];images=[];masks=[]
for v in views:
    name=v['name'];mat=Matrix(v['matrix']);iv=mat.inverted();p=transform(ng,pos.outputs['Vector'],iv,name+' vers caméra')
    xyz=node(ng,'ShaderNodeSeparateXYZ',name+' XYZ');ng.links.new(p,xyz.inputs[0]);z=math_(ng,'MULTIPLY',xyz.outputs['Z'],-1,name+' profondeur')
    fr=[Vector(f) for f in v['frame']];xmin=min(f.x/-f.z for f in fr);xmax=max(f.x/-f.z for f in fr);ymin=min(f.y/-f.z for f in fr);ymax=max(f.y/-f.z for f in fr)
    u=math_(ng,'DIVIDE',math_(ng,'SUBTRACT',math_(ng,'DIVIDE',xyz.outputs['X'],z),xmin),xmax-xmin)
    vv=math_(ng,'DIVIDE',math_(ng,'SUBTRACT',math_(ng,'DIVIDE',xyz.outputs['Y'],z),ymin),ymax-ymin)
    uv=node(ng,'ShaderNodeCombineXYZ',name+' projection');ng.links.new(u,uv.inputs[0]);ng.links.new(vv,uv.inputs[1])
    im=bpy.data.images.load(str(OUT/(name+'-albedo.png')),check_existing=True);im.pack();images.append(im)
    tex=node(ng,'ShaderNodeTexImage',name+' · albédo GPT');tex.image=im;tex.extension='EXTEND';ng.links.new(uv.outputs[0],tex.inputs[0])
    di=bpy.data.images.load(str(OUT/(name+'-depth.exr')),check_existing=True);di.colorspace_settings.name='Non-Color';di.pack();images.append(di)
    dep=node(ng,'ShaderNodeTexImage',name+' · visibilité');dep.image=di;dep.extension='EXTEND';dep.interpolation='Closest';ng.links.new(uv.outputs[0],dep.inputs[0])
    diff=math_(ng,'ABSOLUTE',math_(ng,'SUBTRACT',z,dep.outputs['Color']))
    tolerance=math_(ng,'ADD',.025,math_(ng,'MULTIPLY',z,.004))
    mask=math_(ng,'LESS_THAN',diff,tolerance,name+' masque profondeur')
    mask=math_(ng,'MULTIPLY',mask,math_(ng,'GREATER_THAN',z,.01))
    edge=math_(ng,'MINIMUM',math_(ng,'MINIMUM',u,math_(ng,'SUBTRACT',1,u)),math_(ng,'MINIMUM',vv,math_(ng,'SUBTRACT',1,vv)))
    fade=math_(ng,'MINIMUM',math_(ng,'MAXIMUM',math_(ng,'MULTIPLY',edge,16),0),1,name+' fondu de bord')
    mask=math_(ng,'MULTIPLY',mask,fade)
    rawmask=mask
    protection=bpy.data.images.load(str(OUT/(name+'-protection.png')),check_existing=True);protection.colorspace_settings.name='Non-Color';protection.pack();images.append(protection)
    pt=node(ng,'ShaderNodeTexImage',name+' · protection des contours');pt.image=protection;pt.extension='EXTEND';ng.links.new(uv.outputs[0],pt.inputs[0])
    mask=math_(ng,'MULTIPLY',mask,pt.outputs['Color'],name+' protection des détails géométriques')
    towards=vec(ng,'NORMALIZE',vec(ng,'SUBTRACT',tuple(mat.translation),pos.outputs['Vector']))
    angle=math_(ng,'POWER',math_(ng,'ABSOLUTE',vec(ng,'DOT_PRODUCT',normal,towards)),4,name+' angle de vue')
    rawweights.append(math_(ng,'MULTIPLY',rawmask,angle,name+' poids avant protection'))
    weight=math_(ng,'MULTIPLY',mask,angle,name+' poids final');weights.append(weight);colors.append(scale(ng,tex.outputs['Color'],weight));masks.append(math_(ng,'GREATER_THAN',weight,.015))
sumw=weights[0];sumc=colors[0];count=masks[0];maximum=weights[0]
for w,c,m in zip(weights[1:],colors[1:],masks[1:]):
    sumw=math_(ng,'ADD',sumw,w);sumc=vec(ng,'ADD',sumc,c);count=math_(ng,'ADD',count,m);maximum=math_(ng,'MAXIMUM',maximum,w)
result=scale(ng,sumc,math_(ng,'DIVIDE',1,math_(ng,'MAXIMUM',sumw,.00001)),'Mélange normalisé des couleurs')
sumraw=rawweights[0]
for w in rawweights[1:]:sumraw=math_(ng,'ADD',sumraw,w)
coverage=math_(ng,'MINIMUM',math_(ng,'DIVIDE',sumw,math_(ng,'MAXIMUM',sumraw,.00001)),1,'Couverture protégée');overlap=math_(ng,'GREATER_THAN',count,1.5,'Raccords multi-projections')
go=node(ng,'NodeGroupOutput','Albédos uniquement');ng.links.new(result,go.inputs['Color']);ng.links.new(coverage,go.inputs['Coverage']);ng.links.new(overlap,go.inputs['Overlap'])

eligible_prefixes=('Coque ·','Chants ·','Panneaux ·','Sol ·','Siège ·','Porte ·','Abat-jour ·')
materials=[m for m in bpy.data.materials if m.name.startswith(eligible_prefixes)]
eligible=set(materials)
# A small geometry-node modifier stores evaluated local positions using frozen object matrices.
# No modifier custom-property inputs: Blender 5.2 node modifiers may not support legacy idprops.
coords=bpy.data.node_groups.new('GPT · Rest coordinates template','GeometryNodeTree')
coords.interface.new_socket(name='Geometry',in_out='INPUT',socket_type='NodeSocketGeometry');coords.interface.new_socket(name='Geometry',in_out='OUTPUT',socket_type='NodeSocketGeometry')
gi=node(coords,'NodeGroupInput','Entrée');gout=node(coords,'NodeGroupOutput','Sortie');ip=node(coords,'GeometryNodeInputPosition','Position locale évaluée');ino=node(coords,'GeometryNodeInputNormal','Normale locale évaluée')
pw=transform(coords,ip.outputs['Position'],Matrix.Identity(4),'RestPosition')
nw=transform(coords,ino.outputs['Normal'],Matrix.Identity(4),'RestNormal',False)
sn=node(coords,'GeometryNodeStoreNamedAttribute','Enregistrer la position');sn.data_type='FLOAT_VECTOR';sn.domain='POINT';sn.inputs['Name'].default_value='GPT_RestWorld';coords.links.new(gi.outputs['Geometry'],sn.inputs['Geometry']);coords.links.new(pw,sn.inputs['Value'])
nn=node(coords,'GeometryNodeStoreNamedAttribute','Enregistrer la normale');nn.data_type='FLOAT_VECTOR';nn.domain='CORNER';nn.inputs['Name'].default_value='GPT_RestNormal';coords.links.new(sn.outputs['Geometry'],nn.inputs['Geometry']);coords.links.new(nw,nn.inputs['Value']);coords.links.new(nn.outputs['Geometry'],gout.inputs['Geometry'])
target_objects=[]
for o in sc.objects:
    if o.type!='MESH' or not any(s.material in eligible for s in o.material_slots):continue
    target_objects.append(o);g=coords.copy();g.name='GPT · coordonnées figées · '+o.name
    m=o.matrix_world.copy();nm=m.inverted().transposed()
    for i,a in enumerate('XYZ'):
        g.nodes['RestPosition Row '+a].inputs[1].default_value=tuple(m[i][:3]);g.nodes['RestNormal Row '+a].inputs[1].default_value=tuple(nm[i][:3])
    g.nodes['RestPosition Offset'].inputs[1].default_value=tuple(m.translation)
    mod=o.modifiers.new('GPT · coordonnées locales après chanfreins','NODES');mod.node_group=g

for m in materials:
    nt=m.node_tree;bs=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED');old=bs.inputs['Base Color'].links[0].from_socket if bs.inputs['Base Color'].is_linked else None
    group=node(nt,'ShaderNodeGroup','GPT · projections albédo');group.node_tree=ng
    mix=node(nt,'ShaderNodeMixRGB','Couleur locale / albédo projeté');nt.links.new(group.outputs['Coverage'],mix.inputs[0])
    if old:nt.links.new(old,mix.inputs[1])
    else:mix.inputs[1].default_value=bs.inputs['Base Color'].default_value
    nt.links.new(group.outputs['Color'],mix.inputs[2]);nt.links.new(mix.outputs[0],bs.inputs['Base Color'])
    for socket in ['Roughness','Normal']:
        for l in list(bs.inputs[socket].links):nt.links.remove(l)
    floor=m.name.startswith('Sol ·');seat=m.name.startswith('Siège ·')
    rough=node(nt,'ShaderNodeValToRGB','Réponse physique — rugosité des marques')
    lo,hi=(.23,.105) if floor else ((.61,.48) if seat else (.43,.28))
    rough.color_ramp.elements[0].position=.08;rough.color_ramp.elements[0].color=(lo,lo,lo,1);rough.color_ramp.elements[1].position=.70;rough.color_ramp.elements[1].color=(hi,hi,hi,1)
    nt.links.new(mix.outputs[0],rough.inputs[0]);nt.links.new(rough.outputs[0],bs.inputs['Roughness'])
    bs.inputs['Coat Weight'].default_value=.42 if floor else .12;bs.inputs['Coat Roughness'].default_value=.11 if floor else .24
    bump=node(nt,'ShaderNodeBump','Microrelief fin dérivé des marques');bump.inputs['Strength'].default_value=.12;bump.inputs['Distance'].default_value=.00028 if floor else .00018
    nt.links.new(mix.outputs[0],bump.inputs['Height']);nt.links.new(bump.outputs[0],bs.inputs['Normal'])
    m['GPT_albedo_only']=True;m['projection_note']='Six views blended by visibility and angle. True Principled shading; no photographic emission.'

# Motivated material/light matching to the GPT beauty reference; no texture-based light pools.
chrome=bpy.data.materials.get('Aluminium brossé')
if chrome:chrome.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value=.23
for o in sc.objects:
    if o.type!='LIGHT':continue
    if 'Oculus' in o.name:o.data.energy=180
    elif 'Remplissage' in o.name:o.data.energy=85
    elif 'Rebond' in o.name:o.data.energy*=.8
    elif 'Plafonnier' in o.name:o.data.energy=32;o.data.color=(1,.82,.61);o.visible_glossy=True
    elif 'Éclairage arrière' in o.name:
        o.data.energy=75;o.data.color=(1,.80,.57);o.data.shape='RECTANGLE';o.data.size=1.45;o.data.size_y=.14;o.visible_glossy=True
sc.camera=bpy.data.objects['CAM_ARRIERE_OBLIQUE'];sc.view_settings.view_transform='AgX';sc.view_settings.look='AgX - Medium High Contrast';sc.view_settings.exposure=-.85
sc.cycles.samples=64;sc.cycles.use_denoising=True;sc.render.use_persistent_data=True
sc.render.resolution_x=1456;sc.render.resolution_y=816;sc.render.resolution_percentage=100
try:
    p=bpy.context.preferences.addons['cycles'].preferences;p.compute_device_type='OPTIX';p.get_devices()
    for dev in p.devices:dev.use=dev.type!='CPU'
    sc.cycles.device='GPU'
except Exception as e:print(e)

# Editable inspection path, a small circular move and a complete look around.
data=bpy.data.cameras.new('CAM_TRAJET_INSPECTION');path=bpy.data.objects.new(data.name,data);sc.collection.objects.link(path);data.lens=17
for i in range(9):
    a=i*math.tau/8;path.location=(.35*math.sin(a),.35*math.cos(a),1.6);path.rotation_euler=(math.radians(86),0,-a)
    path.keyframe_insert(data_path='location',frame=1+30*i);path.keyframe_insert(data_path='rotation_euler',frame=1+30*i)
sc.frame_start=1;sc.frame_end=241;sc.frame_set(1);bpy.context.view_layer.update()

# Verify evaluated coordinates really follow the parent independently of camera/world movement.
dg=bpy.context.evaluated_depsgraph_get();root=bpy.data.objects['M_ARR_CONSOLE_COMMUNICATIONS'];sample=next(o for o in root.children if o in target_objects)
def sampled():
    ev=sample.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();vals=[tuple(x.vector) for x in me.attributes['GPT_RestWorld'].data];ev.to_mesh_clear();return vals
prior=sampled();oldloc=root.location.copy();oldrot=root.rotation_euler.copy();mats={o:o.matrix_world.copy() for o in sc.objects};delta=Vector((.18,.21,.04))
root.location+=delta;bpy.context.view_layer.update();stable=sampled()==prior
follows=all(((o.matrix_world.translation-mats[o].translation)-delta).length<1e-4 for o in root.children)
neighbors=all((o.matrix_world.translation-mats[o].translation).length<1e-5 for o in sc.objects if o!=root and o not in root.children)
root.rotation_euler.z+=.2;bpy.context.view_layer.update();rotation_stable=sampled()==prior
root.location=oldloc;root.rotation_euler=oldrot;bpy.context.view_layer.update()
checks={'geometry_and_parents_preserved':before==digest(),'module_moves_with_children':follows,'neighbors_unchanged':neighbors,'projection_stable_on_translation':stable,'projection_stable_on_rotation':rotation_stable,'all_generated_maps_packed':all(im.packed_file for im in images),'projected_materials_are_principled':all(any(n.type=='BSDF_PRINCIPLED' and n.inputs['Base Color'].is_linked for n in m.node_tree.nodes) for m in materials),'glass_not_projected':not any(m.name.startswith('Vitrage') for m in materials)}
assert all(checks.values()),checks
report={'checks':checks,'views':len(views),'projected_objects':len(target_objects),'materials':[m.name for m in materials],'geometry_before':before,'geometry_after':digest(),'method':'Albedo base-color only, depth visibility, angle^4 weights and border feather. Constant rest coordinates after bevels. Original shaders for glass/screens/metal/instruments.','limitations':'Generated albedo is an approximation; fine residual shading and misaligned painted details may remain. Hidden geometry keeps original V2 colors.'}
(OUT/'validation.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
sc['workflow']='Six GPT albedo projections; physical shading; depth/angle feather stitches; materials editable.'
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':area.spaces.active.region_3d.view_perspective='CAMERA';area.spaces.active.shading.type='MATERIAL'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'cockpit-albedo-multivues.blend'))
if '--no-render' not in sys.argv:
    sc.render.resolution_percentage=75 if '--preview' in sys.argv else 100
    for name,f in [('CAM_ARRIERE_OBLIQUE','arriere-oblique-relit'),('CAM_PHOTO','avant-relit'),('CAM_RACCORD_GAUCHE','raccord-relit')]:
        sc.camera=bpy.data.objects[name];sc.render.filepath=str(OUT/(f+'.png'));bpy.ops.render.render(write_still=True)
print('MULTIVIEW_ALBEDO_DONE',json.dumps(checks),flush=True)
