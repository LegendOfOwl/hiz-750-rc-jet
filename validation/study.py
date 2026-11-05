"""Üç ağ, kaynak/provenance tutarlılığı ve benchmark kabulü."""
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from validation.common import LEVELS, digest, read_json, write_json
from validation.convergence import error, gci


def interpolate(points, x):
    points = sorted(points)
    if points[0][0]-1e-8 <= x < points[0][0]:
        return points[0][1]
    if points[-1][0] < x <= points[-1][0]+1e-8:
        return points[-1][1]
    if not points[0][0] <= x <= points[-1][0]:
        raise ValueError("Referans dışında Cp ekstrapolasyonu yapılamaz")
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        if x0 <= x <= x1 and x1 > x0:
            return y0 + (y1-y0) * (x-x0)/(x1-x0)
    return points[-1][1]


def compare_reference(result, reference, work, allow_partial_cp=False):
    from cfd.cases import csv_rows, pick
    if not reference.get("source_url") or not reference.get("conditions"):
        raise ValueError("Referans URL'si ve vaka koşulları gerekli")
    for key in ("mach", "reynolds", "alpha_deg"):
        if not math.isclose(reference["conditions"][key], result["conditions"][key], rel_tol=1e-6, abs_tol=1e-8):
            raise ValueError(f"Referans koşulu uyuşmuyor: {key}")
    errors = {}
    for key, value in reference["scalars"].items():
        if value is not None:
            errors[key] = error(result["metrics"][key], value)
    cp_rmse = None
    partial_rmse = None
    coverage = None
    if result["case"] == "rae2822" and reference.get("cp_upper") and reference.get("cp_lower"):
        # Camber nedeniyle y işareti üst/alt ayırmaz: geometrinin iki dalına uzaklık kullanılır.
        geometry = read_json(work / "geometry.json")
        ile = min(range(len(geometry)), key=lambda i: geometry[i][0])
        upper, lower = geometry[:ile+1], geometry[ile:]
        measured = {"cp_upper": [], "cp_lower": []}
        for r in csv_rows(work / "surface_flow.csv"):
            x, y = pick(r, "x", "x_coord"), pick(r, "y", "y_coord")
            # Segment distances handle spline points slightly beyond source x
            # extrema and cambered lower surfaces above the x axis.
            def distance(branch):
                best = math.inf
                for a,b in zip(branch,branch[1:]):
                    dx,dy = b[0]-a[0],b[1]-a[1]
                    length2 = dx*dx+dy*dy
                    t = max(0.,min(1.,((x-a[0])*dx+(y-a[1])*dy)/length2)) if length2 else 0.
                    best = min(best,math.hypot(x-a[0]-t*dx,y-a[1]-t*dy))
                return best
            du, dl = distance(upper), distance(lower)
            sides = ("cp_upper", "cp_lower") if max(du,dl) < 1e-8 else ("cp_upper" if du <= dl else "cp_lower",)
            for which in sides:
                measured[which].append((x, pick(r, "Pressure_Coefficient")))
        diffs, excluded = [], []
        for side in measured:
            for x,cp in reference[side]:
                try:
                    diffs.append((interpolate(measured[side],x)-cp)**2)
                except ValueError:
                    if not allow_partial_cp:
                        raise
                    excluded.append(dict(side=side,x=x))
        partial_rmse = math.sqrt(sum(diffs)/len(diffs)) if diffs else None
        coverage = dict(compared=len(diffs),excluded=excluded)
        cp_rmse = partial_rmse if not excluded else None
    metrics = dict(result["metrics"])
    if cp_rmse is not None:
        metrics["cp_rmse"] = cp_rmse
    return dict(errors=errors, reference_source=reference, cp_rmse=cp_rmse,
                cp_rmse_partial=partial_rmse,cp_coverage=coverage,metrics=metrics)


def evaluate(directory):
    directory = Path(directory)
    paths = [directory / f"{level}.json" for level in reversed(LEVELS)]
    if not all(p.is_file() for p in paths):
        return dict(status="PENDING", reason="Üç ağ sonucu bekleniyor", metrics={})
    rows = [read_json(p) for p in paths]
    if any(r["status"] not in ("COMPUTED", "REVIEW_REQUIRED", "DIAGNOSTIC") for r in rows):
        return dict(status="PENDING", reason="Üç ağın da yakınsamış COMPUTED sonucu gerekli", metrics={})
    for r in rows:
        if r["provenance"]["params_sha256"] != digest(ROOT / "params.py"):
            return dict(status="STALE", reason="params.py değişti", metrics={})
        if any(not (ROOT / name).is_file() or digest(ROOT / name) != sha for name, sha in r["code_sha256"].items()):
            return dict(status="STALE", reason="Runner kaynakları değişti", metrics={})
        for source,sha in r.get("provenance",{}).get("inputs",{}).items():
            if not Path(source).is_file() or digest(source) != sha:
                return dict(status="STALE", reason="Kaynak veri değişti", metrics={})
    for key in ("case_id", "code_sha256", "conditions", "assumptions"):
        if any(r.get(key) != rows[0].get(key) for r in rows[1:]):
            return dict(status="INCONSISTENT", reason=f"Üç ağda {key} farklı", metrics={})
    if len({r["execution"]["executable_sha256"] for r in rows}) != 1:
        return dict(status="INCONSISTENT", reason="Solver build'leri farklı", metrics={})
    # Ağ/deck doğal olarak farklıdır; referans ve ısıl senaryo ağlar arasında aynı olmalıdır.
    for key in ("reference", "thermal_inputs", "airfoil"):
        if len({r.get("input_sha256", {}).get(key) for r in rows}) != 1:
            return dict(status="INCONSISTENT", reason=f"Girdi değişti: {key}", metrics={})
    metrics = {}
    for name, value in rows[0]["metrics"].items():
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        values = [r["metrics"][name] for r in rows]
        metrics[name] = dict(values_fine_to_coarse=values,
                             convergence=gci([r["mesh"]["h"] for r in rows], values),
                             errors_fine_to_coarse=[r.get("errors",{}).get(name) for r in rows],
                             error_fine=rows[0].get("errors", {}).get(name))
    case = rows[0]["case"]
    targets = {"cantilever": ("tip_deflection_m", "f1_Hz"), "thermal_1d": ("outer_K", "heat_flux_W_m2"),
               "rae2822": ("cl", "cd"), "flat_plate": ("cf_mean",)}.get(case, ())
    if case == "coupon":
        # Homojen membran durumları ağdan bağımsızdır; yuvarlama düzeyindeki salınımda GCI tanımsızdır.
        # Bu durumda üç ağın bağıl yayılımı <= kabul eşiğinin 1/4'ü ve üç ağın her biri eşik içinde olmalı.
        targets = tuple(rows[0].get("acceptance_metrics", ()))
    accepted = bool(targets) and all(r["status"] == "COMPUTED" and not r.get("diagnostic") for r in rows)
    reasons = []
    for name in targets:
        conv = metrics[name]["convergence"]
        if case == "coupon" and conv["status"] != "PLATEAU_UNRESOLVED":
            values = metrics[name]["values_fine_to_coarse"]
            spread = (max(values) - min(values)) / max(abs(v) for v in values)
            metrics[name]["relative_spread"] = spread
            limit = rows[0].get("acceptance_limit_pct", 2)
            each = [abs((r.get("errors", {}).get(name) or {}).get("percent", float("inf"))) for r in rows]
            if conv["status"] not in ("ESTIMATED", "EXACT_OR_ROUNDOFF") and spread <= limit / 400 and max(each) <= limit:
                continue
        if conv["status"] not in ("ESTIMATED", "EXACT_OR_ROUNDOFF"):
            accepted = False; reasons.append(f"{name}: GCI {conv['status']}")
        if conv.get("fine_gci_pct", 0) is not None and conv.get("fine_gci_pct", 0) > 5:
            accepted = False; reasons.append(f"{name}: GCI > %5")
    if case in ("cantilever", "thermal_1d", "rae2822", "coupon"):
        limits = {"cantilever": 2, "thermal_1d": .1, "rae2822": 5, "coupon": rows[0].get("acceptance_limit_pct", 2)}
        for name in targets:
            e = rows[0].get("errors", {}).get(name, {}).get("percent")
            limit = 15 if name == "cd" else limits[case]
            if e is None or abs(e) > limit:
                accepted = False; reasons.append(f"{name}: referans hata sınırı/bilgisi sağlanmadı")
        if case == "rae2822" and (rows[0].get("cp_rmse") is None or rows[0]["cp_rmse"] > .08):
            accepted = False; reasons.append("RAE Cp RMSE <= .08 gerekli")
    if case == "flat_plate":
        cf = rows[0]["metrics"]["cf_mean"]
        for correlation in ("cf_ittc", "cf_schlichting"):
            e = error(cf, rows[0]["metrics"][correlation])
            metrics["cf_mean"]["error_" + correlation] = e
            if abs(e["percent"]) > 15:
                accepted = False; reasons.append("Cf korelasyon farkı > %15")
    secondary = case == "rae2822" and rows[0].get("reference_source", {}).get("scalar_source", {}).get("classification") == "secondary"
    label = "BENCHMARK_ACCEPTED (CL/CD ikincil kaynak)" if accepted and secondary else "BENCHMARK_ACCEPTED" if accepted else "REVIEW_REQUIRED"
    return dict(status="BENCHMARK_ACCEPTED" if accepted else "REVIEW_REQUIRED", case=case,
                acceptance_label=label,
                reference_basis="Cp primary NASA; CL/CD secondary, primary file unverified" if secondary else None,
                metrics=metrics, reasons=reasons,
                note="Eşikler iter5 mühendislik taramasıdır; deney belirsizliği ve fiziksel tasarım kabulü yerine geçmez.")


def save_study(directory):
    directory = Path(directory)
    result = evaluate(directory)
    write_json(directory / "study.json", result)
    lines = [f"# {directory.name}: {result.get('acceptance_label', result['status'])}", "", "| Büyüklük | Kaba / orta / ince | p | GCI ince [%] | Referans hata kaba / orta / ince [%] |", "|---|---|---|---|---|"]
    for name, row in result["metrics"].items():
        c, e = row["convergence"], row.get("error_fine") or {}
        values = " / ".join(f"{x:.8g}" for x in reversed(row["values_fine_to_coarse"]))
        errors = " / ".join(str((v or {}).get("percent", "bekliyor")) for v in reversed(row["errors_fine_to_coarse"]))
        lines.append(f"| {name} | {values} | {c.get('observed_order', c['status'])} | {c.get('fine_gci_pct', '—')} | {errors} |")
    if not result["metrics"]:
        lines += ["| Tüm değerler | bekliyor | — | — | — |", "", result.get("reason", "")]
    (directory / "study.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("directory", type=Path)
    args = p.parse_args()
    print(save_study(args.directory)["status"])
