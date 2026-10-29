"""Export repeatable beauty/basecolor/depth/protection captures from scene cameras."""
import json
from pathlib import Path
import bpy,numpy as np

def capture(scene,folder,resolution=1024,cameras=None):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    cameras=cameras or sorted([o for o in scene.objects if o.type=='CAMERA' and o.name.startswith('PROJ_')],key=lambda o:o.name)
    if not cameras:raise ValueError('Creer des cameras PROJ_ pour les vues a projeter.')
    if any(c.data.type!='PERSP' for c in cameras):raise ValueError('Les captures de projection utilisent des cameras en perspective.')
    if scene.get('pa_multiview_applied'):raise ValueError('Exporter depuis la base avant projection pour eviter de rephotographier les anciennes corrections.')
    saved={'camera':scene.camera,'resolution_x':scene.render.resolution_x,'resolution_y':scene.render.resolution_y,'resolution_percentage':scene.render.resolution_percentage,'filepath':scene.render.filepath,'filter':scene.render.filter_size,'format':scene.render.image_settings.file_format,'depth':scene.render.image_settings.color_depth,'transform':scene.view_settings.view_transform,'look':scene.view_settings.look,'exposure':scene.view_settings.exposure,'samples':scene.cycles.samples,'denoise':scene.cycles.use_denoising,'override':scene.view_layers[0].material_override}
    originals={};temps={};dm=None;views=[]
    try:
        scene.render.resolution_x=scene.render.resolution_y=resolution;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_depth='8'
        bpy.context.view_layer.update()
        for i,cam in enumerate(cameras):
            name='view-%02d'%i;views.append({'name':name,'camera':cam.name,'matrix':list(map(list,cam.matrix_world)),'frame':list(map(list,cam.data.view_frame(scene=scene)))})
            scene.camera=cam;scene.cycles.samples=16;scene.render.filepath=str(folder/(name+'-beauty.png'));bpy.ops.render.render(write_still=True)
        materials={s.material for o in scene.objects for s in o.material_slots if s.material}
        eligible={m for o in scene.objects if o.get('pa_albedo_target') and not o.get('pa_asset_instance') for m in o.data.materials if m}
        for m in materials:
            nt=m.node_tree
            if not nt:continue
            bs=next((n for n in nt.nodes if n.type=='BSDF_PRINCIPLED'),None);out=next((n for n in nt.nodes if n.type=='OUTPUT_MATERIAL' and n.is_active_output),None)
            if not bs or not out or not out.inputs['Surface'].is_linked:continue
            originals[m]=(out,out.inputs['Surface'].links[0].from_socket);e=nt.nodes.new('ShaderNodeEmission');temps[m]=e
            if bs.inputs['Base Color'].is_linked:nt.links.new(bs.inputs['Base Color'].links[0].from_socket,e.inputs['Color'])
            else:e.inputs['Color'].default_value=bs.inputs['Base Color'].default_value
            nt.links.new(e.outputs[0],out.inputs['Surface'])
        scene.view_settings.view_transform='Standard';scene.view_settings.look='None';scene.view_settings.exposure=0;scene.cycles.samples=2;scene.cycles.use_denoising=False
        for v in views:
            scene.camera=bpy.data.objects[v['camera']];scene.render.filepath=str(folder/(v['name']+'-basecolor.png'));bpy.ops.render.render(write_still=True)
        for m,e in temps.items():
            for link in list(e.inputs['Color'].links):m.node_tree.links.remove(link)
            value=1 if m in eligible else 0;e.inputs['Color'].default_value=(value,value,value,1)
        for v in views:
            scene.camera=bpy.data.objects[v['camera']];path=folder/(v['name']+'-eligible.png');scene.render.filepath=str(path);bpy.ops.render.render(write_still=True)
            im=bpy.data.images.load(str(path),check_existing=False);w,h=im.size;pixels=np.empty(w*h*4,np.float32);im.pixels.foreach_get(pixels);a=pixels.reshape(h,w,4);mask=a[:,:,0].copy();padded=np.pad(mask,3,mode='constant');mask=np.minimum.reduce([padded[y:y+h,x:x+w] for y in range(7) for x in range(7)]);a[:,:,:3]=mask[:,:,None];a[:,:,3]=1;im.pixels.foreach_set(a.ravel());im.filepath_raw=str(folder/(v['name']+'-protection.png'));im.file_format='PNG';im.save();bpy.data.images.remove(im)
        for m,(out,sock) in originals.items():m.node_tree.links.new(sock,out.inputs['Surface'])
        dm=bpy.data.materials.new('PA_TEMP_DEPTH');dm.use_nodes=True;nt=dm.node_tree;nt.nodes.clear();tc=nt.nodes.new('ShaderNodeTexCoord');sep=nt.nodes.new('ShaderNodeSeparateXYZ');nt.links.new(tc.outputs['Object'],sep.inputs[0]);mu=nt.nodes.new('ShaderNodeMath');mu.operation='MULTIPLY';mu.inputs[1].default_value=-1;nt.links.new(sep.outputs['Z'],mu.inputs[0]);e=nt.nodes.new('ShaderNodeEmission');nt.links.new(mu.outputs[0],e.inputs[0]);out=nt.nodes.new('ShaderNodeOutputMaterial');nt.links.new(e.outputs[0],out.inputs[0]);scene.view_layers[0].material_override=dm
        scene.render.image_settings.file_format='OPEN_EXR';scene.render.image_settings.color_depth='32';scene.cycles.samples=1;scene.render.filter_size=.1
        for v in views:
            scene.camera=bpy.data.objects[v['camera']];tc.object=scene.camera;scene.render.filepath=str(folder/(v['name']+'-depth.exr'));bpy.ops.render.render(write_still=True)
        (folder/'views.json').write_text(json.dumps(views,indent=2),encoding='utf8')
        return folder/'views.json'
    finally:
        for m,(out,sock) in originals.items():
            m.node_tree.links.new(sock,out.inputs['Surface'])
            if m in temps:m.node_tree.nodes.remove(temps[m])
        scene.view_layers[0].material_override=saved['override']
        if dm:bpy.data.materials.remove(dm)
        scene.camera=saved['camera']
        for key in ('resolution_x','resolution_y','resolution_percentage','filepath'):setattr(scene.render,key,saved[key])
        scene.render.filter_size=saved['filter'];scene.render.image_settings.file_format=saved['format'];scene.render.image_settings.color_depth=saved['depth'];scene.view_settings.view_transform=saved['transform'];scene.view_settings.look=saved['look'];scene.view_settings.exposure=saved['exposure'];scene.cycles.samples=saved['samples'];scene.cycles.use_denoising=saved['denoise']
