"""Photo → scene in Blender: run with
blender --background --factory-startup --python-exit-code 1 --python tests_photo_blender.py

Uses the analytic room fixture, a known depth map and a local fake HTTP server;
no paid API call is made.
"""
import sys
import json
import base64
import threading
import unittest
from pathlib import Path
from concurrent.futures import Future
from http.server import HTTPServer, BaseHTTPRequestHandler
import bpy
import numpy as np

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import pano_atelier
from pano_atelier import engine, providers, photo_pipeline, photo_util as U
import photo_fixtures as F
pano_atelier.register()
OUT=ROOT/'test-output'/'photo'; OUT.mkdir(parents=True,exist_ok=True)
SMALL=dict(samples=6,long=240,preview=120,view_size=128,atlas_max=128,density=64,planner_samples=400,analysis=128,rough=96)


def drive(job):
    value=None
    while True:
        try:
            if isinstance(value,Future):
                try: result=value.result()
                except Exception as e: value=job.throw(e); continue
                value=job.send(result)
            else: value=job.send(None)
        except StopIteration: return


def fixture():
    img,depth,pos,lab=F.render(240,180,noise=.01)
    engine.write_image(OUT/'photo.png',U.srgb_to_linear(img)); np.save(OUT/'depth.npy',depth)
    other,_,_,_=F.render(240,180,matrix=F.camera(yaw=18.))
    engine.write_image(OUT/'photo-2.png',U.srgb_to_linear(other))


def config(**kw):
    c=dict(photos=[str(OUT/'photo.png')],backend='LOCAL',quality='DRAFT',depth=str(OUT/'depth.npy'),fov=70.,views=3,iterations=1,
           refine_albedo=True,max_requests=12,judge=True,endpoint='http://127.0.0.1',image_model='test',vision_model='test',overrides=SMALL)
    c.update(kw); return c


class PhotoLocalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture(); cls.events=[]; cls.before=set(bpy.data.scenes.keys())
        cls.folder=OUT/'local'
        drive(photo_pipeline.run(config(),cls.folder,cls.events.append))
        cls.scene=next(s for s in bpy.data.scenes if s.name not in cls.before)
        cls.manifest=json.loads((cls.folder/'manifest.json').read_text(encoding='utf-8'))

    def test_01_seven_phases_and_artifacts(self):
        phases=self.manifest['phases']
        self.assertEqual([k for k,_ in photo_pipeline.PHASES],list(phases))
        self.assertTrue(all(p['state']=='done' for p in phases.values()),phases)
        for name in ('final.png','comparaison.png','score.json','scene.blend','1-camera-mapping.png','2-modele-argile.png','materiaux.json','procedural.json','look.json'):
            self.assertTrue((self.folder/name).exists(),name)
        score=json.loads((self.folder/'score.json').read_text(encoding='utf-8'))
        self.assertTrue(0<=score['total']<=20); self.assertGreater(score['total'],8)
        self.assertTrue(list((self.folder/'textures').glob('*-raccord-photo.png')),'stitch masks per view')
        self.assertTrue(any(e.get('score') for e in self.events))

    def test_02_modules_are_real_and_editable(self):
        kinds={o.get('pa_photo_kind') for o in self.scene.objects}
        self.assertTrue({'wall','floor','ceiling','object','frame','glass','backdrop'}<=kinds,kinds)
        glass=next(o for o in self.scene.objects if o.get('pa_photo_kind')=='glass')
        self.assertIsNotNone(glass.parent); self.assertEqual(glass.parent.get('pa_photo_kind'),'wall')
        wall=glass.parent; before=glass.matrix_world.translation.copy(); floor=next(o for o in self.scene.objects if o.get('pa_photo_kind')=='floor')
        fbefore=floor.matrix_world.copy()
        wall.location.x+=.5; self.scene.view_layers[0].update()
        self.assertAlmostEqual((glass.matrix_world.translation-before).x,.5,places=5)
        self.assertEqual(floor.matrix_world,fbefore)
        wall.location.x-=.5; self.scene.view_layers[0].update()

    def test_03_albedo_only_in_base_color_and_procedural_detail(self):
        textured=[o for o in self.scene.objects if o.get('pa_photo_kind') in ('wall','floor','ceiling','object','frame')]
        images=set()
        for o in textured:
            mat=o.active_material; nt=mat.node_tree
            bs=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED')
            self.assertFalse(bs.inputs['Emission Strength'].default_value>0)
            self.assertFalse(any(n.type=='EMISSION' for n in nt.nodes))
            atlas=nt.nodes['PA Atlas'].image; self.assertTrue(atlas.packed_file); images.add(atlas.name)
            self.assertIn('Atlas',[u.name for u in o.data.uv_layers])
        self.assertEqual(len(images),len(textured),'one atlas per module')
        self.assertTrue(any(n.type=='GROUP' and n.node_tree.name.startswith('PA Photo · détail') for o in textured for n in o.active_material.node_tree.nodes))

    def test_04_lights_world_and_camera(self):
        self.assertTrue(any(o.type=='LIGHT' for o in self.scene.objects))
        self.assertIsNotNone(self.scene.world); self.assertTrue(self.scene.camera.name.startswith('Caméra photo'))
        self.assertEqual((self.scene.render.resolution_x,self.scene.render.resolution_y),(240,180))

    def test_05_other_scenes_untouched(self):
        self.assertIn('Scene',bpy.data.scenes)
        self.assertEqual(len(bpy.data.scenes['Scene'].objects),len(bpy.data.scenes['Scene'].objects))


class PhotoAPITests(unittest.TestCase):
    def test_api_contract_budget_and_secrecy(self):
        fixture(); calls=[]
        png=(OUT/'photo.png').read_bytes()
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args): pass
            def do_POST(self):
                body=self.rfile.read(int(self.headers['Content-Length'])); calls.append((self.path,body,self.headers.get('Authorization')))
                if self.path.endswith('/chat/completions'):
                    text=json.loads(body)['messages'][0]['content'][0]['text']
                    content={'score':13.5,'notes':'test'} if 'Rate the render' in text else {'scene':'interior','elements':[
                        {'label':'caisse','kind':'furniture','box':[.55,.55,.8,.95],'material':'painted metal'},
                        {'label':'fenêtre','kind':'window','box':[.4,.3,.6,.5],'material':'glass'}],'lights':[],'sun':None,'atmosphere':{'haze':0,'glow':0}}
                    result={'choices':[{'message':{'content':json.dumps(content)}}]}
                else: result={'data':[{'b64_json':base64.b64encode(png).decode()}]}
                self.send_response(200); self.send_header('Content-Type','application/json'); self.end_headers(); self.wfile.write(json.dumps(result).encode())
        server=HTTPServer(('127.0.0.1',0),Handler); threading.Thread(target=server.serve_forever,daemon=True).start()
        try:
            url=f'http://127.0.0.1:{server.server_port}/v1'
            providers.set_key(url,'PA_SECRET_PHOTO_TEST')
            folder=OUT/'api'
            drive(photo_pipeline.run(config(backend='API',endpoint=url,max_requests=4,photos=[str(OUT/'photo.png'),str(OUT/'photo-2.png')]),folder))
            manifest=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
            self.assertLessEqual(len(calls),4); self.assertEqual(manifest['requests'],len(calls))
            self.assertTrue(all(c[2]=='Bearer PA_SECRET_PHOTO_TEST' for c in calls))
            self.assertTrue(any(b'name="mask"' in c[1] and b'name="image[]"' in c[1] for c in calls if c[0].endswith('/images/edits')))
            self.assertTrue((folder/'analysis.json').exists())
            for path in folder.rglob('*'):
                if path.is_file() and path.suffix in ('.json','.blend','.jsonl'): self.assertNotIn(b'PA_SECRET_PHOTO_TEST',path.read_bytes(),path.name)
        finally: server.shutdown(); server.server_close()


class PhotoUITests(unittest.TestCase):
    def test_panel_operators_and_rating_log(self):
        self.assertTrue(hasattr(bpy.types,'PA_PT_photo'))
        s=bpy.context.scene.pa_photo; s.photos.clear()
        self.assertFalse(bpy.ops.pa.photo_generate.poll())
        s.photos.add().path=str(OUT/'photo.png'); s.photos.add().path=str(OUT/'photo-2.png'); s.index=1
        bpy.ops.pa.photo_reference(); self.assertTrue(s.photos[0].path.endswith('photo-2.png'))
        self.assertTrue(bpy.ops.pa.photo_generate.poll())
        s.score=12.; s.details=json.dumps({'total':12.,'subscores':{'structure':.6,'colour':.5,'edges':.5,'detail':.6,'light':.7}}); s.run_folder=str(OUT/'local')
        s.rating=15.5; bpy.ops.pa.photo_rate()
        log=(OUT/'local'/'notes.jsonl').read_text(encoding='utf-8').strip().splitlines()
        self.assertEqual(json.loads(log[-1])['human'],15.5)


if __name__=='__main__':
    result=unittest.main(argv=[sys.argv[0],'-v'],exit=False).result
    print('PHOTO_BLENDER_TESTS_DONE',result.wasSuccessful())
    sys.exit(0 if result.wasSuccessful() else 1)
