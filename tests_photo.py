"""Photo → scene algorithms, without Blender.

python tests_photo.py   (or with Blender: blender --background --python tests_photo.py)
"""
import math
import sys
import types
import unittest
from collections import Counter
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
try:
    import bpy  # noqa: F401  (inside Blender the real package imports)
    import pano_atelier
except ImportError:  # plain Python: load only the pure modules of the package
    pkg=types.ModuleType('pano_atelier'); pkg.__path__=[str(ROOT/'pano_atelier')]; sys.modules['pano_atelier']=pkg
from pano_atelier import photo_util as U, photo_geometry as G, photo_texture as T, photo_look as L, photo_score as S, providers
import photo_fixtures as F


def closed(faces):
    edges=Counter()
    for f in faces:
        for i in range(len(f)): edges[(f[i],f[(i+1)%len(f)])]+=1
    return all(k==1 and edges.get((b,a),0)==1 for (a,b),k in edges.items())


class UtilTests(unittest.TestCase):
    def test_label_and_forbidden_links(self):
        m=np.zeros((6,9),bool); m[:,:3]=True; m[:,5:]=True
        self.assertEqual(U.label(m).max(),1)
        right=np.ones((6,8),bool); right[:,6]=False
        self.assertEqual(U.label(m,right=right).max(),2)

    def test_push_pull_keeps_known_texels(self):
        rng=np.random.default_rng(0); c=rng.random((32,32,3)).astype(np.float32); w=rng.random((32,32))>.6
        out=U.push_pull(c,w.astype(np.float32))
        np.testing.assert_array_equal(out[w],c[w]); self.assertTrue(np.isfinite(out).all())

    def test_masked_blur_does_not_leak(self):
        a=np.zeros((20,20),np.float32); a[:,10:]=1; m=np.zeros((20,20),bool); m[:,:10]=True
        self.assertLess(U.masked_blur(a,m,3)[:, :10].max(),1e-6)


class GeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.img,cls.depth,cls.pos,cls.lab=F.render(320,240)
        cls.r=G.analyse(cls.depth,70.,width=192)

    def test_gravity_height_and_room(self):
        rep=self.r['report']
        self.assertEqual(rep['gravity'],'floor')
        self.assertAlmostEqual(rep['camera_height'],1.5,delta=.05)
        self.assertAlmostEqual(rep['floor'],0,delta=.03); self.assertAlmostEqual(rep['ceiling'],2.7,delta=.05)
        self.assertGreaterEqual(rep['walls'],2)
        back=[p for p in rep['planes'] if p['kind']=='wall' and abs(abs(p['k'])-5)<.1]
        self.assertTrue(back,'back wall at 5 m expected')

    def test_window_is_a_real_opening_with_frame_and_glass(self):
        kinds=Counter(m['kind'] for m in self.r['modules'])
        self.assertEqual(self.r['report']['openings'],1); self.assertEqual(kinds['glass'],1); self.assertEqual(kinds['frame'],1)
        glass=next(m for m in self.r['modules'] if m['kind']=='glass')
        ext=np.ptp(glass['vertices'],0)
        self.assertAlmostEqual(max(ext[0],ext[1]),1.4,delta=.25); self.assertAlmostEqual(ext[2],1.,delta=.25)

    def test_box_object_is_closed_and_on_the_floor(self):
        objs=[m for m in self.r['modules'] if m['kind']=='object']
        box=max(objs,key=lambda m:len(m['faces']))
        v=box['vertices']
        self.assertTrue(closed(box['faces']))
        self.assertLess(v[:,2].min(),.02); self.assertAlmostEqual(v[:,2].max(),.8,delta=.08)
        for m in self.r['modules']:
            if m['kind']!='backdrop': self.assertTrue(closed(m['faces']),m['name'])

    def test_slab_hole_and_prior_depth(self):
        v,f=G.slab((0,0,0),(1,0,0),(0,0,1),(0,-1,0),(0,0,4,3),.2,[(1,1,2,2)])
        self.assertTrue(closed(f))
        front=[q for q in f if all(abs(v[i][1])<1e-9 for i in q)]
        area=sum(np.linalg.norm(np.cross(v[q[1]]-v[q[0]],v[q[3]]-v[q[0]])) for q in front)
        self.assertAlmostEqual(area,11.,places=6)
        d=G.prior_depth(120,160,70.,horizon=.5,height=1.6)
        y=100; ray_y=(1-2*(y+.5)/120)*math.tan(math.radians(35))*120/160
        self.assertAlmostEqual(float(d[y,80]),1.6/-ray_y,places=3)


class TextureTests(unittest.TestCase):
    def test_plan_keeps_photos_and_picks_best_gain(self):
        Q=np.array(((1,1,0,0,0,0),(0,0,0,0,0,0),(0,0,1,1,1,0),(0,0,1,0,0,0)),float)
        chosen,gains,cov=T.plan(Q,np.ones(6),forced=[0],max_views=3,min_gain=.01)
        self.assertEqual(chosen[:2],[0,2]); self.assertAlmostEqual(cov,5/6)

    def test_rasterize_and_blend_reproduce_a_view(self):
        img,depth,pos,lab=F.render(160,120); m=F.camera()
        r=G.analyse(depth,70.,width=128); wall=next(x for x in r['modules'] if x['kind']=='wall' and len(x['faces'])>6)
        v=wall['vertices']
        # Simple planar UV of the back wall front: x → u, z → v.
        tris=[]
        for f in wall['faces']:
            if all(abs(v[i][1]-v[f[0]][1])<1e-6 for i in f) and abs(v[f[0]][1]-v[:,1].min())<1e-6:
                tris+=[(f[0],f[1],f[2]),(f[0],f[2],f[3])]
        tris=np.array(tris); x0,x1=v[:,0].min(),v[:,0].max()
        uv=np.stack(((v[tris][...,0]-x0)/(x1-x0),v[tris][...,2]/2.7),-1)
        P,N,M=T.rasterize(uv,v[tris],np.tile((0,-1.,0),(len(tris),3,1)),64)
        self.assertGreater(M.mean(),.5)
        cam=r['camera']; lin=U.srgb_to_linear(img)
        view=dict(matrix=cam,fov=70.,image=lin,depth=depth,priority=1.)
        col,cov,stitch,_=T.blend(P,N,M,[view])
        seen=cov>.3
        self.assertGreater(seen.mean(),.2)
        self.assertLess(np.median(abs(col[seen].mean(1)-np.median(col[seen].mean(1)))),.08)

    def test_compose_and_inpaint_respect_masks_and_objects(self):
        a=np.zeros((40,40,3),np.float32); a[:,:20]=(1,0,0); a[:,20:]=(0,0,1)
        mask=np.zeros((40,40),np.float32); mask[10:30,15:25]=1
        out=T.compose_masked(a,np.ones_like(a),mask); np.testing.assert_array_equal(out[mask<=0],a[mask<=0])
        labels=np.zeros((40,40),int); labels[:,20:]=1
        fill=T.local_inpaint(a,mask,labels)
        self.assertLess(fill[20,22,0],.05); self.assertLess(fill[20,17,2],.05)


class LookTests(unittest.TestCase):
    def test_haze_recovered_and_absent_indoors(self):
        h,w=120,160; d=np.tile(np.linspace(2,80,h)[::-1,None],(1,w)).astype(np.float32)
        J=np.random.default_rng(1).random((h,w,3)).astype(np.float32)*.5; J[::2]*=.2
        t=np.exp(-.03*d)[...,None]; I=J*t+np.array((.75,.8,.85),np.float32)*(1-t)
        self.assertAlmostEqual(L.fit_haze(I,d,np.ones((h,w),bool))['beta'],.03,delta=.012)
        img,depth,pos,lab=F.render(160,120)
        self.assertEqual(L.fit_haze(U.srgb_to_linear(img),depth,depth>0)['beta'],0.)

    def test_grade_corrects_colour_without_washing_out(self):
        img,depth,pos,lab=F.render(160,120); lin=U.srgb_to_linear(img)
        target=np.clip(lin@np.array(((1.1,.05,0),(0,.9,.05),(.02,0,1.2)),np.float32).T,0,1)
        g=L.fit_grade(lin,target,np.ones(lin.shape[:2],bool))
        self.assertGreater(S.score(U.linear_to_srgb(target),L.apply_look(lin,None,dict(grade=g)))['total'],S.score(U.linear_to_srgb(target),img)['total'])
        bad=np.roll(lin,7,1)*.8+.05
        out=L.apply_look(bad,None,dict(grade=L.fit_grade(bad,lin,np.ones(lin.shape[:2],bool))))
        self.assertGreater(U.luminance(out).std(),.7*U.luminance(img).std())

    def test_light_basis_fit(self):
        rng=np.random.default_rng(0); basis=rng.random((3,20,30,3)).astype(np.float32); base=np.zeros((20,30,3),np.float32)
        target=2*basis[0]+.5*basis[2]
        w,tints,res=L.fit_lights(basis,base,target,np.ones((20,30),bool))
        np.testing.assert_allclose(w,(2,0,.5),atol=.05); self.assertLess(res,.02)

    def test_light_sources_and_materials(self):
        img,depth,pos,lab=F.render(160,120); lin=U.srgb_to_linear(img)
        self.assertEqual(L.light_sources(lin,depth),[])
        lamp=lin.copy(); lamp[20:24,40:44]=1.
        self.assertEqual(len(L.light_sources(lamp,depth)),1)
        st=L.texture_stats(lin,lab==0,.01)
        self.assertEqual(L.classify(st,'floor'),'wood'); self.assertEqual(L.classify(st,'object','brushed steel'),'metal')
        self.assertIn(L.recipe(st,'wood')['type'],('wood',))


class ScoreTests(unittest.TestCase):
    def test_identity_and_degradation_order(self):
        img,*_=F.render(160,120); rng=np.random.default_rng(0)
        self.assertEqual(S.score(img,img)['total'],20.)
        blur=S.score(img,U.blur(img,2))['total']; noise=S.score(img,rng.random(img.shape).astype(np.float32))['total']
        grey=S.score(img,np.full_like(img,.5))['total']
        self.assertGreater(blur,grey); self.assertGreater(grey,noise-1); self.assertLess(noise,8)

    def test_weights_learn_from_ratings(self):
        keys=list(S.WEIGHTS); rng=np.random.default_rng(1)
        records=[{'subscores':{k:float(rng.random()) for k in keys}} for _ in range(60)]
        for r in records: r['human']=20*r['subscores']['colour']
        w=S.fit_weights(records)
        self.assertAlmostEqual(sum(w.values()),1.,places=6); self.assertGreater(w['colour'],S.WEIGHTS['colour'])
        self.assertEqual(S.fit_weights([]),S.WEIGHTS)


class ProviderTests(unittest.TestCase):
    def test_analysis_is_strictly_validated(self):
        data={'scene':'exterior','elements':[{'label':'banc','kind':'furniture','box':[.1,.2,.3,.4],'material':'wood'},
              {'label':'x','kind':'??','box':[.5,.5,.4,.9]},{'label':'y','box':'nope'}],
              'lights':[{'kind':'lamp','box':[0,0,.1,.1],'color':[2,.5]}],'sun':{'azimuth_deg':400,'elevation_deg':120},'atmosphere':{'haze':3}}
        out=providers.clean_analysis(data)
        self.assertEqual(len(out['elements']),1); self.assertEqual(out['elements'][0]['kind'],'furniture')
        self.assertEqual(out['sun'],{'azimuth_deg':40.,'elevation_deg':89.}); self.assertEqual(out['atmosphere']['haze'],1.)
        self.assertEqual(providers.edit_size(1920,1080),(1536,1024)); self.assertEqual(providers.edit_size(800,1200),(1024,1536))


if __name__=='__main__':
    result=unittest.main(argv=[sys.argv[0],'-v'],exit=False).result
    if 'bpy' in sys.modules: print('PHOTO_TESTS_DONE',result.wasSuccessful())
    sys.exit(0 if result.wasSuccessful() else 1)
