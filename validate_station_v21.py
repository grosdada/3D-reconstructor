import bpy,sys,json
from pathlib import Path
from mathutils import Vector
R=Path(__file__).parent;O=R/'output/station-sas-v2.1';sys.path.insert(0,str(R));import pano_atelier
bpy.ops.wm.open_mainfile(filepath=str(O/'station-sas-modulaire-texturee-v2.1.blend'));pano_atelier.register();sc=bpy.context.scene
tree=bpy.data.node_groups['PA · albedos multivues station'];mix=tree.nodes['Reparation masquee · source preservee']
assert mix.inputs[1].links[0].from_node.name=='avant albedo.png'
assert mix.inputs[0].links[0].from_node.image.colorspace_settings.name=='Non-Color'
assert tuple(mix.inputs[0].links[0].from_node.image.size)==(1254,1254)
assert tree.nodes['avant albedo.png'].inputs[0].links[0].from_socket==tree.nodes['Retouche GPT · joints parasites'].inputs[0].links[0].from_socket
mat=bpy.data.materials['V2 · plaques de sol use fine'];bs=mat.node_tree.nodes.get('Principled BSDF');assert bs.inputs['Normal'].links[0].from_node.name=='Normal · relief antiderapant fin'
assert not bs.inputs['Emission Color'].is_linked and bs.inputs['Emission Strength'].default_value==0
fog=next(o for o in sc.objects if o.get('pa_atmosphere'));assert fog.get('pa_noncolliding') and fog.parent
# UI controls modify real shader values and visibility, then restore defaults.
sc.pa_modular.plate_relief_mm=.5;assert abs(mat.node_tree.nodes['Normal · relief antiderapant fin'].inputs['Distance'].default_value-.0005)<1e-7
sc.pa_modular.plate_relief_mm=.32;sc.pa_modular.use_depth_haze=False;assert fog.hide_render and fog.hide_viewport
sc.pa_modular.use_depth_haze=True;assert not fog.hide_render and not fog.hide_viewport
sc.pa_modular.haze_density=.003;density=fog.active_material.node_tree.nodes['Densite · zero au premier plan'];assert abs(density.inputs['To Max'].default_value-.003)<1e-7
sc.pa_modular.haze_density=.0025
# Ignore the renderer-only fog container for physical route checks.
fog.hide_viewport=True;bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();path=bpy.data.objects['CAM_09 · parcours automatique'];old=sc.frame_current;last=None;blocked=[];segments=0
for frame in range(1,301,3):
    sc.frame_set(frame);bpy.context.view_layer.update();pos=path.matrix_world.translation.copy()
    if last is not None:
        delta=pos-last
        for off in ((0,0,0),(.16,0,0),(-.16,0,0),(0,0,.16),(0,0,-.16)):
            hit,loc,n,i,obj,ma=sc.ray_cast(dg,last+Vector(off),delta.normalized(),distance=delta.length+.03);segments+=1
            if hit:blocked.append([frame,obj.name])
    last=pos
sc.frame_set(old);fog.hide_viewport=False
unpacked=[im.name for im in bpy.data.images if im.source=='FILE' and not im.packed_file]
assert not blocked and not unpacked
report={'original_albedo_retained_outside_mask':True,'shared_camera_uv_for_patch_and_source':True,'floor_relief_in_normal_only':True,'surface_controls_tested':True,'fog_has_no_surface_and_no_collision':True,'path_segments_tested':segments,'collisions':blocked,'unpacked_images':unpacked,'geometry_preservation_report':'repair-report.json','note':'Sampled eye path; no universal collision guarantee.'}
(O/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8');print('V21_VALIDATED',flush=True)
