"""CLT kupon benchmarkı: CalculiX *SHELL SECTION, COMPOSITE (S8R) girdisinin yorumlanması.

Her laminat için tek bir deck içinde birbirinden bağımsız dört numune çözülür:
  TX/TY  : kare levha, karşılıklı kenarlarda tutarlı (1/6, 2/3, 1/6) Nx veya Ny; minimum rijit cisim
           kısıtı -> homojen membran+eğrilik durumu. Ex, Ey ve tabaka gerilmeleri (GLOBAL=NO).
  SH     : dört kenarda Nxy; Gxy.
  B3     : dar şerit üç nokta eğilme. Mesnet ve yük hatları genişlik boyunca tutarlı ağırlıkla;
           mesnetler *EQUATION ile "ağırlıklı ortalama w = 0" (çizgisel düzgün tepki), yuvarlanma
           tek bir antisimetrik denklemle tutulur. Böylece antiklastik/burulma eğriliği serbesttir ve
           referans dar kiriş b/d11 (CLT ters ABD) + eşdeğer tek katman kayma terimidir.
           D11_beam, L/8-L/4-3L/8 genişlik ortalaması w ikinci farkından (kayma terimi doğrusal,
           ikinci farkta sıfır) çıkarılır.
Referanslar fem/clt.py (bağımsız CLT). Kabul eşiği %2 (ince ağ) ve üç ağda ağdan bağımsızlık/GCI.
"""
import math

import numpy as np

from fem import clt

# b/L <= 1/30: yük hattındaki antiklastik uyumsuzluk (plaka etkisi) dar kiriş referansını <~%0.5 bozar.
SPAN_B3 = {"UD0": .3, "UD45S": .3, "SKIN_F": .4, "CAP": .4, "WEB": .3}
WIDTH_B3 = .01
PLATE = .2   # sandviç yük girişi sönüm boyu (çekirdek kayma gecikmesi) ölçüm bölgesine girmesin
NX_FORCE = 1000.0   # N/m
P_B3 = 1.0          # N
LIMIT_PCT = 2.0


def laminates(mats):
    """(katlar alt->üst, OFFSET, sandviç çekirdek indeksi). CAP/SKIN_F/WEB kanat kök kat planıdır."""
    from structures import structures as ST
    ud, fab, core = mats["UD"], mats["FAB"], mats["CORE"]
    tu, tf, tc = ST.MAT["UD"]["t_ply"], ST.MAT["FAB"]["t_ply"], ST.MAT["CORE"]["t"]
    nf = 3
    return {
        "UD0": ([(ud, tu, 0.)] * 5, 0., None),
        "UD45S": ([(ud, tu, 45.), (ud, tu, -45.), (ud, tu, -45.), (ud, tu, 45.)], 0., None),
        "SKIN_F": ([(fab, nf * tf, 45.), (core, tc, 0.), (fab, nf * tf, 45.)], 0., 1),
        # Kök kiriş kapağı: 3 kat UD iç yüzde + sandviç; kanattaki gibi OFFSET=0.5 ve simetrik değil.
        "CAP": ([(ud, 3 * tu, 0.), (fab, nf * tf, 45.), (core, tc, 0.), (fab, nf * tf, 45.)], .5, 2),
        "WEB": ([(fab, 3 * tf, 45.)], 0., None),
    }


def _orientation_name(theta):
    return "OR_%s%03d" % ("M" if theta < 0 else "P", abs(round(theta)))


def _weights(n_el, length):
    """Kuadratik kenar boyunca 2n+1 düğüm için tutarlı yük ağırlıkları (toplam = length)."""
    w = np.zeros(2 * n_el + 1)
    seg = length / n_el
    for e in range(n_el):
        w[2 * e] += seg / 6
        w[2 * e + 1] += 2 * seg / 3
        w[2 * e + 2] += seg / 6
    return w


class Plate:
    def __init__(self, first_node, first_el, lx, ly, nx, ny, x0):
        self.nx, self.ny, self.lx, self.ly = nx, ny, lx, ly
        self.first_node = first_node
        self.nodes, self.elements = {}, {}
        for j in range(2 * ny + 1):
            for i in range(2 * nx + 1):
                if i % 2 and j % 2:
                    continue  # quad8: merkez düğüm yok
                self.nodes[self.id(i, j)] = (x0 + lx * i / (2 * nx), ly * j / (2 * ny), 0.)
        tag = first_el
        for ej in range(ny):
            for ei in range(nx):
                i, j = 2 * ei, 2 * ej
                self.elements[tag] = [self.id(i, j), self.id(i + 2, j), self.id(i + 2, j + 2), self.id(i, j + 2),
                                      self.id(i + 1, j), self.id(i + 2, j + 1), self.id(i + 1, j + 2), self.id(i, j + 1)]
                tag += 1

    def id(self, i, j):
        return self.first_node + i + (2 * self.nx + 1) * j

    def column(self, i):
        return [self.id(i, j) for j in range(2 * self.ny + 1)]

    def row(self, j):
        return [self.id(i, j) for i in range(2 * self.nx + 1)]


def offset_deck(mats):
    """Ayrı küçük deck: CAP (OFFSET=0.5) tek levha, *NODE FILE OUTPUT=3D ile genişletilmiş geometri.

    OUTPUT=3D ana kupon deck'inde kullanılmaz: CCX 2.20'de *NODE PRINT kabuk düğüm sonuçlarını bozduğu
    gözlendi (kaba/orta/ince kupon değerleri anlamsızlaştı).
    """
    layers, offset, _ = laminates(mats)["CAP"]
    plate = Plate(1, 1, PLATE, PLATE, 2, 2, 0.)
    lines = ["*NODE, NSET=NALL"] + [f"{n}, {p[0]:.10e}, {p[1]:.10e}, {p[2]:.10e}" for n, p in plate.nodes.items()]
    lines += ["*ELEMENT, TYPE=S8R, ELSET=EALL"] + [f"{t}, " + ", ".join(map(str, c)) for t, c in plate.elements.items()]
    for mname, m in mats.items():
        lines += [f"*MATERIAL, NAME={mname}", "*ELASTIC, TYPE=ENGINEERING CONSTANTS",
                  ", ".join(f"{m[k]:.10e}" for k in ("E1", "E2", "E3", "nu12", "nu13", "nu23", "G12", "G13")),
                  f"{m['G23']:.10e}", "*DENSITY", f"{m['rho']:.10e}"]
    for th in sorted({th for _, _, th in layers}):
        c, s = math.cos(math.radians(th)), math.sin(math.radians(th))
        lines += [f"*ORIENTATION, NAME={_orientation_name(th)}", f"{c:.12f}, {s:.12f}, 0., {-s:.12f}, {c:.12f}, 0."]
    lines += [f"*SHELL SECTION, ELSET=EALL, COMPOSITE, OFFSET={offset}"]
    lines += [f"{t:.10e}, , {m['name']}, {_orientation_name(th)}" for m, t, th in layers]
    n = plate.id
    lines += ["*BOUNDARY", f"{n(0, 0)}, 1, 3", f"{n(4, 0)}, 2, 3", f"{n(0, 4)}, 3, 3",
              "*STEP", "*STATIC, SOLVER=SPOOLES", "*CLOAD", f"{n(4, 0)}, 1, 1.", f"{n(0, 0)}, 1, -1.",
              "*NODE FILE, OUTPUT=3D", "U", "*END STEP"]
    return chr(10).join(lines) + chr(10), sum(t for _, t, _ in layers)


def build(level, mats):
    factor = 2 ** ("coarse", "medium", "fine").index(level)
    lams = laminates(mats)
    lines = ["*HEADING", "HIZ750 iter5 CLT coupon benchmark, SI", "*NODE, NSET=NALL"]
    elements, sections, bc, loads, equations = [], [], [], [], []
    info, node0, el0, x0 = {}, 1, 1, 0.
    thetas = sorted({th for layers, _, _ in lams.values() for _, _, th in layers})
    for name, (layers, offset, core) in lams.items():
        specimens = {}
        for test in ("TX", "TY", "SH", "B3"):
            if test == "B3":
                plate = Plate(node0, el0, SPAN_B3[name], WIDTH_B3, 8 * factor, 4 * factor, x0)
            else:
                plate = Plate(node0, el0, PLATE, PLATE, 4 * factor, 4 * factor, x0)
            # Sıkı numaralama: CCX dizileri en büyük eleman/düğüm numarasıyla boyutlanır.
            node0 += (2 * plate.nx + 1) * (2 * plate.ny + 1)
            el0 += plate.nx * plate.ny
            x0 += 1.
            elset = f"E_{name}_{test}"
            lines += [f"{n}, {p[0]:.10e}, {p[1]:.10e}, {p[2]:.10e}" for n, p in plate.nodes.items()]
            elements += [f"*ELEMENT, TYPE=S8R, ELSET={elset}"]
            elements += [f"{t}, " + ", ".join(map(str, c)) for t, c in plate.elements.items()]
            sections += [f"*SHELL SECTION, ELSET={elset}, COMPOSITE, OFFSET={offset}"]
            sections += [f"{t:.10e}, , {m['name']}, {_orientation_name(th)}" for m, t, th in layers]
            n, nx, ny = plate.id, 2 * plate.nx, 2 * plate.ny
            if test in ("TX", "TY", "SH"):
                wx, wy = _weights(plate.nx, plate.lx), _weights(plate.ny, plate.ly)
                # Minimum kısıt: (0,0) u,v,w; düzlem içi dönme TX/SH'de (Lx,0) v, TY'de (0,Ly) u ile.
                bc += [f"{n(0, 0)}, 1, 3", f"{n(nx, 0)}, 3, 3", f"{n(0, ny)}, 3, 3"]
                bc += [f"{n(0, ny)}, 1, 1"] if test == "TY" else [f"{n(nx, 0)}, 2, 2"]
                if test == "TX":
                    for j, w in enumerate(wy):
                        loads += [f"{n(nx, j)}, 1, {NX_FORCE * w:.10e}", f"{n(0, j)}, 1, {-NX_FORCE * w:.10e}"]
                elif test == "TY":
                    for i, w in enumerate(wx):
                        loads += [f"{n(i, ny)}, 2, {NX_FORCE * w:.10e}", f"{n(i, 0)}, 2, {-NX_FORCE * w:.10e}"]
                else:
                    for j, w in enumerate(wy):
                        loads += [f"{n(nx, j)}, 2, {NX_FORCE * w:.10e}", f"{n(0, j)}, 2, {-NX_FORCE * w:.10e}"]
                    for i, w in enumerate(wx):
                        loads += [f"{n(i, ny)}, 1, {NX_FORCE * w:.10e}", f"{n(i, 0)}, 1, {-NX_FORCE * w:.10e}"]
            else:
                wy = _weights(plate.ny, plate.ly)
                mid = ny // 2
                bc += [f"{n(0, mid)}, 1, 2", f"{n(nx, mid)}, 2, 2"]
                for i in (0, nx):
                    terms = [(n(i, j), 3, wy[j]) for j in range(ny + 1)]
                    equations.append(terms)
                # Yuvarlanma: iki mesnet hattının ağırlıklı birinci momentlerinin toplamı sıfır.
                ys = np.linspace(-plate.ly / 2, plate.ly / 2, ny + 1)
                roll = [(n(i, j), 3, wy[j] * ys[j]) for i in (nx, 0) for j in range(ny + 1) if j != mid]
                # Bağımlı serbestlik: denklemlerde birinci terim; mesnet denklemlerinde j=0, burada j=ny (B tarafı).
                roll.sort(key=lambda r: 0 if r[0] == n(nx, ny) else 1)
                equations.append(roll)
                for j, w in enumerate(wy):
                    loads.append(f"{n(nx // 2, j)}, 3, {-P_B3 * w / plate.ly:.10e}")
            specimens[test] = dict(x0=x0 - 1., nx=nx, ny=ny, first=plate.first_node, lx=plate.lx, ly=plate.ly,
                                   elements=[min(plate.elements), max(plate.elements)], elset=elset)
        info[name] = dict(specimens=specimens, offset=offset, core=core)
    lines += elements
    for mname, m in mats.items():
        lines += [f"*MATERIAL, NAME={mname}", "*ELASTIC, TYPE=ENGINEERING CONSTANTS",
                  ", ".join(f"{m[k]:.10e}" for k in ("E1", "E2", "E3", "nu12", "nu13", "nu23", "G12", "G13")),
                  f"{m['G23']:.10e}", "*DENSITY", f"{m['rho']:.10e}"]
    for th in thetas:
        c, s = math.cos(math.radians(th)), math.sin(math.radians(th))
        lines += [f"*ORIENTATION, NAME={_orientation_name(th)}", f"{c:.12f}, {s:.12f}, 0., {-s:.12f}, {c:.12f}, 0."]
    lines += sections
    lines += ["*BOUNDARY"] + bc
    for terms in equations:
        lines += ["*EQUATION", str(len(terms))]
        flat = [f"{a}, {b}, {c:.12e}" for a, b, c in terms]
        lines += [", ".join(flat[k:k + 4]) for k in range(0, len(flat), 4)]
    # CCX 2.20 Windows varsayılan PaStiX çözücüsü serbest yüzen/denklemli kupon sisteminde %1-%100
    # gürültü üretti (kaba/orta/ince salınım); SPOOLES doğrudan çözücü kararlı ve tekrarlanabilir.
    lines += ["*STEP", "*STATIC, SOLVER=SPOOLES", "*CLOAD"] + loads
    lines += ["*NODE PRINT, NSET=NALL", "U"]
    for name in info:
        lines += [f"*EL PRINT, ELSET={info[name]['specimens']['TX']['elset']}, GLOBAL=NO", "S"]
    lines += ["*END STEP"]
    nodes = sum((s["nx"] + 1) * (s["ny"] + 1) - (s["nx"] // 2) * (s["ny"] // 2)
                for v in info.values() for s in v["specimens"].values())
    return "\n".join(lines) + "\n", info, dict(factor=factor, nodes=nodes)


def element_stresses(text):
    """İlk adımın *EL PRINT S blokları: {(eleman, int.nokta): [sxx, syy, szz, sxy, sxz, syz]}; isim sütunu atlanır.

    CCX print istekleri sonraki adımlara taşınır (ör. *FREQUENCY modları için de gerilme basılır);
    yalnız ilk (statik) blok okunur.
    """
    out, active, first_time = {}, False, None
    for line in text.splitlines():
        if "stresses" in line.lower():
            time = line.split("time")[-1].strip() if "time" in line else None
            if first_time is None:
                first_time = time
            elif time != first_time:
                break  # sonraki adım (ör. *FREQUENCY) bloğu; aynı adımdaki diğer ELSET blokları okunur
            active = True
            continue
        if not active:
            continue
        parts = line.split()
        if len(parts) >= 8:
            try:
                key = (int(parts[0]), int(parts[1]))
                out[key] = [float(v.replace("D", "E")) for v in parts[2:8]]
            except ValueError:
                active = False
        elif line.strip() and out:
            active = False
    return out


def expanded_z_range(frd_text, x_lo, x_hi):
    """OUTPUT=3D FRD düğüm bloğundan genişletilmiş katı düğümlerin z aralığı (OFFSET kontrolü)."""
    zs = []
    for line in frd_text.splitlines():
        if line.startswith(" -1") and len(line) >= 49:
            x, z = float(line[13:25]), float(line[37:49])
            if x_lo - 1e-9 <= x <= x_hi + 1e-9:
                zs.append(z)
        elif line.startswith(" -3"):
            break
    return (min(zs), max(zs)) if zs else (None, None)


def references(mats):
    ref = {}
    for name, (layers, offset, core) in laminates(mats).items():
        e = clt.engineering_constants(layers)
        span = SPAN_B3[name]
        w, bend, shear = clt.three_point_deflection(layers, P_B3, span, WIDTH_B3)
        w_sw = clt.three_point_deflection(layers, P_B3, span, WIDTH_B3, core)[0] if core is not None else w
        plies, _ = clt.ply_stresses(layers, [NX_FORCE, 0., 0.])
        ref[name] = dict(Ex=e["Ex"], Ey=e["Ey"], Gxy=e["Gxy"], nuxy=e["nuxy"], D11_plate=e["D11"],
                         D11_beam=e["D11_beam"], w_B3=w, w_B3_bending=bend, w_B3_shear_esl=shear,
                         w_B3_sandwich_theory=w_sw, h=e["h"], ply_TX=[list(map(float, p)) for p in plies],
                         layers=[dict(material=m["name"], t=t, theta=th) for m, t, th in layers])
    return ref


def postprocess(text, info, mats):
    from fem.cases import node_blocks
    blocks = node_blocks(text, "displacements")
    if not blocks:
        raise RuntimeError("Kupon DAT içinde yer değiştirme yok")
    u = blocks[0]
    stress = element_stresses(text)
    ref = references(mats)
    metrics, errors, detail = {}, {}, {}
    for name, item in info.items():
        sp = item["specimens"]
        h = ref[name]["h"]

        def node(test, i, j):
            s = sp[test]
            return s["first"] + i + (s["nx"] + 1) * j

        def edge_mean(test, comp, i=None, j=None):
            s = sp[test]
            ids = [node(test, i, jj) for jj in range(s["ny"] + 1)] if i is not None else \
                  [node(test, ii, j) for ii in range(s["nx"] + 1)]
            w = _weights(s["ny"] // 2, 1.) if i is not None else _weights(s["nx"] // 2, 1.)
            return float(sum(wi * u[k][comp] for wi, k in zip(w, ids)))

        def central_mean(test, comp, i=None, j=None):
            # Yük giriş kenarlarından uzak (St-Venant) orta yarı; ölçüm "gerinim ölçer" gibi iç bölgede.
            s = sp[test]
            if i is not None:
                ids = [node(test, i, jj) for jj in range(s["ny"] // 4, 3 * s["ny"] // 4 + 1)]
                w = _weights(s["ny"] // 4, 1.)
            else:
                ids = [node(test, ii, j) for ii in range(s["nx"] // 4, 3 * s["nx"] // 4 + 1)]
                w = _weights(s["nx"] // 4, 1.)
            return float(sum(wi * u[k][comp] for wi, k in zip(w, ids)))

        s = sp["TX"]
        q1, q3 = s["nx"] // 4, 3 * s["nx"] // 4
        ex = (central_mean("TX", 0, i=q3) - central_mean("TX", 0, i=q1)) / (s["lx"] / 2)
        s = sp["TY"]
        ey = (central_mean("TY", 1, j=3 * s["ny"] // 4) - central_mean("TY", 1, j=s["ny"] // 4)) / (s["ly"] / 2)
        s = sp["SH"]
        gam = ((central_mean("SH", 0, j=3 * s["ny"] // 4) - central_mean("SH", 0, j=s["ny"] // 4)) / (s["ly"] / 2)
               + (central_mean("SH", 1, i=3 * s["nx"] // 4) - central_mean("SH", 1, i=s["nx"] // 4)) / (s["lx"] / 2))
        s = sp["B3"]
        nx = s["nx"]
        wc = edge_mean("B3", 2, i=nx // 2)
        w1, w2, w3 = (edge_mean("B3", 2, i=k * nx // 8) for k in (1, 2, 3))
        delta = s["lx"] / 8
        kappa = (w1 - 2 * w2 + w3) / delta ** 2  # sarkma: w<0 ve w''>0, M>0
        moment = P_B3 / 2 * s["lx"] / 4 / s["ly"]
        values = {f"{name}_Ex": NX_FORCE / (h * ex), f"{name}_Ey": NX_FORCE / (h * ey),
                  f"{name}_Gxy": NX_FORCE / (h * gam), f"{name}_D11beam": moment / kappa,
                  f"{name}_wB3": -wc}
        refs = {f"{name}_Ex": ref[name]["Ex"], f"{name}_Ey": ref[name]["Ey"], f"{name}_Gxy": ref[name]["Gxy"],
                f"{name}_D11beam": ref[name]["D11_beam"], f"{name}_wB3": ref[name]["w_B3"]}
        # Tabaka gerilmeleri: her tabaka 8 nokta (2x2 düzlem x 2 kalınlık), alttan üste; eleman ortalaması.
        e0, e1 = sp["TX"]["elements"]
        pnx = sp["TX"]["nx"] // 2
        central = [e0 + ei + pnx * ej for ej in range(pnx // 4, 3 * pnx // 4) for ei in range(pnx // 4, 3 * pnx // 4)]
        nlayer = len(ref[name]["layers"])
        layer_mean = []
        for k in range(nlayer):
            vals = [stress[(e, 8 * k + p)] for e in central for p in range(1, 9) if (e, 8 * k + p) in stress]
            if len(vals) != 8 * len(central):
                raise RuntimeError(f"{name}: tabaka {k+1} için 8 nokta/eleman bulunamadı; integration point sırası farklı")
            arr = np.mean(vals, axis=0)
            layer_mean.append([float(arr[0]), float(arr[1]), float(arr[3])])
        for k, (fe, cl) in enumerate(zip(layer_mean, ref[name]["ply_TX"])):
            if ref[name]["layers"][k]["material"] == "CORE":
                continue
            comp = int(np.argmax(np.abs(cl)))
            key = f"{name}_TX_L{k+1}_s{('11', '22', '12')[comp]}"
            values[key], refs[key] = fe[comp], cl[comp]
        for key, v in values.items():
            metrics[key] = float(v)
            errors[key] = dict(absolute=float(v - refs[key]), percent=float(100 * (v - refs[key]) / abs(refs[key])))
        detail[name] = dict(layer_stress_TX_fe=layer_mean, kappa_B3=kappa, w_center=wc)
    return metrics, errors, ref, detail


def solve(args, work, solver):
    from validation.common import digest, run_solver, require_module
    from fem.wing_shell import materials
    mats = materials()
    for k, m in mats.items():
        m["name"] = k
    text, info, size = build(args.level, mats)
    (work / "case.inp").write_text(text, encoding="ascii")
    mesh = dict(cells=sum(len(range(s["elements"][0], s["elements"][1] + 1)) for v in info.values()
                          for s in v["specimens"].values()),
                nodes=size["nodes"], h=1 / size["factor"], element="S8R_COMPOSITE",
                deck_sha256=digest(work / "case.inp"))
    mats_out = {k: {kk: vv for kk, vv in m.items()} for k, m in mats.items()}
    if args.prepare_only:
        return dict(status="PREPARED", mesh=mesh, metrics={}, references=references(mats), quality={})
    text_offset, h_cap = offset_deck(mats)
    (work / "offset.inp").write_text(text_offset, encoding="ascii")
    run_solver([solver, "-i", "offset"], work, args.timeout, args.threads)
    zr = expanded_z_range((work / "offset.frd").read_text(errors="replace"), 0., PLATE)
    execution = run_solver([solver, "-i", "case"], work, args.timeout, args.threads)
    dat = (work / "case.dat").read_text(errors="replace")
    metrics, errors, ref, detail = postprocess(dat, info, mats)
    # OFFSET yorumu: CAP (OFFSET=0.5) genişletilmiş düğümleri referans yüzeyin -normal tarafında olmalı.
    offset_ok = zr[0] is not None and abs(zr[0] + h_cap) < 1e-6 * max(1, h_cap) + 1e-9 and abs(zr[1]) < 1e-9
    offset_check = dict(CAP_offset=0.5, expanded_z_min=zr[0], expanded_z_max=zr[1], expected=[-h_cap, 0.],
                        passed=bool(offset_ok),
                        note="OFFSET=0.5: malzeme referans yüzeyin altında (-normal); ilk tabaka en altta.")
    worst = max(abs(e["percent"]) for e in errors.values())
    require_module("matplotlib")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(8, 4))
    keys = list(errors)
    ax.bar(range(len(keys)), [errors[k]["percent"] for k in keys], color="#4477aa")
    ax.axhline(LIMIT_PCT, color="r", lw=.8); ax.axhline(-LIMIT_PCT, color="r", lw=.8)
    ax.set_xticks(range(len(keys)), keys, rotation=90, fontsize=6)
    ax.set_ylabel("CCX - CLT [%]"); ax.set_title(f"CLT kupon, {args.level}")
    fig.tight_layout(); fig.savefig(work / "plot.png", dpi=140); plt.close(fig)
    return dict(status="COMPUTED" if worst <= LIMIT_PCT and offset_ok else "REVIEW_REQUIRED", mesh=mesh, metrics=metrics,
                references={k: v for k, v in ref.items()}, errors=errors, execution=execution,
                quality=dict(max_abs_error_pct=worst, limit_pct=LIMIT_PCT, detail=detail, offset_check=offset_check),
                materials=mats_out, acceptance_metrics=list(errors), acceptance_limit_pct=LIMIT_PCT,
                limitations=["CLT/eşdeğer tek katman referansı: sandviç çekirdek kayması (zigzag) CCX kabuk "
                             "genişlemesinde temsil edilmez; w_B3_sandwich_theory ayrıca raporlanır.",
                             "Kupon yorumlama doğrulamasıdır; malzeme sabitleri ölçülmüş değildir."])
