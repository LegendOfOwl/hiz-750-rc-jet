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
    p.add_argument("--geometry", action="store_true", required=True)
    p.parse_args()
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


if __name__ == "__main__":
    main()
