# -*- coding: utf-8 -*-
"""Genera public/data/ecosistemas_R26.pmtiles desde el ráster maestro R26.

Cada píxel guarda el CÓDIGO de clase, no su color: PNG con paleta en la que el índice i
tiene RGB = (código >> 8, código & 255, 0) y el índice 0 es transparente (sin dato).
El navegador decodifica el código y lo pinta con la paleta oficial del .qml, lo que permite
filtrar clases e identificar la clase con un clic sin otra capa.

Pirámide: z13 (≈19 m/píxel) se muestrea por vecino más cercano desde el ráster de 30 m;
z12 a z5 se construyen por moda de 2×2 (la clase más frecuente), sin promediar códigos.
"""
from __future__ import annotations

import io
import json
import math
import os
import re
import sys
import tempfile
import time
from pathlib import Path

import mercantile
import numpy as np
import rasterio
from PIL import Image
from rasterio.enums import Resampling
from rasterio.vrt import WarpedVRT
from rasterio.warp import transform_bounds
from rasterio.transform import Affine
from rasterio.windows import Window

AQUI = Path(__file__).resolve().parent
APP = AQUI.parent
R26 = Path(os.environ.get("ECOSYSTEMS_R26_DIR", APP.parent / "Entrega_final_R26"))
TIF = R26 / "Geodatos" / "Mapa_Ecosistemas_R26_30m.tif"
QML = R26 / "Geodatos" / "Mapa_Ecosistemas_R26_30m.qml"
SALIDA = APP / "public" / "data" / "ecosistemas_R26.pmtiles"
TMP = APP / "datos" / "_tmp"
TMP.mkdir(parents=True, exist_ok=True)
tempfile.tempdir = str(TMP)  # el escritor de PMTiles usa un temporal: que no vaya a C:

from pmtiles.tile import Compression, TileType, zxy_to_tileid  # noqa: E402
from pmtiles.writer import Writer  # noqa: E402

ZMAX, ZBASE, ZMIN = 13, 10, 5
LADO = 256


def codigos_oficiales() -> list[int]:
    q = QML.read_text(encoding="utf-8")
    return sorted({int(v) for v in re.findall(r'value="(\d+)"[^>]*?color="#', q)})


def moda2x2(a: np.ndarray) -> np.ndarray:
    """Reduce a la mitad tomando la clase más frecuente de cada bloque 2×2; el 0 (sin dato) solo gana si no hay otra."""
    v = np.stack([a[0::2, 0::2], a[0::2, 1::2], a[1::2, 0::2], a[1::2, 1::2]])
    cuenta = np.zeros(v.shape, np.int8)
    for i in range(4):
        for j in range(4):
            cuenta[i] += v[i] == v[j]
    cuenta[v == 0] = 0
    eleg = np.argmax(cuenta, axis=0)
    return np.take_along_axis(v, eleg[None], 0)[0]


def png(arr: np.ndarray, indice: np.ndarray, paleta: bytes) -> bytes | None:
    if not arr.any():
        return None
    im = Image.fromarray(indice[arr].astype(np.uint8), "P")
    im.putpalette(paleta)
    im.info["transparency"] = 0
    b = io.BytesIO()
    im.save(b, "PNG", optimize=True, transparency=0)
    return b.getvalue()


def main() -> None:
    t0 = time.time()
    codigos = codigos_oficiales()
    assert len(codigos) == 115, len(codigos)
    indice = np.zeros(65536, np.uint16)
    pal = [0, 0, 0]
    for i, c in enumerate(codigos, start=1):
        indice[c] = i
        pal += [c >> 8, c & 255, 0]
    paleta = bytes(pal + [0] * (768 - len(pal)))

    teselas: dict[tuple[int, int, int], bytes] = {}
    base: dict[tuple[int, int], np.ndarray] = {}
    with rasterio.open(TIF) as src:
        w, s, e, n = transform_bounds(src.crs, "EPSG:4326", *src.bounds)
        bloques = list(mercantile.tiles(w, s, e, n, ZBASE))
        lado_base = LADO * 2 ** (ZMAX - ZBASE)  # 2048
        xs = [t.x for t in bloques]; ys = [t.y for t in bloques]
        x0, y0 = min(xs), min(ys)
        nx, ny = max(xs) - x0 + 1, max(ys) - y0 + 1
        esq = mercantile.xy_bounds(mercantile.Tile(x0, y0, ZBASE))
        res = 2 * math.pi * 6378137 / (LADO * 2 ** ZMAX)
        malla = Affine(res, 0, esq.left, 0, -res, esq.top)
        with WarpedVRT(src, crs="EPSG:3857", transform=malla, width=nx * lado_base, height=ny * lado_base,
                       resampling=Resampling.nearest, nodata=0) as vrt:
            for k, t in enumerate(bloques, 1):
                win = Window((t.x - x0) * lado_base, (t.y - y0) * lado_base, lado_base, lado_base)
                a = vrt.read(1, window=win)
                if not a.any():
                    continue
                desc = set(np.unique(a)) - {0} - set(codigos)
                assert not desc, f"códigos fuera de la leyenda: {desc}"
                nivel = a
                for z in range(ZMAX, ZBASE - 1, -1):
                    f = 2 ** (z - ZBASE)
                    for i in range(f):
                        for j in range(f):
                            sub = nivel[i * LADO:(i + 1) * LADO, j * LADO:(j + 1) * LADO]
                            d = png(sub, indice, paleta)
                            if d:
                                teselas[(z, t.x * f + j, t.y * f + i)] = d
                    if z > ZBASE:
                        nivel = moda2x2(nivel)
                base[(t.x, t.y)] = nivel
                if k % 25 == 0:
                    print(f"  z{ZBASE} {k}/{len(bloques)} · teselas {len(teselas)} · {time.time() - t0:.0f} s", flush=True)

    # Niveles bajos por moda desde z10
    nivel = base
    for z in range(ZBASE - 1, ZMIN - 1, -1):
        padres: dict[tuple[int, int], np.ndarray] = {}
        for (x, y) in {(x // 2, y // 2) for (x, y) in nivel}:
            m = np.zeros((2 * LADO, 2 * LADO), np.uint16)
            for dy in (0, 1):
                for dx in (0, 1):
                    h = nivel.get((2 * x + dx, 2 * y + dy))
                    if h is not None:
                        m[dy * LADO:(dy + 1) * LADO, dx * LADO:(dx + 1) * LADO] = h
            r = moda2x2(m)
            padres[(x, y)] = r
            d = png(r, indice, paleta)
            if d:
                teselas[(z, x, y)] = d
        nivel = padres

    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    with open(SALIDA, "wb") as fh:
        wr = Writer(fh)
        for (z, x, y) in sorted(teselas, key=lambda k: zxy_to_tileid(*k)):
            wr.write_tile(zxy_to_tileid(z, x, y), teselas[(z, x, y)])
        e7 = lambda v: int(round(v * 1e7))
        wr.finalize(
            {
                "tile_type": TileType.PNG,
                "tile_compression": Compression.NONE,
                "min_lon_e7": e7(w), "min_lat_e7": e7(s), "max_lon_e7": e7(e), "max_lat_e7": e7(n),
                "center_zoom": 7, "center_lon_e7": e7((w + e) / 2), "center_lat_e7": e7((s + n) / 2),
            },
            {
                "name": "Mapa de Ecosistemas de Honduras R26",
                "description": "Código de clase por píxel: R = código >> 8, G = código & 255; índice 0 = sin dato",
                "attribution": "SERNA · ICF · UICN ORMACC · CCAD/KfW · INGTELSIG",
                "codigos": codigos,
                "fuente": TIF.name,
            },
        )
    tam = SALIDA.stat().st_size
    por_z = {}
    for (z, _, _), d in teselas.items():
        por_z.setdefault(z, [0, 0]); por_z[z][0] += 1; por_z[z][1] += len(d)
    print(json.dumps({"teselas": len(teselas), "MB": round(tam / 1e6, 1), "por_zoom": {z: {"n": v[0], "MB": round(v[1] / 1e6, 1)} for z, v in sorted(por_z.items())}, "segundos": round(time.time() - t0)}, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
