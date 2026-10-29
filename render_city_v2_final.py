import bpy,sys,json,time
from pathlib import Path
R=Path(__file__).parent;O=R/'output/ville-brutaliste-v2';sys.path.insert(0,str(R))
from pano_atelier.station_procedural import node,feed,noise,mapped,mix
bpy.ops.wm.open_mainfile(filepath=str(O/'ville-brutaliste-V2.blend'));sc=bpy.context.scene
# Give the near view its own rest attributes, also for later independent module edits.
for o in sc.objects:
 if o.type!='MESH' or not o.get('pa_city_project'):continue
 for old,new,domain in [('PA_CityRest','PA_CityRest_02','POINT'),('PA_CityNormal','PA_CityNormal_02','CORNER')]:
  if new not in o.data.attributes:
   vals=[c for x in o.data.attributes[old].data for c in x.vector]
   o.data.attributes.new(new,'FLOAT_VECTOR',domain).data.foreach_set('vector',vals)
for ng in bpy.data.node_groups:
 if any(n.type=='TEX_IMAGE' and n.image and 'projection-close' in n.image.filepath for n in ng.nodes):
  for n in ng.nodes:
   if n.type=='ATTRIBUTE' and n.attribute_name in ('PA_CityRest','PA_CityNormal'):n.attribute_name+='_02'
layers=json.loads(sc['pa_city_projection_layers']);layers[-1]['position_attribute']='PA_CityRest_02';layers[-1]['normal_attribute']='PA_CityNormal_02';sc['pa_city_projection_layers']=json.dumps(layers)
# Fine aggregate on the street, without large blurry high-contrast reflective patches.
m=bpy.data.materials['VILLE · asphalte humide'];t=m.node_tree;bs=t.nodes.get('Principled BSDF');a=node(t,'ShaderNodeAttribute','Asphalte · metres locaux');a.attribute_name='PA_SourceLocal'
grain=noise(t,'Asphalte · granulat fin',a.outputs['Vector'],95,2)
feed(t,bs.inputs['Base Color'],mix(t,'Asphalte · mineral sombre',grain,(.027,.033,.030,1),(.065,.074,.067,1)))
feed(t,bs.inputs['Roughness'],mapped(t,'Asphalte · rugosite du granulat',grain,.1,.9,.59,.86))
bump=node(t,'ShaderNodeBump','Asphalte · grain 3 mm');bump.inputs['Distance'].default_value=.003;bump.inputs['Strength'].default_value=.45;feed(t,bump.inputs['Height'],grain);feed(t,bs.inputs['Normal'],bump.outputs[0])
bpy.ops.outliner.orphans_purge(do_local_ids=True,do_linked_ids=False,do_recursive=True)
sc.camera=next(o for o in sc.objects if o.type=='CAMERA' and o.name.startswith('CAM_01'));sc.render.resolution_x=2400;sc.render.resolution_y=1333;sc.render.resolution_percentage=100
bpy.ops.wm.save_as_mainfile(filepath=str(O/'ville-brutaliste-V2.blend'),compress=True)
(O/'projection-layers.json').write_text(json.dumps(layers,ensure_ascii=False,indent=2),encoding='utf8')
p=bpy.context.preferences.addons['cycles'].preferences;p.compute_device_type='OPTIX';p.get_devices()
for d in p.devices:d.use=d.type!='CPU'
sc.cycles.device='GPU';sc.cycles.use_denoising=True;sc.cycles.samples=48;sc.render.use_persistent_data=True;sc.render.image_settings.file_format='PNG';sc.render.image_settings.color_mode='RGB'
cams=sorted([o for o in sc.objects if o.type=='CAMERA' and o.name.startswith('CAM_')],key=lambda o:o.name);jobs=[]
for idx in (3,0,1,4,7):
 sc.camera=cams[idx];sc.render.resolution_x=2400 if idx==0 else 1800;sc.render.resolution_y=1333 if idx==0 else 1100
 sc.render.filepath=str(O/('CAM_%02d.png'%(idx+1)));t=time.perf_counter();bpy.ops.render.render(write_still=True);jobs.append({'camera':sc.camera.name,'file':sc.render.filepath,'seconds':time.perf_counter()-t});print('FINAL_RENDER',json.dumps(jobs[-1]),flush=True)
(O/'renders.json').write_text(json.dumps(jobs,ensure_ascii=False,indent=2),encoding='utf8');print('ALL_FINAL_RENDERS_DONE',flush=True)
