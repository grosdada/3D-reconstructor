"""Single-view GPT photographic plate, perspective-correct local projection with depth visibility."""
import bpy,json,hashlib,math
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'output/cockpit-projection-gpt-test'
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'output/cockpit-photo-modulaire-v2/cockpit-patine-360.blend'))
sc=bpy.context.scene;sc.name='TEST — photographie GPT reprojetée sur V2'
cam=bpy.data.objects['CAM_ARRIERE_OBLIQUE'];sc.camera=cam
sc.render.resolution_x=1456;sc.render.resolution_y=816;sc.render.resolution_percentage=100
sc.render.use_persistent_data=True
def digest():
    h=hashlib.sha256()
    for o in sorted(sc.objects,key=lambda o:o.name):
        if o.type=='MESH':h.update(str((o.name,o.parent.name if o.parent else None,list(map(tuple,o.matrix_world)),[tuple(v.co) for v in o.data.vertices],[tuple(p.vertices) for p in o.data.polygons])).encode())
    return h.hexdigest()
before=digest()
def node(nt,typ,label):
    n=nt.nodes.new(typ);n.name=n.label=label;return n
def math_(nt,op,a,b,label):
    n=node(nt,'ShaderNodeMath',label);n.operation=op
    for i,x in enumerate([a,b]):
        if isinstance(x,(int,float)):n.inputs[i].default_value=x
        else:nt.links.new(x,n.inputs[i])
    return n.outputs[0]

# An opaque first-surface axial depth pass, including the glazing for this photographic experiment.
depthmat=bpy.data.materials.new('TEST · profondeur caméra axiale');depthmat.use_nodes=True
nt=depthmat.node_tree;nt.nodes.clear()
tc=node(nt,'ShaderNodeTexCoord','Coordonnées caméra');tc.object=cam
xyz=node(nt,'ShaderNodeSeparateXYZ','Axes caméra');nt.links.new(tc.outputs['Object'],xyz.inputs[0])
dep=math_(nt,'MULTIPLY',xyz.outputs['Z'],-1,'Distance axiale')
em=node(nt,'ShaderNodeEmission','Profondeur linéaire');nt.links.new(dep,em.inputs['Color'])
out=node(nt,'ShaderNodeOutputMaterial','Sortie');nt.links.new(em.outputs[0],out.inputs['Surface'])
sc.view_layers[0].material_override=depthmat
sc.cycles.device='CPU';sc.cycles.samples=1;sc.cycles.use_denoising=False
sc.render.filter_size=.01
sc.render.image_settings.file_format='OPEN_EXR';sc.render.image_settings.color_depth='32';sc.render.image_settings.color_mode='RGBA'
sc.render.filepath=str(OUT/'projecteur-profondeur.exr')
bpy.ops.render.render(write_still=True)
sc.view_layers[0].material_override=None
depth=bpy.data.images.load(str(OUT/'projecteur-profondeur.exr'),check_existing=True);depth.colorspace_settings.name='Non-Color';depth.pack()
plate=bpy.data.images.load(str(OUT/'gpt-photo-globale.png'),check_existing=True);plate.pack()

# Homogeneous coordinates are stored per vertex, not divided UVs: perspective remains exact on large polygons.
# Rest coordinates and their depth mask follow each movable mesh and are unaffected by later camera movement.
inv=cam.matrix_world.inverted();attrname='GPT_ProjectorRest'
for o in sc.objects:
    if o.type!='MESH':continue
    if o.data.users>1:o.data=o.data.copy()
    at=o.data.attributes.get(attrname) or o.data.attributes.new(attrname,'FLOAT_VECTOR','POINT')
    values=[]
    for v in o.data.vertices:values.extend(inv@(o.matrix_world@v.co))
    at.data.foreach_set('vector',values)

# Recompute the same rest-camera attribute AFTER bevel/solidify. Interpolated pre-modifier
# attributes may otherwise produce thin unprojected rims on newly created bevel vertices.
# Constant object-to-projector matrices keep the texture attached when a module moves.
restgroup=bpy.data.node_groups.new('GPT · coordonnées après chanfreins','GeometryNodeTree')
restgroup.interface.new_socket(name='Geometry',in_out='INPUT',socket_type='NodeSocketGeometry')
restgroup.interface.new_socket(name='Geometry',in_out='OUTPUT',socket_type='NodeSocketGeometry')
sockets={name:restgroup.interface.new_socket(name=name,in_out='INPUT',socket_type='NodeSocketVector') for name in ['Row X','Row Y','Row Z','Offset']}
gi=node(restgroup,'NodeGroupInput','Géométrie et matrice figée');go_rest=node(restgroup,'NodeGroupOutput','Géométrie inchangée')
pos=node(restgroup,'GeometryNodeInputPosition','Position finale locale')
comb=node(restgroup,'ShaderNodeCombineXYZ','Rotation et échelle vers caméra')
for axis,name in zip(['X','Y','Z'],['Row X','Row Y','Row Z']):
    dot=node(restgroup,'ShaderNodeVectorMath',name);dot.operation='DOT_PRODUCT';restgroup.links.new(pos.outputs['Position'],dot.inputs[0]);restgroup.links.new(gi.outputs[name],dot.inputs[1]);restgroup.links.new(dot.outputs['Value'],comb.inputs[axis])
add=node(restgroup,'ShaderNodeVectorMath','Translation vers caméra');add.operation='ADD';restgroup.links.new(comb.outputs[0],add.inputs[0]);restgroup.links.new(gi.outputs['Offset'],add.inputs[1])
store=node(restgroup,'GeometryNodeStoreNamedAttribute','Coordonnées exactes des surfaces évaluées');store.data_type='FLOAT_VECTOR';store.domain='POINT';store.inputs['Name'].default_value=attrname
restgroup.links.new(gi.outputs['Geometry'],store.inputs['Geometry']);restgroup.links.new(add.outputs['Vector'],store.inputs['Value']);restgroup.links.new(store.outputs['Geometry'],go_rest.inputs['Geometry'])
for o in sc.objects:
    if o.type!='MESH':continue
    m=inv@o.matrix_world;mod=o.modifiers.new('GPT · coordonnées locales finales','NODES');mod.node_group=restgroup
    for i,name in enumerate(['Row X','Row Y','Row Z']):mod[sockets[name].identifier]=tuple(m[i][:3])
    mod[sockets['Offset'].identifier]=tuple(m.translation)
bpy.context.view_layer.update()

frame=cam.data.view_frame(scene=sc)
xmin=min(v.x/-v.z for v in frame);xmax=max(v.x/-v.z for v in frame)
ymin=min(v.y/-v.z for v in frame);ymax=max(v.y/-v.z for v in frame)
ng=bpy.data.node_groups.new('GPT · projection photographique locale','ShaderNodeTree')
ng.interface.new_socket(name='Photographie',in_out='OUTPUT',socket_type='NodeSocketColor')
ng.interface.new_socket(name='Masque visible',in_out='OUTPUT',socket_type='NodeSocketFloat')
at=node(ng,'ShaderNodeAttribute','Coordonnées figées sur le maillage');at.attribute_name=attrname
xyz=node(ng,'ShaderNodeSeparateXYZ','XYZ caméra source');ng.links.new(at.outputs['Vector'],xyz.inputs[0])
z=math_(ng,'MULTIPLY',xyz.outputs['Z'],-1,'Profondeur positive')
u=math_(ng,'DIVIDE',math_(ng,'SUBTRACT',math_(ng,'DIVIDE',xyz.outputs['X'],z,'x/z'),xmin,'x cadré'),xmax-xmin,'U projectif')
v=math_(ng,'DIVIDE',math_(ng,'SUBTRACT',math_(ng,'DIVIDE',xyz.outputs['Y'],z,'y/z'),ymin,'y cadré'),ymax-ymin,'V projectif')
uv=node(ng,'ShaderNodeCombineXYZ','Coordonnées image');ng.links.new(u,uv.inputs['X']);ng.links.new(v,uv.inputs['Y'])
tex=node(ng,'ShaderNodeTexImage','Image GPT globale');tex.image=plate;tex.extension='EXTEND';ng.links.new(uv.outputs[0],tex.inputs[0])
dt=node(ng,'ShaderNodeTexImage','Première surface vue par le projecteur');dt.image=depth;dt.extension='EXTEND';dt.interpolation='Closest';ng.links.new(uv.outputs[0],dt.inputs[0])
diff=math_(ng,'ABSOLUTE',math_(ng,'SUBTRACT',z,dt.outputs['Color'],'Écart à la profondeur visible'),0,'Écart absolu')
mask=math_(ng,'LESS_THAN',diff,.055,'Visibilité — tolérance 5,5 cm aux chanfreins')
for condition in [math_(ng,'GREATER_THAN',z,.02,'Devant la caméra'),math_(ng,'GREATER_THAN',u,0,'U minimum'),math_(ng,'LESS_THAN',u,1,'U maximum'),math_(ng,'GREATER_THAN',v,0,'V minimum'),math_(ng,'LESS_THAN',v,1,'V maximum')]:
    mask=math_(ng,'MULTIPLY',mask,condition,'Masque cadrage')
strength=node(ng,'ShaderNodeValue','Intensité globale — propriété de scène');strength.outputs[0].default_value=1
sc['GPT_projection_mix']=1.0;sc.id_properties_ui('GPT_projection_mix').update(min=0,max=1,description='Projection photo; remettre AgX/exposition -0.85 pour examiner les matériaux V2 seuls.')
fc=strength.outputs[0].driver_add('default_value');d=fc.driver;var=d.variables.new();var.name='mix';var.type='SINGLE_PROP';var.targets[0].id_type='SCENE';var.targets[0].id=sc;var.targets[0].data_path='["GPT_projection_mix"]';d.expression='mix'
mask=math_(ng,'MULTIPLY',mask,strength.outputs[0],'Intensité projection')
go=node(ng,'NodeGroupOutput','Sortie projection');ng.links.new(tex.outputs['Color'],go.inputs['Photographie']);ng.links.new(mask,go.inputs['Masque visible'])

used={slot.material for o in sc.objects if o.type=='MESH' for slot in o.material_slots if slot.material}
for m in used:
    nt=m.node_tree
    if not nt:continue
    outputs=[n for n in nt.nodes if n.type=='OUTPUT_MATERIAL' and n.is_active_output]
    if not outputs:continue
    output=outputs[0]
    if not output.inputs['Surface'].is_linked:continue
    original=output.inputs['Surface'].links[0].from_socket
    group=node(nt,'ShaderNodeGroup','TEST GPT — coordonnées locales');group.node_tree=ng
    emission=node(nt,'ShaderNodeEmission','Photographie — lumière déjà intégrée');nt.links.new(group.outputs['Photographie'],emission.inputs['Color'])
    lp=node(nt,'ShaderNodeLightPath','Ne pas éclairer la pièce avec la photographie')
    fac=math_(nt,'MULTIPLY',group.outputs['Masque visible'],lp.outputs['Is Camera Ray'],'Projection sur rayons caméra uniquement')
    blend=node(nt,'ShaderNodeMixShader','Original V2 / photographie');nt.links.new(fac,blend.inputs[0]);nt.links.new(original,blend.inputs[1]);nt.links.new(emission.outputs[0],blend.inputs[2]);nt.links.new(blend.outputs[0],output.inputs['Surface'])

# Display-referred photo: Standard avoids applying AgX/exposure a second time to the generated lighting.
sc.view_settings.view_transform='Standard';sc.view_settings.look='None';sc.view_settings.exposure=0;sc.view_settings.gamma=1
sc.render.image_settings.file_format='PNG';sc.render.image_settings.color_depth='8';sc.render.image_settings.color_mode='RGB'
sc.render.filter_size=1;sc.cycles.samples=48;sc.cycles.use_denoising=True
try:
    p=bpy.context.preferences.addons['cycles'].preferences;p.compute_device_type='OPTIX';p.get_devices()
    for dev in p.devices:dev.use=dev.type!='CPU'
    sc.cycles.device='GPU'
except Exception as e:print(e)
shift=cam.copy();shift.data=cam.data.copy();shift.name='CAM_TEST_DECALAGE_15CM';sc.collection.objects.link(shift)
shift.location+=cam.matrix_world.to_3x3()@Vector((.15,0,0))
bpy.context.view_layer.update()

# Check real editability of a projected module, including stored coordinates.
root=bpy.data.objects['M_ARR_CONSOLE_COMMUNICATIONS'];old=root.location.copy();matrices={o:o.matrix_world.copy() for o in sc.objects}
attrhash=lambda:hashlib.sha256(str([(o.name,[tuple(x.vector) for x in o.data.attributes[attrname].data]) for o in root.children if o.type=='MESH']).encode()).hexdigest()
ah=attrhash();delta=Vector((.18,.21,.04));root.location+=delta;bpy.context.view_layer.update()
follows=all(((o.matrix_world.translation-matrices[o].translation)-delta).length<1e-4 for o in root.children)
neighbors=all((o.matrix_world.translation-matrices[o].translation).length<1e-5 for o in sc.objects if o!=root and o not in root.children)
stable=attrhash()==ah;root.location=old;bpy.context.view_layer.update()
after=digest()
checks={'geometry_transforms_parents_preserved':before==after,'module_moves_with_children':follows,'neighbors_unchanged':neighbors,'projection_coordinates_follow_module':stable,'plate_packed':bool(plate.packed_file),'visibility_depth_packed':bool(depth.packed_file)}
assert all(checks.values()),checks
report={'checks':checks,'geometry_before':before,'geometry_after':after,'source_camera':cam.name,'camera_matrix':list(map(list,cam.matrix_world)),'lens':cam.data.lens,'sensor_width':cam.data.sensor_width,'resolution':[1456,816],'plate_resolution':list(plate.size),'normalized_camera_frame':[xmin,xmax,ymin,ymax],'method':'Perspective-correct per-vertex rest-camera XYZ, per-fragment divide, depth visibility; camera-ray emission over original shaders','limits':['Single view. Hidden surfaces retain V2 materials.','Glazing receives the photographed appearance in this test, with baked transparency/reflections.','Generated silhouette changes cannot be repaired by reprojection.','Standard display for plate fidelity; original V2 used AgX exposure -0.85.']}
(OUT/'projection-report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
sc['projection_note']='Essai depuis CAM_ARRIERE_OBLIQUE. Une vue, lumière/reflets figés. Coordonnées et masque suivent chaque objet.'
sc.camera=cam
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':area.spaces.active.region_3d.view_perspective='CAMERA';area.spaces.active.shading.type='MATERIAL'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'cockpit-test-projection-gpt.blend'))
for camera,name in [(cam,'reprojection-camera'),(shift,'reprojection-decalage-15cm')]:
    sc.camera=camera;sc.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
print('PROJECTION_TEST_DONE',json.dumps(checks),flush=True)
