"""Blender UI for explicit modular recipes and masked panorama wrap repair."""
import json
from pathlib import Path
import bpy,numpy as np
from mathutils import Vector,Euler
from bpy.props import StringProperty,FloatProperty,PointerProperty,IntProperty,BoolProperty
from . import station_scene,panorama_seam,multiview_albedo,projection_guides,station_refinement,station_procedural

def update_surface_controls(settings,context):
    mat=bpy.data.materials.get('V2 · plaques de sol use fine')
    if mat and mat.use_nodes:
        bump=mat.node_tree.nodes.get('Normal · relief antiderapant fin')
        if bump:bump.inputs['Distance'].default_value=settings.plate_relief_mm*.001
    mat=bpy.data.materials.get('Atmosphere · profondeur tres legere')
    if mat and mat.use_nodes:
        density=mat.node_tree.nodes.get('Densite · zero au premier plan')
        if density:density.inputs['To Max'].default_value=settings.haze_density
    if context and context.scene:
        for o in context.scene.objects:
            if o.get('pa_atmosphere'):o.hide_render=not settings.use_depth_haze;o.hide_viewport=not settings.use_depth_haze

class PA_ModularSettings(bpy.types.PropertyGroup):
    asset_root:StringProperty(name='Bibliotheque KitBash',subtype='DIR_PATH')
    reference:StringProperty(name='Reference panorama',subtype='FILE_PATH')
    output:StringProperty(name='Dossier du decor',subtype='DIR_PATH',default='//station-output/')
    seam_width:FloatProperty(name='Bande de raccord',default=.44,min=.05,max=.49,subtype='FACTOR')
    seam_edit:StringProperty(name='Correction GPT Image',subtype='FILE_PATH')
    projection_manifest:StringProperty(name='Manifest multivues JSON',subtype='FILE_PATH')
    detail_albedo:StringProperty(name='Albedo detail des sas',subtype='FILE_PATH')
    variation_seed:IntProperty(name='Graine de variations',default=48,min=0)
    plate_relief_mm:FloatProperty(name='Relief des plaques (mm)',default=.32,min=0,max=2,precision=3,update=update_surface_controls)
    haze_density:FloatProperty(name='Densite du voile',default=.0025,min=0,max=.02,precision=4,update=update_surface_controls)
    use_depth_haze:BoolProperty(name='Voile de profondeur',default=True,update=update_surface_controls)
    status:StringProperty(default='Recette explicite : station a sas circulaires')

class PA_BuildStation(bpy.types.Operator):
    bl_idname='pa.build_station';bl_label='Construire la station modulaire';bl_options={'REGISTER','UNDO'}
    def execute(self,context):
        s=context.scene.pa_modular
        try:
            # Preflight before any geometry mutation.
            root=Path(bpy.path.abspath(s.asset_root))
            for file in ('hatches-and-cover.blend','SCI-FI-PANEL-VOL-01.blend','KitBash_control_panel_industrial.blend'):
                if not (root/file).is_file():raise ValueError('Bibliotheque incomplete : '+file)
            _,r=station_scene.build(context.scene,root,Path(bpy.path.abspath(s.output)),bpy.path.abspath(s.reference) if s.reference else '')
            s.status='Station construite : %d objets, modules deplacables'%r['objects']
        except Exception as e:self.report({'ERROR'},str(e));return {'CANCELLED'}
        return {'FINISHED'}

def read_rgba(path):
    im=bpy.data.images.load(str(path),check_existing=False);w,h=im.size
    a=np.empty(w*h*4,np.float32);im.pixels.foreach_get(a);bpy.data.images.remove(im)
    return a.reshape(h,w,4)

def write_rgba(path,a):
    h,w,c=a.shape;im=bpy.data.images.new(Path(path).stem,w,h,alpha=True,float_buffer=False)
    im.pixels.foreach_set(a.astype(np.float32).ravel());im.filepath_raw=str(path);im.file_format='PNG';im.save();bpy.data.images.remove(im)

class PA_PrepareSeam(bpy.types.Operator):
    bl_idname='pa.prepare_panorama_seam';bl_label='Exporter le raccord centre et son masque'
    def execute(self,context):
        s=context.scene.pa_modular
        try:
            path=Path(bpy.path.abspath(s.reference))
            if not path.is_file():raise ValueError('Choisir une image source existante')
            out=Path(bpy.path.abspath(s.output))/'seam';out.mkdir(parents=True,exist_ok=True)
            a=read_rgba(path);rolled,mask,shift=panorama_seam.prepare(a,s.seam_width,min(.035,s.seam_width/4))
            write_rgba(out/'centered.png',rolled);rgba=np.ones((*mask.shape,4),np.float32);rgba[:,:,:3]=mask[:,:,None];write_rgba(out/'mask.png',rgba)
            (out/'job.json').write_text(json.dumps({'source':str(path),'shift':shift,'width':s.seam_width,'feather':min(.035,s.seam_width/4),'shape':list(a.shape)}),encoding='utf8')
            s.status='Raccord et masque exportes ; generer une correction, puis reintegrer.'
        except Exception as e:self.report({'ERROR'},str(e));return {'CANCELLED'}
        return {'FINISHED'}

class PA_ApplySeam(bpy.types.Operator):
    bl_idname='pa.apply_panorama_seam';bl_label='Reintegrer uniquement la bande masquee'
    def execute(self,context):
        s=context.scene.pa_modular
        try:
            out=Path(bpy.path.abspath(s.output))/'seam';job=json.loads((out/'job.json').read_text(encoding='utf8'))
            a=read_rgba(job['source']);b=read_rgba(bpy.path.abspath(s.seam_edit));_,mask,shift=panorama_seam.prepare(a,job['width'],job['feather'])
            c=panorama_seam.reintegrate(a,b,mask,shift);write_rgba(out/'panorama-repaired.png',c)
            s.status='Raccord reintegre ; reference originale conservee.'
        except Exception as e:self.report({'ERROR'},str(e));return {'CANCELLED'}
        return {'FINISHED'}

class PA_ModularPanel(bpy.types.Panel):
    bl_idname='PA_PT_modular';bl_label='Decor modulaire · station';bl_space_type='VIEW_3D';bl_region_type='UI';bl_category='Pano Atelier'
    @classmethod
    def poll(cls,context):return not context.scene.get('pa_city_recipe')
    def draw(self,context):
        s=context.scene.pa_modular;l=self.layout
        l.prop(s,'reference');l.prop(s,'asset_root');l.prop(s,'output')
        l.operator('pa.build_station',icon='MOD_BUILD')
        l.operator('pa.explore_modular',icon='VIEW_CAMERA')
        l.label(text='Recette adaptee a cette reference, pas une inference IA.')
        box=l.box();box.label(text='Raccord horizontal du panorama');box.prop(s,'seam_width');box.operator('pa.prepare_panorama_seam');box.prop(s,'seam_edit');box.operator('pa.apply_panorama_seam')
        box.label(text='Correction externe, meme taille que l’image exportee.')
        box=l.box();box.label(text='Albédos multivues');box.operator('pa.export_multiview_guides');box.prop(s,'projection_manifest');box.operator('pa.apply_multiview_albedo')
        box.label(text='Exporter depuis la base avant projection; cameras PROJ_.')
        l.operator('pa.finish_station_details')
        box=l.box();box.label(text='Passe 2 · details et eclairage');box.prop(s,'detail_albedo');box.operator('pa.refine_station')
        box.label(text='Enregistrer une copie avant application sur la V1.')
        if context.scene.get('pa_depth_haze'):
            box=l.box();box.label(text='Finition des surfaces');box.prop(s,'plate_relief_mm');box.prop(s,'use_depth_haze');box.prop(s,'haze_density')
            box.operator('pa.procedural_station')
            if context.scene.get('pa_station_procedural'):box.label(text='Plaques usinees et patine procedurale appliquees.')
        l.label(text=s.status[:85])

class PA_ApplyMultiview(bpy.types.Operator):
    bl_idname='pa.apply_multiview_albedo';bl_label='Appliquer les albedos avec masques de visibilite';bl_options={'REGISTER','UNDO'}
    def execute(self,context):
        s=context.scene.pa_modular
        try:
            report=multiview_albedo.apply(context.scene,bpy.path.abspath(s.projection_manifest));s.status='%d vues appliquees dans Base Color uniquement'%report['views'];context.scene['pa_multiview_report']=json.dumps(report)
        except Exception as e:self.report({'ERROR'},str(e));return {'CANCELLED'}
        return {'FINISHED'}

class PA_ExportMultiview(bpy.types.Operator):
    bl_idname='pa.export_multiview_guides';bl_label='Exporter les guides des cameras PROJ_'
    def execute(self,context):
        s=context.scene.pa_modular
        try:
            path=projection_guides.capture(context.scene,Path(bpy.path.abspath(s.output))/'exported-projections');s.projection_manifest=str(path);s.status='Guides exportes; fournir view-XX-albedo.png avant application.'
        except Exception as e:self.report({'ERROR'},str(e));return {'CANCELLED'}
        return {'FINISHED'}

class PA_ExploreModular(bpy.types.Operator):
    bl_idname='pa.explore_modular';bl_label='Explorer le decor a la souris'
    @classmethod
    def poll(cls,context):return context.area is not None and context.area.type=='VIEW_3D' and context.scene.camera is not None
    def invoke(self,context,event):
        self.region=context.space_data.region_3d;self.initial=(self.region.view_rotation.copy(),self.region.view_location.copy(),self.region.view_distance,self.region.view_perspective)
        self.position=context.scene.camera.matrix_world.translation.copy();self.root=context.scene.camera.matrix_world.to_quaternion();self.yaw=0.;self.pitch=0.;self.drag=False
        self.update(context);context.area.header_text_set('Glisser gauche : regarder | Molette : avancer | Maj+glisser : deplacer | Z/W Q/A S D : pas | E/C : hauteur | Echap : retour | clic droit : terminer')
        context.window_manager.modal_handler_add(self);return {'RUNNING_MODAL'}
    def update(self,context):
        self.rotation=self.root@Euler((self.pitch,self.yaw,0),'YXZ').to_quaternion();self.region.view_rotation=self.rotation;self.region.view_perspective='PERSP';self.region.view_distance=.01;self.region.view_location=self.position+self.rotation@Vector((0,0,-.01));context.area.tag_redraw()
    def move(self,context,delta):
        if delta.length<1e-8:return
        # Volume bounds are renderer containers, not physical walls. Continue the
        # ray beyond explicitly noncolliding surfaces, retaining the safety margin.
        direction=delta.normalized();origin=self.position.copy();remaining=delta.length+.18
        for _ in range(16):
            hit,loc,normal,index,obj,matrix=context.scene.ray_cast(context.evaluated_depsgraph_get(),origin,direction,distance=remaining)
            if not hit:self.position+=delta;return
            if not obj.get('pa_noncolliding'):return
            step=(loc-origin).length+.001;remaining-=step;origin=loc+direction*.001
            if remaining<=0:self.position+=delta;return
    def modal(self,context,event):
        if event.type in {'ESC','RIGHTMOUSE'}:
            if event.type=='ESC':self.region.view_rotation,self.region.view_location,self.region.view_distance,self.region.view_perspective=self.initial
            context.area.header_text_set(None);context.area.tag_redraw();return {'FINISHED'}
        if event.type=='LEFTMOUSE':self.drag=event.value=='PRESS';self.last=(event.mouse_x,event.mouse_y)
        if event.type=='MOUSEMOVE' and self.drag:
            dx=event.mouse_x-self.last[0];dy=event.mouse_y-self.last[1];self.last=(event.mouse_x,event.mouse_y)
            if event.shift:self.move(context,self.rotation@Vector((-dx*.003,-dy*.003,0)))
            else:self.yaw-=dx*.003;self.pitch=max(-1.45,min(1.45,self.pitch+dy*.003))
        if event.type in {'WHEELUPMOUSE','WHEELDOWNMOUSE'}:self.move(context,self.rotation@Vector((0,0,-.25 if event.type=='WHEELUPMOUSE' else .25)))
        if event.value=='PRESS':
            step={'W':(0,0,-.18),'Z':(0,0,-.18),'S':(0,0,.18),'Q':(-.18,0,0),'A':(-.18,0,0),'D':(.18,0,0),'E':(0,.18,0),'C':(0,-.18,0)}.get(event.type)
            if step:self.move(context,self.rotation@Vector(step))
        self.update(context);return {'RUNNING_MODAL'}

class PA_FinishStationDetails(bpy.types.Operator):
    bl_idname='pa.finish_station_details';bl_label='Finaliser les ferrures et la teinte';bl_options={'REGISTER','UNDO'}
    @classmethod
    def poll(cls,context):return bool(context.scene and context.scene.get('pa_multiview_applied') and context.scene.get('pa_modular_recipe')=='station-habitat' and not context.scene.get('pa_station_details'))
    def execute(self,context):
        try:station_scene.finish_details(context.scene)
        except Exception as e:self.report({'ERROR'},str(e));return {'CANCELLED'}
        context.scene.pa_modular.status='Ferrures ajoutees ; elements et materiaux editables.';return {'FINISHED'}

class PA_RefineStation(bpy.types.Operator):
    bl_idname='pa.refine_station';bl_label='Ajouter cables, patine locale et lumiere V2';bl_options={'REGISTER','UNDO'}
    @classmethod
    def poll(cls,context):return bool(context.scene and context.scene.get('pa_station_details') and not context.scene.get('pa_station_refinement'))
    def execute(self,context):
        s=context.scene.pa_modular
        try:
            r=station_refinement.apply(context.scene,bpy.path.abspath(s.asset_root),bpy.path.abspath(s.detail_albedo),s.variation_seed)
            s.status='V2 appliquee: %d elements; texture native %s'%(r['added_objects'],r['texture_native_pixels'])
        except Exception as e:self.report({'ERROR'},str(e));return {'CANCELLED'}
        return {'FINISHED'}

class PA_ProceduralStation(bpy.types.Operator):
    bl_idname='pa.procedural_station';bl_label='Usiner les plaques et appliquer la patine procedurale';bl_options={'REGISTER','UNDO'}
    @classmethod
    def poll(cls,context):return bool(context.scene and context.scene.get('pa_surface_repair') and not context.scene.get('pa_station_procedural'))
    def execute(self,context):
        try:r=station_procedural.apply(context.scene)
        except Exception as e:self.report({'ERROR'},str(e));return {'CANCELLED'}
        context.scene.pa_modular.status='%d plaques usinees; patine sans bitmap sur 5 materiaux'%len(r['plates']);return {'FINISHED'}

CLASSES=(PA_ModularSettings,PA_BuildStation,PA_PrepareSeam,PA_ApplySeam,PA_ApplyMultiview,PA_ExportMultiview,PA_FinishStationDetails,PA_RefineStation,PA_ProceduralStation,PA_ExploreModular,PA_ModularPanel)
def register():
    for cls in CLASSES:bpy.utils.register_class(cls)
    bpy.types.Scene.pa_modular=PointerProperty(type=PA_ModularSettings)
def unregister():
    del bpy.types.Scene.pa_modular
    for cls in reversed(CLASSES):bpy.utils.unregister_class(cls)
