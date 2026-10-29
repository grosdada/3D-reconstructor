"""Simple interface: photos in, one big Generate button, phases, score and your rating."""
import json
import sys
import time
import uuid
from pathlib import Path
from concurrent.futures import Future
import bpy
from bpy.props import StringProperty, FloatProperty, IntProperty, BoolProperty, EnumProperty, CollectionProperty, PointerProperty
from . import providers, photo_pipeline, photo_score

RUNNING=False
IMAGES='*.jpg;*.jpeg;*.png;*.webp;*.tif;*.tiff;*.bmp;*.exr'
OPTIONS=('backend','quality','depth','fov','views','iterations','refine_albedo','max_requests','judge','output')


def base():
    return sys.modules[__package__]


def user_file(name):
    return Path(bpy.utils.user_resource('CONFIG',path='pano_atelier',create=True))/name


def learned_weights():
    """Score weights refitted from your ratings (falls back to the defaults)."""
    try: return json.loads(user_file('photo-score-weights.json').read_text(encoding='utf-8'))
    except (OSError,ValueError): return None


class PA_PhotoItem(bpy.types.PropertyGroup):
    path: StringProperty(name='Photo',subtype='FILE_PATH')


class PA_PhotoSettings(bpy.types.PropertyGroup):
    photos: CollectionProperty(type=PA_PhotoItem)
    index: IntProperty(name='Photo active')
    backend: EnumProperty(name='Textures',items=[
        ('LOCAL','Locales','Projection de la photo et remplissage local, sans réseau'),
        ('API','Modèle API','Vision, albédo et vues manquantes générés par l’API configurée')],default='LOCAL')
    quality: EnumProperty(name='Qualité',items=[('DRAFT','Brouillon','Rapide, pour vérifier la spatialité'),
        ('STANDARD','Standard','Équilibre durée / fidélité'),('FINAL','Final','Atlas 2K, rendu 1600 px, 128 échantillons')],default='STANDARD')
    depth: StringProperty(name='Profondeur (option)',subtype='FILE_PATH',description='NPY/EXR de profondeur axiale de la première photo. Vide = MoGe si configuré, sinon diorama sol + fond')
    fov: FloatProperty(name='Champ horizontal si inconnu',default=60,min=10,max=150,description='Utilisé sans MoGe')
    views: IntProperty(name='Caméras de texturing',default=6,min=1,max=24,description='Photos comprises ; les autres sont placées automatiquement')
    iterations: IntProperty(name='Itérations d’amélioration',default=2,min=0,max=6)
    refine_albedo: BoolProperty(name='Affiner l’albédo par comparaison',default=True,
        description='Corrige la couleur des surfaces vues par la photo à partir de l’écart photo / rendu. Les lumières restent physiques')
    max_requests: IntProperty(name='Maximum appels API',default=12,min=1,max=100)
    judge: BoolProperty(name='Avis du juge IA',default=True,description='Une requête vision pour noter le rendu final (API)')
    output: StringProperty(name='Dossier',subtype='DIR_PATH',default='//photo-3d/')
    status: StringProperty(default='Ajoutez une ou plusieurs photos, puis Générer.')
    phases: StringProperty(default='{}')
    score: FloatProperty(default=-1)
    details: StringProperty(default='{}')
    run_folder: StringProperty()
    rating: FloatProperty(name='Votre note',default=10,min=0,max=20,precision=1,step=50)
    comment: StringProperty(name='Commentaire',description='Ce qui trahit le rendu : géométrie, matière, lumière…')


class PA_UL_Photos(bpy.types.UIList):
    def draw_item(self,context,layout,data,item,icon,active_data,active_propname,index):
        name=Path(bpy.path.abspath(item.path)).name or '—'
        layout.label(text=name,icon='SOLO_ON' if index==0 else 'IMAGE_DATA')
        if index==0: layout.label(text='référence')


class PA_OT_PhotoAdd(bpy.types.Operator):
    bl_idname='pa.photo_add'; bl_label='Ajouter des photos'; bl_options={'REGISTER','UNDO'}
    files: CollectionProperty(type=bpy.types.OperatorFileListElement,options={'HIDDEN','SKIP_SAVE'})
    directory: StringProperty(subtype='DIR_PATH',options={'HIDDEN','SKIP_SAVE'})
    filepath: StringProperty(subtype='FILE_PATH',options={'HIDDEN','SKIP_SAVE'})
    filter_glob: StringProperty(default=IMAGES,options={'HIDDEN'})
    def invoke(self,context,event):
        context.window_manager.fileselect_add(self); return {'RUNNING_MODAL'}
    def execute(self,context):
        s=context.scene.pa_photo
        paths=[Path(self.directory)/f.name for f in self.files if f.name] or ([Path(self.filepath)] if self.filepath else [])
        for p in paths:
            if p.is_file(): s.photos.add().path=str(p)
        s.index=max(0,len(s.photos)-1)
        s.status=f'{len(s.photos)} photo(s). La première sert de caméra de référence.'
        return {'FINISHED'}


class PA_OT_PhotoRemove(bpy.types.Operator):
    bl_idname='pa.photo_remove'; bl_label='Retirer la photo'; bl_options={'REGISTER','UNDO'}
    @classmethod
    def poll(cls,context): return not RUNNING and len(context.scene.pa_photo.photos)>0
    def execute(self,context):
        s=context.scene.pa_photo; s.photos.remove(s.index); s.index=max(0,min(s.index,len(s.photos)-1)); return {'FINISHED'}


class PA_OT_PhotoReference(bpy.types.Operator):
    bl_idname='pa.photo_reference'; bl_label='Définir comme référence'; bl_options={'REGISTER','UNDO'}
    bl_description='La photo de référence fixe la caméra, la spatialité et la note /20'
    @classmethod
    def poll(cls,context): return not RUNNING and context.scene.pa_photo.index>0
    def execute(self,context):
        s=context.scene.pa_photo; s.photos.move(s.index,0); s.index=0; return {'FINISHED'}


def copy_settings(src,dst):
    dst.photos.clear()
    for item in src.photos: dst.photos.add().path=item.path
    for name in OPTIONS: setattr(dst,name,getattr(src,name))


class PA_OT_PhotoGenerate(bpy.types.Operator):
    bl_idname='pa.photo_generate'; bl_label='Générer'
    bl_description='Camera mapping, modélisation, texturing multivues, matériaux, procédural, lumière puis note /20 dans une nouvelle scène'
    @classmethod
    def poll(cls,context): return not RUNNING and len(context.scene.pa_photo.photos)>0
    def execute(self,context):
        global RUNNING
        s=context.scene.pa_photo; p=base().prefs(context)
        photos=[bpy.path.abspath(i.path) for i in s.photos if i.path]
        missing=[x for x in photos if not Path(x).is_file()]
        if not photos or missing: self.report({'ERROR'},'Photo introuvable : '+(missing[0] if missing else '—')); return {'CANCELLED'}
        if s.backend=='API':
            try: providers.check_endpoint(p.endpoint)
            except ValueError as e: self.report({'ERROR'},str(e)); return {'CANCELLED'}
            if not providers.get_key(p.endpoint) and not p.endpoint.startswith(('http://localhost','http://127.0.0.1')):
                self.report({'ERROR'},'Saisir la clé API pour cette session (préférences de l’add-on).'); return {'CANCELLED'}
        root=Path(bpy.path.abspath(s.output)); folder=root/(time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:6])
        config=dict(photos=photos,backend=s.backend,quality=s.quality,depth=bpy.path.abspath(s.depth) if s.depth else '',fov=s.fov,
            views=s.views,iterations=s.iterations,refine_albedo=s.refine_albedo,max_requests=s.max_requests,judge=s.judge,
            endpoint=p.endpoint,image_model=p.image_model,vision_model=p.vision_model,
            moge_python=bpy.path.abspath(p.moge_python) if p.moge_python else '',weights=learned_weights())
        s.phases='{}'; s.score=-1; s.details='{}'; s.run_folder=str(folder); s.status='Démarrage…'
        self.source=s; self.target=s; self.window=context.window; self.phases={}
        self.generator=photo_pipeline.run(config,folder,self.progress); self.pending=None
        RUNNING=True
        self.timer=context.window_manager.event_timer_add(.1,window=context.window)
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}
    def progress(self,event):
        if 'scene' in event:
            scene=event['scene']; copy_settings(self.source,scene.pa_photo)
            scene.pa_photo.run_folder=self.source.run_folder; self.target=scene.pa_photo
            if self.window: self.window.scene=scene
        if 'phase' in event:
            self.phases[event['phase']]={k:v for k,v in event.items() if k!='phase'}
            self.target.phases=json.dumps(self.phases,ensure_ascii=False)
        if 'score' in event:
            self.target.score=event['score']['total']; self.target.details=json.dumps(event['score'],ensure_ascii=False)
            self.target.rating=round(event['score']['total']*2)/2
    def finish(self,context):
        global RUNNING
        context.window_manager.event_timer_remove(self.timer); RUNNING=False
        for area in context.screen.areas if context.screen else []: area.tag_redraw()
    def modal(self,context,event):
        if event.type=='ESC':
            self.generator.close(); self.finish(context)
            self.target.status='Arrêté. Un appel API déjà envoyé peut encore être facturé.'; return {'CANCELLED'}
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
            elif value: self.target.status=str(value)
            for area in context.screen.areas if context.screen else []: area.tag_redraw()
        except StopIteration:
            self.finish(context); return {'FINISHED'}
        except Exception as e:
            self.generator.close(); self.finish(context)
            self.target.status='Échec : '+str(e)[:160]; self.report({'ERROR'},str(e)); return {'CANCELLED'}
        return {'PASS_THROUGH'}


class PA_OT_PhotoOpen(bpy.types.Operator):
    bl_idname='pa.photo_open'; bl_label='Ouvrir'
    what: EnumProperty(items=[('COMPARISON','Comparaison',''),('FINAL','Rendu final',''),('FOLDER','Dossier','')],default='COMPARISON')
    @classmethod
    def poll(cls,context): return bool(context.scene.pa_photo.run_folder)
    def execute(self,context):
        folder=Path(context.scene.pa_photo.run_folder)
        path={'COMPARISON':folder/'comparaison.png','FINAL':folder/'final.png','FOLDER':folder}[self.what]
        if not path.exists(): self.report({'ERROR'},'Pas encore produit : '+path.name); return {'CANCELLED'}
        bpy.ops.wm.path_open(filepath=str(path)); return {'FINISHED'}


class PA_OT_PhotoCamera(bpy.types.Operator):
    bl_idname='pa.photo_camera'; bl_label='Voir par la caméra photo'
    @classmethod
    def poll(cls,context): return context.scene.camera is not None and context.area is not None and context.area.type=='VIEW_3D'
    def execute(self,context):
        context.space_data.region_3d.view_perspective='CAMERA'; return {'FINISHED'}


class PA_OT_PhotoRate(bpy.types.Operator):
    bl_idname='pa.photo_rate'; bl_label='Enregistrer ma note'
    bl_description='Ajoute votre note /20 au journal et réajuste les poids de la note automatique'
    @classmethod
    def poll(cls,context): return context.scene.pa_photo.score>=0
    def execute(self,context):
        s=context.scene.pa_photo; details=json.loads(s.details or '{}')
        record=dict(time=time.strftime('%Y-%m-%d %H:%M:%S'),run=s.run_folder,human=round(s.rating,2),comment=s.comment,
            automatic=details.get('metric',details.get('total')),subscores=details.get('subscores',{}),weights=details.get('weights'),
            judge=details.get('judge',{}).get('score'),quality=s.quality,backend=s.backend)
        lines=json.dumps(record,ensure_ascii=False)+'\n'
        for path in (Path(s.run_folder)/'notes.jsonl',user_file('photo-ratings.jsonl')):
            try:
                with open(path,'a',encoding='utf-8') as f: f.write(lines)
            except OSError: pass
        records=photo_score.read_ratings(user_file('photo-ratings.jsonl'))
        weights=photo_score.fit_weights(records)
        user_file('photo-score-weights.json').write_text(json.dumps(weights,indent=2),encoding='utf-8')
        s.status=f'Note enregistrée ({len(records)} au total). Poids de la note automatique réajustés.'
        return {'FINISHED'}


ICONS={'done':'CHECKMARK','running':'SORTTIME','failed':'ERROR','skipped':'REMOVE'}


class PA_PT_Photo(bpy.types.Panel):
    bl_label='Photo → Scène 3D'; bl_idname='PA_PT_photo'
    bl_space_type='VIEW_3D'; bl_region_type='UI'; bl_category='Pano Atelier'
    def draw(self,context):
        s=context.scene.pa_photo; l=self.layout
        row=l.row()
        row.template_list('PA_UL_Photos','',s,'photos',s,'index',rows=3)
        col=row.column(align=True)
        col.operator('pa.photo_add',text='',icon='ADD'); col.operator('pa.photo_remove',text='',icon='REMOVE')
        col.operator('pa.photo_reference',text='',icon='SOLO_ON')
        row=l.row(align=True); row.prop(s,'backend',expand=True)
        l.prop(s,'quality',text='')
        if s.backend=='API':
            p=base().prefs(context); box=l.box(); box.label(text=p.endpoint,icon='URL')
            box.operator('pa.api_key',text='Clé API (session)',icon='KEYINGSET'); box.prop(s,'max_requests')
        big=l.row(); big.scale_y=3.
        big.operator('pa.photo_generate',text='GÉNÉRER' if not RUNNING else 'Génération… (Échap pour arrêter)',icon='PLAY' if not RUNNING else 'TIME')
        l.label(text=s.status[:90])
        phases=json.loads(s.phases or '{}')
        if phases or RUNNING:
            box=l.box()
            for i,(key,label) in enumerate(photo_pipeline.PHASES):
                info=phases.get(key,{}); state=info.get('state','')
                row=box.row(); row.label(text=f'{i+1} · {label}',icon=ICONS.get(state,'RADIOBUT_OFF'))
                if info.get('seconds') is not None: row.label(text=f"{info['seconds']:.0f} s")
                if info.get('note') and state in ('done','failed'): box.label(text='   '+info['note'][:70])
        if s.score>=0:
            details=json.loads(s.details or '{}')
            box=l.box(); row=box.row(); row.scale_y=1.6; row.label(text=f'Note : {s.score:.1f} / 20',icon='SOLO_ON')
            if 'camera_mapping_reference' in details: box.label(text=f"Projection brute de la photo : {details['camera_mapping_reference']:.1f} / 20")
            for k,v in details.get('subscores',{}).items():
                box.progress(factor=float(v),type='BAR',text=f'{photo_score.LABELS.get(k,k)} {v*100:.0f} %')
            if details.get('judge'): box.label(text=f"Juge IA : {details['judge']['score']:.1f} / 20")
            row=box.row(align=True)
            row.operator('pa.photo_open',text='Comparaison',icon='IMAGE_DATA').what='COMPARISON'
            row.operator('pa.photo_open',text='Rendu',icon='RENDER_RESULT').what='FINAL'
            row.operator('pa.photo_open',text='',icon='FILE_FOLDER').what='FOLDER'
            box.operator('pa.photo_camera',icon='VIEW_CAMERA')
            box=l.box(); box.label(text='Votre note (améliore le modèle)')
            box.prop(s,'rating',slider=True); box.prop(s,'comment',text=''); box.operator('pa.photo_rate',icon='CHECKMARK')
        header,panel=l.panel('pa_photo_advanced',default_closed=True); header.label(text='Réglages avancés')
        if panel:
            for name in ('depth','fov','views','iterations','refine_albedo','judge','output'): panel.prop(s,name)
            panel.label(text='Profondeur : fichier, sinon MoGe (préférences), sinon diorama.')


CLASSES=(PA_PhotoItem,PA_PhotoSettings,PA_UL_Photos,PA_OT_PhotoAdd,PA_OT_PhotoRemove,PA_OT_PhotoReference,PA_OT_PhotoGenerate,
         PA_OT_PhotoOpen,PA_OT_PhotoCamera,PA_OT_PhotoRate,PA_PT_Photo)


def register():
    for cls in CLASSES: bpy.utils.register_class(cls)
    bpy.types.Scene.pa_photo=PointerProperty(type=PA_PhotoSettings)


def unregister():
    if RUNNING: raise RuntimeError('Arrêter la génération avant de désactiver Pano Atelier.')
    del bpy.types.Scene.pa_photo
    for cls in reversed(CLASSES): bpy.utils.unregister_class(cls)
