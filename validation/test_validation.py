"""Solver gerektirmeyen anlamlı nümerik ve sonuç-durumu regresyonları."""
import math
from pathlib import Path
import tempfile
import unittest

from validation.convergence import error, gci
from validation.study import evaluate
from fem.cases import frequencies, node_blocks, set_lines, tsai_wu
from thermal.cases import energy_solution, stack_mesh
from cfd.inlet_metrics import calculate
from cfd.cases import csv_rows, pick, coordinates
from validation.common import Blocked
from types import SimpleNamespace


class GridConvergenceTests(unittest.TestCase):
    def test_auxiliary_nan_does_not_hide_invalid_physical_field(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"history.csv"
            path.write_text('"CD","Buffet","CL"\n0.003,nan,inf\n')
            row=csv_rows(path)[0]
            self.assertEqual(pick(row,"CD"),.003)
            with self.assertRaises(Blocked): pick(row,"CL")

    def test_lednicer_geometry_becomes_closed_selig_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"rae.dat"
            upper=[(i/19,.01*math.sin(math.pi*i/19)) for i in range(20)]
            lower=[(x,-y) for x,y in upper]
            path.write_text('Example\n20 20\n'+ '\n'.join(f'{x} {y}' for x,y in upper+lower))
            points,_=coordinates(SimpleNamespace(case="rae2822",airfoil=path))
            self.assertEqual(points[0][0],1.)
            self.assertEqual(points[-1][0],1.)
            self.assertEqual(min(range(len(points)),key=lambda i:points[i][0]),19)

    def test_nonuniform_second_order(self):
        h = [.1, .18, .33]
        result = gci(h, [2.5 + 3*x*x for x in h])
        self.assertEqual(result["status"], "ESTIMATED")
        self.assertAlmostEqual(result["observed_order"], 2, places=10)
        self.assertAlmostEqual(result["richardson"], 2.5, places=12)
        self.assertAlmostEqual(result["fine_gci_absolute"], 1.25 * .03, places=12)

    def test_exact_and_oscillatory_are_not_fabricated_orders(self):
        self.assertEqual(gci([1, 2, 4], [1, 1, 1])["status"], "EXACT_OR_ROUNDOFF")
        self.assertEqual(gci([1, 2, 4], [1, 2, 1.5])["status"], "OSCILLATORY")
        self.assertEqual(gci([1, 2, 4], [1, 3, 4])["status"], "NO_OBSERVED_ORDER")

    def test_invalid_and_insufficient_grids(self):
        with self.assertRaises(ValueError):
            gci([2, 1, 3], [1, 2, 3])
        self.assertEqual(gci([1, 1.1, 1.2], [1, 2, 3])["status"], "INSUFFICIENT_REFINEMENT")
        self.assertIsNone(error(1e-6, 0)["percent"])

    def test_missing_results_never_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(evaluate(tmp)["status"], "PENDING")


class ThermalTests(unittest.TestCase):
    def test_linear_network_matches_series_resistances(self):
        # Bağımsız kapalı form: hot--hgap--slab--hexternal--ambient.
        layer = [("SHELL", .02, .5)]
        case = dict(emissivity_effective=0., emissivity_external=0., k_air=.1, gap_m=.01,
                    h_bypass=0., h_external=20., motor_K=500., bypass_K=300., external_K=300.)
        r = energy_solution(layer, case)
        q = 200 / (.01/.1 + .02/.5 + 1/20)
        self.assertAlmostEqual(r["heat_flux_W_m2"], q, places=8)
        self.assertAlmostEqual(r["inner_K"], 500 - q*.1, places=8)

    def test_bricks_have_positive_orientation_and_right_boundary_faces(self):
        nodes, elements, _, _ = stack_mesh([("SHELL", .1, 10)], 1)
        for conn in elements.values():
            p = [nodes[n] for n in conn]
            v = [[p[i][j]-p[0][j] for j in range(3)] for i in (1, 3, 4)]
            determinant = (v[0][0]*(v[1][1]*v[2][2]-v[1][2]*v[2][1])
                           - v[0][1]*(v[1][0]*v[2][2]-v[1][2]*v[2][0])
                           + v[0][2]*(v[1][0]*v[2][1]-v[1][1]*v[2][0]))
            self.assertGreater(determinant, 0)
            self.assertEqual(len({p[i][0] for i in (1, 2, 6, 5)}), 1)  # x+ face4
            self.assertEqual(len({p[i][0] for i in (3, 0, 4, 7)}), 1)  # x- face6


class DistortionTests(unittest.TestCase):
    @staticmethod
    def disk(shift=0):
        return [dict(area=1/360, rho=1., un=10., p=900., pt=1000. if i >= 60 else 950.,
                     theta_deg=(i+.5+shift) % 360) for i in range(360)]

    def test_sector_deficit_and_rotation_invariance(self):
        r = calculate(self.disk(), 1000)
        self.assertAlmostEqual(r["DC60"], ((1000*5/6+950/6)-950)/50)
        self.assertAlmostEqual(r["mdot_kg_s"], 10.)
        self.assertAlmostEqual(r["DC60"], calculate(self.disk(137), 1000)["DC60"])
        self.assertAlmostEqual(r["recovery_mass"], (1000*5/6+950/6)/1000)

    def test_backflow_is_not_silently_removed(self):
        rows = self.disk()
        rows[0]["un"] = -1
        with self.assertRaises(ValueError):
            calculate(rows, 1000)


class FemTests(unittest.TestCase):
    def test_tsai_wu_uniaxial_limits(self):
        mat = dict(Xt=1000., Xc=800., Yt=50., Yc=150., S12=60., F12=0.)
        for stress in ((1000., 0, 0), (-800., 0, 0), (0, 50., 0), (0, -150., 0), (0, 0, 60.)):
            self.assertAlmostEqual(tsai_wu(*stress, mat), 1.)

    def test_dat_parser_synthetic_format(self):
        # Biçim testi; bir solver çalıştırmasının çıktısı olduğu iddia edilmez.
        text = ' displacements (vx,vy,vz) for set TIP and time 1\n\n 1 0. 0. -1.D-3\n\n temperatures for set NALL\n\n 1 3.0E2\n'
        self.assertEqual(node_blocks(text, "displacements")[0][1][2], -.001)
        self.assertEqual(node_blocks(text, "temperatures")[0][1][0], 300)
        freq = ' E I G E N V A L U E   O U T P U T\n MODE NO. EIGENVALUE OMEGA FREQUENCY\n'
        freq += '\n'.join(f' {i} 1.0 2.0 {i*10}.0 0.0' for i in range(1, 6))
        self.assertEqual(frequencies(freq), [10., 20., 30., 40., 50.])

    def test_ccx_set_line_limit(self):
        self.assertEqual([len(s.split(',')) for s in set_lines(range(33))], [16, 16, 1])


if __name__ == "__main__":
    unittest.main()
