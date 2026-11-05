"""Compare explicit SU2 options; absence means a solver default, not equivalence."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from validation.common import digest, write_json


def options(path):
    result = {}
    for line in Path(path).read_text().splitlines():
        line = line.split('%',1)[0].strip()
        if '=' in line:
            key,value = line.split('=',1)
            result[key.strip()] = ''.join(value.split())
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('official',type=Path)
    p.add_argument('generated',type=Path)
    p.add_argument('--output',type=Path,required=True)
    a = p.parse_args()
    official,generated = options(a.official),options(a.generated)
    differences = {k:dict(official=official.get(k),generated=generated.get(k))
                   for k in sorted(official.keys()|generated.keys()) if official.get(k)!=generated.get(k)}
    write_json(a.output,dict(official_sha256=digest(a.official),generated_sha256=digest(a.generated),
                             differences=differences,
                             note='Explicit options only; null denotes implicit SU2 defaults. Different marker names map different mesh boundaries. This comparison alone does not identify a divergence cause.'))


if __name__ == '__main__': main()
