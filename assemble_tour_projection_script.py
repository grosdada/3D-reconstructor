"""Reuse the proven projection node implementation, generating a standalone tower script."""
from pathlib import Path
root=Path(__file__).parent
src=(root/'build_albedo_multiview.py').read_text(encoding='utf8')
helpers=src[src.index('def node('):src.index('eligible_prefixes=')]
helpers=helpers.replace("math_(ng,'ABSOLUTE',vec(ng,'DOT_PRODUCT',normal,towards))","math_(ng,'MAXIMUM',vec(ng,'DOT_PRODUCT',normal,towards),0)")
helpers=helpers.replace(".025,math_(ng,'MULTIPLY',z,.004)",".05,math_(ng,'MULTIPLY',z,.0015)")
helpers=helpers.replace(",4,name+' angle de vue'",",8,name+' angle de vue'")
helpers=helpers.replace("rawweights.append(math_(ng,'MULTIPLY',rawmask,angle,name+' poids avant protection'))","angle=math_(ng,'MULTIPLY',angle,v.get('priority',1),name+' priorite detail')\n    rawweights.append(math_(ng,'MULTIPLY',rawmask,angle,name+' poids avant protection'))")
coords=src[src.index('# A small geometry-node'):src.index('for m in materials:')]
header='''"""Six GPT albedo projections on the approved tower; physical shading, local frozen coordinates."""
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
'''
selection='''eligible_prefixes=('Beton ·','Couverture ·','Batiments ·','Etancheite ·','Menuiseries ·','Trottoirs ·','Voirie ·')
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
'''
tail='''
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
'''
(root/'build_tour_albedo.py').write_text(header+helpers+selection+coords+tail,encoding='utf8')
print('STANDALONE_TOUR_SCRIPT_READY')
