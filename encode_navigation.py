"""Encode the rendered camera test with Blender's bundled video encoder."""
from pathlib import Path
import bpy
root=Path(__file__).resolve().parent/'output'/'cockpit-lowpoly-v2'
files=sorted((root/'motion').glob('frame-*.png'))
assert len(files)==36
scene=bpy.context.scene
editor=scene.sequence_editor_create()
strip=editor.strips.new_image('Navigation check',filepath=str(files[0]),channel=1,frame_start=1)
for path in files[1:]: strip.elements.append(path.name)
strip.frame_final_duration=len(files)
scene.frame_start=1; scene.frame_end=len(files)
scene.render.resolution_x=768; scene.render.resolution_y=432; scene.render.resolution_percentage=100
scene.render.fps=12; scene.view_settings.view_transform='Standard'
scene.render.image_settings.media_type='VIDEO'
scene.render.ffmpeg.format='MPEG4'; scene.render.ffmpeg.codec='H264'
scene.render.ffmpeg.constant_rate_factor='MEDIUM'
scene.render.filepath=str(root/'navigation.mp4')
bpy.ops.render.render(animation=True)
print('ENCODED',scene.render.filepath,flush=True)
