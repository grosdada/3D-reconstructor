import bpy,sys,json,unittest,shutil
from pathlib import Path
import numpy as np
from mathutils import Vector
R=Path(__file__).parent;O=R/'test-output/modular-v040';O.mkdir(parents=True,exist_ok=True);sys.path.insert(0,str(R))
import pano_atelier
from pano_atelier import panorama_seam as seam,projection_guides,multiview_albedo
from pano_atelier.modular_scene import Builder,material,camera
bpy.ops.wm.read_factory_settings(use_empty=True);pano_atelier.register()
class ModularTests(unittest.TestCase):
    def test_01_wrap_mask_preserves_other_pixels(self):
        a=np.arange(7*19*3,dtype=np.uint16).reshape(7,19,3);rolled,m,shift=seam.prepare(a,.4,.04);edit=rolled.copy();edit[:]=600
        result=seam.reintegrate(a,edit,m,shift);allowed=np.roll(m,-shift,axis=1)>0
        np.testing.assert_array_equal(result[~allowed],a[~allowed]);self.assertFalse(np.array_equal(result[allowed],a[allowed]));np.testing.assert_array_equal(seam.reintegrate(a,rolled,m,shift),a)
    def test_02_invalid_correction_is_rejected(self):
        a=np.ones((4,20,3),np.uint8);_,m,s=seam.prepare(a)
        with self.assertRaises(ValueError):seam.reintegrate(a,np.ones((4,21,3)),m,s)
        with self.assertRaises(ValueError):seam.prepare(a,.6)
    def test_03_capture_restores_scene_and_projection_moves(self):
        sc=bpy.context.scene;b=Builder(sc,'TEST');root=b.root('TEST_ROOT');mat=material('ST · panneaux test',(.5,.4,.3));ob=b.box('TEST_BOX',(0,3,0),(2,1,2),mat,root,.02);ob['pa_albedo_target']=True
        cam=camera(b,'PROJ_test',(0,0,0),(0,3,0),32,64,64);sc.camera=cam;sc.render.engine='CYCLES';sc.cycles.device='CPU';sc.render.resolution_x=123;sc.render.resolution_y=87;sc.cycles.samples=7;sc.view_settings.exposure=.3
        sc.world=bpy.data.worlds.new('TEST_WORLD');sc.world.use_nodes=True
        output=mat.node_tree.nodes.get('Material Output');socket=output.inputs['Surface'].links[0].from_socket
        manifest=projection_guides.capture(sc,O/'guides',64,[cam]);self.assertEqual((sc.render.resolution_x,sc.render.resolution_y),(123,87));self.assertEqual(sc.cycles.samples,7);self.assertAlmostEqual(sc.view_settings.exposure,.3);self.assertEqual(output.inputs['Surface'].links[0].from_socket,socket)
        im=bpy.data.images.load(str(O/'guides/view-00-depth.exr'));px=np.array(im.pixels[:]).reshape(64,64,4);self.assertAlmostEqual(float(px[32,32,0]),2.5,delta=.03);bpy.data.images.remove(im)
        shutil.copy2(O/'guides/view-00-basecolor.png',O/'guides/view-00-albedo.png');report=multiview_albedo.apply(sc,manifest);self.assertEqual(report['views'],1)
        def sample():
            e=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());me=e.to_mesh();a=[tuple(v.vector) for v in me.attributes['PA_RestWorld'].data];e.to_mesh_clear();return a
        before=sample();root.location.x=2;root.rotation_euler.z=.4;bpy.context.view_layer.update();self.assertEqual(before,sample())
        bs=mat.node_tree.nodes.get('Principled BSDF');self.assertFalse(bs.inputs['Emission Color'].is_linked);self.assertTrue(bs.inputs['Base Color'].is_linked)
        with self.assertRaises(ValueError):multiview_albedo.apply(sc,manifest)
        self.assertIsNotNone(bpy.types.Operator.bl_rna_get_subclass_py('PA_OT_build_station'));self.assertIsNotNone(bpy.types.Operator.bl_rna_get_subclass_py('PA_OT_export_multiview_guides'))
    def test_04_mouse_navigation_checks_scene_geometry(self):
        from types import SimpleNamespace
        from pano_atelier.modular_workflow import PA_ExploreModular
        root=bpy.data.objects['TEST_ROOT'];root.location=(0,0,0);root.rotation_euler=(0,0,0);bpy.context.view_layer.update()
        walker=SimpleNamespace(position=Vector((0,0,0)))
        PA_ExploreModular.move(walker,bpy.context,Vector((0,4,0)));self.assertEqual(tuple(walker.position),(0,0,0))
        PA_ExploreModular.move(walker,bpy.context,Vector((0,1,0)));self.assertEqual(tuple(walker.position),(0,1,0))
    def test_05_atmosphere_boundary_does_not_hide_real_obstacles(self):
        from types import SimpleNamespace
        from pano_atelier.modular_workflow import PA_ExploreModular
        b=Builder(bpy.context.scene,'TEST_NONCOLLIDING');fog=b.box('TEST_FOG_BOUNDARY',(0,.6,0),(2,.2,2),None);fog['pa_noncolliding']=True;bpy.context.view_layer.update()
        walker=SimpleNamespace(position=Vector((0,0,0)))
        PA_ExploreModular.move(walker,bpy.context,Vector((0,1,0)));self.assertEqual(tuple(walker.position),(0,1,0))
        walker.position=Vector((0,0,0));PA_ExploreModular.move(walker,bpy.context,Vector((0,4,0)));self.assertEqual(tuple(walker.position),(0,0,0))
result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ModularTests));(O/'tests.json').write_text(json.dumps({'run':result.testsRun,'errors':len(result.errors),'failures':len(result.failures)}));print('MODULAR_TESTS_DONE',result.wasSuccessful(),flush=True)
if not result.wasSuccessful():raise SystemExit(1)
