import bpy,sys,json
from pathlib import Path
from mathutils import Vector
R=Path(__file__).parent;O=R/'output/ville-brutaliste-v2';sys.path.insert(0,str(R))
from pano_atelier.city_projection import apply
from pano_atelier.station_procedural import node,feed,noise,mapped,mix
bpy.ops.wm.open_mainfile(filepath=str(O/'ville-brutaliste-V2.blend'));sc=bpy.context.scene
r=apply(sc,O/'projection-close',.78,incidence_exponent=.8,append=True)
for m in bpy.data.materials:
 if not m.node_tree or not m.get('pa_v2_weathering'):continue
 t=m.node_tree;bs=t.nodes.get('Principled BSDF');base=bs.inputs['Base Color'].links[0].from_socket
 co=node(t,'ShaderNodeAttribute','Proximite · coordonnees locales');co.attribute_name='PA_BuildingLocal'
 n=noise(t,'Proximite · pores et granulat',co.outputs['Vector'],52,2)
 feed(t,bs.inputs['Base Color'],mix(t,'Proximite · grain mineral',mapped(t,'Proximite · fines inclusions',n,.25,.75,.015,.12),base,(.07,.075,.06,1)))
 prev=bs.inputs['Normal'].links[0].from_socket;bump=node(t,'ShaderNodeBump','Proximite · relief de surface 3 mm');bump.inputs['Distance'].default_value=.003;bump.inputs['Strength'].default_value=.24;feed(t,bump.inputs['Normal'],prev);feed(t,bump.inputs['Height'],n);feed(t,bs.inputs['Normal'],bump.outputs[0])
for o in sc.objects:
 if o.type=='LIGHT' and o.data.type=='SUN':
  o.location=(-55,-95,125);o.rotation_euler=(Vector((8,10,20))-o.location).to_track_quat('-Z','Y').to_euler();o.data.energy=2.0;o.data.color=(.95,.97,.92)
sc['pa_city_version']='2.1';sc['pa_city_close_projection']=str(O/'projection-close')
(O/'close-projection-report.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf8')
bpy.ops.wm.save_as_mainfile(filepath=str(O/'ville-brutaliste-V2.blend'),compress=True)
p=bpy.context.preferences.addons['cycles'].preferences;p.compute_device_type='OPTIX';p.get_devices()
for d in p.devices:d.use=d.type!='CPU'
sc.cycles.device='GPU';sc.cycles.samples=24;sc.render.resolution_x=1200;sc.render.resolution_y=733;sc.render.resolution_percentage=100;sc.camera=next(o for o in sc.objects if o.type=='CAMERA' and o.name.startswith('CAM_04'));sc.render.filepath=str(O/'preview-close-corrected.png');bpy.ops.render.render(write_still=True)
print('CLOSE_REFINED_READY',flush=True)
