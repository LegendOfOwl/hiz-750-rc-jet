"""Connectivity/orientation regressions independent of SU2."""
from pathlib import Path
import tempfile
import unittest

from cfd.mesh_audit import audit
from cfd.cases import configuration
from validation.run_case import parser
from cfd.convergence import assess


class MeshTests(unittest.TestCase):
    def test_stable_force_does_not_hide_insufficient_residual_drop(self):
        rows = [dict(CD=.003, **{'rms[Rho]':-1-i*.05,'rms[nu]':-2-i*.05,'rms[RhoE]':3.}) for i in range(101)]
        self.assertTrue(assess(rows)['iterative_converged'])
        rows[-1]['rms[nu]'] = -5.
        self.assertFalse(assess(rows)['iterative_converged'])
        rows[-1]['rms[nu]'] = -7.
        rows[-1]['CD'] = .004
        self.assertFalse(assess(rows)['iterative_converged'])

    def test_inverted_cell_and_missing_marker_are_detected(self):
        mesh = ('NDIME= 2\nNELEM= 1\n9 0 1 2 3 0\nNPOIN= 4\n'
                '0 0 0\n1 0 1\n1 1 2\n0 1 3\nNMARK= 1\n'
                'MARKER_TAG= WALL\nMARKER_ELEMS= 4\n3 0 1\n3 1 2\n3 2 3\n3 3 0\n')
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'mesh.su2'
            path.write_text(mesh)
            result = audit(path)
            self.assertEqual(result['nonpositive_cells'],0)
            self.assertEqual(result['boundary_mismatches'],0)
            path.write_text(mesh.replace('0 0 0\n1 0 1\n1 1 2\n0 1 3',
                                         '0 0 0 0\n1 0 0 1\n1 1 0 2\n0 1 0 3'))
            self.assertEqual(audit(path)['nodes'],4)
            path.write_text(mesh.replace('9 0 1 2 3 0','9 3 2 1 0 0'))
            self.assertEqual(audit(path)['nonpositive_cells'],1)
            path.write_text(mesh.replace('MARKER_ELEMS= 4','MARKER_ELEMS= 3').replace('3 3 0\n',''))
            self.assertGreater(audit(path)['boundary_mismatches'],0)

    def test_case6_and_centered_reconstruction_are_consistent(self):
        args = parser().parse_args(['rae2822'])
        cfg, conditions = configuration(args)
        self.assertEqual(conditions['mach'],.729)
        self.assertEqual(conditions['alpha_deg'],2.31)
        self.assertIn('CONV_NUM_METHOD_FLOW= JST',cfg)
        self.assertIn('MUSCL_FLOW= NO',cfg)
        self.assertIn('LINEAR_SOLVER_PREC= ILU',cfg)
        self.assertIn('LINEAR_SOLVER_ERROR= 1E-6',cfg)
        self.assertIn('MGLEVEL= 3',cfg)
        self.assertIn('CONV_FIELD= ( RMS_NU_TILDE, DRAG )',cfg)
        self.assertEqual(conditions['solver_scheme'],'mg3')
        cfg, conditions = configuration(parser().parse_args(['rae2822','--rae-scheme','mg0']))
        self.assertIn('MGLEVEL= 0',cfg)
        self.assertIn('CFL_ADAPT= YES',cfg)
        self.assertIn('CONV_NUM_METHOD_FLOW= JST',cfg)
        self.assertEqual(conditions['solver_scheme'],'mg0')

    def test_flat_plate_runs_until_project_gate_criteria(self):
        cfg, _ = configuration(parser().parse_args(['flat_plate']))
        for line in ('MGLEVEL= 0','CFL_ADAPT= YES','LINEAR_SOLVER_PREC= ILU',
                     'CONV_FIELD= ( RMS_NU_TILDE, DRAG )','CONV_CAUCHY_EPS= 1e-8',
                     'CONV_RESIDUAL_MINVAL= -9.3'):
            self.assertIn(line,cfg)

    def test_c_grid_quality_farfield_and_growth(self):
        import math
        from types import SimpleNamespace
        from cfd.structured_airfoil import generate, two_sided
        s = two_sided(128, 1e-3, 4e-3)
        self.assertAlmostEqual(s[1]-s[0], 1e-3, delta=5e-5)
        self.assertAlmostEqual(s[-1]-s[-2], 4e-3, delta=2e-4)
        # Closed sharp-TE NACA 0012 in Selig order (TE-upper -> LE -> TE-lower).
        def thickness(x):
            return .6*(.2969*math.sqrt(x)-.126*x-.3516*x**2+.2843*x**3-.1036*x**4)
        xs = [.5*(1-math.cos(math.pi*k/64)) for k in range(65)]
        upper = [(x, thickness(x)) for x in reversed(xs)]
        lower = [(x, -thickness(x)) for x in xs[1:]]
        xy = upper+lower
        with tempfile.TemporaryDirectory() as tmp:
            info = generate(SimpleNamespace(level='coarse'), Path(tmp), xy, {'geometry': 'naca0012'})
            again = audit(Path(tmp)/'mesh.su2')
        self.assertEqual(info['cells'], again['cells'])
        self.assertEqual(again['nonpositive_cells'], 0)
        self.assertEqual(again['nonmanifold_edges'], 0)
        self.assertEqual(again['boundary_mismatches'], 0)
        self.assertGreater(again['minimum_corner_sine'], .5)
        self.assertEqual(again['markers'], {'WALL': 256, 'FARFIELD': 2*(48+128)+2*96})
        x0, x1, y0, y1 = again['bounds']
        self.assertLessEqual(x0, -98); self.assertGreaterEqual(x1, 100)
        self.assertLessEqual(y0, -98); self.assertGreaterEqual(y1, 98)
        self.assertLessEqual(info['max_normal_growth'], 1.2)
        self.assertLessEqual(info['max_streamwise_growth_wall'], 1.2)
        self.assertLessEqual(info['max_streamwise_growth'], 1.3)
        self.assertAlmostEqual(again['minimum_wall_connected_edge'], 2e-6, delta=1e-9)


if __name__ == '__main__':
    unittest.main()
