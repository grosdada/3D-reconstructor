"""Compare visible projected coverage from identical cameras, separately from fallback maps."""
import bpy,json,numpy as np
from pathlib import Path
from mathutils import Matrix
R=Path(__file__).parent;O=R/'output/tour-belvedere-v3';D=O/'coverage';D.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(O/'tour-belvedere-foret-360-v3.blend'))
shots=[]
for o in sorted(bpy.context.scene.objects,key=lambda o:o.name):
    if o.type=='CAMERA' and o.name.startswith('CAM_') and o.data.type=='PERSP' and int(o.name[4:6])<=13:
        shots.append({'name':o.name,'matrix':list(map(list,o.matrix_world)),'lens':o.data.lens,'aspect':o.get('pa_resolution_x',1440)/o.get('pa_resolution_y',960)})
rows={s['name']:{} for s in shots}
for phase,path in [('v2',R/'output/tour-belvedere-v2/tour-belvedere-albedo-v2.blend'),('v3',O/'tour-belvedere-foret-360-v3.blend')]:
    bpy.ops.wm.open_mainfile(filepath=str(path));sc=bpy.context.scene
    for c in bpy.data.collections:
        if c.name.startswith(('05 ·','08 ·')):c.hide_render=True
    sc.world.node_tree.nodes['Background'].inputs['Strength'].default_value=0
    for m in bpy.data.materials:
        nt=m.node_tree
        if not nt:continue
        out=next((n for n in nt.nodes if n.type=='OUTPUT_MATERIAL' and n.is_active_output),None)
        if not out:continue
        e=nt.nodes.new('ShaderNodeEmission');e.inputs[0].default_value=(0,0,0,1);nt.links.new(e.outputs[0],out.inputs['Surface'])
        g=nt.nodes.get('GPT · projections albedo tour')
        if g:
            threshold=nt.nodes.new('ShaderNodeMath');threshold.operation='GREATER_THAN';threshold.inputs[1].default_value=.5;nt.links.new(g.outputs['Coverage'],threshold.inputs[0])
            mix=nt.nodes.new('ShaderNodeMixRGB');mix.inputs[1].default_value=(1,0,0,1);mix.inputs[2].default_value=(0,1,0,1);nt.links.new(threshold.outputs[0],mix.inputs[0]);nt.links.new(mix.outputs[0],e.inputs[0])
    p=bpy.context.preferences.addons['cycles'].preferences;p.compute_device_type='OPTIX';p.get_devices()
    for d in p.devices:d.use=d.type!='CPU'
    sc.cycles.device='GPU';sc.cycles.samples=1;sc.cycles.use_denoising=False;sc.render.use_persistent_data=True;sc.render.resolution_percentage=100
    sc.view_settings.view_transform='Standard';sc.view_settings.look='None';sc.view_settings.exposure=0
    for s in shots:
        cam=sc.objects.get(s['name'])
        if not cam:
            d=bpy.data.cameras.new(s['name']);cam=bpy.data.objects.new(s['name'],d);sc.collection.objects.link(cam)
        cam.matrix_world=Matrix(s['matrix']);cam.data.lens=s['lens'];sc.camera=cam
        sc.render.resolution_x=420;sc.render.resolution_y=round(420/s['aspect'])
        file=D/(phase+'-'+s['name'][4:6]+'.png');sc.render.filepath=str(file);bpy.ops.render.render(write_still=True)
        im=bpy.data.images.load(str(file));px=np.empty(len(im.pixels),np.float32);im.pixels.foreach_get(px);px=px.reshape(-1,4)
        green=(px[:,1]>.55)&(px[:,0]<.35);red=(px[:,0]>.55)&(px[:,1]<.35)
        n=int(green.sum()+red.sum());rows[s['name']][phase]={'projected_fraction':round(float(green.sum()/n),4) if n else None,'evaluated_pixels':n}
        bpy.data.images.remove(im)
report={'definition':'Visible eligible surfaces with camera-projection coverage above 50 percent; vegetation, glass, physical details and atlas fallback excluded. Identical camera transforms/lenses, one-sample diagnostic render. This is coverage, not image fidelity or collision proof.','shots':rows}
(O/'coverage-comparison.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('V3_COVERAGE_DONE',json.dumps(rows),flush=True)
