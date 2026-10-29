"""Run with blender --background --factory-startup --python tests_blender.py."""
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
from mathutils import Matrix

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import pano_atelier
from pano_atelier import core,engine,pipeline,providers
pano_atelier.register()
OUT=ROOT/'test-output'; OUT.mkdir(exist_ok=True)


class CoreTests(unittest.TestCase):
    def test_depth_discontinuity_is_not_bridged(self):
        d=np.ones((5,8),np.float32)*5; d[:,:4]=2
        v,f,uv=core.grid_mesh(d)
        self.assertTrue(f)
        for face in f: self.assertLess(np.ptp(d.ravel()[list(face)]),.01)

    def test_panorama_wrap_and_radial_distance(self):
        v,f,uv=core.grid_mesh(np.ones((9,17))*4,panorama=True)
        v=v.reshape(9,17,3)
        np.testing.assert_allclose(v[:,0],v[:,-1],atol=1e-6)
        np.testing.assert_allclose(np.linalg.norm(v,axis=-1),4,atol=1e-6)

    def test_invalid_ai_boxes_are_ignored(self):
        boxes=[{'kind':'texture','box':[-1,0,1,1]}, {'kind':'geometry','box':[0,0,1,1]},
               {'kind':'seam','box':[.2,.3,.4,.6]}]
        self.assertEqual(int(core.boxes_mask(boxes,(10,10)).sum()),6)

    def test_local_fill_preserves_unmasked(self):
        a=np.ones((20,30,4),np.float32)*.4; a[:,14:16,:3]=1
        m=np.zeros((20,30),bool); m[:,13:17]=True
        b=core.local_fill(a,m)
        np.testing.assert_array_equal(a[~m],b[~m])
        self.assertLess(core.boundary_error(b,m),core.boundary_error(a,m)+.001)

    def test_secret_endpoint_and_redirect_rules(self):
        for url in ['http://example.com','https://user:key@example.com','https://example.com?key=x']:
            with self.assertRaises(ValueError): providers.check_endpoint(url)
        providers.check_endpoint('http://127.0.0.1:8188/v1')

    def test_depth_alignment_requires_consistent_overlap(self):
        predicted=np.ones((20,30),np.float32)*2
        ref=np.ones((20,30),np.float32)*6; holes=np.zeros((20,30),bool); holes[:,20:]=True; ref[holes]=0
        result,info=core.align_missing_depth(predicted,ref,holes)
        np.testing.assert_allclose(result[holes],6); self.assertEqual(info['scale'],3)
        self.assertEqual(np.count_nonzero(result[~holes]),0)
        with self.assertRaises(ValueError): core.align_missing_depth(predicted,np.zeros_like(ref),np.ones_like(holes))

    def test_heldout_positions_are_distinct(self):
        poses=core.path_poses(.3,True)
        train={(p,yaw) for p,yaw,h in poses if not h}
        hold={(p,yaw) for p,yaw,h in poses if h}
        self.assertFalse(train & hold); self.assertEqual(len(hold),4)


class SceneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scene=bpy.data.scenes.new('PA Integration Test')
        bpy.context.window.scene=cls.scene
        cls.obj=engine.fixture(cls.scene,OUT/'fixture')

    def test_00_colour_roundtrip(self):
        a=np.ones((8,8,4),np.float32); a[...,:3]=(.05,.2,.6)
        engine.write_image(OUT/'colour.png',a)
        b=engine.load_pixels(OUT/'colour.png')
        np.testing.assert_allclose(a,b,atol=.005)

    def test_01_scan_detects_seam_and_disocclusion(self):
        surface=engine.Surface(self.scene)
        original=engine.scan(surface,engine.base_matrix(),70,128,72)
        moved=engine.scan(surface,engine.base_matrix() @ Matrix.Translation((.35,0,0)),70,128,72)
        self.assertGreater(int(original['masks']['texture'].sum()),0)
        self.assertGreater(int(moved['masks']['holes'].sum()),int(original['masks']['holes'].sum()))
        engine.save_scan(OUT/'original',original); engine.save_scan(OUT/'moved',moved)

    def test_02_patch_is_baked_and_reversible(self):
        surface=engine.Surface(self.scene); shot=engine.scan(surface,engine.base_matrix(),70,192,108)
        mask=np.zeros((108,192),np.float32); mask[20:70,128:135]=1
        colour=shot['rgb'].copy(); colour[...,:3]=(.05,.7,.1)
        before=engine.pixels(bpy.data.images[self.obj['pa_image']]); previous=self.obj['pa_image']
        patch=engine.bake_patch(surface,shot,colour,mask,OUT/'patch')
        self.assertGreater(patch['texels'],10)
        after=engine.pixels(bpy.data.images[self.obj['pa_image']])
        np.testing.assert_allclose(before[:,:300],after[:,:300],atol=.01)
        self.assertGreater(np.max(abs(before-after)),.1)
        engine.restore(patch); self.assertEqual(self.obj['pa_image'],previous)

    def test_03_pipeline_and_holdout(self):
        cfg=dict(backend='LOCAL',radius=.25,width=128,fov=70,vision=False,max_requests=2,max_patches=2,
            endpoint='http://127.0.0.1',image_model='test',vision_model='test',prompt='')
        job=pipeline.run(self.scene,cfg,OUT/'run'); value=None
        while True:
            try: value=job.send(value.result() if isinstance(value,Future) else None)
            except StopIteration: break
        report=json.loads((OUT/'run'/'report.json').read_text())
        self.assertEqual(report['requests'],0)
        self.assertGreater(report['accepted'],0)
        self.assertTrue((OUT/'run'/'control-00-after'/'view.png').exists())
        self.assertEqual(report['status'],'patch_limit' if report['accepted']==2 else 'review_required')
        providers.set_key('https://api.openai.com/v1','PA_SECRET_TEST_DO_NOT_PERSIST')
        bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'demo.blend'))
        self.assertNotIn(b'PA_SECRET_TEST_DO_NOT_PERSIST',(OUT/'demo.blend').read_bytes())
        self.assertNotIn('PA_SECRET_TEST_DO_NOT_PERSIST',(OUT/'run'/'report.json').read_text())

    def test_04_api_contract_and_budget(self):
        payloads=[]
        square=np.ones((1024,1024,4),np.float32); square[...,:3]=.1
        square[224:800]=engine.resize(engine.load_pixels(OUT/'fixture'/'source.png'),1024,576)
        engine.write_image(OUT/'api-square.png',square)
        png=(OUT/'api-square.png').read_bytes()
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args): pass
            def do_POST(self):
                body=self.rfile.read(int(self.headers['Content-Length']))
                payloads.append((self.path,body))
                if self.path.endswith('/chat/completions'):
                    result={'choices':[{'message':{'content':json.dumps({'defects':[{'kind':'seam','box':[.65,.1,.71,.85],'confidence':.95}]})}}]}
                else: result={'data':[{'b64_json':base64.b64encode(png).decode()}]}
                self.send_response(200); self.send_header('Content-Type','application/json'); self.end_headers(); self.wfile.write(json.dumps(result).encode())
        server=HTTPServer(('127.0.0.1',0),Handler); thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
        try:
            url=f'http://127.0.0.1:{server.server_port}/v1'
            defects=providers.inspect_image(url,'','test',OUT/'fixture'/'source.png')
            self.assertEqual(len(defects),1)
            providers.edit_image(url,'','test',OUT/'fixture'/'source.png',OUT/'original'/'mask-texture.png',OUT/'api.png','repair')
            self.assertEqual((OUT/'api.png').read_bytes(),png)
            self.assertIn(b'name="mask"',payloads[-1][1])
            cfg=dict(backend='API',radius=.2,width=64,fov=70,vision=True,max_requests=1,max_patches=2,
                endpoint=url,image_model='test',vision_model='test',prompt='')
            job=pipeline.run(self.scene,cfg,OUT/'api-budget'); value=None
            while True:
                try: value=job.send(value.result() if isinstance(value,Future) else None)
                except StopIteration: break
            report=json.loads((OUT/'api-budget'/'report.json').read_text())
            self.assertEqual(report['requests'],1); self.assertEqual(report['status'],'request_limit')
            cfg['max_requests']=2
            job=pipeline.run(self.scene,cfg,OUT/'api-roundtrip'); value=None
            while True:
                try: value=job.send(value.result() if isinstance(value,Future) else None)
                except StopIteration: break
            report=json.loads((OUT/'api-roundtrip'/'report.json').read_text())
            self.assertEqual(report['requests'],2)
            self.assertTrue((OUT/'api-roundtrip'/'view-000'/'api-mask.png').exists())
            self.assertIn(report['views'][0]['status'],('accepted_heuristic','rejected'))
        finally: server.shutdown(); server.server_close()

    def test_05_geometry_extension_reduces_holes_and_undo(self):
        surface=engine.Surface(self.scene)
        matrix=engine.base_matrix() @ Matrix.Translation((.35,0,0))
        shot=engine.scan(surface,matrix,70,128,72)
        predicted=shot['depth'].copy(); predicted[shot['masks']['holes']]=5
        np.save(OUT/'new-depth.npy',predicted)
        obj,alignment=engine.add_missing_surface(self.scene,shot,OUT/'fixture'/'source.png',OUT/'new-depth.npy',OUT/'new-surface')
        after=engine.scan(engine.Surface(self.scene),matrix,70,128,72)
        self.assertLess(after['masks']['holes'].sum(),shot['masks']['holes'].sum())
        engine.restore({'old':{},'added_objects':[obj.name]})
        self.assertTrue(obj.hide_render)

    def test_06_panorama_in_blender_has_full_directional_coverage(self):
        scene=bpy.data.scenes.new('PA Panorama Test')
        a=np.ones((64,128,4),np.float32); a[...,:3]=(.1,.2,.3)
        engine.write_image(OUT/'panorama.png',a); np.save(OUT/'panorama-depth.npy',np.ones((64,128),np.float32)*4)
        obj=engine.build(scene,OUT/'panorama.png',OUT/'panorama-depth.npy',panorama=True,resolution=128)
        surface=engine.Surface(scene)
        from mathutils import Euler
        for yaw in (0,90,180,270):
            matrix=engine.base_matrix() @ Euler((0,np.radians(yaw),0)).to_matrix().to_4x4()
            shot=engine.scan(surface,matrix,80,64,36)
            self.assertEqual(int(shot['masks']['holes'].sum()),0)

    def test_07_cancel_persists_status(self):
        cfg=dict(backend='AUDIT',radius=.2,width=64,fov=70,vision=False,max_requests=1,max_patches=1,
            endpoint='',image_model='',vision_model='',prompt='')
        job=pipeline.run(self.scene,cfg,OUT/'cancel'); next(job); job.close()
        report=json.loads((OUT/'cancel'/'report.json').read_text())
        self.assertEqual(report['status'],'cancelled')


class StructuralTests(unittest.TestCase):
    def test_architecture_recesses_and_object_scoped_projection(self):
        from pano_atelier import structural
        scene=bpy.data.scenes.new('PA Architecture Test')
        objects=structural.build(scene,OUT/'architecture',atlas_size=512,architecture=True)
        triangles=0
        for obj in objects:
            obj.data.calc_loop_triangles(); triangles+=len(obj.data.loop_triangles)
        self.assertEqual(triangles,764)
        self.assertEqual(len([o for o in objects if ' glass' in o.name]),12)
        self.assertEqual(len([o for o in objects if 'leaf ajar' in o.name]),2)
        surface=engine.Surface(scene)
        for origin in ((0,0,1.6),(.9,0,1.6),(-.9,0,1.6),(0,.9,1.6),(0,-.9,1.6)):
            for _,matrix in structural.cameras(origin):
                shot=engine.scan(surface,matrix,90,40,40)
                self.assertEqual(int((shot['ids']<0).sum()),0)
        shot=engine.scan(surface,structural.cameras()[0][1],90,128,128)
        selected=[o.name for o in objects if o.name.startswith('PA Central')]
        mask=engine.object_mask(surface,shot,selected)
        self.assertTrue(mask.any())
        self.assertTrue(all(surface.records[int(i)][0].name in selected for i in np.unique(shot['ids'][mask])))
        before=surface.images[objects[0].name].copy()
        image=shot['rgb'].copy(); image[...,:3]=(.8,.05,.05)
        scores=np.zeros((512,512),np.float32)
        patch=engine.bake_patch(surface,shot,image,mask,OUT/'object-scope',score_buffer=scores)
        self.assertGreater(patch['texels'],0)
        updated=engine.Surface(scene)
        repeated=engine.bake_patch(updated,shot,image*0,mask,OUT/'object-scope-repeat',score_buffer=scores)
        self.assertEqual(repeated['texels'],0)
        # Non-selected face UVs must stay byte-for-byte untouched, despite sharing the atlas.
        after=updated.images[objects[0].name]
        for obj in objects:
            if obj.name in selected: continue
            for poly in obj.data.polygons:
                uv=np.mean([obj.data.uv_layers.active.data[li].uv[:] for li in poly.loop_indices],axis=0)
                x=int(uv[0]*512); y=int((1-uv[1])*512)
                np.testing.assert_array_equal(before[y,x],after[y,x])
        # Blender may drop old unreferenced image datablocks on reopen.
        previous_image=bpy.data.images[patch['old'][objects[0].name]]
        bpy.data.images.remove(previous_image)
        engine.restore(patch)
        np.testing.assert_allclose(engine.pixels(bpy.data.images[objects[0]['pa_image']]),before,atol=.005)

    def test_closed_lightweight_room_and_fixed_projection(self):
        from pano_atelier import structural
        scene=bpy.data.scenes.new('PA Structural Test')
        objects=structural.build(scene,OUT/'structure',atlas_size=1024)
        triangles=0
        for obj in objects:
            obj.data.calc_loop_triangles(); triangles+=len(obj.data.loop_triangles)
        self.assertEqual(triangles,404)
        surface=engine.Surface(scene)
        self.assertEqual(len({id(a) for a in surface.images.values()}),1)
        for origin in ((0,0,1.6),(.7,0,1.6),(-.7,0,1.6),(0,.7,1.6),(0,-.7,1.6)):
            for name,matrix in structural.cameras(origin):
                self.assertAlmostEqual(matrix.to_3x3().determinant(),1.,places=5)
                shot=engine.scan(surface,matrix,90,32,32)
                self.assertEqual(int((shot['ids']<0).sum()),0,(origin,name))
        # A real masked update on a shared structural atlas must keep every
        # object's texture pointer synchronized and undo all of them together.
        matrix=structural.cameras()[0][1]
        shot=engine.scan(surface,matrix,90,64,64)
        generated=shot['rgb'].copy(); generated[...,:3]=(.8,.05,.05)
        mask=np.zeros((64,64),np.float32); mask[22:42,22:42]=1
        original=objects[0]['pa_image']; signature=engine.geometry_signature(scene)
        patch=engine.bake_patch(surface,shot,generated,mask,OUT/'structural-patch')
        self.assertGreater(patch['texels'],0)
        self.assertEqual(len({o['pa_image'] for o in objects}),1)
        self.assertNotEqual(objects[0]['pa_image'],original)
        self.assertEqual(engine.geometry_signature(scene),signature)
        engine.restore(patch)
        self.assertTrue(all(o['pa_image']==original for o in objects))


suite=unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
result=unittest.TextTestRunner(verbosity=2).run(suite)
(OUT/'tests.json').write_text(json.dumps({'run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors)},indent=2))
if not result.wasSuccessful(): raise SystemExit(1)
