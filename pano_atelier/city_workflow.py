"""UI for the reference-specific A1 city recipe; keeps other open scenes intact."""
from pathlib import Path
import bpy
from bpy.props import StringProperty,FloatProperty,PointerProperty,BoolProperty,EnumProperty
from . import city_scene,city_projection,city_optimize,city_opposite,city_dressing

def ring_fog_update(settings,context):
    if not context or not context.scene.get('pa_city_dressing'):return
    for o in context.scene.objects:
        if not o.get('pa_ring_fog') or not o.active_material:continue
        n=o.active_material.node_tree.nodes.get('Densite anneau')
        if n:n.outputs[0].default_value=settings.ring_fog_density*(1.5555556 if 'lointaines' in o.name else 1)

def fog_update(settings,context):
    if not context or not context.scene.get('pa_city_recipe'):return
    if context.scene.get('pa_continuous_city_haze'):
        m=bpy.data.materials.get('VIS · atmosphere urbaine continue')
        if m:
            v=m.node_tree.nodes.get('Brume continue');v.inputs['Density'].default_value=settings.fog_density/6;v.inputs['Emission Strength'].default_value=settings.fog_density/6*.233333
        return
    m=bpy.data.materials.get('VIS · brume nord raccordee') or bpy.data.materials.get('VILLE · brume atmospherique')
    if m and m.node_tree:
        n=m.node_tree.nodes.get('Brume · faible devant dense derriere')
        if n:n.inputs['To Max'].default_value=settings.fog_density

class PA_CitySettings(bpy.types.PropertyGroup):
    reference:StringProperty(name='Reference A1',subtype='FILE_PATH')
    asset_root:StringProperty(name='Racine des assets',subtype='DIR_PATH')
    output:StringProperty(name='Dossier de la ville',subtype='DIR_PATH',default='//ville-output/')
    projection_folder:StringProperty(name='Guides et albedo detail',subtype='DIR_PATH')
    projection_strength:FloatProperty(name='Poids maximal du detail',default=.28,min=0,max=.85)
    append_projection:BoolProperty(name='Ajouter une vue de detail',default=False,description='Ajouter une projection depuis un autre dossier de guides; chaque vue garde ses propres coordonnees figees')
    projection_scope:EnumProperty(name='Batiments cibles',items=[('ALL','Toute la ville','Toutes les facades eligibles'),('OPPOSITE','Vis-a-vis uniquement','Preserver les materiaux du quartier initial')],default='ALL')
    fog_density:FloatProperty(name='Densite de brume',default=.008,min=0,max=.02,precision=4,update=fog_update)
    ring_fog_density:FloatProperty(name='Brume des fonds · Ring Fog',default=.045,min=0,max=.10,precision=4,update=ring_fog_update)

class PA_BuildCity(bpy.types.Operator):
    bl_idname='pa.build_brutalist_city';bl_label='Construire A1 dans une nouvelle scene';bl_options={'REGISTER','UNDO'}
    def execute(self,context):
        s=context.scene.pa_city
        ref=Path(bpy.path.abspath(s.reference));assets=Path(bpy.path.abspath(s.asset_root));out=Path(bpy.path.abspath(s.output))
        if any(sc.get('pa_city_recipe') for sc in bpy.data.scenes):
            self.report({'ERROR'},'Une recette A1 existe deja dans ce fichier. Utiliser un nouveau fichier pour la reconstruire.');return {'CANCELLED'}
        if not s.reference or not ref.is_file():self.report({'ERROR'},'Choisir la reference A1.');return {'CANCELLED'}
        if not assets.is_dir():self.report({'ERROR'},'Choisir la racine des assets.');return {'CANCELLED'}
        new=bpy.data.scenes.new('Ville brutaliste A1');context.window.scene=new
        try:city_scene.build(new,out,assets,ref)
        except Exception as e:self.report({'ERROR'},str(e));return {'CANCELLED'}
        new.pa_city.reference=str(ref);new.pa_city.asset_root=str(assets);new.pa_city.output=str(out)
        self.report({'INFO'},'Ville creee. Enregistrer ce nouveau decor.');return {'FINISHED'}

class PA_ProjectCity(bpy.types.Operator):
    bl_idname='pa.project_city_details';bl_label='Projeter les details sur le beton';bl_options={'REGISTER','UNDO'}
    @classmethod
    def poll(cls,context):return bool(context.scene and context.scene.get('pa_city_recipe') and (not context.scene.get('pa_city_projection') or context.scene.pa_city.append_projection))
    def execute(self,context):
        s=context.scene.pa_city
        try:city_projection.apply(context.scene,bpy.path.abspath(s.projection_folder),s.projection_strength,append=s.append_projection,scope=s.projection_scope)
        except Exception as e:self.report({'ERROR'},str(e));return {'CANCELLED'}
        return {'FINISHED'}

class PA_OptimizeCity(bpy.types.Operator):
    bl_idname='pa.optimize_city';bl_label='Regrouper par batiment';bl_options={'REGISTER','UNDO'}
    bl_description='Consolide les pieces, simplifie les chanfreins lointains et preserve les coordonnees des textures; chaque batiment reste deplacable'
    @classmethod
    def poll(cls,context):return bool(context.scene and context.scene.get('pa_city_recipe') and not context.scene.get('pa_city_optimized'))
    def execute(self,context):
        import json
        try:report=city_optimize.optimize(context.scene)
        except Exception as e:self.report({'ERROR'},str(e));return {'CANCELLED'}
        context.scene['pa_optimization_report']=json.dumps(report)
        self.report({'INFO'},'%s -> %s objets; batiments deplacables'%(report['before']['objects'],report['after']['objects']))
        return {'FINISHED'}

class PA_BuildCityOpposite(bpy.types.Operator):
    bl_idname='pa.build_city_opposite';bl_label='Construire le vis-a-vis';bl_options={'REGISTER','UNDO'}
    bl_description='Prolonge la recette A1 au sud avec des batiments modulaires; conserver une copie du fichier avant cette extension'
    @classmethod
    def poll(cls,context):return bool(context.scene and context.scene.get('pa_city_recipe') and context.scene.get('pa_city_optimized') and not context.scene.get('pa_city_opposite'))
    def execute(self,context):
        import json
        try:report=city_opposite.build(context.scene)
        except Exception as e:self.report({'ERROR'},str(e));return {'CANCELLED'}
        context.scene['pa_opposite_report']=json.dumps(report)
        self.report({'INFO'},'Vis-a-vis cree : %s batiments et 5 cameras.'%report['buildings'])
        return {'FINISHED'}

class PA_DressCity(bpy.types.Operator):
    bl_idname='pa.dress_city';bl_label='Ajouter mobilier et Ring Fog';bl_options={'REGISTER','UNDO'}
    bl_description='Recette A1 : mobilier partage, panneaux et Ring Fog de la bibliotheque Elements-decor'
    @classmethod
    def poll(cls,context):return bool(context.scene and context.scene.get('pa_city_opposite') and not context.scene.get('pa_city_dressing'))
    def execute(self,context):
        import json
        try:report=city_dressing.build(context.scene,bpy.path.abspath(context.scene.pa_city.asset_root))
        except Exception as e:self.report({'ERROR'},str(e));return {'CANCELLED'}
        context.scene['pa_dressing_report']=json.dumps(report)
        context.scene.pa_city.ring_fog_density=.045
        self.report({'INFO'},'Mobilier et deux Ring Fog crees; chaque ensemble reste deplacable.')
        return {'FINISHED'}

class PA_CityPanel(bpy.types.Panel):
    bl_idname='PA_PT_city';bl_label='Decor modulaire · ville A1';bl_space_type='VIEW_3D';bl_region_type='UI';bl_category='Pano Atelier'
    def draw(self,context):
        l=self.layout;s=context.scene.pa_city
        l.label(text='Recette A1, proportions estimees depuis la reference.')
        l.prop(s,'reference');l.prop(s,'asset_root');l.prop(s,'output');l.operator('pa.build_brutalist_city')
        if context.scene.get('pa_city_recipe'):
            l.operator('pa.optimize_city',icon='MOD_DECIM')
            if context.scene.get('pa_city_optimized'):l.label(text='Geometrie regroupee par batiment.',icon='CHECKMARK')
            l.operator('pa.build_city_opposite',icon='ADD')
            if context.scene.get('pa_city_opposite'):l.label(text='Vis-a-vis modulaire construit.',icon='CHECKMARK')
            if context.scene.get('pa_city_opposite'):l.operator('pa.dress_city',icon='ADD')
            if context.scene.get('pa_city_dressing'):l.prop(s,'ring_fog_density')
            l.prop(s,'fog_density');l.operator('pa.explore_modular',text='Explorer la ville a la souris')
            l.prop(s,'projection_folder');l.prop(s,'projection_strength')
            if context.scene.get('pa_city_opposite'):l.prop(s,'projection_scope')
            l.operator('pa.project_city_details')
            if context.scene.get('pa_city_projection'):l.prop(s,'append_projection')
            if context.scene.get('pa_city_projection'):l.label(text='Details projetes; matieres de fond procedurales.')

CLASSES=(PA_CitySettings,PA_BuildCity,PA_ProjectCity,PA_OptimizeCity,PA_BuildCityOpposite,PA_DressCity,PA_CityPanel)
def register():
    for c in CLASSES:bpy.utils.register_class(c)
    bpy.types.Scene.pa_city=PointerProperty(type=PA_CitySettings)
def unregister():
    del bpy.types.Scene.pa_city
    for c in reversed(CLASSES):bpy.utils.unregister_class(c)
