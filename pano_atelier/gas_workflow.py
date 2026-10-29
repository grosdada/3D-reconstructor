"""Reference-specific exterior recipe and explicit multiview detail import.

Image generation remains an external step; this panel does not claim automatic
photo reconstruction or a quality-driven camera planner.
"""
from pathlib import Path
import json
import bpy
from bpy.props import StringProperty,FloatProperty,PointerProperty
from . import gas_station,city_projection,gas_weather,gas_interior,gas_details

def reminder_update(settings,context):
    if not context:return
    mats={s.material for o in context.scene.objects for s in o.material_slots if s.material}
    for m in mats:
        n=m.node_tree.nodes.get('Procedural + rappel GPT') if m.node_tree else None
        if n:n.inputs[0].default_value=settings.gpt_reminder;m['pa_gpt_reminder']=settings.gpt_reminder

def fog_update(settings,context):
    if not context or not context.scene.get('pa_gas_station'):return
    for o in context.scene.objects:
        if not o.get('pa_noncolliding') or not o.active_material:continue
        nt=o.active_material.node_tree
        n=nt.nodes.get('Brume progressive') if nt else None
        if n:n.inputs['To Max'].default_value=settings.fog_far

class PA_GasSettings(bpy.types.PropertyGroup):
    projection_folder:StringProperty(name='Dossier de projection',subtype='DIR_PATH')
    detail_strength:FloatProperty(name='Poids de la nouvelle vue',default=.9,min=0,max=1)
    fog_far:FloatProperty(name='Brume lointaine',default=.035,min=0,max=.08,precision=4,update=fog_update)
    gpt_reminder:FloatProperty(name='Rappel des maps GPT',default=.25,min=0,max=1,update=reminder_update,description='0 : peinture entierement procedurale ; 1 : anciennes couches albedo')
    trash_library:StringProperty(name='TrashKit.blend',subtype='FILE_PATH')

class PA_GasWeather(bpy.types.Operator):
    bl_idname='pa.gas_procedural_weather';bl_label='Creer les peintures procedurales';bl_options={'REGISTER','UNDO'}
    @classmethod
    def poll(cls,context):return bool(context.scene.get('pa_gas_station') and not context.scene.get('pa_gas_proc_weather'))
    def execute(self,context):
        try:gas_weather.install(context.scene)
        except Exception as exc:self.report({'ERROR'},str(exc));return {'CANCELLED'}
        return {'FINISHED'}

class PA_GasInterior(bpy.types.Operator):
    bl_idname='pa.gas_interior';bl_label='Amenager le couloir et la boutique';bl_options={'REGISTER','UNDO'}
    @classmethod
    def poll(cls,context):return bool(context.scene.get('pa_gas_proc_weather') and not context.scene.get('pa_gas_interior'))
    def execute(self,context):
        try:gas_interior.build(context.scene,bpy.data.materials['PA · BLANC patine procedural'],bpy.data.materials['PA · BLEU patine procedural'])
        except Exception as exc:self.report({'ERROR'},str(exc));return {'CANCELLED'}
        return {'FINISHED'}

class PA_GasDebris(bpy.types.Operator):
    bl_idname='pa.gas_debris';bl_label='Habiller avec Trash-Kit';bl_options={'REGISTER','UNDO'}
    @classmethod
    def poll(cls,context):return bool(context.scene.get('pa_gas_station') and not context.scene.get('pa_gas_dressing'))
    def execute(self,context):
        s=context.scene.pa_gas;path=Path(bpy.path.abspath(s.trash_library))
        if not s.trash_library or not path.is_file():self.report({'ERROR'},'Choisir votre fichier TrashKit.blend.');return {'CANCELLED'}
        try:gas_details.dress(context.scene,path)
        except Exception as exc:self.report({'ERROR'},str(exc));return {'CANCELLED'}
        return {'FINISHED'}

class PA_BuildGasExterior(bpy.types.Operator):
    bl_idname='pa.build_gas_exterior';bl_label='Nouvelle station-service · exterieur';bl_options={'REGISTER','UNDO'}
    bl_description='Recette interpretee de la reference 035 : volumes modulaires et materiaux proceduraux, sans interieur'
    def execute(self,context):
        if any(s.get('pa_gas_station') for s in bpy.data.scenes):
            self.report({'ERROR'},'Cette recette existe deja dans le fichier. Utiliser un autre fichier pour une seconde station.');return {'CANCELLED'}
        old=context.window.scene;new=bpy.data.scenes.new('Station abandonnee · exterieur');context.window.scene=new
        try:gas_station.build(new)
        except Exception as exc:
            context.window.scene=old;bpy.data.scenes.remove(new);self.report({'ERROR'},str(exc));return {'CANCELLED'}
        self.report({'INFO'},'Exterieur cree dans une nouvelle scene. Generer puis importer les details albedo separement.');return {'FINISHED'}

class PA_ProjectGasExterior(bpy.types.Operator):
    bl_idname='pa.project_gas_exterior';bl_label='Ajouter cette vue d albedo';bl_options={'REGISTER','UNDO'}
    @classmethod
    def poll(cls,context):return bool(context.scene and context.scene.get('pa_gas_station'))
    def execute(self,context):
        s=context.scene.pa_gas
        if not s.projection_folder:self.report({'ERROR'},'Choisir le dossier de guides et detail-albedo.png.');return {'CANCELLED'}
        folder=Path(bpy.path.abspath(s.projection_folder))
        try:
            meta=json.loads((folder/'projection.json').read_text(encoding='utf8'))
            if len(meta.get('matrix',[]))!=4:raise ValueError('Matrice camera absente.')
            for filename in ('detail-albedo.png','guide-mask.png','guide-depth.exr'):
                if not (folder/filename).is_file():raise ValueError('Fichier absent : '+filename)
            city_projection.apply(context.scene,folder,s.detail_strength,1.2,append=bool(context.scene.get('pa_city_projection')))
        except Exception as exc:self.report({'ERROR'},str(exc));return {'CANCELLED'}
        self.report({'INFO'},'Detail ajoute au Base Color. Roughness, relief et eclairage proceduraux conserves.');return {'FINISHED'}

class PA_PT_gas(bpy.types.Panel):
    bl_label='Station-service · decor modulaire';bl_idname='PA_PT_gas';bl_space_type='VIEW_3D';bl_region_type='UI';bl_category='Pano Atelier';bl_options=set()
    def draw(self,context):
        l=self.layout;s=context.scene.pa_gas
        if not context.scene.get('pa_gas_station'):
            l.operator('pa.build_gas_exterior',icon='HOME');l.label(text='Recette dediee a la reference 035.');return
        l.label(text='Exterieur et interieur modulaires' if context.scene.get('pa_gas_interior') else 'Exterieur modulaire')
        l.prop(s,'fog_far');l.prop(context.scene.view_settings,'exposure')
        if context.scene.get('pa_gas_proc_weather'):l.prop(s,'gpt_reminder')
        else:l.operator('pa.gas_procedural_weather',icon='MATERIAL')
        if not context.scene.get('pa_gas_interior'):l.operator('pa.gas_interior',icon='HOME')
        if not context.scene.get('pa_gas_dressing'):
            l.prop(s,'trash_library');l.operator('pa.gas_debris',icon='OUTLINER_OB_GROUP_INSTANCE')
        l.label(text='Details GPT : import albedo uniquement')
        l.prop(s,'projection_folder');l.prop(s,'detail_strength');l.operator('pa.project_gas_exterior',icon='TEXTURE')
        l.label(text='Guides : albedo, masque, profondeur, camera.')
        l.label(text='Selectionner un parent STATION pour deplacer un module.')

CLASSES=(PA_GasSettings,PA_BuildGasExterior,PA_ProjectGasExterior,PA_GasWeather,PA_GasInterior,PA_GasDebris,PA_PT_gas)
def register():
    for c in CLASSES:bpy.utils.register_class(c)
    bpy.types.Scene.pa_gas=PointerProperty(type=PA_GasSettings)
def unregister():
    del bpy.types.Scene.pa_gas
    for c in reversed(CLASSES):bpy.utils.unregister_class(c)
