"""SU2 ASCII ağ ENGINE marker'ı ve SURFACE_CSV'den üçgen merkez örnekleri."""
import math
from pathlib import Path

from cfd.cases import csv_rows, pick
from validation.common import Blocked


def samples(mesh_path, surface_path, center_yz=(0., 0.)):
    lines = iter(Path(mesh_path).read_text().splitlines())
    points, faces = {}, []
    for line in lines:
        if line.strip().startswith("NPOIN="):
            count = int(line.split("=")[1].split()[0])
            for i in range(count):
                fields = next(lines).split()
                points[int(fields[3]) if len(fields) > 3 else i] = tuple(map(float, fields[:3]))
        elif line.strip().startswith("MARKER_TAG="):
            name = line.split("=")[1].strip()
            count = int(next(lines).split("=")[1])
            for _ in range(count):
                f = list(map(int, next(lines).split()))
                if name == "ENGINE":
                    if f[0] == 5:
                        faces.append(f[1:4])
                    elif f[0] == 9:
                        faces += [f[1:4], [f[1], f[3], f[4]]]
                    else:
                        raise Blocked("ENGINE yalnız triangle/quad yüzey elemanları içermeli.")
    if not faces:
        raise Blocked("SU2 ASCII ağda ENGINE yüzeyi bulunamadı.")
    field = {}
    for row in csv_rows(surface_path):
        xyz = tuple(round(pick(row, name), 8) for name in ("x", "y", "z"))
        field[xyz] = row
    output = []
    for face in faces:
        xyz = [points[n] for n in face]
        rows = []
        for point in xyz:
            row = field.get(tuple(round(v, 8) for v in point))
            if row is None:
                raise Blocked("ENGINE düğümleri yüzey CSV'de yok; MARKER_PLOTTING/CSV hassasiyeti kontrol edilmeli.")
            rows.append(row)
        a, b = [[xyz[i][j] - xyz[0][j] for j in range(3)] for i in (1, 2)]
        cross = (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
        norm = math.sqrt(sum(c*c for c in cross))
        if norm <= 0:
            raise Blocked("ENGINE sıfır alanlı üçgen")
        if abs(cross[0]/norm) < .95:
            raise Blocked("ENGINE disk x-sabit olmalı; postprocess merkez/normal varsayımı bu geometriye uymuyor.")
        def mean(*names):
            return sum(pick(r, *names) for r in rows)/3
        velocity = [mean("Velocity_" + axis) for axis in "xyz"]
        un = sum(c*v/norm for c, v in zip(cross, velocity))
        # Motor yüzü yaklaşık x-sabit disktir; +x yönü motora doğrudur.
        if cross[0] < 0:
            un = -un
        pressure, density = mean("Pressure"), mean("Density")
        m2 = sum(v*v for v in velocity) / (1.4 * pressure / density)
        center = [sum(p[j] for p in xyz)/3 for j in range(3)]
        output.append(dict(area=norm/2, rho=density, un=un, p=pressure,
                           pt=pressure*(1+.2*m2)**3.5,
                           theta_deg=math.degrees(math.atan2(center[2]-center_yz[1], center[1]-center_yz[0])) % 360))
    return output
