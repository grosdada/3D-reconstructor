"""Six GPT albedo projections on the approved tower; physical shading, local frozen coordinates."""
import bpy,bmesh,json,hashlib,sys,math
from pathlib import Path
from mathutils import Vector,Matrix
ROOT=Path(__file__).parent;OUT=ROOT/'output/tour-belvedere-v2'
bpy.ops.wm.open_mainfile(filepath=str(OUT/'base-projections.blend'))
sc=bpy.context.scene;sc.name='Tour belvedere · albedos GPT multivues · V2'
views=json.loads((OUT/'views.json').read_text())
def fingerprint():
    return hashlib.sha256(str([(o.name,o.type,o.parent.name if o.parent else None,list(map(tuple,o.matrix_world)),[tuple(v.co) for v in o.data.vertices] if o.type=='MESH' else None,[tuple(sorted(p.vertices)) for p in o.data.polygons] if o.type=='MESH' else None) for o in sorted(sc.objects,key=lambda x:x.name) if o.type not in {'CAMERA','LIGHT'}]).encode()).hexdigest()
before=fingerprint()
# Correct reversed winding in the original box primitive; no vertex, face membership,
# dimensions or hierarchy changes. This lets front-facing projection work correctly.
normal_fixes=[]
for obj in sc.objects:
    if obj.type!='MESH' or len(obj.data.vertices)!=8 or len(obj.data.polygons)!=6:continue
    bm=bmesh.new();bm.from_mesh(obj.data)
    if bm.calc_volume(signed=True)<0:
        bmesh.ops.reverse_faces(bm,faces=list(bm.faces));bm.to_mesh(obj.data);normal_fixes.append(obj.name)
    bm.free()
bpy.context.view_layer.update()
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
    tolerance=math_(ng,'ADD',.05,math_(ng,'MULTIPLY',z,.0015))
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
    angle=math_(ng,'POWER',math_(ng,'MAXIMUM',vec(ng,'DOT_PRODUCT',normal,towards),0),8,name+' angle de vue')
    angle=math_(ng,'MULTIPLY',angle,v.get('priority',1),name+' priorite detail')
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

eligible_prefixes=('Beton ·','Couverture ·','Batiments ·','Etancheite ·','Menuiseries ·','Trottoirs ·','Voirie ·')
materials=[m for m in bpy.data.materials if m.name.startswith(eligible_prefixes)]
eligible=set(materials)
# Curve-based mullions have no rest-coordinate modifier. Keep their physical material.
curve_materials={}
for obj in sc.objects:
    if obj.type!='CURVE':continue
    for slot in obj.material_slots:
        if slot.material in eligible:
            source=slot.material
            if source not in curve_materials:
                curve_materials[source]=source.copy();curve_materials[source].name=source.name+' · courbes physiques'
            slot.material=curve_materials[source]
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
    nt=m.node_tree;bs=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED')
    old=tuple(bs.inputs['Base Color'].default_value)
    group=node(nt,'ShaderNodeGroup','GPT · projections albedo tour');group.node_tree=ng
    mix=node(nt,'ShaderNodeMixRGB','Materiau initial / patine GPT')
    nt.links.new(group.outputs['Coverage'],mix.inputs[0]);mix.inputs[1].default_value=old
    nt.links.new(group.outputs['Color'],mix.inputs[2]);nt.links.new(mix.outputs[0],bs.inputs['Base Color'])
    # Gentle physical response: tonal patina modulates roughness, not displacement.
    ramp=node(nt,'ShaderNodeValToRGB','Rugosite physique de la peinture')
    road=m.name.startswith(('Voirie','Trottoirs','Etancheite'))
    trim=m.name.startswith('Menuiseries')
    lo,hi=(.98,.83) if road else ((.72,.46) if trim else (.91,.66))
    ramp.color_ramp.elements[0].position=.10;ramp.color_ramp.elements[0].color=(lo,lo,lo,1)
    ramp.color_ramp.elements[1].position=.76;ramp.color_ramp.elements[1].color=(hi,hi,hi,1)
    nt.links.new(mix.outputs[0],ramp.inputs[0]);nt.links.new(ramp.outputs[0],bs.inputs['Roughness'])
    bs.inputs['Metallic'].default_value=.12 if trim else 0
    bs.inputs['Coat Weight'].default_value=0
    m['GPT_albedo_only']=True;m['note']='No photographic emission. Rest-coordinate front projection with depth, front-facing incidence and semantic guards.'

# Validate frozen coordinates after both translation and rotation of a complete module.
root=bpy.data.objects['BATIMENT · aile principale'];sample=next(o for o in root.children_recursive if o in target_objects)
def sampled():
    ev=sample.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh()
    value=[tuple(v.vector) for v in me.attributes['GPT_RestWorld'].data];ev.to_mesh_clear();return value
prior=sampled();orig=root.location.copy();rot=root.rotation_euler.copy()
before_m={o:o.matrix_world.copy() for o in sc.objects};delta=Vector((2,1,.3));family=set(root.children_recursive)
root.location+=delta;bpy.context.view_layer.update();translation_ok=sampled()==prior
children_ok=all((o.matrix_world.translation-before_m[o].translation-delta).length<1e-4 for o in family)
neighbors_ok=all((o.matrix_world.translation-before_m[o].translation).length<1e-5 for o in sc.objects if o not in family and o!=root)
root.rotation_euler.z+=.24;bpy.context.view_layer.update();rotation_ok=sampled()==prior
root.location=orig;root.rotation_euler=rot;bpy.context.view_layer.update()
checks={'approved_geometry_and_parents_preserved':before==fingerprint(),'texture_coordinates_stable_on_translation':translation_ok,'texture_coordinates_stable_on_rotation':rotation_ok,'module_children_follow':children_ok,'neighbors_unchanged':neighbors_ok,'all_projection_maps_packed':all(im.packed_file for im in images),'glass_excluded':not any(m.name.startswith('Vitrages') for m in materials),'botaniq_materials_excluded':not any('Leaf' in m.name or 'Bark' in m.name for m in materials)}
assert all(checks.values()),checks
sc.camera=bpy.data.objects['CAM_01 · reference portrait'];sc.cycles.samples=64;sc.cycles.use_denoising=True
sc.render.resolution_x=1000;sc.render.resolution_y=1200;sc.render.resolution_percentage=100
sc.view_settings.view_transform='AgX';sc.view_settings.look='AgX - Medium High Contrast';sc.view_settings.exposure=0
sc.render.use_persistent_data=True
p=bpy.context.preferences.addons['cycles'].preferences;p.compute_device_type='OPTIX';p.get_devices()
for d in p.devices:d.use=d.type!='CPU'
sc.cycles.device='GPU'
sc['phase']='02 · albedos GPT projetes; geometrie approuvee conservee'
report={'checks':checks,'geometry_before':before,'geometry_after':fingerprint(),'geometry_comparison':'Vertex coordinates, face vertex membership, object transforms and parents. Face winding explicitly excluded to permit normal correction.','normal_orientation_corrected_objects':normal_fixes,'views':len(views),'projected_objects':len(target_objects),'projected_materials':[m.name for m in materials],'method':'Six generated albedo images -> Principled Base Color, front-facing angle weighting, depth visibility, border fade, semantic edge guards; frozen evaluated coordinates per object. Close facade view has priority 8.','limitations':['Generated albedos can retain slight shading and imperfectly aligned paint details.','Uncovered or protected surfaces retain original material colors.','Projection is object-attached; UV baking for export is not included in this version.']}
(OUT/'validation-projection.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf8')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'tour-belvedere-albedo-v2.blend'))
print('TOUR_ALBEDO_SAVED',json.dumps(checks),flush=True)
if '--no-render' not in sys.argv:
    sc.render.filepath=str(OUT/'01-reference.png');bpy.ops.render.render(write_still=True)
print('TOUR_ALBEDO_DONE',flush=True)
