"""SU2 v8.2 resmi düz levha config+mesh kontrolü; gmsh vakasından ayrı kayıt."""
import argparse
import csv
import os
from pathlib import Path
import sys
import time
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from validation.common import digest,write_json,read_json,run_solver,work_directory,provenance


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--iterations",type=int,default=6000)
    p.add_argument("--timeout",type=int,default=1800)
    p.add_argument("--case",choices=("flatplate","rae2822"),default="flatplate")
    a=p.parse_args()
    tools_path = ROOT/"validation/tools.local.json"
    tools=read_json(tools_path) if tools_path.is_file() else {"SU2_CFD":os.environ.get("SU2_CFD","C:/hz750tools/SU2/win64/bin/SU2_CFD.exe")}
    work=work_directory(a.case+"_native",tools)
    urls={"case.cfg":"https://raw.githubusercontent.com/su2code/SU2/v8.2.0/TestCases/rans/flatplate/turb_SA_flatplate.cfg",
          "mesh_flatplate_turb_137x97.su2":"https://raw.githubusercontent.com/su2code/TestCases/v8.2.0/rans/flatplate/mesh_flatplate_turb_137x97.su2"}
    if a.case == "rae2822":
        urls={"case.cfg":"https://raw.githubusercontent.com/su2code/SU2/v8.2.0/TestCases/rans/rae2822/turb_SA_RAE2822.cfg",
              "mesh_RAE2822_turb.su2":"https://raw.githubusercontent.com/su2code/TestCases/v8.2.0/rans/rae2822/mesh_RAE2822_turb.su2"}
    record=dict(status="FAILED",raw_directory=str(work),sources={},provenance=provenance(),design_accepted=False)
    started=time.monotonic()
    try:
        for name,url in urls.items():
            with urllib.request.urlopen(url,timeout=60) as response: content=response.read()
            (work/name).write_bytes(content)
            record["sources"][name]=dict(url=url,sha256=digest(work/name))
        cfg=(work/"case.cfg").read_text()
        cfg=cfg.replace("ITER= 99999",f"ITER= {a.iterations}")
        # Numerical settings/BC remain official. Add full precision observables.
        cfg += '\nHISTORY_OUTPUT= (ITER, RMS_RES, AERO_COEFF)\nOUTPUT_FILES= (RESTART, SURFACE_CSV)\n'
        (work/"case.cfg").write_text(cfg,encoding="ascii")
        record["execution"]=run_solver([tools["SU2_CFD"],"case.cfg"],work,a.timeout,4)
        with (work/"history.csv").open() as f:
            rows=list(csv.DictReader(f,skipinitialspace=True))
        record.update(status="SOLVER_COMPLETED_NOT_VALIDATED",last_history=rows[-1],elapsed_s=time.monotonic()-started,
                      note="Resmi kaynak+mesh kontrolü; henüz üç ağ/GCI, y+ ve deney kabulü yok.")
    except Exception as exc:
        record.update(reason=f"{type(exc).__name__}: {exc}",elapsed_s=time.monotonic()-started)
    write_json(ROOT/f"validation/results/{a.case}_native.json",record)
    print(record["status"],work)
    return int(record['status'] == 'FAILED')


if __name__=="__main__": sys.exit(main())
