import bpy,sys
from pathlib import Path
from mathutils import Vector
R=Path(__file__).parent;O=R/'output/ville-brutaliste-v1';sys.path.insert(0,str(R))
from pano_atelier.station_procedural import node,feed,mapped,math as smath
bpy.ops.wm.open_mainfile(filepath=str(O/'ville-brutaliste-geometrie.blend'));sc=bpy.context.scene
cam=sc.camera;cam.data.lens=42;cam.rotation_euler=(Vector((-4,12,37))-cam.location).to_track_quat('-Z','Y').to_euler()
bpy.data.objects['EXT · ilot 01'].location=(100,35,0)
o=bpy.data.objects['Podium · voile monumental'];mw=o.matrix_world.copy();o.parent=bpy.data.objects['A1 · podium haut'];o.matrix_world=mw
# A1 tower is intentionally more blind than a generic office block: vary small apertures.
# Window groups remain editable; reserve filled service openings to selected storeys.
for o in sc.objects:
 if o.type=='MESH' and o.parent and o.parent.parent and o.parent.parent.name in ('A1 · noyau porteur tour droite','A1 · liaison verticale') and 'vitrage poussiereux' in o.name:
  o.data.materials.clear();o.data.materials.append(bpy.data.materials['VILLE · beton humide sombre'])
# Organized assemblies with preserved world positions.
for prefix,label in [('A1 ·','ILOT · ensemble principal A1'),('BG ·','SKYLINE · arriere plan'),('EXT ·','ILOTS · prolongement invente'),('VEGETATION ·','VEGETATION · arbres mobiles'),('VEHICULE ·','VEHICULES · stationnement'),('MOBILIER ·','MOBILIER · voirie')]:
 root=bpy.data.objects.new(label,None);sc.collection.objects.link(root);root.parent=bpy.data.objects['VILLE · ensemble'];root['pa_module']=True
 for o in list(sc.objects):
  if o is not root and o.name.startswith(prefix) and o.parent==bpy.data.objects['VILLE · ensemble']:
   mw=o.matrix_world.copy();o.parent=root;o.matrix_world=mw
fog=bpy.data.materials['VILLE · brume atmospherique'];t=fog.node_tree;t.nodes.clear();v=node(t,'ShaderNodeVolumePrincipled','Brume douce');v.inputs['Color'].default_value=(.90,.94,.84,1);v.inputs['Anisotropy'].default_value=.2
tc=node(t,'ShaderNodeTexCoord','Brume · coordonnees locales');sep=node(t,'ShaderNodeSeparateXYZ','Brume · axe profondeur');t.links.new(tc.outputs['Object'],sep.inputs[0]);density=mapped(t,'Brume · faible devant dense derriere',smath(t,'ADD',sep.outputs['Y'],90),0,100,.0006,.008)
feed(t,v.inputs['Density'],density);v.inputs['Emission Color'].default_value=(.68,.75,.53,1);feed(t,v.inputs['Emission Strength'],smath(t,'MULTIPLY',density,.22));out=node(t,'ShaderNodeOutputMaterial','Volume uniquement');t.links.new(v.outputs[0],out.inputs['Volume'])
bpy.context.view_layer.update();bpy.ops.wm.save_as_mainfile(filepath=str(O/'ville-brutaliste-geometrie.blend'));print('CITY_CALIBRATED',flush=True)
p=bpy.context.preferences.addons['cycles'].preferences;p.compute_device_type='OPTIX';p.get_devices()
for d in p.devices:d.use=d.type!='CPU'
sc.cycles.device='GPU';sc.cycles.samples=16;sc.render.resolution_percentage=65;sc.render.filepath=str(O/'A1-preview-calibrated.png');bpy.ops.render.render(write_still=True);print('CITY_CALIBRATED_PREVIEW_DONE',flush=True)
