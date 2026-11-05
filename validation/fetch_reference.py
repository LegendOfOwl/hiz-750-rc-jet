"""Host'ta açık çağrıyla yalnız profil geometrisini indir; deney verisi icat edilmez."""
import argparse
from pathlib import Path
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from validation.common import digest, write_json


def main():
    p = argparse.ArgumentParser(description=__doc__)
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--geometry", action="store_true")
    mode.add_argument("--experiment", action="store_true", help="NASA NPARC Case 6 Cp, not Case 9")
    args = p.parse_args()
    if args.experiment:
        fetch_experiment()
        return
    url = "https://m-selig.ae.illinois.edu/ads/coord/rae2822.dat"
    target = ROOT / "validation/reference/rae2822.dat"
    if target.exists():
        raise SystemExit("Mevcut geometri korunuyor: " + str(target))
    with urllib.request.urlopen(url, timeout=30) as response:
        content = response.read()
    if b"<html" in content.lower() or len(content.splitlines()) < 30:
        raise SystemExit("DAT yerine hata sayfası/geçersiz içerik geldi")
    target.write_bytes(content)
    write_json(target.with_suffix(".source.json"), dict(url=url, sha256=digest(target), kind="geometry_only"))


def fetch_experiment():
    base = 'https://www.grc.nasa.gov/www/wind/valid/raetaf/raetaf01/'
    directory = ROOT/'validation/reference'
    sources = {}
    for name in ('cp.exp.gen', 'cfpost.cp.com', 'raetaf01.html'):
        with urllib.request.urlopen(base+name, timeout=60) as response:
            content = response.read()
        target = directory/name
        if name == 'cp.exp.gen' and not content.lstrip().startswith(b'TitleText:'):
            raise ValueError('Expected GENPLOT pressure data')
        target.write_bytes(content)
        sources[name] = dict(url=base+name, sha256=digest(target))
    rows = []
    for line in (directory/'cp.exp.gen').read_text().splitlines():
        try:
            x, minus_cp = map(float, line.split())
            rows.append([x, -minus_cp])
        except ValueError:
            continue
    le = min(range(len(rows)),key=lambda i: rows[i][0])
    if le < 20 or len(rows)-le < 20:
        raise ValueError('Missing upper/lower Cp branch')
    write_json(directory/'rae2822.local.json',dict(
        source_url=base+'raetaf01.html', sources=sources, case='AGARD AR-138 Case 6',
        source_note='NASA NPARC archive. Stored GENPLOT ordinates are -Cp; sign reversed, verified against cfpost.cp.com. Not Case 9. Cp is primary; integral coefficients are secondary values supplied by the reviewer, not extracted from these files.',
        conditions=dict(mach=.729,reynolds=6.5e6,alpha_deg=2.31),
        scalars=dict(cl=.743,cd=.0127,cm=-.095),
        scalar_source=dict(classification='secondary',source='Cook, McDonald, Firmin, AGARD AR-138 (1979)',
                           note='Literaturden aktarilan deger; birincil dosya dogrulanmadi. Reviewer supplied approximations.',
                           primary_file_verified=False),
        cp_upper=rows[:le+1],cp_lower=rows[le:],
        experimental_uncertainty=None))


if __name__ == "__main__":
    main()
