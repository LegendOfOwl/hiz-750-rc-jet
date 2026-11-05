"""HIZ-750 inceleme kopyasi. Python 3.12, yalniz standart kutuphane."""

from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
from datetime import datetime
import hashlib
import html
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import unicodedata
from urllib.parse import quote


REPO = Path(__file__).resolve().parents[1]
DEFAULT_TARGET = Path("C:/Users/Urungu/Desktop/HIZ-750_Inceleme")
MARKER = ".hiz750_paket"
SKIP = {".git", "logs", "__pycache__", ".venv"}
OUTPUT_EXTENSIONS = {".png", ".svg", ".pdf", ".dxf", ".step", ".stp",
                     ".stl", ".json", ".md", ".csv", ".txt"}
RAW_EXTENSIONS = {".inp", ".cfg", ".su2", ".msh", ".geo", ".dat", ".bdf"}
FOLDERS = [
    "00_BASLA_BURADAN", "01_Raporlar", "02_Tasarim_Parametreleri",
    "03_CAD_Modeller/Montaj", "03_CAD_Modeller/Parcalar",
    "04_Teknik_Cizimler", "05_Aerodinamik", "06_Yapi_ve_Flutter",
    "07_Performans_ve_Kutle", "08_Ucus_Kontrol",
    "09_Yuksek_Dogruluk_Dogrulama/CFD_SU2",
    "09_Yuksek_Dogruluk_Dogrulama/FEM_CalculiX",
    "09_Yuksek_Dogruluk_Dogrulama/Termal",
    "09_Yuksek_Dogruluk_Dogrulama/Benchmarklar", "10_Kaynak_Kod",
    "11_Loglar", "99_Diger",
]
REPORT_NAMES = {
    "02_aerodinamik_stabilite.md": "02_Aerodinamik_ve_Stabilite.md",
    "03_cad.md": "03_CAD_Tasarimi.md",
    "04_yapi_flutter.md": "04_Yapi_ve_Flutter_Analizi.md",
    "05_sistemler_performans.md": "05_Sistemler_ve_Performans.md",
    "06_uretim_test_maliyet.md": "06_Uretim_Test_ve_Maliyet.md",
    "07_mevzuat_risk.md": "07_Mevzuat_ve_Risk.md",
    "08_sonuclar_cikarimlar.md": "08_Sonuclar_ve_Cikarimlar.md",
    "09_ucus_kontrol.md": "09_Ucus_Kontrol.md",
    "10_yuksek_dogruluk_dogrulama.md": "10_Yuksek_Dogruluk_Dogrulamasi.md",
}
# Ilk eslesen kural uygulanir. Daha ozel kurallar genel modullerden once gelir.
# (repo yolu glob deseni, hedef klasor, dosya aciklamasi)
MAPPING_RULES = [
    ("aero/*/fc_*", "08_Ucus_Kontrol", "Ucus kontrol grafigi veya sonucu"),
    ("aero/fc_*", "08_Ucus_Kontrol", "Ucus kontrol grafigi veya sonucu"),
    ("cad/*", "03_CAD_Modeller", "CAD gorseli veya model raporu"),
    ("aero/*", "05_Aerodinamik", "Aerodinamik analiz ciktisi"),
    ("structures/*", "06_Yapi_ve_Flutter", "Yapi veya flutter analiz ciktisi"),
    ("performance/*", "07_Performans_ve_Kutle", "Performans veya kutle sonucu"),
    ("out/*", "07_Performans_ve_Kutle", "On boyutlandirma ciktisi"),
    ("flight_control/*", "08_Ucus_Kontrol", "Ucus kontrol ciktisi"),
    ("control/*", "08_Ucus_Kontrol", "Ucus kontrol ciktisi"),
    ("cfd/*", "09_Yuksek_Dogruluk_Dogrulama/CFD_SU2", "CFD SU2 calismasi"),
    ("fem/*", "09_Yuksek_Dogruluk_Dogrulama/FEM_CalculiX", "Kabuk FEM calismasi"),
    ("thermal/*", "09_Yuksek_Dogruluk_Dogrulama/Termal", "Termal calisma"),
    ("validation/*", "09_Yuksek_Dogruluk_Dogrulama/Benchmarklar", "Dogrulama ve benchmark"),
]
# Uzun anahtarlar once degistirilir. Bilinmeyen deney/varyant kodlari korunur.
TRANSLATIONS = {
    "flat_plate_SA": "Duz_Levha_SA", "wing": "Kanat_Kabuk_FEM",
    "airfoil": "Kanat_Profili", "cantilever": "Ankastre_Kiris",
    "coupon": "Malzeme_Kuponu", "thermal_1d": "Bir_Boyutlu_Termal",
    "stiffening": "Rijitlestirme", "coarse": "kaba_ag", "medium": "orta_ag",
    "fine": "ince_ag", "study": "ag_calismasi", "plot": "grafik",
    "status": "durum", "summary": "ozet", "corrected": "duzeltilmis",
    "empty": "bos", "full": "dolu", "case": "cozucu_girdisi",
    "mesh": "ag", "review": "inceleme", "model": "model",
    "assembly": "Montaj", "on_dolly": "Tasima_Arabali_Montaj",
    "3view": "Uc_Gorunus", "inboard": "Ic_Yerlesim", "iso": "Izometrik",
    "aileron": "Yatircak", "elevator": "Irtifa_Dumeni", "rudder": "Yon_Dumeni",
    "fuselage": "Govde", "htail": "Yatay_Kuyruk", "vtail": "Dikey_Kuyruk",
    "engine": "Motor", "exhaust_pipe": "Egzoz_Borusu", "frames": "Govde_Cerceveleri",
    "belly_fairing": "Karin_Kaplamasi", "inlet_duct": "Hava_Aligi_Kanali",
    "ht_carry_yoke": "Yatay_Kuyruk_Baglantisi", "skid": "Kizak",
    "tail_bumper": "Kuyruk_Tamponu", "tank": "Yakit_Tanki", "center": "Orta",
    "box": "Kutu", "panels": "Paneller", "dolly": "Tasima_Arabasi",
    "mass_properties": "Kutle_ve_Atalet", "cad_report": "CAD_Raporu",
    "RESULTS": "Sonuclar", "README": "Modul_Aciklamasi", "L": "Sol", "R": "Sag",
}
PREFIXES = {"cad": "CAD", "aero": "Aerodinamik", "structures": "Yapi_Flutter",
            "performance": "Performans_Kutle", "out": "On_Boyutlandirma",
            "cfd": "CFD_SU2", "fem": "FEM", "thermal": "Termal",
            "validation": "Benchmark", "control": "Ucus_Kontrol",
            "flight_control": "Ucus_Kontrol"}


@dataclass(frozen=True)
class Entry:
    source: Path
    destination: Path
    description: str


def linked(path: Path) -> bool:
    """Windows junction dahil tum reparse noktalarini tanir."""
    info = path.lstat()
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
    )


def walk_files(root: Path, skip: set[str]):
    """Baglantilar takip edilmez, sessiz veri eksilmesi yerine hata verilir."""
    def fail(error):
        raise error

    for directory, dirs, files in os.walk(root, followlinks=False, onerror=fail):
        dirs[:] = sorted(d for d in dirs if d.lower() not in skip)
        for name in dirs + sorted(files):
            path = Path(directory) / name
            if linked(path):
                raise ValueError(f"Baglanti/reparse noktasi incelenmeli: {path}")
        for name in sorted(files):
            yield Path(directory) / name


def safe_name(value: str) -> str:
    value = value.translate(str.maketrans("ıİşŞğĞçÇöÖüÜ", "iIsSgGcCoOuU"))
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    value = re.sub(r"[^A-Za-z0-9_-]+", "_", value).strip("_ .") or "Dosya"
    if re.fullmatch(r"(?i:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])", value):
        value = "Dosya_" + value
    if len(value) > 110:
        digest = hashlib.sha256(value.encode()).hexdigest()[:10]
        value = value[:95] + "_" + digest
    return value


def translated(value: str) -> str:
    pattern = "|".join(re.escape(k) for k in sorted(TRANSLATIONS, key=len, reverse=True))
    return re.sub(r"(?<![A-Za-z0-9])(" + pattern + r")(?![A-Za-z0-9])",
                  lambda match: TRANSLATIONS[match.group()], value)


def descriptive_name(relative: Path) -> str:
    context = [p for p in relative.parts[1:-1]
               if p not in {"out", "results", "step", "stl"}]
    prefix = PREFIXES.get(relative.parts[0], "Cikti")
    if relative.name.startswith("fc_"):
        prefix = "Ucus_Kontrol"
    text = "_".join([prefix, *context, relative.stem])
    name = translated(text)
    if relative.parts[0] == "cad":
        name = name.replace("Kanat_Kabuk_FEM", "Kanat")
    return safe_name(name) + relative.suffix.lower()


def destination_for(relative: Path) -> tuple[Path, str]:
    from fnmatch import fnmatchcase

    path = relative.as_posix()
    exact = {
        "README.md": "01_Raporlar/00_Proje_Ozeti.md",
        "CHANGELOG.md": "01_Raporlar/Degisiklik_Gunlugu.md",
        "BASARIM_AGACI.md": "00_BASLA_BURADAN/Basarim_Agaci.md",
        "params.py": "02_Tasarim_Parametreleri/Tasarim_Parametreleri_params.py",
    }
    if path in exact:
        return Path(exact[path]), "Proje temel belgesi"
    if relative.parts[0] == "docs":
        name = REPORT_NAMES.get(relative.name, descriptive_name(relative))
        return Path("01_Raporlar", *relative.parts[1:-1], name), "Proje raporu"
    if relative.suffix.lower() in {".step", ".stp", ".stl"}:
        assembly = any(word in relative.stem.lower() for word in ("assembly", "montaj", "on_dolly"))
        group = "Montaj" if assembly else "Parcalar"
        return Path("03_CAD_Modeller", group, descriptive_name(relative)), "CAD geometrisi"
    for pattern, folder, description in MAPPING_RULES:
        if fnmatchcase(path, pattern):
            if relative.suffix.lower() in RAW_EXTENSIONS:
                folder += "/Ham_Girdiler"
            elif relative.suffix.lower() in {".dxf", ".pdf", ".svg"} and relative.parts[0] == "cad":
                folder = "04_Teknik_Cizimler"
            return Path(folder, descriptive_name(relative)), description
    # Bilinmeyen ciktilar icin kaynak yolu birebir korunur.
    return Path("99_Diger") / relative, "Siniflandirilmamis cikti"


def build_plan(repo: Path) -> list[Entry]:
    entries = []
    for source in walk_files(repo, SKIP):
        relative = source.relative_to(repo)
        if relative.as_posix() == "tools/README.md":
            continue
        if source.suffix.lower() not in OUTPUT_EXTENSIONS | RAW_EXTENSIONS and relative != Path("params.py"):
            continue
        destination, description = destination_for(relative)
        entries.append(Entry(source, destination, description))
    # logs normal taramadan ayri ele alinir, uzanti siniri uygulanmaz.
    for source in walk_files(repo, SKIP - {"logs"}):
        relative = source.relative_to(repo)
        if "logs" in [part.lower() for part in relative.parts[:-1]]:
            entries.append(Entry(source, Path("11_Loglar") / relative, "Calisma gunlugu"))
    used = {
        "00_basla_buradan/oku_beni.md",
        "02_tasarim_parametreleri/parametre_tablosu.md",
        "10_kaynak_kod/kodun_konumu.md",
    }
    result = []
    for entry in sorted(entries, key=lambda e: e.source.as_posix()):
        destination = entry.destination
        # Windows buyuk/kucuk harf ve ad donusumu cakismalarinda veri ezilmez.
        counter = 1
        while destination.as_posix().casefold() in used or destination.name.casefold() == "icindekiler.md":
            counter += 1
            destination = entry.destination.with_stem(entry.destination.stem + f"_{counter}")
        used.add(destination.as_posix().casefold())
        result.append(Entry(entry.source, destination, entry.description))
    return result


def literal_value(node: ast.AST):
    """dict(a=...) da desteklenir. Hicbir cagri veya ifade calistirilmaz."""
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "dict":
        if node.args or any(k.arg is None for k in node.keywords):
            raise ValueError("Sabit olmayan dict")
        return {k.arg: literal_value(k.value) for k in node.keywords}
    if isinstance(node, ast.Dict):
        return {literal_value(k): literal_value(v) for k, v in zip(node.keys, node.values)}
    if isinstance(node, (ast.List, ast.Tuple)):
        return [literal_value(item) for item in node.elts]
    return ast.literal_eval(node)


def parameter_table(repo: Path) -> str:
    lines = ["# Tasarim parametreleri", "",
             "Kaynak `params.py`. Yalniz AST ile okunabilen sabitler listelenir. "
             "Hesaplanan ifadeler ve okunamayan sozlukler atlanir. Kaynaktaki birimler gecerlidir.", "",
             "| Parametre | Deger |", "|---|---|"]

    def rows(name, value):
        if isinstance(value, dict):
            for key, child in value.items():
                rows(f"{name}.{key}", child)
        else:
            rendered = repr(value).replace("|", "&#124;").replace("\n", " ")
            lines.append(f"| {name} | {rendered} |")

    source = repo / "params.py"
    if source.exists():
        tree = ast.parse(source.read_text(encoding="utf-8-sig"))
        for node in tree.body:
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                try:
                    value = literal_value(node.value)
                except (ValueError, TypeError, SyntaxError):
                    continue
                for target in targets:
                    if isinstance(target, ast.Name):
                        rows(target.id, value)
    else:
        lines.extend(["", "params.py bulunamadi."])
    return "\n".join(lines) + "\n"


def validate_target(target: Path, repo: Path) -> None:
    # Cozulmus hedef repo icinde, repo ustunde veya repo ile ayni olamaz.
    for path in [target, *target.parents]:
        if path.exists() or path.is_symlink():
            if linked(path):
                raise ValueError(f"Hedef yolunda baglanti/reparse noktasi var: {path}")
    resolved = target.resolve()
    if resolved.is_relative_to(repo) or repo.is_relative_to(resolved):
        raise ValueError("Hedef repo ile cakisamaz. Repo disinda bir klasor secin.")
    if not target.exists():
        return
    if not target.is_dir():
        raise ValueError("Hedef bir klasor olmali.")
    # Silmeden once agacin tamami kontrol edilir.
    list(walk_files(target, set()))
    if not any(target.iterdir()):
        return
    marker = target / MARKER
    if not marker.is_file():
        raise ValueError(f"Dolu hedefte {MARKER} yok. Hicbir sey silinmedi.")
    expected = {"creator": "hiz750-inceleme-v1", "repo": str(repo), "target": str(resolved)}
    if json.loads(marker.read_text(encoding="utf-8")) != expected:
        raise ValueError("Paket isareti bu repo ve hedefe ait degil. Hicbir sey silinmedi.")


def git_commit(repo: Path) -> str:
    try:
        result = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"],
                                capture_output=True, text=True, timeout=10, check=True)
        return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return "Git commit bilgisi alinamadi"


def summary_text(repo: Path) -> str:
    folders = "\n".join(f"- `{folder}/`" for folder in FOLDERS)
    return (
        "# HIZ-750 inceleme paketi\n\n"
        "HIZ-750, 750 km/h hedefli, turbin motorlu bir RC jet IHA tasarim projesidir. "
        "Bu paket CAD modellerini, teknik cizimleri, raporlari ve analiz ciktilarini "
        "inceleme amaciyla bir araya getirir. Sonuclarin guncel durumu ve acik konular "
        "Basarim_Agaci.md ile dogrulama raporlarinda yer alir.\n\n"
        "Once Basarim_Agaci.md ve 01_Raporlar/00_Proje_Ozeti.md dosyalarini okuyun. "
        "Ardindan raporlar, CAD ve ilgili analiz klasorlerine gecin. "
        "index.html tum dosyalari ve PNG onizlemelerini listeler. "
        "Her klasordeki ICINDEKILER.md kaynak repo yollarini gosterir. "
        "Kopyalanan raporlarin goreli baglantilari kaynak repo duzenine ait olabilir.\n\n"
        f"Olusturma tarihi {datetime.now().astimezone().isoformat(timespec='seconds')}\n\n"
        f"Git commit `{git_commit(repo)}`\n\nRepo `{repo}`\n\n"
        "## Klasor haritasi\n\n" + folders + "\n"
    )


def write_package(target: Path, repo: Path, entries: list[Entry], generated: dict[Path, str]):
    validate_target(target, repo)
    if target.exists() and any(target.iterdir()):
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)
    (target / MARKER).write_text(json.dumps({
        "creator": "hiz750-inceleme-v1", "repo": str(repo), "target": str(target.resolve())
    }), encoding="utf-8")
    for folder in FOLDERS:
        (target / folder).mkdir(parents=True, exist_ok=True)
    for entry in entries:
        destination = target / entry.destination
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(entry.source, destination)
    for relative, content in generated.items():
        (target / relative).write_text(content, encoding="utf-8")
    records = {e.destination: (e.description, e.source.relative_to(repo).as_posix()) for e in entries}
    records.update({p: ("Paket icin olusturuldu", "Script tarafindan uretildi") for p in generated})
    # Once tum klasorler bilinir, sonra her seviyede yerel bir icerik listesi yazilir.
    directories = [target, *sorted(p for p in target.rglob("*") if p.is_dir())]
    for directory in directories:
        lines = [f"# {directory.name} icindekiler", ""]
        for child in sorted(directory.iterdir()):
            if child.is_dir():
                href = quote(child.name + "/ICINDEKILER.md")
                lines.append(f"- [{child.name}/]({href}) - Alt klasor dizini.")
            elif child.name != MARKER:
                desc, original = records[child.relative_to(target)]
                lines.append(f"- [{child.name}]({quote(child.name)}) - {desc}. Kaynak `{original}`.")
        (directory / "ICINDEKILER.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    index = target / "00_BASLA_BURADAN/index.html"
    parts = ["<!doctype html><html lang='tr'><meta charset='utf-8'>",
             "<meta name='viewport' content='width=device-width, initial-scale=1'>",
             "<title>HIZ-750 inceleme paketi</title>",
             "<style>body{font:16px system-ui;max-width:1100px;margin:2em auto;padding:1em}"
             "pre{white-space:pre-wrap}img{max-width:180px;max-height:120px;vertical-align:middle}"
             "li{margin:1em 0;overflow-wrap:anywhere}</style><body>",
             "<pre>" + html.escape(generated[Path("00_BASLA_BURADAN/OKU_BENI.md")]) + "</pre>",
             "<h2>Tum paket dosyalari</h2><ul>"]
    for file in sorted(p for p in target.rglob("*") if p.is_file()):
        relative = file.relative_to(target)
        href = quote("../" + relative.as_posix())
        label = html.escape(relative.as_posix())
        preview = f" <img loading='lazy' src='{href}' alt='{label}'>" if file.suffix.lower() == ".png" else ""
        parts.append(f"<li><a href='{href}'>{label}</a>{preview}</li>")
    parts.append("<li><a href='index.html'>00_BASLA_BURADAN/index.html</a></li></ul></body></html>")
    index.write_text("\n".join(parts), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="HIZ-750 inceleme paketini repo disinda olusturur.")
    parser.add_argument("--hedef", type=Path, default=DEFAULT_TARGET, help="Paket klasoru")
    parser.add_argument("--dry-run", action="store_true", help="Yalniz esleme listesini yazdir")
    args = parser.parse_args()
    target = Path(os.path.abspath(args.hedef.expanduser()))
    try:
        validate_target(target, REPO)
        entries = build_plan(REPO)
        generated = {
            Path("00_BASLA_BURADAN/OKU_BENI.md"): summary_text(REPO),
            Path("02_Tasarim_Parametreleri/Parametre_Tablosu.md"): parameter_table(REPO),
            Path("10_Kaynak_Kod/Kodun_Konumu.md"):
                f"# Kaynak kod\n\nRepo yolu `{REPO}`\n\nKod repoda calistirilir.\n",
        }
        for entry in entries:
            print(f"{entry.source.relative_to(REPO).as_posix()} -> {entry.destination.as_posix()}")
        total = sum(entry.source.stat().st_size for entry in entries)
        if args.dry_run:
            for path in generated:
                print(f"[URETILECEK] {path.as_posix()}")
            print("[URETILECEK] 00_BASLA_BURADAN/index.html ve her klasorde ICINDEKILER.md")
            print(f"Dry-run tamamlandi. Planlanan {len(entries)} dosya, {total} bayt ({total / 1048576:.2f} MiB).")
        else:
            write_package(target, REPO, entries, generated)
            print(f"Kopyalandi {len(entries)} dosya, {total} bayt ({total / 1048576:.2f} MiB).")
            print(f"Paket {target}")
        return 0
    except (OSError, ValueError, SyntaxError) as error:
        print(f"Hata: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
