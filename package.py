"""Explicit allowlist: never package inputs, environments, credentials or reports."""
from pathlib import Path
import zipfile
root=Path(__file__).resolve().parent
dist=root/'dist'; dist.mkdir(exist_ok=True)
names=['__init__.py','core.py','engine.py','structural.py','providers.py','pipeline.py','depth_worker.py','camera_navigation.py','modular_scene.py','station_scene.py','station_refinement.py','station_surface_repairs.py','station_procedural.py','panorama_seam.py','modular_workflow.py','multiview_albedo.py','projection_guides.py','city_scene.py','city_projection.py','city_workflow.py','city_material_detail.py','blender_manifest.toml']
names.extend(['city_optimize.py','city_opposite.py','city_dressing.py','gas_station.py','gas_workflow.py','gas_weather.py','gas_interior.py','gas_details.py'])
names.extend(['photo_util.py','photo_geometry.py','photo_texture.py','photo_look.py','photo_score.py','photo_scene.py','photo_pipeline.py','photo_workflow.py','photo_worker.py'])
with zipfile.ZipFile(dist/'pano_atelier-0.7.0.zip','w',zipfile.ZIP_DEFLATED) as z:
    for name in names: z.write(root/'pano_atelier'/name,name)
print(dist/'pano_atelier-0.7.0.zip')
