"""Scene-camera browsing, without selecting or moving a camera object."""
import bpy
from bpy.props import IntProperty, StringProperty


def cameras(scene):
    return sorted((o for o in scene.objects if o.type == 'CAMERA'
                   and not o.name.startswith(('PROJ_', 'TEMP_'))
                   and not o.get('pa_projection_only', False)), key=lambda o: o.name)


def activate(context, camera):
    context.scene.camera = camera
    if camera.get('pa_resolution_x') and camera.get('pa_resolution_y'):
        context.scene.render.resolution_x = camera['pa_resolution_x']
        context.scene.render.resolution_y = camera['pa_resolution_y']
    # Only the caller's 3D view changes. No camera transforms, selection or other windows.
    if context.area and context.area.type == 'VIEW_3D':
        space = context.area.spaces.active
        space.use_local_camera = False
        space.region_3d.view_perspective = 'CAMERA'


class PA_CameraStep(bpy.types.Operator):
    bl_idname = 'pa.camera_step'
    bl_label = 'Changer de caméra'
    bl_description = 'Parcourir les caméras de prise de vue, sans déplacer les objets'
    bl_options = {'REGISTER', 'UNDO'}
    direction: IntProperty(default=1)

    @classmethod
    def poll(cls, context):
        return bool(context.scene and cameras(context.scene))

    def execute(self, context):
        items = cameras(context.scene)
        current = context.scene.camera
        index = items.index(current) if current in items else (-1 if self.direction > 0 else 0)
        activate(context, items[(index + self.direction) % len(items)])
        return {'FINISHED'}


class PA_CameraChoose(bpy.types.Operator):
    bl_idname = 'pa.camera_choose'
    bl_label = 'Voir cette caméra'
    bl_options = {'REGISTER', 'UNDO'}
    camera_name: StringProperty()

    def execute(self, context):
        camera = context.scene.objects.get(self.camera_name)
        if camera not in cameras(context.scene):
            self.report({'WARNING'}, 'Cette caméra n’est plus disponible.')
            return {'CANCELLED'}
        activate(context, camera)
        return {'FINISHED'}


class PA_CameraBrowser(bpy.types.Panel):
    bl_idname = 'PA_PT_camera_browser'
    bl_label = 'Caméras du décor'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Pano Atelier'

    def draw(self, context):
        layout = self.layout
        items = cameras(context.scene)
        if not items:
            layout.label(text='Aucune caméra de prise de vue.')
            return
        row = layout.row(align=True)
        row.operator('pa.camera_step', text='Précédente', icon='TRIA_LEFT').direction = -1
        row.operator('pa.camera_step', text='Suivante', icon='TRIA_RIGHT').direction = 1
        active = context.scene.camera
        for camera in items:
            op = layout.operator('pa.camera_choose', text=camera.name,
                                 icon='VIEW_CAMERA', depress=camera == active)
            op.camera_name = camera.name


CLASSES = (PA_CameraStep, PA_CameraChoose, PA_CameraBrowser)


def registered_class(cls):
    if issubclass(cls, bpy.types.Panel):
        return bpy.types.Panel.bl_rna_get_subclass_py(cls.bl_idname)
    prefix, name = cls.bl_idname.split('.', 1)
    return bpy.types.Operator.bl_rna_get_subclass_py(prefix.upper() + '_OT_' + name)


def register():
    for cls in CLASSES:
        if registered_class(cls) is None:
            bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(CLASSES):
        existing = registered_class(cls)
        if existing:
            bpy.utils.unregister_class(existing)
