"""Mapas de distribución de las fichas (uno por clase) dibujados desde el ráster maestro (con el ajuste de manglares).

Adaptado de Entrega_final_R26/scripts/pipeline/dibujar_catalogo_R26.py (mismo encuadre, colores, escala y norte);
cambia el rótulo, que dice
«Honduras · 2026 · UTM 16N». No dibuja los mapas de grupo, que el visor no usa.

Salida: datos/raster/mapas_fichas/<codigo>.png (los lee 03_fichas.py) y public/data/fichas/mapas/<codigo>.webp.
"""
from __future__ import annotations

import csv
import json
import math
import os
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import rasterio
from PIL import Image, ImageColor, ImageDraw, ImageFilter, ImageFont
from rasterio.windows import Window

AQUI = Path(__file__).resolve().parent
R26 = Path(os.environ.get("ECOSYSTEMS_R26_DIR", AQUI.parent.parent / "Entrega_final_R26"))
GEO = R26 / "Geodatos"
TIF = GEO / "Mapa_Ecosistemas_R26_30m.tif"
CTX = Path(os.environ.get("CONTEXTO_MAPA", "D:/web_D_anctigravity/analisis_ecosistemas/@MAPA_ECOSISTEMAS_V00/"
                          "20_V004_revision_ecologica_final_20261024/09_reproducibilidad/assets_revision/contexto_mapa.json"))
PNG = AQUI / "raster" / "mapas_fichas"
WEBP = AQUI.parent / "public" / "data" / "fichas" / "mapas"
ROTULO = "Honduras  ·  2026  ·  UTM 16N"
LAGOS = (6111, 6112, 6113)  # se dibujan por densidad

style = {int(e.get("value")): e.attrib for e in ET.parse(GEO / "Mapa_Ecosistemas_R26_30m.qml").findall(".//paletteEntry")}
with (GEO / "Superficies_R25_R26.csv").open(encoding="utf-8-sig", newline="") as f:
    data = {int(r["codigo"]): r for r in csv.DictReader(f)}
codes = sorted(data)
n = len(codes) + 1
assert len(codes) == 115 and set(style) == set(codes)
lookup = np.zeros(65536, np.uint8)
lookup[codes] = np.arange(1, n)
chunks: dict[int, list] = {k: [] for k in codes}
step = 10
with rasterio.open(TIF) as src:
    assert src.crs.to_epsg() == 32616 and src.nodata == 0 and src.res == (30, 30)
    x0, y0 = src.transform.c, src.transform.f
    width = math.ceil(src.width / step)
    col = np.arange(src.width, dtype=np.uint32) // step
    for y in range(0, src.height, 300):
        block = src.read(1, window=Window(0, y, src.width, min(300, src.height - y)))
        ix = lookup[block]
        assert np.count_nonzero(block) == np.count_nonzero(ix)
        rows = (np.arange(y, y + len(ix), dtype=np.uint32) // step) * width
        good = np.nonzero(ix)
        ids = ix[good].astype(np.uint32)
        u, v = np.unique(ids * (1 << 24) + rows[good[0]] + col[good[1]], return_counts=True)
        if v.size:
            who = u >> 24
            places = u & ((1 << 24) - 1)
            end = np.r_[0, np.flatnonzero(np.diff(who)) + 1, len(who)]
            for a, b in zip(end[:-1], end[1:]):
                chunks[codes[who[a] - 1]].append((places[a:b], v[a:b].astype(np.uint8)))
        if y % 4800 == 0:
            print(y, src.height, flush=True)
hits = {k: tuple(np.concatenate(p) for p in zip(*parts)) for k, parts in chunks.items()}
context = json.loads(CTX.read_text(encoding="utf-8"))


def font(size, strong=False):
    return ImageFont.truetype("C:/Windows/Fonts/" + ("arialbd.ttf" if strong else "arial.ttf"), size)


W, PW, M = 1380, 1320, 30
SEA, LAND, FOREIGN, INK = "#edf4f7", "#f5f1e6", "#e9eae2", "#1a353b"
boundaries = {"land": (232000, 1412000, 934000, 1848000), "coast": (232000, 1412000, 1055000, 1885000),
              "marine": (238000, 1413000, 1245000, 2177000)}


def polygons(geometry):
    c = geometry["coordinates"]
    return [c] if geometry["type"] == "Polygon" else c if geometry["type"] == "MultiPolygon" else []


def fit(key, k):
    l, b, r, t = boundaries[key]
    loc = hits[k][0]
    x = x0 + (loc % width + .5) * 300
    y = y0 - (loc // width + .5) * 300
    l, r = min(l, int(x.min()) - 5000), max(r, int(x.max()) + 5000)
    b, t = min(b, int(y.min()) - 5000), max(t, int(y.max()) + 5000)
    scale = (r - l) / PW
    H = round((t - b) / scale)
    return (l, t - H * scale, r, t), H, scale


def framing(k):
    g = int(data[k]["grupo"])
    return "marine" if g == 1 else ("coast" if g <= 4 or k in (624, 625) else "land")


def render(k):
    kind = framing(k)
    (l, b, r, t), H, scale = fit(kind, k)
    canvas = Image.new("RGB", (W, H + 110 + 35), "#f8faf9")
    draw = ImageDraw.Draw(canvas)

    def pg(x, y):
        return (round((x - l) / scale), round((t - y) / scale))

    panel = Image.new("RGB", (PW, H), SEA)
    dr = ImageDraw.Draw(panel)
    for country in context["inset_countries"]:
        c = LAND if country["name"] == "Honduras" else FOREIGN
        for rings in polygons(country["geometry"]):
            if not rings:
                continue
            dr.polygon([pg(*p) for p in rings[0]], fill=c, outline="#a6b6b5")
            for hole in rings[1:]:
                dr.polygon([pg(*p) for p in hole], fill=SEA)
    if kind != "marine":
        for dep in context["departments"]:
            for rings in polygons(dep["geometry"]):
                for ring in rings:
                    dr.line([pg(*p) for p in ring], fill="#bcc8c5", width=1)
    pos, counts = hits[k]
    u = np.floor((x0 + (pos % width + .5) * 300 - l) / scale).astype(np.int32)
    v = np.floor((t - y0 + (pos // width + .5) * 300) / scale).astype(np.int32)
    presence = np.zeros((H, PW), np.uint8)
    np.maximum.at(presence, (v, u), counts)
    arr = np.array(panel)
    if k in LAGOS:
        # lagos: cada bloque de 300 m con una intensidad según la fracción ocupada (100 celdas = bloque lleno), para que
        # las lagunas pequeñas en fila no se lean como un río. Sin red fluvial de fondo: en azul se confundía con el lago.
        a =np.clip(0.35 + 0.65 * presence / 50.0, 0, 1)[..., None] * (presence > 0)[..., None]
        arr[:] = (arr * (1 - a) + np.array(ImageColor.getrgb(style[k]["color"])) * a).astype(np.uint8)
    else:
        presence = (presence > 0).astype(np.uint8) * 255
        if int((presence > 0).sum()) < 110:
            presence = np.asarray(Image.fromarray(presence).filter(ImageFilter.MaxFilter(3)))
        arr[presence > 0] = ImageColor.getrgb(style[k]["color"])
    canvas.paste(Image.fromarray(arr), (M, 22))
    draw.rectangle((M, 22, M + PW, 22 + H), outline="#8fa8aa", width=1)
    draw.text((M + PW - 45, 42), "N", font=font(24, True), fill=INK)
    draw.polygon([(M + PW - 37, 78), (M + PW - 47, 103), (M + PW - 27, 103)], fill=INK)
    y = H + 37
    length = 100000 / scale
    draw.line((M, y, M + length, y), fill=INK, width=6)
    for dx in (0, length / 2, length):
        draw.line((M + dx, y - 6, M + dx, y + 6), fill=INK, width=2)
    draw.text((M, y + 11), "0", font=font(19), fill=INK)
    draw.text((M + length - 20, y + 11), "100 km", font=font(19), fill=INK)
    draw.text((M + PW, y + 11), ROTULO, anchor="ra", font=font(19), fill=INK)
    draw.rectangle((M, y + 45, M + 22, y + 65), fill=style[k]["color"], outline="#839394", width=1)
    draw.text((M + 30, y + 42), str(k), font=font(19, True), fill=INK)
    canvas.save(PNG / f"{k}.png")
    im = canvas.copy()
    im.thumbnail((960, 960))
    im.save(WEBP / f"{k}.webp", "WEBP", quality=78, method=6)


PNG.mkdir(parents=True, exist_ok=True)
WEBP.mkdir(parents=True, exist_ok=True)
import sys
for k in [int(a) for a in sys.argv[1:]] or codes:
    render(k)
print(f"{len(codes)} mapas de clase dibujados desde {TIF.name}")
