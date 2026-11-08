"""Bağımlılıksız kayıt, kısa çalışma yolu ve solver çağrıları."""
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
LEVELS = ("coarse", "medium", "fine")


class Blocked(RuntimeError):
    """Eksik araç/veri veya henüz doğrulanmamış çözüm zinciri."""


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def require_module(name):
    if importlib.util.find_spec(name) is None:
        raise Blocked(f"Python paketi yok: {name}; validation/README.md kurulumuna bakın.")


def executable(env, config):
    value = os.environ.get(env) or config.get(env)
    resolved = shutil.which(value) if value else None
    if value and Path(value).is_file():
        resolved = str(Path(value).resolve())
    if not resolved:
        raise Blocked(f"{env} tam executable yolu tanımlı değil veya dosya bulunamadı.")
    return resolved


def provenance(inputs=()):
    versions = {}
    for name in ("gmsh", "numpy", "scipy", "aerosandbox", "matplotlib"):
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    return dict(utc=datetime.now(timezone.utc).isoformat(), python=sys.version,
                packages=versions, params_sha256=digest(ROOT / "params.py"),
                inputs={str(p): digest(p) for p in inputs if Path(p).is_file()})


def work_directory(key, config):
    # OCP ve solver dosyaları kısa, ASCII yolda; eski çıktı asla tekrar okunmaz.
    base = Path(os.environ.get("HZ750_WORK", config.get("HZ750_WORK", "C:/hz750run")))
    base.mkdir(parents=True, exist_ok=True)
    import tempfile
    return Path(tempfile.mkdtemp(prefix=key + "_", dir=base))


def run_solver(command, work, timeout, threads=4):
    env = dict(os.environ, OMP_NUM_THREADS=str(threads), CCX_NPROC_RESULTS=str(threads))
    with (work / "solver.log").open("w", encoding="utf-8") as log:
        try:
            proc = subprocess.run(command, cwd=work, stdout=log, stderr=subprocess.STDOUT,
                                  timeout=timeout, env=env, check=False)
        except subprocess.TimeoutExpired as exc:
            raise Blocked(f"Süre sınırı ({timeout}s) aşıldı; ham kayıt: {work}") from exc
    if proc.returncode:
        raise RuntimeError(f"Solver kodu {proc.returncode}; {work / 'solver.log'}")
    return dict(command=command, executable_sha256=digest(command[0]),
                log_sha256=digest(work / "solver.log"))


def status_plot(path, title, reason):
    # BLOCKED durumunda bile bağımlılıksız, açık bir grafik artefaktı üret.
    import html
    lines = [reason[i:i + 95] for i in range(0, len(reason), 95)]
    text = "".join(f'<text x="24" y="{90 + 22*i}">{html.escape(s)}</text>' for i, s in enumerate(lines))
    Path(path).write_text('<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="260">'
                         '<rect width="100%" height="100%" fill="#fafafa"/>'
                         '<g font-family="sans-serif" font-size="15" fill="#333">'
                         f'<text x="24" y="38" font-size="21">{html.escape(title)}</text>{text}</g></svg>',
                         encoding="utf-8")
