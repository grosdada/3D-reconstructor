"""Masked albedo repairs, analytic floor microrelief and bounded subtle haze."""
from pathlib import Path
import bpy
from .modular_scene import Builder
from .multiview_albedo import node,mathn


def patch_projection(scene,view,proposal_path,mask_path):
    if scene.get('pa_surface_repair'):raise ValueError('Correction deja appliquee.')
    for p in (proposal_path,mask_path):
        if not Path(p).is_file():raise FileNotFoundError(p)
    tree=bpy.data.node_groups.get('PA · albedos multivues station')
    if not tree:raise ValueError('Projections multivues absentes.')
    old=tree.nodes.get(view+' albedo.png')
    if not old or not old.image:raise ValueError('Vue absente: '+view)
    image=bpy.data.images.load(str(proposal_path),check_existing=True);mask=bpy.data.images.load(str(mask_path),check_existing=True)
    if tuple(image.size)!=tuple(mask.size):raise ValueError('Le masque et la proposition doivent avoir la meme taille.')
    image.pack();mask.colorspace_settings.name='Non-Color';mask.pack()
    targets=[link.to_socket for link in list(old.outputs['Color'].links)]
    uv=old.inputs['Vector'].links[0].from_socket
    patch=node(tree,'ShaderNodeTexImage','Retouche GPT · joints parasites');patch.image=image;patch.extension='EXTEND';tree.links.new(uv,patch.inputs[0])
    gate=node(tree,'ShaderNodeTexImage','Masque local · joints parasites');gate.image=mask;gate.extension='EXTEND';tree.links.new(uv,gate.inputs[0])
    mix=node(tree,'ShaderNodeMixRGB','Reparation masquee · source preservee');tree.links.new(gate.outputs['Color'],mix.inputs[0]);tree.links.new(old.outputs['Color'],mix.inputs[1]);tree.links.new(patch.outputs['Color'],mix.inputs[2])
    for socket in targets:tree.links.new(mix.outputs[0],socket)
    scene['pa_surface_repair']=True
    return {'view':view,'source':old.image.name,'proposal':image.name,'mask':mask.name,'pixels':list(image.size),'outside_mask':'Original albedo unchanged; final mix factor zero.'}


def floor_relief(scene,pitch=.018,height=.00032):
    mat=bpy.data.materials.get('V2 · plaques de sol use fine')
    if not mat:raise ValueError('Materiau de plaques V2 absent.')
    if mat.get('pa_floor_relief'):raise ValueError('Microrelief deja applique.')
    nt=mat.node_tree;bs=nt.nodes.get('Principled BSDF');tc=node(nt,'ShaderNodeTexCoord','Plaques · coordonnees locales')
    sep=node(nt,'ShaderNodeSeparateXYZ','Plaques · axes');nt.links.new(tc.outputs['Object'],sep.inputs[0])
    # Smooth pressed dots, 18 mm spacing; completely analytic, no bitmap texel limit.
    cells=[]
    for axis in ('X','Y'):
        f=mathn(nt,'SUBTRACT',mathn(nt,'FRACT',mathn(nt,'DIVIDE',sep.outputs[axis],pitch)),.5)
        cells.append(mathn(nt,'MULTIPLY',f,f))
    r2=mathn(nt,'ADD',cells[0],cells[1]);shape=node(nt,'ShaderNodeMapRange','Antiderapant · pastilles arrondies')
    shape.interpolation_type='SMOOTHERSTEP';shape.clamp=True;shape.inputs['From Min'].default_value=.005;shape.inputs['From Max'].default_value=.125;shape.inputs['To Min'].default_value=1;shape.inputs['To Max'].default_value=0;nt.links.new(r2,shape.inputs[0])
    bump=node(nt,'ShaderNodeBump','Normal · relief antiderapant fin');bump.inputs['Strength'].default_value=.62;bump.inputs['Distance'].default_value=height
    if bs.inputs['Normal'].is_linked:nt.links.new(bs.inputs['Normal'].links[0].from_socket,bump.inputs['Normal'])
    nt.links.new(shape.outputs[0],bump.inputs['Height']);nt.links.new(bump.outputs[0],bs.inputs['Normal'])
    noise=node(nt,'ShaderNodeTexNoise','Plaques · grain et frottements discrets');noise.inputs['Scale'].default_value=95;noise.inputs['Detail'].default_value=2;nt.links.new(tc.outputs['Object'],noise.inputs[0])
    rough=node(nt,'ShaderNodeMapRange','Plaques · rugosite 0.43 a 0.55');rough.inputs['To Min'].default_value=.43;rough.inputs['To Max'].default_value=.55;nt.links.new(noise.outputs['Fac'],rough.inputs[0]);nt.links.new(rough.outputs[0],bs.inputs['Roughness'])
    # Slightly burnished raised dots respond to grazing light without painted shadows.
    old=bs.inputs['Base Color'].links[0].from_socket
    tones=node(nt,'ShaderNodeMixRGB','Plaques · variation fine de teinte');tones.blend_type='MULTIPLY';tones.inputs[0].default_value=.12;nt.links.new(old,tones.inputs[1]);nt.links.new(noise.outputs['Fac'],tones.inputs[2]);nt.links.new(tones.outputs[0],bs.inputs['Base Color'])
    mat['pa_floor_relief']=True;mat['pa_pitch_m']=pitch;mat['pa_height_m']=height
    return {'material':mat.name,'pitch_m':pitch,'height_m':height,'strength':.62,'method':'Analytic local-coordinate height to bump normal; no geometry subdivision, no bitmap enlargement.'}


def depth_haze(scene,density=.0025):
    if scene.get('pa_depth_haze'):raise ValueError('Volume de profondeur deja present.')
    b=Builder(scene,'STATION · atmosphere legere');root=bpy.data.objects.get('STATION · ensemble')
    m=bpy.data.materials.new('Atmosphere · profondeur tres legere');m.use_nodes=True;nt=m.node_tree;nt.nodes.clear()
    out=node(nt,'ShaderNodeOutputMaterial','Volume seulement');scatter=node(nt,'ShaderNodeVolumeScatter','Diffusion subtile');scatter.inputs['Color'].default_value=(.82,.85,.84,1);scatter.inputs['Anisotropy'].default_value=.22
    tc=node(nt,'ShaderNodeTexCoord','Volume · position locale');sep=node(nt,'ShaderNodeSeparateXYZ','Profondeur du couloir');nt.links.new(tc.outputs['Object'],sep.inputs[0])
    distance=mathn(nt,'ABSOLUTE',mathn(nt,'ADD',sep.outputs['Y'],3.2))
    ramp=node(nt,'ShaderNodeMapRange','Densite · zero au premier plan');ramp.interpolation_type='SMOOTHERSTEP';ramp.inputs['From Min'].default_value=3;ramp.inputs['From Max'].default_value=8;ramp.inputs['To Min'].default_value=0;ramp.inputs['To Max'].default_value=density
    nt.links.new(distance,ramp.inputs[0]);nt.links.new(ramp.outputs[0],scatter.inputs['Density']);nt.links.new(scatter.outputs[0],out.inputs['Volume'])
    o=b.box('ATMOSPHERE · volume sans collision',(0,2,1.60),(4.28,35.5,3.12),m,root,0);o.display_type='WIRE';o.hide_select=True;o['pa_noncolliding']=True;o['pa_atmosphere']=True
    scene['pa_depth_haze']=True;scene.cycles.volume_bounces=2
    return {'object':o.name,'max_density':density,'fade_distance_m':[3,8],'reference_position_y':-1.2,'note':'Bounded volume, clear near reference camera; no surface or collision.'}
