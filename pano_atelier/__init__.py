bl_info = {'name':'Pano Atelier','author':'Pano Atelier','version':(0,7,0),'blender':(4,2,0),
    'location':'Vue 3D > barre latérale > Pano Atelier','description':'Photo → scène 3D éditable, décors depuis images, inspection et raccords masqués','category':'3D View'}

import json
import math
import time
import uuid
from pathlib import Path
from concurrent.futures import Future
import bpy
from bpy.props import StringProperty, FloatProperty, IntProperty, BoolProperty, EnumProperty, PointerProperty
from mathutils import Vector, Euler
from . import core, engine, pipeline, providers, structural, camera_navigation, modular_workflow, city_workflow, gas_workflow, photo_workflow

RUNNING=False


def prefs(context):
    addon=context.preferences.addons.get(__package__)
    if addon: return addon.preferences
    # Registration directly from source during tests / portable launcher.
    return context.scene.pa_settings


def output_dir(settings):
    path=Path(bpy.path.abspath(settings.output))
    path.mkdir(parents=True,exist_ok=True)
    return path


def run_dir(settings):
    return output_dir(settings)/(time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:6])


class PA_Settings(bpy.types.PropertyGroup):
    image: StringProperty(name='Image source',subtype='FILE_PATH')
    depth: StringProperty(name='Profondeur NPY / EXR',subtype='FILE_PATH',description='Distance positive : axe caméra pour perspective, rayon pour panorama. Vide = MoGe')
    panorama: BoolProperty(name='Panorama 360° équirectangulaire 2:1',default=False)
    estimate_fov: BoolProperty(name='Estimer le champ de vision avec MoGe',default=True)
    fov: FloatProperty(name='Champ horizontal (degrés)',default=70,min=20,max=120)
    resolution: IntProperty(name='Résolution du maillage',default=180,min=32,max=512)
    depth_scale: FloatProperty(name='Échelle profondeur',default=1,min=.0001,max=10000)
    edge_limit: FloatProperty(name='Seuil rupture profondeur',default=.15,min=.01,max=1)
    radius: FloatProperty(name='Déplacement (m)',default=.35,min=.01,max=5)
    width: IntProperty(name='Largeur inspection',default=192,min=64,max=1024)
    backend: EnumProperty(name='Mode',items=[('AUDIT','Inspection seule','Aucune génération ni requête réseau'),
        ('LOCAL','Réparation locale de test','Diffusion des couleurs, sans IA ni réseau'),
        ('API','IA via API','Analyse visuelle et génération sous masque via une API compatible')],default='AUDIT')
    vision: BoolProperty(name='Détection visuelle par IA',default=True)
    extend_geometry: BoolProperty(name='Compléter les surfaces cachées (expérimental)',default=False,
        description='Génération API puis profondeur MoGe, alignée sur les surfaces déjà connues')
    max_requests: IntProperty(name='Maximum appels API',default=8,min=1,max=200)
    max_patches: IntProperty(name='Maximum corrections',default=3,min=1,max=50)
    prompt: StringProperty(name='Consigne complémentaire',default='')
    output: StringProperty(name='Dossier de sortie',subtype='DIR_PATH',default='//pano-atelier-output/')
    manual_image: StringProperty(name='Correction générée',subtype='FILE_PATH')
    manual_mask: StringProperty(name='Masque blanc = corriger',subtype='FILE_PATH')
    mask_selected: BoolProperty(name='Masquer uniquement les objets sélectionnés',default=False,
        description='Crée le masque depuis les surfaces visibles des objets sélectionnés et protège les autres objets à la reprojection')
    projection_atlas: StringProperty(name='Atlas généré 3 × 2',subtype='FILE_PATH')
    status: StringProperty(default='Prêt')
    # These fallbacks contain no secrets; used by source launcher only.
    endpoint: StringProperty(name='URL API',default='https://api.openai.com/v1')
    image_model: StringProperty(name='Modèle image',default='gpt-image-1')
    vision_model: StringProperty(name='Modèle vision',default='gpt-4.1-mini')
    moge_python: StringProperty(name='Python MoGe',subtype='FILE_PATH')


class PA_Preferences(bpy.types.AddonPreferences):
    bl_idname=__package__
    endpoint: StringProperty(name='URL API compatible',default='https://api.openai.com/v1')
    image_model: StringProperty(name='Modèle image',default='gpt-image-1')
    vision_model: StringProperty(name='Modèle vision',default='gpt-4.1-mini')
    moge_python: StringProperty(name='Python avec MoGe installé',subtype='FILE_PATH')
    def draw(self,context):
        l=self.layout
        for p in ('endpoint','image_model','vision_model','moge_python'): l.prop(self,p)
        l.operator('pa.api_key',text='Saisir / remplacer la clé API',icon='KEYINGSET')
        l.operator('pa.clear_key',text='Oublier la clé')
        l.label(text='Clé en mémoire uniquement ; à ressaisir après fermeture de Blender.')
        l.label(text='API : /chat/completions + /images/edits (PNG b64_json).')


class PA_Key(bpy.types.Operator):
    bl_idname='pa.api_key'; bl_label='Clé API — session courante'; bl_options={'INTERNAL'}
    value: StringProperty(name='Clé API',subtype='PASSWORD',options={'SKIP_SAVE'})
    def invoke(self,context,event): return context.window_manager.invoke_props_dialog(self)
    def draw(self,context):
        self.layout.label(text='Destination : '+prefs(context).endpoint)
        self.layout.prop(self,'value')
        self.layout.label(text='Jamais enregistrée dans le .blend ou les exports.')
    def execute(self,context):
        p=prefs(context)
        try: providers.check_endpoint(p.endpoint)
        except ValueError as e:
            self.value=''; self.report({'ERROR'},str(e)); return {'CANCELLED'}
        providers.set_key(p.endpoint,self.value); self.value=''
        return {'FINISHED'}
    def cancel(self,context): self.value=''


class PA_ClearKey(bpy.types.Operator):
    bl_idname='pa.clear_key'; bl_label='Oublier la clé API'; bl_options={'INTERNAL'}
    def execute(self,context):
        providers.set_key(prefs(context).endpoint,''); return {'FINISHED'}


class PA_Demo(bpy.types.Operator):
    bl_idname='pa.demo'; bl_label='Créer la scène de démonstration'; bl_options={'REGISTER','UNDO'}
    @classmethod
    def poll(cls,context): return not RUNNING
    def execute(self,context):
        old=context.scene; folder=run_dir(old.pa_settings)/'demo'
        scene=bpy.data.scenes.new('Pano Atelier — Démonstration')
        try:
            obj=engine.fixture(scene,folder)
            scene.pa_settings.output=str(folder.parent)
            scene.pa_settings.image=str(folder/'source.png'); scene.pa_settings.depth=str(folder/'depth.npy')
            scene.pa_settings.backend='LOCAL'
            engine.create_path(scene,obj,.35)
            context.window.scene=scene
            scene.pa_settings.status='Démo synthétique : couture claire et objet au premier plan.'
        except Exception as e:
            self.report({'ERROR'},str(e)); return {'CANCELLED'}
        return {'FINISHED'}


class JobOperator:
    def begin(self,context,generator):
        global RUNNING
        RUNNING=True; self.generator=generator; self.pending=None; self.scene=context.scene
        self.timer=context.window_manager.event_timer_add(.1,window=context.window)
        context.window_manager.modal_handler_add(self); return {'RUNNING_MODAL'}
    def cleanup(self,context):
        global RUNNING
        context.window_manager.event_timer_remove(self.timer); RUNNING=False
        if context.area: context.area.tag_redraw()
    def modal(self,context,event):
        if event.type=='ESC' or context.scene!=self.scene:
            self.generator.close(); self.cleanup(context)
            self.scene.pa_settings.status='Arrêté. Un appel API déjà envoyé peut encore être facturé.'
            return {'CANCELLED'}
        if event.type!='TIMER': return {'PASS_THROUGH'}
        if self.pending and not self.pending.done(): return {'PASS_THROUGH'}
        try:
            if self.pending:
                pending=self.pending; self.pending=None
                try: result=pending.result()
                except Exception as e: value=self.generator.throw(e)
                else: value=self.generator.send(result)
            else: value=next(self.generator)
            if isinstance(value,Future): self.pending=value
            elif value: self.scene.pa_settings.status=str(value)
            if context.area: context.area.tag_redraw()
        except StopIteration:
            self.cleanup(context); return {'FINISHED'}
        except Exception as e:
            self.generator.close(); self.cleanup(context)
            self.scene.pa_settings.status=str(e); self.report({'ERROR'},str(e)); return {'CANCELLED'}
        return {'PASS_THROUGH'}


class PA_Build(JobOperator,bpy.types.Operator):
    bl_idname='pa.build'; bl_label='Reconstruire dans une nouvelle scène'
    @classmethod
    def poll(cls,context): return not RUNNING
    def execute(self,context):
        s=context.scene.pa_settings; p=prefs(context)
        image=bpy.path.abspath(s.image); depth=bpy.path.abspath(s.depth) if s.depth else ''
        if not s.image or not Path(image).is_file(): self.report({'ERROR'},'Choisir une image source.'); return {'CANCELLED'}
        if not depth and not p.moge_python: self.report({'ERROR'},'Fournir une profondeur ou configurer Python MoGe dans les préférences.'); return {'CANCELLED'}
        cfg={'panorama':s.panorama,'fov':s.fov,'resolution':s.resolution,'scale':s.depth_scale,'edge':s.edge_limit}
        folder=run_dir(s); radius=s.radius; python=bpy.path.abspath(p.moge_python); auto_fov=s.estimate_fov
        def job():
            nonlocal depth
            if not depth:
                yield 'Estimation de profondeur MoGe…'
                depth=yield pipeline.POOL.submit(pipeline.infer_depth,python,image,folder/'moge',cfg['panorama'],0 if auto_fov else cfg['fov'])
                metadata=Path(depth).with_name('metadata.json')
                if not cfg['panorama'] and metadata.exists(): cfg['fov']=json.loads(metadata.read_text())['fov_degrees']
                # Respect the estimator validity mask (sky / unsupported pixels).
                mask_path=Path(depth).with_name('mask.png')
                if mask_path.exists():
                    d=engine.load_pixels(depth,True)[...,0]; m=engine.load_pixels(mask_path,True)[...,0]
                    d[engine.resize(m,d.shape[1],d.shape[0])<.5]=0
                    Path(folder).mkdir(parents=True,exist_ok=True); npy=folder/'depth-valid.npy'
                    import numpy as np
                    np.save(npy,d); depth=str(npy)
            yield 'Construction du maillage et projection…'
            scene=bpy.data.scenes.new('Pano Atelier — Décor')
            obj=engine.build(scene,image,depth,**cfg)
            scene.pa_settings.output=str(folder); scene.pa_settings.panorama=cfg['panorama']; scene.pa_settings.fov=cfg['fov']
            engine.create_path(scene,obj,radius)
            scene.pa_settings.status='Décor construit. Lancer une inspection.'
            context.window.scene=scene
            self.scene=scene
        return self.begin(context,job())


class PA_Run(JobOperator,bpy.types.Operator):
    bl_idname='pa.run'; bl_label='Explorer et traiter le parcours'
    @classmethod
    def poll(cls,context): return not RUNNING and bool(engine.owned(context.scene))
    def execute(self,context):
        s=context.scene.pa_settings; p=prefs(context)
        if s.backend=='API':
            try: providers.check_endpoint(p.endpoint)
            except ValueError as e: self.report({'ERROR'},str(e)); return {'CANCELLED'}
            if not providers.get_key(p.endpoint) and not p.endpoint.startswith(('http://localhost','http://127.0.0.1')):
                self.report({'ERROR'},'Saisir la clé API pour cette session.'); return {'CANCELLED'}
        config={name:getattr(s,name) for name in ('radius','width','fov','backend','vision','max_requests','max_patches','prompt','extend_geometry')}
        config.update({name:getattr(p,name) for name in ('endpoint','image_model','vision_model')})
        if context.scene.get('pa_structural'): config['extend_geometry']=False
        config['moge_python']=bpy.path.abspath(p.moge_python) if p.moge_python else ''
        if s.backend=='API' and s.extend_geometry and not Path(config['moge_python']).is_file():
            self.report({'ERROR'},'La reconstruction des surfaces cachées nécessite Python MoGe.'); return {'CANCELLED'}
        folder=run_dir(s); context.scene['pa_last_folder']=str(folder)
        return self.begin(context,pipeline.run(context.scene,config,folder))


class PA_UndoPatch(bpy.types.Operator):
    bl_idname='pa.undo_patch'; bl_label='Retirer la dernière correction'; bl_options={'REGISTER','UNDO'}
    @classmethod
    def poll(cls,context): return not RUNNING and bool(json.loads(context.scene.get('pa_patch_history','[]')))
    def execute(self,context):
        history=json.loads(context.scene['pa_patch_history'])
        try: engine.restore(history.pop())
        except ValueError as e: self.report({'ERROR'},str(e)); return {'CANCELLED'}
        context.scene['pa_patch_history']=json.dumps(history); return {'FINISHED'}


class PA_Capture(bpy.types.Operator):
    bl_idname='pa.capture'; bl_label='Capturer la caméra et créer son masque'
    @classmethod
    def poll(cls,context): return not RUNNING and bool(engine.owned(context.scene)) and context.scene.camera is not None
    def execute(self,context):
        s=context.scene.pa_settings; cam=context.scene.camera; folder=run_dir(s)/'manual'
        allowed=[o.name for o in context.selected_objects if o in engine.owned(context.scene)] if s.mask_selected else []
        if s.mask_selected and not allowed:
            self.report({'ERROR'},'Sélectionner les objets du décor à retoucher.'); return {'CANCELLED'}
        surface=engine.Surface(context.scene)
        shot=engine.scan(surface,cam.matrix_world,s.fov,s.width,round(s.width*9/16)); engine.save_scan(folder,shot)
        if allowed:
            engine.write_image(folder/'mask-texture.png',engine.object_mask(surface,shot,allowed).astype(float),True)
        s.manual_mask=str(folder/'mask-texture.png')
        # Store camera and geometry signature, so applying cannot silently target another view.
        context.scene['pa_manual_capture']=json.dumps({'folder':str(folder),'matrix':[list(r) for r in cam.matrix_world],
            'fov':s.fov,'width':s.width,'signature':engine.geometry_signature(context.scene),'allowed_objects':allowed})
        s.status='Masque créé : blanc = corriger. Le modifier dans un éditeur d’images et enregistrer.'
        return {'FINISHED'}


class PA_Manual(bpy.types.Operator):
    bl_idname='pa.manual'; bl_label='Appliquer l’image dans le masque'; bl_options={'REGISTER','UNDO'}
    @classmethod
    def poll(cls,context): return not RUNNING and bool(context.scene.get('pa_manual_capture'))
    def execute(self,context):
        from mathutils import Matrix
        s=context.scene.pa_settings
        try:
            data=json.loads(context.scene['pa_manual_capture'])
            if engine.geometry_signature(context.scene)!=data['signature']: raise ValueError('Géométrie modifiée : refaire la capture.')
            surface=engine.Surface(context.scene)
            shot=engine.scan(surface,Matrix(data['matrix']),data['fov'],data['width'],round(data['width']*9/16))
            generated=engine.load_pixels(bpy.path.abspath(s.manual_image)); mask=engine.load_pixels(bpy.path.abspath(s.manual_mask),True)[...,0]
            mask=engine.resize(mask,shot['ids'].shape[1],shot['ids'].shape[0])
            if data.get('allowed_objects'): mask=mask*engine.object_mask(surface,shot,data['allowed_objects'])
            patch=engine.bake_patch(surface,shot,generated,mask,run_dir(s)/'manual-patch')
            history=json.loads(context.scene.get('pa_patch_history','[]')); history.append(patch); context.scene['pa_patch_history']=json.dumps(history)
            s.status=f"Correction manuelle : {patch['texels']} texels modifiés."
        except Exception as e: self.report({'ERROR'},str(e)); return {'CANCELLED'}
        return {'FINISHED'}


class PA_PaintMask(bpy.types.Operator):
    bl_idname='pa.paint_mask'; bl_label='Peindre le masque dans Blender'
    @classmethod
    def poll(cls,context): return not RUNNING and bool(context.scene.pa_settings.manual_mask) and context.area is not None
    def execute(self,context):
        path=bpy.path.abspath(context.scene.pa_settings.manual_mask)
        try: image=bpy.data.images.load(path,check_existing=True)
        except Exception:
            self.report({'ERROR'},'Capturer une vue pour créer son masque.'); return {'CANCELLED'}
        image.colorspace_settings.name='Non-Color'
        editors=[a for a in context.screen.areas if a.type=='IMAGE_EDITOR']
        if not editors:
            previous=set(a.as_pointer() for a in context.screen.areas)
            bpy.ops.screen.area_split(direction='VERTICAL',factor=.65)
            editors=[a for a in context.screen.areas if a.as_pointer() not in previous]
        if not editors: self.report({'ERROR'},'Ouvrir le masque dans un éditeur d’images.'); return {'CANCELLED'}
        area=editors[0]; area.type='IMAGE_EDITOR'; area.spaces.active.image=image; area.spaces.active.ui_mode='PAINT'
        context.scene.pa_settings.status='Peindre en blanc/noir, puis Image > Enregistrer avant application.'
        return {'FINISHED'}


class PA_Open(bpy.types.Operator):
    bl_idname='pa.open_output'; bl_label='Ouvrir les résultats'
    def execute(self,context):
        folder=context.scene.get('pa_last_folder',str(output_dir(context.scene.pa_settings)))
        bpy.ops.wm.path_open(filepath=folder); return {'FINISHED'}


class PA_Walk(bpy.types.Operator):
    bl_idname='pa.walk'; bl_label='Explorer à la souris'
    @classmethod
    def poll(cls,context): return not RUNNING and context.area is not None and context.area.type=='VIEW_3D' and bool(engine.owned(context.scene))
    def invoke(self,context,event):
        self.region=context.space_data.region_3d; self.old=(self.region.view_matrix.copy(),self.region.view_perspective)
        obj=engine.owned(context.scene)[0]
        from mathutils import Matrix
        import numpy as np
        self.root=Matrix(np.array(obj['pa_source_matrix']).reshape(4,4)); self.location=self.root.translation.copy()
        self.yaw=0; self.pitch=0; self.drag=False; self.surface=engine.Surface(context.scene)
        self.radius=context.scene.pa_settings.radius; self.update(context)
        context.area.header_text_set('Pano Atelier : glisser = regarder • molette = avancer/reculer • Maj+glisser = déplacement • Échap = quitter')
        context.window_manager.modal_handler_add(self); return {'RUNNING_MODAL'}
    def update(self,context):
        rotation=self.root.to_quaternion() @ Euler((self.pitch,self.yaw,0),'YXZ').to_quaternion()
        self.rotation=rotation; self.region.view_rotation=rotation; self.region.view_perspective='PERSP'
        self.region.view_distance=.01; self.region.view_location=self.location+rotation @ Vector((0,0,-.01))
        context.area.tag_redraw()
    def move(self,delta):
        target=self.location+delta
        if (target-self.root.translation).length>self.radius: return
        if delta.length>1e-6:
            _,_,face,_=self.surface.tree.ray_cast(self.location,delta.normalized(),delta.length+.08)
            if face is not None: return
        self.location=target
    def modal(self,context,event):
        if event.type in ('ESC','RIGHTMOUSE'):
            context.area.header_text_set(None); return {'FINISHED'}
        if event.type=='LEFTMOUSE':
            self.drag=event.value=='PRESS'; self.last=(event.mouse_x,event.mouse_y)
        if event.type=='MOUSEMOVE' and self.drag:
            dx=event.mouse_x-self.last[0]; dy=event.mouse_y-self.last[1]; self.last=(event.mouse_x,event.mouse_y)
            if event.shift: self.move(self.rotation @ Vector((-dx*.002,-dy*.002,0)))
            else:
                self.yaw-=dx*.004; self.pitch=max(-1.45,min(1.45,self.pitch+dy*.004))
            self.update(context)
        if event.type in ('WHEELUPMOUSE','WHEELDOWNMOUSE'):
            self.move(self.rotation @ Vector((0,0,-.05 if event.type=='WHEELUPMOUSE' else .05))); self.update(context)
        return {'RUNNING_MODAL'}


class PA_Structure(bpy.types.Operator):
    bl_idname='pa.structure'; bl_label='Créer le cockpit low-poly (gabarit)'; bl_options={'REGISTER','UNDO'}
    @classmethod
    def poll(cls,context): return not RUNNING
    def execute(self,context):
        folder=run_dir(context.scene.pa_settings)/'structure'
        scene=bpy.data.scenes.new('Pano Atelier — Cockpit low-poly')
        try:
            structural.build(scene,folder,architecture=True)
            context.window.scene=scene
            scene.pa_settings.status='Gabarit 764 triangles, fenêtres en retrait et portes entrouvertes.'
        except Exception as e:
            bpy.data.scenes.remove(scene); self.report({'ERROR'},str(e)); return {'CANCELLED'}
        return {'FINISHED'}


class PA_Guides(bpy.types.Operator):
    bl_idname='pa.guides'; bl_label='Exporter les six vues pour GPT Image'
    @classmethod
    def poll(cls,context): return not RUNNING and bool(context.scene.get('pa_structural'))
    def execute(self,context):
        scene=context.scene; folder=run_dir(scene.pa_settings)/'guides'
        saved=(scene.render.engine,scene.render.resolution_x,scene.render.resolution_y,scene.render.resolution_percentage,scene.render.filepath,scene.camera)
        try:
            structural.export_guides(scene,folder)
            scene['pa_last_folder']=str(folder)
            scene.pa_settings.status='guide-atlas.png : avant, droite, arrière / gauche, haut, bas.'
        except Exception as e:
            self.report({'ERROR'},str(e)); return {'CANCELLED'}
        finally:
            (scene.render.engine,scene.render.resolution_x,scene.render.resolution_y,scene.render.resolution_percentage,scene.render.filepath,scene.camera)=saved
        return {'FINISHED'}


class PA_ProjectAtlas(bpy.types.Operator):
    bl_idname='pa.project_atlas'; bl_label='Projeter les six vues sur le décor'; bl_options={'REGISTER','UNDO'}
    @classmethod
    def poll(cls,context): return not RUNNING and bool(context.scene.get('pa_structural'))
    def execute(self,context):
        scene=context.scene; s=scene.pa_settings; path=bpy.path.abspath(s.projection_atlas)
        if not s.projection_atlas or not Path(path).is_file():
            self.report({'ERROR'},'Choisir l’atlas généré, 3 colonnes × 2 lignes sans marges.'); return {'CANCELLED'}
        old={obj.name:obj['pa_image'] for obj in engine.owned(scene)}
        old_paths={name:bpy.path.abspath(bpy.data.images[image].filepath) for name,image in old.items()}
        try:
            folder=run_dir(s)/'projection'; report=structural.project_atlas(scene,path,folder)
            history=json.loads(scene.get('pa_patch_history','[]'))
            history.append({'old':old,'old_paths':old_paths,'texels':report['uv_texels']}); scene['pa_patch_history']=json.dumps(history)
            scene['pa_last_folder']=str(folder)
            s.status='Projection appliquée. Vérifier les raccords en se déplaçant.'
        except Exception as e:
            engine.restore({'old':old}); self.report({'ERROR'},str(e)); return {'CANCELLED'}
        return {'FINISHED'}


class PA_Panel(bpy.types.Panel):
    bl_label='Pano Atelier · Prototype 0.4'; bl_idname='PA_PT_main'
    bl_space_type='VIEW_3D'; bl_region_type='UI'; bl_category='Pano Atelier'
    def draw(self,context):
        s=context.scene.pa_settings; l=self.layout
        if context.scene.get('pa_gas_station'):
            l.label(text='Station-service : exterieur modulaire')
            l.label(text='Reglages dans le panneau Station-service.')
            l.operator('pa.open_output',icon='FILE_FOLDER')
            return
        if context.scene.get('pa_station_collection'):
            l.label(text='Station modulaire · outils dans le panneau Decor modulaire')
            l.operator('pa.explore_modular',icon='VIEW_CAMERA')
            l.operator('pa.open_output',icon='FILE_FOLDER')
            return
        box=l.box(); box.label(text='Cockpit low-poly · atelier GPT Image')
        box.operator('pa.structure',icon='MESH_CUBE')
        if context.scene.get('pa_structural'):
            box.operator('pa.guides',icon='RENDER_STILL')
            box.prop(s,'projection_atlas'); box.operator('pa.project_atlas',icon='TEXTURE')
            box.label(text='Gabarit architectural ; génération ici puis import.')
        l.operator('pa.demo',icon='SCENE_DATA')
        header,box=l.panel('pa_source',default_closed=bool(engine.owned(context.scene)))
        header.label(text='1 · Étude de profondeur depuis une image')
        if box:
            for p in ('image','depth','panorama','estimate_fov','fov','resolution','depth_scale','edge_limit'): box.prop(s,p)
            if prefs(context) is s: box.prop(s,'moge_python')
            box.operator('pa.build',icon='MESH_GRID')
        box=l.box(); box.label(text='2 · Parcours et corrections')
        for p in ('radius','width','backend'): box.prop(s,p)
        if s.backend=='API':
            p=prefs(context)
            if p is s:
                for name in ('endpoint','image_model','vision_model','moge_python'): box.prop(p,name)
            box.label(text='Envoi : vues du décor + masques au fournisseur')
            box.label(text=p.endpoint)
            box.operator('pa.api_key',text='Clé API (session)')
            box.prop(s,'vision'); box.prop(s,'max_requests'); box.prop(s,'prompt')
            if not context.scene.get('pa_structural'): box.prop(s,'extend_geometry')
            box.label(text='Le plafond porte sur les appels, pas sur les euros.')
        if s.backend!='AUDIT': box.prop(s,'max_patches')
        box.prop(s,'output'); box.operator('pa.run',icon='PLAY')
        if RUNNING: box.label(text='Traitement… Échap pour arrêter.',icon='TIME')
        l.label(text=s.status[:75])
        l.operator('pa.walk',icon='VIEW_CAMERA'); l.operator('pa.undo_patch',icon='LOOP_BACK')
        header,box=l.panel('pa_manual',default_closed=True); header.label(text='3 · Retouche manuelle')
        if box:
            box.prop(s,'mask_selected'); box.operator('pa.capture'); box.prop(s,'manual_mask'); box.operator('pa.paint_mask'); box.prop(s,'manual_image'); box.operator('pa.manual')
        l.operator('pa.open_output',icon='FILE_FOLDER')
        l.label(text='Rose : géométrie manquante • Orange : texture candidate')
        if context.scene.get('pa_structural'): l.label(text='Structure conservée pendant les retouches.')
        else: l.label(text='Surfaces cachées : API + MoGe requis, expérimental.')


CLASSES=(PA_Settings,PA_Preferences,PA_Key,PA_ClearKey,PA_Demo,PA_Build,PA_Run,PA_UndoPatch,PA_Capture,PA_Manual,PA_PaintMask,PA_Open,PA_Walk,PA_Structure,PA_Guides,PA_ProjectAtlas,PA_Panel)


def register():
    photo_workflow.register()  # first: the photo → scene panel opens the sidebar tab
    for cls in CLASSES: bpy.utils.register_class(cls)
    bpy.types.Scene.pa_settings=PointerProperty(type=PA_Settings)
    camera_navigation.register()
    modular_workflow.register()
    city_workflow.register()
    gas_workflow.register()


def unregister():
    if RUNNING or photo_workflow.RUNNING: raise RuntimeError('Arrêter le traitement avant de désactiver Pano Atelier.')
    gas_workflow.unregister()
    city_workflow.unregister()
    modular_workflow.unregister()
    camera_navigation.unregister()
    providers._KEYS.clear()
    del bpy.types.Scene.pa_settings
    for cls in reversed(CLASSES): bpy.utils.unregister_class(cls)
    photo_workflow.unregister()
