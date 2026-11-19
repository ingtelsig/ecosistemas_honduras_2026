# -*- coding: utf-8 -*-
"""Genera las capas de comparación del geovisor: criterios ecológicos base y Mapa de Ecosistemas 2002.

Salida en public/data/capas/:
  <id>.pmtiles     un PMTiles por capa, PNG de 8 bits con paleta: índice 0 = sin dato, 1..255 = valor
  capas.json       metadatos para el navegador (nombre, fuente, unidades, cómo pasar de índice a valor,
                   colores, clases y umbrales de la clasificación)
Y en datos/:
  correspondencia_2002_R26.csv   clase 2002 → clase R26 dominante (para los colores del mapa 2002).
                                 La columna «codigo_r26_color» se puede editar a mano; el script la respeta.

Valores continuos: índice = 1 + round(254 · f((v − min) / (max − min))), con f lineal o raíz cuadrada.
Valores de clase: índice = código (o código + 1 cuando el 0 es un valor válido).
Pirámide: el nivel máximo se remuestrea desde la fuente (promedio en continuas, vecino más cercano en
clases); los niveles inferiores se construyen por promedio o moda de 2×2.

Clima y fenología usan las versiones del R26 (CHPclim2 1991–2020 y Sentinel-2 2019–2025), no las
capas iniciales HND_11–16 de WorldClim y amplitud EVI2 v04.
"""
from __future__ import annotations

import sys as _sys
_sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
from texto_2026 import a_2026_obj  # «R26» -> «2026» en los textos públicos
import csv
import io
import json
import math
import os
import sys
import tempfile
import time
import warnings
from collections import defaultdict
from pathlib import Path

import mercantile
import numpy as np
import rasterio
from PIL import Image
from rasterio.enums import Resampling
from rasterio.features import rasterize
from rasterio.transform import Affine
from rasterio.vrt import WarpedVRT
from rasterio.warp import transform_bounds
from rasterio.windows import Window

AQUI = Path(__file__).resolve().parent
APP = AQUI.parent
TMP = AQUI / "_tmp"
TMP.mkdir(parents=True, exist_ok=True)
tempfile.tempdir = str(TMP)  # nada de temporales en C:
os.environ.setdefault("CPL_TMPDIR", str(TMP))
warnings.filterwarnings("ignore", category=RuntimeWarning)

from pmtiles.tile import Compression, TileType, zxy_to_tileid  # noqa: E402
from pmtiles.writer import Writer  # noqa: E402

BASE = Path(os.environ.get("CAPAS_BASE", "D:/web_GPT_proyectos/informe_mapa_ecosistemas/capas_base"))
ANALISIS = Path(os.environ.get("ANALISIS_DIR", "D:/web_D_anctigravity/analisis_ecosistemas"))
S2 = ANALISIS / "@MAPA_ECOSISTEMAS_V00/35_fenologia_sentinel2_2019_2025/Honduras_S2_fenologia_2019_2025_30m.tif"
CHP = APP.parent / "insumos_GEE" / "CHPclim2_mensual_1991_2020.tif"
V2002 = ANALISIS / "insumos" / "ecosistemas.geojson"
R26 = APP.parent / "Entrega_final_R26" / "Geodatos" / "Mapa_Ecosistemas_R26_30m.tif"
SALIDA = APP / "public" / "data" / "capas"
CORR = AQUI / "correspondencia_2002_R26.csv"

LADO = 256
ZBLOQUE = 8   # cada bloque de lectura es una tesela de z8
ZMIN = 5

COB_2024 = [  # Mapa Forestal y de Cobertura ICF 2024 (colores de MapaForestal_2024.qml)
    (1, "Bosque latifoliado siempreverde", "#006300"), (2, "Bosque de conífera", "#427d11"),
    (3, "Bosque mixto", "#4d5100"), (4, "Bosque latifoliado deciduo", "#8ca038"),
    (5, "Bosque de mangle", "#9f1fee"), (6, "Cultivos de ciclo corto", "#ffc0cc"),
    (7, "Musáceas", "#004200"), (8, "Caña de azúcar", "#851f4f"), (9, "Café", "#c58000"),
    (10, "Otros cultivos permanentes", "#b08f6a"), (11, "Frutales", "#8775ad"),
    (12, "Palma africana", "#33615f"), (13, "Vegetación arbustiva / matorral", "#cccccc"),
    (14, "Pastizales", "#f7f45a"), (15, "Sabana de bosque de pino", "#f4f4db"),
    (16, "Humedales con vegetación", "#ffa600"), (17, "Cuerpos de agua", "#0000ff"),
    (18, "Camaroneras / salineras", "#00006f"), (19, "Asentamiento", "#f60909"), (20, "Suelo", "#7f7f7f"),
    (21, "Playa", "#fff8e1"), (22, "Nubes / sombra", "#e0e0e0"), (23, "Bancos de arena", "#00ffff"),
    (24, "Arrozales", "#e88573"), (25, "Marismas", "#8ca3ed"),
]


# ----------------------------------------------------------------------------- definición de capas
ALTIMONTANO = 2000  # m; el mapa agrupa montano y altimontano, aquí se separan como referencia


def piso_r26(a):
    """Piso altitudinal con los umbrales del mapa: Caribe <500 / 500–1000 / ≥1000 m · Pacífico <700 / 700–1200 / ≥1200 m;
    altimontano ≥ 2000 m en ambas vertientes."""
    elev, vert = a
    pac = vert == 2
    p = np.full(elev.shape, np.nan, np.float32)
    ok = ~np.isnan(elev) & ~np.isnan(vert) & (vert > 0)
    p[ok] = 1
    p[ok & ~pac & (elev >= 500)] = 2
    p[ok & ~pac & (elev >= 1000)] = 3
    p[ok & pac & (elev >= 700)] = 2
    p[ok & pac & (elev >= 1200)] = 3
    p[ok & (elev >= ALTIMONTANO)] = 4
    return p


def lluvia_anual(a):
    m = a[0]
    s = m.sum(axis=0)
    s[(m < 0).any(axis=0) | np.isnan(m).any(axis=0)] = np.nan
    return s


def meses_secos(a):
    m = a[0]
    s = (m < 60).sum(axis=0).astype(np.float32)
    s[(m < 0).any(axis=0) | np.isnan(m).any(axis=0)] = np.nan
    return s


def cero_es_vacio(a):
    v = a[0].astype(np.float32)
    v[v <= 0] = np.nan
    return v


CAPAS = [
    {"id": "cobertura_2024", "uso": 'Es la base de cobertura del mapa. Separa bosque latifoliado, conífera, mixto, mangle, cultivos, pastizales, humedales y áreas transformadas, y decide a qué familia de clases (grupo nacional) pertenece cada celda antes de aplicar régimen, piso y drenaje.', "nombre": "Cobertura forestal y uso del suelo 2024", "grupo": "Cobertura",
     "fuente": "ICF, Mapa Forestal y de Cobertura de la Tierra 2024 (HND_02)", "tipo": "clases", "zmax": 12,
     "src": [(BASE / "HND_02_mapa_cobertura_2024.tif", 1)], "nodata0": True,
     "clases": [{"v": c, "n": n, "c": col} for c, n, col in COB_2024]},
    {"id": "elevacion", "uso": 'Define el piso altitudinal junto con la vertiente. Sus umbrales separan tierras bajas, submontano y montano en los bosques, arbustales y cafetales.', "nombre": "Elevación", "grupo": "Relieve", "unidad": "m s.n.m.",
     "fuente": "SRTM 30 m (HND_01)", "tipo": "continua", "zmax": 11, "min": 0, "max": 2800, "f": "lineal",
     "src": [(BASE / "HND_01_elevacion_srtm_m.tif", 1)], "rampa": "terreno",
     "umbrales": [{"v": 500, "n": "500 m: piso submontano (Caribe)"}, {"v": 700, "n": "700 m: piso submontano (Pacífico)"},
                  {"v": 1000, "n": "1.000 m: piso montano (Caribe)"}, {"v": 1200, "n": "1.200 m: piso montano (Pacífico)"},
                  {"v": 2000, "n": "2.000 m: piso altimontano"}]},
    {"id": "piso", "uso": 'Es el factor P del código de clase (1 tierras bajas, 2 submontano, 3 montano / altimontano) en bosques latifoliados, coníferas, mixtos y cafetales. Los umbrales cambian por vertiente porque en el Pacífico los pisos suben unos 200 m.', "nombre": "Piso altitudinal", "grupo": "Relieve",
     "fuente": "Derivado de SRTM (HND_01) y vertiente (HND_03) con los umbrales del R26", "tipo": "clases", "zmax": 11,
     "src": [(BASE / "HND_01_elevacion_srtm_m.tif", 1), (BASE / "HND_03_vertiente_caribe_pacifico.tif", 1)],
     "calc": piso_r26, "clases": [{"v": 1, "n": "Tierras bajas", "c": "#f2e6b6"}, {"v": 2, "n": "Submontano", "c": "#c9a86a"},
                                   {"v": 3, "n": "Montano", "c": "#8a6a44"}, {"v": 4, "n": "Altimontano", "c": "#4a3426"}],
     "nota": "Caribe: <500 / 500–1.000 / ≥1.000 m. Pacífico: <700 / 700–1.200 / ≥1.200 m. Altimontano: ≥2.000 m en ambas vertientes."},
    {"id": "vertiente", "uso": 'Ajusta los umbrales de piso: en el Caribe el submontano empieza a 500 m y el montano a 1.000 m; en el Pacífico, a 700 y 1.200 m.', "nombre": "Vertiente", "grupo": "Relieve", "fuente": "Cuencas hidrográficas (HND_03)",
     "tipo": "clases", "zmax": 11, "src": [(BASE / "HND_03_vertiente_caribe_pacifico.tif", 1)], "calc": cero_es_vacio,
     "clases": [{"v": 1, "n": "Caribe / Atlántico", "c": "#4f86c6"}, {"v": 2, "n": "Pacífico", "c": "#e0a040"}]},
    {"id": "hand", "uso": 'Mide la altura del terreno sobre el cauce más cercano. Con el área drenada y el agua superficial define el factor de drenaje (D): aluvial o mal drenado hasta 10 m, moderadamente drenado de 10 a 25 m y bien drenado por encima.', "nombre": "Altura sobre el drenaje (HAND)", "grupo": "Drenaje", "unidad": "m",
     "fuente": "MERIT Hydro (HND_06)", "tipo": "continua", "zmax": 11, "min": 0, "max": 150, "f": "raiz",
     "src": [(BASE / "HND_06_hand_altura_sobre_drenaje_m.tif", 1)], "rampa": "agua",
     "umbrales": [{"v": 3, "n": "3 m: hidromórfico (con agua superficial)"}, {"v": 10, "n": "10 m: aluvial o mal drenado"},
                  {"v": 25, "n": "25 m: moderadamente / bien drenado"}]},
    {"id": "drenaje", "uso": 'Es el factor D del código de bosques latifoliados, arbustales y pastizales: 2 aluvial o mal drenado (incluye el hidromórfico), 3 moderadamente drenado y 4 bien drenado.', "nombre": "Grupo de drenaje", "grupo": "Drenaje",
     "fuente": "Derivado de HAND, área acumulada (MERIT) y agua superficial GSW (HND_10)", "tipo": "clases", "zmax": 12,
     "src": [(BASE / "HND_10_grupo_drenaje.tif", 1)], "calc": cero_es_vacio,
     "clases": [{"v": 1, "n": "Hidromórfico", "c": "#1f4e9c"}, {"v": 2, "n": "Aluvial o mal drenado", "c": "#5fa3d9"},
                {"v": 3, "n": "Moderadamente drenado", "c": "#c7d98a"}, {"v": 4, "n": "Bien drenado", "c": "#e8c26a"}],
     "nota": "En la leyenda R26 el grupo hidromórfico se une con aluvial o mal drenado."},
    {"id": "agua_estacional", "uso": 'Indica cuántos meses al año hay agua en superficie. Una celda con agua al menos un mes pasa al grupo aluvial o mal drenado, y ayuda a delimitar humedales y lagunas.', "nombre": "Meses con agua superficial", "grupo": "Drenaje", "unidad": "meses",
     "fuente": "JRC Global Surface Water, estacionalidad (HND_08)", "tipo": "clases", "zmax": 12,
     "src": [(BASE / "HND_08_gsw_seasonality_meses.tif", 1)], "calc": cero_es_vacio, "rampa_clases": "agua",
     "clases": [{"v": m, "n": f"{m} {'mes' if m == 1 else 'meses'}"} for m in range(1, 13)]},
    {"id": "lluvia", "uso": 'Con los meses secos define el régimen climático (factor R: pluvial / siempreverde, estacional / semideciduo o seco / deciduo) mediante un modelo calibrado con las zonas de vida de Holdridge.', "nombre": "Precipitación anual", "grupo": "Clima", "unidad": "mm",
     "fuente": "CHPclim2 1991–2020 (versión usada en el R26; celdas de 0,05° ≈ 5,5 km)", "tipo": "continua",
     "zmax": 10, "min": 600, "max": 3600, "f": "lineal", "src": [(CHP, list(range(1, 13)))], "calc": lluvia_anual,
     "remuestreo": "vecino", "rampa": "lluvia"},
    {"id": "meses_secos", "uso": 'Cuenta los meses con menos de 60 mm. Es la variable de estacionalidad del régimen climático: más meses secos llevan a régimen estacional o seco.', "nombre": "Meses secos (< 60 mm)", "grupo": "Clima", "unidad": "meses",
     "fuente": "CHPclim2 1991–2020 (versión usada en el R26; celdas de 0,05° ≈ 5,5 km)", "tipo": "clases", "zmax": 10,
     "src": [(CHP, list(range(1, 13)))], "calc": meses_secos, "cero_valido": True, "rampa_clases": "seco",
     "clases": [{"v": m, "n": f"{m} {'mes' if m == 1 else 'meses'}"} for m in range(0, 13)]},
    {"id": "evi2", "uso": 'Mide cuánto cambia el verdor del dosel entre la época lluviosa y la seca. Confirma o corrige el régimen climático: amplitud baja indica dosel siempreverde y amplitud alta, dosel deciduo. Separa, por ejemplo, el bosque estacional del seco con la misma lluvia.', "nombre": "Cambio estacional del verdor (amplitud EVI2)", "grupo": "Fenología", "unidad": "",
     "fuente": "Sentinel-2 2019–2025, EVI2 P90 − P10 (versión usada en el R26)", "tipo": "continua", "zmax": 11,
     "min": 0, "max": 0.5, "f": "lineal", "decimales": 2, "src": [(S2, 10)], "escala": 0.0001, "nodata": -32768,
     "rampa": "fenologia",
     "umbrales": [{"v": 0.12, "n": "0,12: siempreverde / pluvial"}, {"v": 0.22, "n": "0,22: deciduo (seco)"}]},
    {"id": "altura_dosel", "uso": 'Separa formaciones por estructura: bosque frente a arbustal, matorral o pastizal, y bosque denso frente a ralo o sabana de pino.', "nombre": "Altura de la vegetación", "grupo": "Estructura", "unidad": "m",
     "fuente": "Integración ETH 2020 y GLAD/GEDI (HND_22)", "tipo": "continua", "zmax": 11, "min": 0, "max": 35,
     "f": "lineal", "src": [(BASE / "HND_22_altura_vegetacion_integrada_m.tif", 1)], "rampa": "verde"},
    {"id": "cobertura_arborea", "uso": 'Completa a la altura: indica si la vegetación forma dosel cerrado (bosque), abierto (bosque ralo, sabana arbolada) o no arbóreo (arbustal, pastizal).', "nombre": "Cobertura arbórea", "grupo": "Estructura", "unidad": "%",
     "fuente": "Integración GFCC, Copernicus y Dynamic World (HND_23)", "tipo": "continua", "zmax": 11,
     "min": 0, "max": 100, "f": "lineal", "src": [(BASE / "HND_23_cobertura_arborea_integrada_pct.tif", 1)],
     "rampa": "verde"},
    {"id": "regimen_629", "uso": 'No cambia la leyenda: la clase 629 (bosque latifoliado abierto y/o perturbado) conserva su código. Esta capa reparte la 629 por régimen con los mismos criterios del arbustal y del ajuste del bosque seco: toma el régimen del bosque latifoliado vecino, pasa a seco solo con señal seca firme (caída de verdor Sentinel-2 y lluvia del trimestre seco) y deja de ser seca sobre siempreverde ICF o con evidencias en contra. Resultado: 948.328 ha secas, 362.651 estacionales y 269.104 pluviales.', "nombre": "Régimen de la clase 629", "grupo": "Complementos del R26", "tipo": "clases", "zmax": 12,
     "fuente": "Capa complementaria del R26 (Geodatos/Complementarias/Regimen_629_R26_30m.tif; scripts 63 y 65)",
     "src": [(APP.parent / "Entrega_final_R26" / "Geodatos" / "Complementarias" / "Regimen_629_R26_30m.tif", 1)], "calc": cero_es_vacio,
     "clases": [{"v": 1, "n": "629 pluvial / siempreverde", "c": "#2c7fb8"}, {"v": 2, "n": "629 estacional / semideciduo", "c": "#fc8d59"},
                {"v": 3, "n": "629 seco / deciduo", "c": "#d7301f"}]},
    {"id": "mapa_2002", "uso": 'No interviene en la clasificación. Es el antecedente nacional (Mejía Ordóñez y House 2002) que sirvió de base al sistema de clases y permite comparar visualmente los cambios.', "nombre": "Mapa de Ecosistemas 2002", "grupo": "Mapa anterior", "tipo": "clases", "zmax": 12,
     "fuente": "Mejía Ordóñez y House (2002), Mapa de Ecosistemas Vegetales de Honduras",
     "vector": V2002,
     "nota": "Colores tomados de la clase R26 con la que más se superpone cada clase 2002 (tabla de correspondencia revisable)."},
]

RAMPAS = {  # colores de 0 a 1
    "terreno": ["#2e7d4f", "#8bbf6a", "#e9e3a6", "#c79a5b", "#8a5a3c", "#f2f2f2"],
    "agua": ["#08306b", "#2171b5", "#6baed6", "#c6dbef", "#f7fbff"],
    "lluvia": ["#f6e8c3", "#c7eae5", "#5ab4ac", "#2166ac", "#08306b"],
    "seco": ["#2166ac", "#67a9cf", "#d1e5f0", "#fddbc7", "#ef8a62", "#b2182b"],
    "fenologia": ["#0b6e3a", "#62b357", "#d9ef8b", "#fdae61", "#a6501e"],
    "verde": ["#f7f4e8", "#c2e09a", "#5fae5a", "#1d6b35", "#0a3d1f"],
}


def interp(rampa: list[str], t: float) -> str:
    t = min(1.0, max(0.0, t)) * (len(rampa) - 1)
    i = min(int(t), len(rampa) - 2)
    a = [int(rampa[i][k:k + 2], 16) for k in (1, 3, 5)]
    b = [int(rampa[i + 1][k:k + 2], 16) for k in (1, 3, 5)]
    f = t - i
    return "#" + "".join(f"{round(x + (y - x) * f):02x}" for x, y in zip(a, b))


# ----------------------------------------------------------------------------- utilidades de teselas
def moda2x2(a: np.ndarray) -> np.ndarray:
    v = np.stack([a[0::2, 0::2], a[0::2, 1::2], a[1::2, 0::2], a[1::2, 1::2]])
    cuenta = np.zeros(v.shape, np.int8)
    for i in range(4):
        for j in range(4):
            cuenta[i] += v[i] == v[j]
    cuenta[v == 0] = 0
    return np.take_along_axis(v, np.argmax(cuenta, axis=0)[None], 0)[0]


def media2x2(a: np.ndarray) -> np.ndarray:
    v = np.stack([a[0::2, 0::2], a[0::2, 1::2], a[1::2, 0::2], a[1::2, 1::2]])
    return np.nanmean(v, axis=0)


PALETA = bytes(sum(([i, 0, 0] for i in range(256)), []))


def png(idx: np.ndarray) -> bytes | None:
    if not idx.any():
        return None
    im = Image.fromarray(idx.astype(np.uint8), "P")
    im.putpalette(PALETA)
    b = io.BytesIO()
    im.save(b, "PNG", optimize=True, transparency=0)
    return b.getvalue()


def a_indice(capa: dict, v: np.ndarray) -> np.ndarray:
    out = np.zeros(v.shape, np.uint8)
    ok = ~np.isnan(v)
    if capa["tipo"] == "continua":
        t = np.clip((v[ok] - capa["min"]) / (capa["max"] - capa["min"]), 0, 1)
        if capa["f"] == "raiz":
            t = np.sqrt(t)
        out[ok] = 1 + np.round(254 * t).astype(np.uint8)
    else:
        validos = np.array([c["v"] for c in capa["clases"]])
        r = np.round(v[ok]).astype(np.int32)
        r[~np.isin(r, validos)] = -1
        idx = r + (1 if capa.get("cero_valido") else 0)
        idx[r < 0] = 0
        out[ok] = idx.astype(np.uint8)
    return out


def malla_bloques(w: float, s: float, e: float, n: float, zmax: int):
    bloques = list(mercantile.tiles(w, s, e, n, ZBLOQUE))
    lado = LADO * 2 ** (zmax - ZBLOQUE)
    x0, y0 = min(t.x for t in bloques), min(t.y for t in bloques)
    nx, ny = max(t.x for t in bloques) - x0 + 1, max(t.y for t in bloques) - y0 + 1
    esq = mercantile.xy_bounds(mercantile.Tile(x0, y0, ZBLOQUE))
    res = 2 * math.pi * 6378137 / (LADO * 2 ** zmax)
    return bloques, lado, x0, y0, nx, ny, Affine(res, 0, esq.left, 0, -res, esq.top)


# ----------------------------------------------------------------------------- mapa 2002
def leer_2002():
    import geopandas as gpd
    g = gpd.read_file(V2002).to_crs(3857)
    nombres = sorted(g["ecosistema"].dropna().unique())
    clase = {n: i for i, n in enumerate(nombres, start=1)}
    g["clase"] = g["ecosistema"].map(clase)
    g = g[g["clase"].notna() & g.geometry.notna()]
    une = g.groupby("ecosistema")["codigo_une"].first().to_dict()
    ha = g.groupby("ecosistema")["HAS"].sum().to_dict()
    return g, nombres, clase, une, ha


ANTROPICAS_2002 = ("acuacultura", "urbana", "agropecuario")
GRUPOS_USO = {"G12", "G13", "G14"}
NO_EQUIVALENTES = {629, 16201}  # bosque perturbado y zona marina potencial: estados o ámbitos, no tipos equivalentes


def colores_2002(nombres, clase, une, ha, cruce: np.ndarray) -> list[dict]:
    """Color de cada clase 2002: la clase R26 equivalente con mayor superposición.

    Para las clases 2002 naturales solo cuentan las clases R26 naturales (sin pastizales intervenidos,
    cultivos, áreas urbanas ni bosque perturbado), de modo que el color refleje el tipo de ecosistema
    y no lo que lo sustituyó. La columna codigo_r26_color del CSV (si se edita) manda."""
    cat = {c["codigo"]: c for c in json.loads((APP / "public/data/clases.json").read_text(encoding="utf-8"))["clases"]}
    uso = {k for k, c in cat.items() if c["grupo"] in GRUPOS_USO} | NO_EQUIVALENTES
    manual = {}
    if CORR.exists():
        with CORR.open(encoding="utf-8-sig") as fh:
            for r in csv.DictReader(fh):
                if (r.get("codigo_r26_color") or "").strip().isdigit() and r["codigo_r26_color"].strip() != str(r.get("r26_equivalente", "")):
                    manual[r["ecosistema_2002"]] = int(r["codigo_r26_color"])
    filas, clases = [], []
    for n in nombres:
        i = clase[n]
        fila = cruce[i]
        total = fila.sum()
        orden = [c for c in np.argsort(fila)[::-1][:3] if fila[c] > 0 and c in cat]
        dom = orden[0] if orden else 0
        antropica = any(a in n.lower() for a in ANTROPICAS_2002)
        candidatos = [c for c in np.argsort(fila)[::-1] if fila[c] > 0 and c in cat and ((c in uso and c not in NO_EQUIVALENTES) if antropica else c not in uso)]
        equiv = int(candidatos[0]) if candidatos else dom
        elegido = manual.get(n, equiv)
        col = cat[elegido]["color"] if elegido in cat else "#bdbdbd"
        clases.append({"v": i, "n": n, "c": col, "une": une.get(n, ""), "r26": int(elegido)})
        filas.append({
            "clase_2002": i, "ecosistema_2002": n, "codigo_une": une.get(n, ""), "ha_2002": round(ha.get(n, 0), 1),
            "r26_dominante": dom, "nombre_r26_dominante": cat[dom]["nombre"] if dom in cat else "",
            "pct_superposicion": round(100 * fila[dom] / total, 1) if total else 0,
            "r26_equivalente": equiv, "nombre_r26_equivalente": cat[equiv]["nombre"] if equiv in cat else "",
            "pct_equivalente": round(100 * fila[equiv] / total, 1) if total else 0,
            "codigo_r26_color": elegido, "color": col,
        })
    with CORR.open("w", encoding="utf-8-sig", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(filas[0]))
        wr.writeheader()
        wr.writerows(filas)
    return clases


# ----------------------------------------------------------------------------- proceso de una capa
def procesar(capa: dict, w: float, s: float, e: float, n: float) -> dict:
    """Continuas: la pirámide guarda valores (float, NaN = sin dato) y se reduce por promedio.
    Clases: guarda índices (uint8, 0 = sin dato) y se reduce por moda."""
    t0 = time.time()
    zmax = capa["zmax"]
    continua = capa["tipo"] == "continua"
    bloques, lado, x0, y0, nx, ny, malla = malla_bloques(w, s, e, n, zmax)
    kw = dict(crs="EPSG:3857", transform=malla, width=nx * lado, height=ny * lado)
    teselas: dict[tuple[int, int, int], bytes] = {}
    base: dict[tuple[int, int], np.ndarray] = {}
    r26 = rasterio.open(R26)
    mascara = WarpedVRT(r26, resampling=Resampling.nearest, nodata=0, **kw)
    abiertos, vrts = [], []
    vector = "vector" in capa
    if vector:
        import shapely
        g, nombres, clase, une, ha = leer_2002()
        geoms, valores = list(g.geometry), g["clase"].astype(int).tolist()
        sindex = g.sindex
        cruce = np.zeros((len(nombres) + 1, 65536), np.int64)
    else:
        promedio = continua and capa.get("remuestreo") != "vecino"
        for ruta, banda in capa["src"]:
            ds = rasterio.open(ruta)
            abiertos.append(ds)
            nd = capa.get("nodata", ds.nodata)
            if nd is None and ds.dtypes[0].startswith("float"):
                nd = float("nan")
            remu = Resampling.average if (promedio or (ruta.name.startswith("HND_01") and "calc" in capa)) else Resampling.nearest
            vrts.append((WarpedVRT(ds, resampling=remu, src_nodata=nd, nodata=nd, **kw), banda, nd))

    def indices(v: np.ndarray) -> np.ndarray:
        if vector:
            return np.nan_to_num(v, nan=0).astype(np.uint8)
        return a_indice(capa, v)

    for k, t in enumerate(bloques, 1):
        win = Window((t.x - x0) * lado, (t.y - y0) * lado, lado, lado)
        m = mascara.read(1, window=win)
        if not m.any():
            continue
        if vector:
            b = mercantile.xy_bounds(t)
            sel = sindex.query(shapely.box(b.left, b.bottom, b.right, b.top))
            if len(sel) == 0:
                continue
            tr = Affine(malla.a, 0, b.left, 0, malla.e, b.top)
            v = rasterize(((geoms[i], valores[i]) for i in sel), out_shape=(lado, lado), transform=tr, fill=0, dtype="uint16")
            np.add.at(cruce, (v.astype(np.int64).ravel(), m.astype(np.int64).ravel()), 1)
            v = v.astype(np.float32)
            v[v == 0] = np.nan
        else:
            arrs = []
            for vrt, banda, nd in vrts:
                a = vrt.read(banda, window=win).astype(np.float32)
                if nd is not None and not (isinstance(nd, float) and math.isnan(nd)):
                    a[a == nd] = np.nan
                if "escala" in capa:
                    a *= capa["escala"]
                arrs.append(a)
            v = capa["calc"](arrs) if "calc" in capa else arrs[0]
            if capa.get("nodata0"):
                v[v == 0] = np.nan
        v[m == 0] = np.nan  # solo dentro de la huella del mapa R26
        if np.isnan(v).all():
            continue
        nivel = v if continua else indices(v)
        for z in range(zmax, ZBLOQUE - 1, -1):
            f = 2 ** (z - ZBLOQUE)
            idx = indices(nivel) if continua else nivel
            for i in range(f):
                for j in range(f):
                    d = png(idx[i * LADO:(i + 1) * LADO, j * LADO:(j + 1) * LADO])
                    if d:
                        teselas[(z, t.x * f + j, t.y * f + i)] = d
            if z > ZBLOQUE:
                nivel = media2x2(nivel) if continua else moda2x2(nivel)
        base[(t.x, t.y)] = nivel
        if k % 40 == 0:
            print(f"    {capa['id']} bloque {k}/{len(bloques)} · {len(teselas)} teselas · {time.time() - t0:.0f} s", flush=True)

    if vector:
        capa["clases"] = colores_2002(nombres, clase, une, ha, cruce)
    nivel = base
    for z in range(ZBLOQUE - 1, ZMIN - 1, -1):
        padres = {}
        for (x, y) in {(x // 2, y // 2) for (x, y) in nivel}:
            mm = np.full((2 * LADO, 2 * LADO), np.nan, np.float32) if continua else np.zeros((2 * LADO, 2 * LADO), np.uint8)
            for dy in (0, 1):
                for dx in (0, 1):
                    h = nivel.get((2 * x + dx, 2 * y + dy))
                    if h is not None:
                        mm[dy * LADO:(dy + 1) * LADO, dx * LADO:(dx + 1) * LADO] = h
            r = media2x2(mm) if continua else moda2x2(mm)
            padres[(x, y)] = r
            d = png(indices(r) if continua else r)
            if d:
                teselas[(z, x, y)] = d
        nivel = padres
    for ds in abiertos:
        ds.close()
    r26.close()

    SALIDA.mkdir(parents=True, exist_ok=True)
    ruta = SALIDA / f"{capa['id']}.pmtiles"
    with open(ruta, "wb") as fh:
        wr = Writer(fh)
        for (z, x, y) in sorted(teselas, key=lambda q: zxy_to_tileid(*q)):
            wr.write_tile(zxy_to_tileid(z, x, y), teselas[(z, x, y)])
        e7 = lambda q: int(round(q * 1e7))
        wr.finalize(
            {"tile_type": TileType.PNG, "tile_compression": Compression.NONE,
             "min_lon_e7": e7(w), "min_lat_e7": e7(s), "max_lon_e7": e7(e), "max_lat_e7": e7(n),
             "center_zoom": 7, "center_lon_e7": e7((w + e) / 2), "center_lat_e7": e7((s + n) / 2)},
            {"name": capa["nombre"], "description": "Índice por píxel en el canal rojo (0 = sin dato); ver capas.json"},
        )
    mb = ruta.stat().st_size / 1e6
    print(f"  {capa['id']}: {len(teselas)} teselas · {mb:.1f} MB · {time.time() - t0:.0f} s", flush=True)
    return {"MB": round(mb, 1), "teselas": len(teselas)}


# Orden en el visor: criterios de relieve, drenaje, clima, fenología y estructura; al final la cobertura 2024 y el mapa 2002
ORDEN = ["elevacion", "piso", "vertiente", "hand", "drenaje", "agua_estacional", "lluvia", "meses_secos", "evi2",
         "altura_dosel", "cobertura_arborea", "cobertura_2024", "mapa_2002", "regimen_629"]
CAPAS.sort(key=lambda c: ORDEN.index(c["id"]))


def metadatos(capa: dict) -> dict:
    out = {k: capa[k] for k in ("id", "nombre", "grupo", "fuente", "uso", "tipo", "zmax") if k in capa}
    for k in ("unidad", "min", "max", "f", "umbrales", "nota", "decimales"):
        if k in capa:
            out[k] = capa[k]
    out["archivo"] = f"capas/{capa['id']}.pmtiles"
    if capa["tipo"] == "continua":
        rampa = RAMPAS[capa["rampa"]]
        out["rampa"] = rampa
        # tabla índice → color (1..255)
        lut = []
        for i in range(1, 256):
            t = (i - 1) / 254
            lut.append(interp(rampa, t))
        out["lut"] = lut
    else:
        clases = capa["clases"]
        if "rampa_clases" in capa:
            r = RAMPAS[capa["rampa_clases"]]
            for j, c in enumerate(clases):
                c["c"] = interp(r if capa["rampa_clases"] != "agua" else r[::-1], j / max(1, len(clases) - 1))
        out["desplazamiento"] = 1 if capa.get("cero_valido") else 0
        out["clases"] = clases
    return out


def main() -> None:
    solo = set(sys.argv[1:])
    with rasterio.open(R26) as r:
        w, s, e, n = transform_bounds(r.crs, "EPSG:4326", *r.bounds)
    previo = {}
    meta_ruta = SALIDA / "capas.json"
    if meta_ruta.exists():
        previo = {c["id"]: c for c in json.loads(meta_ruta.read_text(encoding="utf-8"))["capas"]}
    salida = []
    for capa in CAPAS:
        if solo and capa["id"] not in solo:
            if capa["id"] in previo:
                textos = {k: capa[k] for k in ("nombre", "grupo", "fuente", "uso", "nota", "umbrales") if k in capa}
                salida.append({**previo[capa["id"]], **textos})
            continue
        print(f"== {capa['nombre']}", flush=True)
        info = procesar(capa, w, s, e, n)
        m = metadatos(capa)
        m.update(info)
        salida.append(m)
        meta_ruta.parent.mkdir(parents=True, exist_ok=True)
        meta_ruta.write_text(json.dumps({"capas": a_2026_obj(salida)}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    meta_ruta.write_text(json.dumps({"capas": a_2026_obj(salida)}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("total MB:", round(sum(c.get("MB", 0) for c in salida), 1))


if __name__ == "__main__":
    main()
