"""Solver gerektirmeyen anlamlı nümerik ve sonuç-durumu regresyonları."""
import math
from pathlib import Path

import numpy as np
import tempfile
import unittest

from validation.convergence import error, gci
from validation.study import evaluate
from fem.cases import frequencies, node_blocks, set_lines, tsai_wu
from fem import clt
from fem.coupon import element_stresses
from fem.wing_post import tsai_wu_ratio
from thermal.cases import energy_solution, stack_mesh
from cfd.inlet_metrics import calculate
from cfd.cases import csv_rows, pick, coordinates
from validation.common import Blocked, ROOT, digest, write_json
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

    def test_single_roundoff_difference_is_unresolved(self):
        for values in ([1, 1, 2], [1, 2, 2], [1, 1 + 1e-12, 2], [1, 2, 2 + 1e-12]):
            with self.subTest(values=values):
                self.assertEqual(gci([1, 2, 4], values)["status"], "PLATEAU_UNRESOLVED")
        self.assertEqual(gci([1, 2, 4], [1, 1 + 1e-12, 1 + 2e-12])["status"], "EXACT_OR_ROUNDOFF")

    def test_plateau_never_passes_study_including_coupon_spread_exception(self):
        for case in ("flat_plate", "coupon"):
            for values in ([1, 1, 1.001], [1, 1.001, 1.001]):
                with self.subTest(case=case, values=values), tempfile.TemporaryDirectory() as tmp:
                    for level, h, value in zip(("fine", "medium", "coarse"), (1, 2, 4), values):
                        row = dict(case=case, case_id=case, status="COMPUTED", mesh=dict(h=h),
                                   provenance=dict(params_sha256=digest(ROOT / "params.py")),
                                   code_sha256={}, execution=dict(executable_sha256="synthetic"),
                                   conditions={}, assumptions={}, acceptance_metrics=["cf_mean"],
                                   metrics=dict(cf_mean=value, cf_ittc=1., cf_schlichting=1.),
                                   errors=dict(cf_mean=dict(percent=0.)))
                        write_json(Path(tmp) / f"{level}.json", row)
                    result = evaluate(tmp)
                    self.assertEqual(result["status"], "REVIEW_REQUIRED")
                    self.assertIn("cf_mean: GCI PLATEAU_UNRESOLVED", result["reasons"])

    def test_missing_results_never_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(evaluate(tmp)["status"], "PENDING")

    def test_low_observed_order_uses_bounded_order_and_fs3(self):
        # Iter5 düz levha: p_gözlenen .434 << 2 -> p_kullanılan .5, Fs 3 (Roy/Roache).
        h = [52224 ** -.5, 29376 ** -.5, 13056 ** -.5]
        q = [.0028613266, .0028586462, .0028542517]
        plain = gci(h, q)
        bounded = gci(h, q, formal_order=2)
        self.assertAlmostEqual(plain["observed_order"], .434, delta=.01)
        self.assertEqual(plain["safety_factor"], 1.25)
        self.assertEqual(bounded["order_used"], .5)
        self.assertEqual(bounded["safety_factor"], 3.0)
        expected = 3 * abs(q[0] - q[1]) / ((h[1] / h[0]) ** .5 - 1) / q[0] * 100
        self.assertAlmostEqual(bounded["fine_gci_pct"], expected, places=9)
        self.assertGreater(bounded["fine_gci_pct"], 2 * plain["fine_gci_pct"])
        # Formal mertebeye yakın gözlenen p'de Roache Fs=1.25 korunur.
        near = gci([1, 2, 4], [2.5 + 3*x*x for x in (1, 2, 4)], formal_order=2)
        self.assertEqual(near["safety_factor"], 1.25)

    def test_stale_record_is_reported_even_when_study_incomplete(self):
        with tempfile.TemporaryDirectory() as tmp:
            row = dict(case="rae2822", level="coarse", status="UNCONVERGED", metrics={},
                       provenance=dict(params_sha256="0"*64), code_sha256={})
            write_json(Path(tmp) / "coarse.json", row)
            # Benchmark params.py okumaz; uygulama vakası (airfoil) params değişince eskir.
            self.assertEqual(evaluate(tmp)["status"], "PENDING")
            write_json(Path(tmp) / "coarse.json", dict(row, case="airfoil"))
            self.assertEqual(evaluate(tmp)["status"], "STALE")
            row["provenance"]["params_sha256"] = digest(ROOT / "params.py")
            # Test dosyaları, rapor aracı ve başka alanın kaynakları CFD sonucunu eskitmez; vaka kaynağı eskitir.
            row["code_sha256"] = {"validation\\test_validation.py": "0"*64, "fem\\cases.py": "0"*64,
                                  "validation\\report.py": "0"*64}
            write_json(Path(tmp) / "coarse.json", row)
            self.assertEqual(evaluate(tmp)["status"], "PENDING")
            row["code_sha256"]["cfd\\cases.py"] = "0"*64
            write_json(Path(tmp) / "coarse.json", row)
            self.assertEqual(evaluate(tmp)["status"], "STALE")


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


class CltTests(unittest.TestCase):
    """Bağımsız kapalı formlarla CLT (fem/clt.py) doğrulaması; CalculiX kupon benchmarkının referansıdır."""
    UD = dict(E1=125e9, E2=9e9, nu12=.3, G12=5e9, G13=5e9, G23=3.5e9)

    def test_single_ply_axes_and_rotation(self):
        e = clt.engineering_constants([(self.UD, 1e-3, 0.)])
        for key, ref in (("Ex", 125e9), ("Ey", 9e9), ("Gxy", 5e9), ("nuxy", .3)):
            self.assertAlmostEqual(e[key] / ref, 1., places=10)
        self.assertAlmostEqual(clt.engineering_constants([(self.UD, 1e-3, 90.)])["Ex"] / 9e9, 1., places=10)
        # Lekhnitskii dönüşümü: 1/Ex(θ) = c^4/E1 + (1/G12 - 2nu12/E1) s^2 c^2 + s^4/E2
        for theta in (15., 30., 45., 60.):
            c, s_ = math.cos(math.radians(theta)), math.sin(math.radians(theta))
            inv = c**4 / 125e9 + (1 / 5e9 - 2 * .3 / 125e9) * s_**2 * c**2 + s_**4 / 9e9
            self.assertAlmostEqual(clt.engineering_constants([(self.UD, 1e-3, theta)])["Ex"] * inv, 1., places=10)
        q0, q180 = clt.q_bar(self.UD, 20.), clt.q_bar(self.UD, 200.)
        self.assertTrue(abs(q0 - q180).max() < 1e-6 * abs(q0).max())

    def test_coupling_and_bending_closed_forms(self):
        t = .2e-3
        a, b, d, h = clt.abd([(self.UD, t, 0.), (self.UD, t, 90.)])
        q = clt.q_matrix(self.UD)
        self.assertAlmostEqual(b[0, 0] / ((q[1, 1] - q[0, 0]) * t * t / 2), 1., places=10)
        self.assertAlmostEqual(b[1, 1], -b[0, 0], delta=1e-9 * abs(b[0, 0]))
        a, b, d, h = clt.abd([(self.UD, t, 0.), (self.UD, t, 90.), (self.UD, t, 90.), (self.UD, t, 0.)])
        self.assertTrue(abs(b).max() < 1e-12 * abs(a).max())
        iso = dict(E1=70e9, E2=70e9, nu12=.3, G12=70e9 / 2.6)
        e = clt.engineering_constants([(iso, 2e-3, 0.)])
        self.assertAlmostEqual(e["D11"] / (70e9 * 8e-9 / (12 * (1 - .09))), 1., places=10)
        self.assertAlmostEqual(e["D11_beam"] / (70e9 * 8e-9 / 12), 1., places=10)
        w, bend, shear = clt.three_point_deflection([(iso, 2e-3, 0.)], 10., .2, .02)
        self.assertAlmostEqual(bend / (10 * .2**3 / (48 * 70e9 * .02 * 8e-9 / 12)), 1., places=10)
        self.assertAlmostEqual(shear / (10 * .2 / (4 * .02 * 5 / 6 * 70e9 / 2.6 * 2e-3)), 1., places=10)

    def test_ply_stress_equilibrium_and_offset_reference(self):
        lay = [(self.UD, .2e-3, 0.), (self.UD, .2e-3, 90.), (self.UD, .2e-3, 90.), (self.UD, .2e-3, 0.)]
        plies, _ = clt.ply_stresses(lay, [1000., 0., 0.])
        # Global sigma_x katmanlar boyunca toplamı Nx olmalı (0° katta s11, 90° katta s22 = sigma_x).
        self.assertAlmostEqual((plies[0][0] + plies[1][1] + plies[2][1] + plies[3][0]) * .2e-3, 1000., places=6)
        unsym = [(self.UD, .6e-3, 0.), (self.UD, .2e-3, 90.)]
        k_mid = clt.ply_stresses(unsym, [1000., 0., 0.])[1][3:]
        k_top = clt.ply_stresses(unsym, [1000., 0., 0.], z_ref=.8e-3)[1][3:]
        # Referans yüzey değişince yük aynı yüzeye uygulandığından eğrilik değişir; ABD invariantı:
        a, b, d, h = clt.abd(unsym)
        a2, b2, d2, _ = clt.abd(unsym, z_ref=.8e-3)
        self.assertTrue(abs(d2 - (d + 2 * (-.4e-3) * b + .4e-3**2 * a)).max() < 1e-9 * abs(d2).max())
        self.assertFalse(np.allclose(k_mid, k_top))

    def test_sandwich_shear_and_strength_ratio(self):
        core = dict(E1=70e6, E2=70e6, nu12=.3, G12=19e6, G13=19e6, G23=19e6)
        lay = [(self.UD, 1e-3, 0.), (core, 4e-3, 0.), (self.UD, 1e-3, 0.)]
        self.assertAlmostEqual(clt.shear_stiffness(lay, 1) / (19e6 * 5e-3**2 / 4e-3), 1., places=10)
        mat = dict(Xt=1000., Xc=800., Yt=50., Yc=150., S12=60., F12=-.5 / math.sqrt(1000 * 800 * 50 * 150))
        for stress in ((300., 10., 5.), (-200., -40., 20.), (0., 0., 30.)):
            r = tsai_wu_ratio(*stress, mat)
            self.assertAlmostEqual(tsai_wu(*(r * v for v in stress), mat), 1., places=10)

    def test_composite_stress_parser_ignores_orientation_name_digits(self):
        text = "\n".join([
            " stresses (elem, integ.pnt.,sxx,syy,szz,sxy,sxz,syz) for set E and time  0.1E+01", "",
            "         7   9  1.0E+06 -2.0E+05  0.0E+00  3.0E+04  0.0E+00  0.0E+00 OR12_shell_0000000007", "",
            " stresses (elem, integ.pnt.,sxx,syy,szz,sxy,sxz,syz) for set E and time  0.2E+01", "",
            "         7   9  9.0E+09  0.0E+00  0.0E+00  0.0E+00  0.0E+00  0.0E+00 OR12_shell_0000000007", ""])
        s = element_stresses(text)
        self.assertEqual(s[(7, 9)], [1e6, -2e5, 0., 3e4, 0., 0.])  # yalnız ilk (statik) blok


class WingStudyGuardTests(unittest.TestCase):
    """Kanat rijitleştirme çalışması inceleme düzeltmeleri (Codex çapraz incelemesi, iter5)."""

    def test_variants_define_every_option_explicitly(self):
        from fem.stiffening_study import VARIANTS
        from fem.wing_shell import OPTION_KEYS
        for name, env in VARIANTS.items():
            self.assertEqual(set(env), set(OPTION_KEYS), name)
            self.assertTrue(all(str(v).strip() for v in env.values()), name)

    def test_variant_without_explicit_options_is_blocked(self):
        import os
        from unittest import mock
        from fem.wing_shell import options
        with mock.patch.dict(os.environ, {"HZ750_VARIANT": "x", "HZ750_SKIN_PLIES": "3,1"}, clear=False):
            for k in ("HZ750_WEB_EXTRA", "HZ750_RIB_PITCH", "HZ750_RIB_PLIES"):
                os.environ.pop(k, None)
            with self.assertRaises(Blocked):
                options()

    def test_rib_pitch_must_be_representable_on_mesh(self):
        from fem.wing_shell import rib_rows
        b2 = .7245688
        self.assertEqual(rib_rows(32, .0216, b2), list(range(1, 33)))       # ince: her şerit sınırı
        self.assertEqual(rib_rows(16, .043, b2), list(range(1, 17)))
        self.assertEqual(rib_rows(16, .086, b2), list(range(2, 17, 2)))
        for ny, pitch in ((16, .0216), (8, .043), (32, .065)):          # orta 21.6 mm, kaba 43 mm, 65 mm
            with self.assertRaises(Blocked):
                rib_rows(ny, pitch, b2)

    def test_every_review_flag_is_required(self):
        import re
        from fem import wing_review
        from fem.cases import REQUIRED_REVIEW_FLAGS
        documented = set(re.findall(r"^  (\w+)\s+:", wing_review.__doc__, re.M))
        self.assertIn("sandwich_no_overlap", documented)
        self.assertEqual(documented, set(REQUIRED_REVIEW_FLAGS))

    def test_wing_gate_needs_coupon_and_iter4_reference_is_pinned(self):
        from validation.run_case import CASES
        self.assertEqual(set(CASES["wing"][2]), {"cantilever", "coupon"})
        from fem.stiffening_study import iter4_reference
        gvt, info = iter4_reference()
        self.assertAlmostEqual(gvt["dolu"]["f1T"], 305.677, places=2)
        self.assertEqual(info["sha256"][:12], "933f5d7dad5c")


if __name__ == "__main__":
    unittest.main()
