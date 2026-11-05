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


if __name__ == '__main__':
    unittest.main()
