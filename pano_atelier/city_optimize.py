"""Batch a city by movable building; preserve local material and projection data.

Explicit geometry consolidation, undoable from the add-on. No asset is edited.
"""
import bpy,hashlib,time
from collections import defaultdict
from mathutils import Matrix


def building_root(o):
    p=o.parent
    while p:
        if p.type=='EMPTY' and p.name.startswith(('A1 ·','BG ·','EXT ·','VOIRIE ·','MOBILIER ·','VEHICULE ·')):return p
        p=p.parent
    return None


def metrics(scene):
    dg=bpy.context.evaluated_depsgraph_get();unique={};evaluated=0
    for o in scene.objects:
        if o.type!='MESH':continue
        unique[o.data.as_pointer()]=sum(len(p.vertices)-2 for p in o.data.polygons)
        e=o.evaluated_get(dg);evaluated+=sum(len(p.vertices)-2 for p in e.data.polygons)
    return {'objects':len(scene.objects),'meshes':sum(o.type=='MESH' for o in scene.objects),'unique_triangles':sum(unique.values()),'evaluated_triangles':evaluated}


def freeze_coordinates(o,root):
    me=o.data
    if me.users>1:o.data=me=me.copy()
    coords=[c for v in me.vertices for c in v.co]
    if 'PA_SourceLocal' not in me.attributes:
        me.attributes.new('PA_SourceLocal','FLOAT_VECTOR','POINT').data.foreach_set('vector',coords)
    if 'PA_BuildingLocal' not in me.attributes:
        mx=root.matrix_world.inverted()@o.matrix_world
        me.attributes.new('PA_BuildingLocal','FLOAT_VECTOR','POINT').data.foreach_set('vector',[c for v in me.vertices for c in mx@v.co])
    if 'PA_SourceSeed' not in me.attributes:
        seed=int(hashlib.sha256(o.name.encode()).hexdigest()[:8],16)/4294967295
        me.attributes.new('PA_SourceSeed','FLOAT','POINT').data.foreach_set('value',[seed]*len(me.vertices))


def material_coordinates(materials):
    for m in materials:
        if not m or not m.node_tree or m.get('pa_batched_coordinates'):continue
        nt=m.node_tree
        for n in list(nt.nodes):
            if n.type=='TEX_COORD' and n.object is None:
                links=list(n.outputs['Object'].links)
                if links:
                    a=nt.nodes.new('ShaderNodeAttribute');a.attribute_name='PA_SourceLocal';a.label='Coordonnees locales preservees avant regroupement'
                    for l in links:nt.links.new(a.outputs['Vector'],l.to_socket)
            elif n.type=='OBJECT_INFO':
                links=list(n.outputs['Random'].links)
                if links:
                    a=nt.nodes.new('ShaderNodeAttribute');a.attribute_name='PA_SourceSeed';a.label='Variation conservee par piece'
                    for l in links:nt.links.new(a.outputs['Fac'],l.to_socket)
        m['pa_batched_coordinates']=True


def optimize(scene):
    if scene.get('pa_city_optimized'):raise ValueError('Cette ville est deja regroupee.')
    started=time.perf_counter();before=metrics(scene);groups=defaultdict(list);materials=set()
    candidates=[o for o in scene.objects if o.type in ('MESH','CURVE') and building_root(o) and not (o.get('pa_asset_instance') and not o.modifiers and len(o.parent.children)==1)]
    # Distant frame bevels do not contribute to the silhouette. Near masonry keeps one segment.
    for o in candidates:
        root=building_root(o)
        for mod in list(o.modifiers):
            if mod.type=='BEVEL':
                if root.name.startswith(('BG ·','EXT ·')) or mod.width<.022:o.modifiers.remove(mod)
                else:mod.segments=1
            elif mod.type=='WEIGHTED_NORMAL':o.modifiers.remove(mod)
        if o.type=='MESH':freeze_coordinates(o,root)
        materials.update(s.material for s in o.material_slots if s.material and s.material.name.startswith('VILLE'))
    bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get()
    for i,o in enumerate(candidates):
        root=building_root(o);mw=o.matrix_world.copy();slots=[s.material for s in o.material_slots]
        if o.modifiers or o.type=='CURVE':
            me=bpy.data.meshes.new_from_object(o.evaluated_get(dg),preserve_all_data_layers=True,depsgraph=dg)
            if o.type=='CURVE':
                n=bpy.data.objects.new(o.name+' · mesh',me);o.users_collection[0].objects.link(n);n.parent=root;n.matrix_world=mw
                for k in o.keys():n[k]=o[k]
                bpy.data.objects.remove(o,do_unlink=True);o=n
            else:o.modifiers.clear();o.data=me
            freeze_coordinates(o,root)
        # Convert object-slot overrides into real slots before joining.
        for j,m in enumerate(slots):
            if j<len(o.material_slots):o.material_slots[j].link='DATA';o.data.materials[j]=m
        o.parent=root;o.matrix_world=mw
        groups[(root,bool(o.get('pa_city_project')))].append(o)
        if i%1000==0:print('OPT_EVALUATE',i,len(candidates),flush=True)
    material_coordinates(materials)
    bpy.ops.object.select_all(action='DESELECT')
    for (root,project),obs in groups.items():
        print('OPT_JOIN',root.name,project,len(obs),flush=True)
        for o in obs:o.hide_select=False;o.select_set(True)
        active=obs[0];bpy.context.view_layer.objects.active=active
        if len(obs)>1:bpy.ops.object.join()
        # Rebase the actual mesh; rest attributes are intentionally not transformed.
        matrix=root.matrix_world.inverted()@active.matrix_world;active.data.transform(matrix);active.matrix_world=root.matrix_world.copy();active.parent=root
        active.name=root.name+(' · beton projete' if project else ' · structure et details');active['pa_city_project']=project;active['pa_batched']=True;active['pa_source_objects']=len(obs)
        active.select_set(False)
    for o in list(scene.objects):
        if o.type=='EMPTY' and o.name.startswith('Etage ') and not o.children:bpy.data.objects.remove(o,do_unlink=True)
    scene['pa_city_optimized']=True;bpy.context.view_layer.update()
    return {'before':before,'after':metrics(scene),'seconds':time.perf_counter()-started,'groups':len(groups),'coordinates':'PA_SourceLocal / PA_SourceSeed / PA_BuildingLocal; projection rest attributes preserved','mobility':'One parent per building; material-separated geometry inside each building'}
