import bpy,json,numpy as np
from pathlib import Path
R=Path(__file__).parent;O=R/'output/tour-belvedere-v4';A=Path(r'K:\Connector-Blender\HDR\HDRI-Haven\Pure-sky')
names=['kloofendal_38d_partly_cloudy_puresky_4k.exr','kloppenheim_02_puresky_4k.exr','kloppenheim_05_puresky_4k.exr','mpumalanga_veld_puresky_4k.exr','quarry_01_puresky_4k.exr','qwantani_puresky_4k.exr','table_mountain_1_puresky_4k.exr','table_mountain_2_puresky_4k.exr']
rows=[]
for name in names:
    im=bpy.data.images.load(str(A/name));im.scale(600,300)
    px=np.empty(len(im.pixels),np.float32);im.pixels.foreach_get(px);px=px.reshape(-1,4)
    q=float(np.percentile(px[:,:3],65));scale=.35/max(q,.0001);px[:,:3]*=scale;im.pixels.foreach_set(px.ravel())
    bpy.context.scene.view_settings.view_transform='Standard';bpy.context.scene.view_settings.look='None'
    im.save_render(str(O/(Path(name).stem+'.png')));rows.append({'name':name,'size':list(im.size),'preview_scale':scale});bpy.data.images.remove(im)
(O/'hdri-previews.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
print('HDRI_BLENDER_PREVIEWS_DONE')
