# -*- coding: utf-8 -*-
"""Genera los datos tabulares y los límites del geovisor a partir de la entrega R26.

Salidas en public/data/:
  clases.json                 115 clases con nombre, grupo, color oficial (.qml), GET L1–L3, EFG y superficies oficiales
  limites/<capa>.geojson      límites simplificados (cobertura topológica) en WGS 84
  limites/contexto.geojson    contorno terrestre y límite marino para el mapa base propio
  unidades/<capa>.json        por unidad: superficie medida a 30 m, hectáreas por clase y hectáreas dentro del SINAPH
  manifiesto.json             edición, fuentes, fecha y huellas sha256

Los resúmenes se calculan sobre el ráster maestro de 30 m (celda = 0,09 ha), rasterizando cada capa
sobre la misma malla (centro de celda). Se contrastan con Control/Indicadores_fichas/cruces_territoriales.csv.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import sys
import time
import unicodedata
from collections import defaultdict
from datetime import date
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
import shapely
from rasterio.features import rasterize
from rasterio.windows import Window

AQUI = Path(__file__).resolve().parent
APP = AQUI.parent
R26 = Path(os.environ.get("ECOSYSTEMS_R26_DIR", APP.parent / "Entrega_final_R26"))
TERR = Path(os.environ.get("TERRITORIOS_GPKG", "I:/Catalogo_Ecologico_Honduras_V004/01_base_datos/territorios.gpkg"))
PUEBLOS = Path(os.environ.get("PUEBLOS_SHP", AQUI / "fuentes" / "pueblos_indigenas" / "Pueblos indigenas.shp"))
MARINO = Path(os.environ.get("LIMITE_MARINO", "D:/web_GPT_proyectos/informe_mapa_ecosistemas/capas_base/Marino/Limite_Territorio_Marino.shp"))
TIF = R26 / "Geodatos" / "Mapa_Ecosistemas_R26_30m.tif"
QML = R26 / "Geodatos" / "Mapa_Ecosistemas_R26_30m.qml"
OUT = APP / "public" / "data"
HA = 0.09

CAPAS = {
    # clave web: (capa en territorios.gpkg, nombre en cruces_territoriales.csv, tolerancia de simplificación en m)
    # None en la capa: se lee de otro archivo; None en cruces: no hay referencia R26 con qué contrastar
    "areas_protegidas": ("areas_protegidas", "SINAPH", 40),
    "pueblos_indigenas": (None, None, 60),
    "departamentos": ("departamentos", "Departamento", 60),
    "municipios": ("municipios", "Municipio", 40),
}


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def leer_csv(p: Path) -> list[dict]:
    with open(p, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def catalogo_clases() -> dict:
    q = QML.read_text(encoding="utf-8")
    color = {int(v): c.lower() for v, c in re.findall(r'value="(\d+)"[^>]*?color="(#[0-9a-fA-F]{6})', q)}
    sup = leer_csv(R26 / "Clasificacion" / "Superficies_ajustadas_R26_por_codigo.csv")
    niv = leer_csv(R26 / "Clasificacion" / "Superficies_ajustadas_R26_por_nivel.csv")
    nombre = {(r["nivel"], r["codigo"]): r["nombre"] for r in niv}
    corr = defaultdict(list)
    for r in leer_csv(R26 / "Clasificacion" / "Correspondencias_nacionales_GET_UICN_R26.csv"):
        corr[int(r["class_id"])].append([r["EFG"], r["EFG_nombre_es"], r["es_principal"] == "True"])
    # Nombres ajustados en el geovisor (ver datos/nombres_ajustados.json)
    ajustes = json.loads((Path(__file__).parent / "nombres_ajustados.json").read_text(encoding="utf-8"))
    ajuste = {int(k): v for k, v in ajustes.items() if k.isdigit()}
    color.update({int(k): v for k, v in ajustes.get("colores", {}).items() if k.isdigit()})
    clases = []
    for r in sorted(sup, key=lambda r: int(r["codigo"])):
        c = int(r["codigo"])
        clases.append({
            "codigo": c,
            "nombre": ajuste.get(c, r["unidad_nacional"]),
            "grupo": r["grupo_nacional"],
            "get1": r["GET_L1"], "get2": r["GET_L2"], "get3": r["GET_L3"],
            "color": color[c],
            "efg": corr.get(c, []),
            "ha_ajustada": round(float(r["total_ajustado_ha"]), 2),
            "ha_cartografiada": round(float(r["R26_cartografiada_ha"]), 2),
        })
    assert len(clases) == 115 and all(k["color"] for k in clases)
    grupos = [{"codigo": r["codigo"], "nombre": r["nombre"]} for r in niv if r["nivel"] == "G" and r["codigo"] != "TOTAL"]
    get = {lv: {r["codigo"]: r["nombre"] for r in niv if r["nivel"] == lv and r["codigo"] != "TOTAL"} for lv in ("GET_L1", "GET_L2", "GET_L3")}
    return {"edicion": "R26", "clases": clases, "grupos": grupos, "get": get}


# Nombres normalizados del campo ETNIA_1 (variantes de escritura de la misma etiqueta)
NOMBRE_PUEBLO = {
    "Maya Chorti": "Maya Chortí",
    "Miskito-Miskitu": "Miskito (Miskitu)",
    "Miskito,Garífuna y Mestizo": "Miskito, Garífuna y Mestizo",
    "Tawahka & Mestizo": "Tawahka y Mestizo",
}
INDIGENAS = {"Lenca", "Tolupán", "Pech", "Nahua", "Maya Chortí", "Tawahka", "Miskito (Miskitu)"}
AFRO = {"Garífuna", "Garífuna e Isleño"}


def slug(s: str) -> str:
    s = unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_")


def unidades_pueblos() -> gpd.GeoDataFrame:
    """Una unidad por pueblo: se unen los polígonos con la misma etiqueta ETNIA_1."""
    g = gpd.read_file(PUEBLOS).to_crs(32616)
    g["geometry"] = shapely.make_valid(g.geometry.values)
    g["nombre"] = g["ETNIA_1"].str.strip().map(lambda s: NOMBRE_PUEBLO.get(s, s))
    d = g.dissolve(by="nombre", aggfunc={"ETNIA_1": "count"}).rename(columns={"ETNIA_1": "poligonos"}).reset_index()
    d["id"] = d["nombre"].map(slug)
    d["categoria"] = d["nombre"].map(
        lambda n: "Pueblo indígena" if n in INDIGENAS else "Pueblo afrohondureño" if n in AFRO else "Territorio compartido")
    d["categoria"] = d["categoria"] + " · " + d["poligonos"].map(lambda n: f"{n} polígono" + ("s" if n > 1 else ""))
    d["padre"] = ""
    d = d[["id", "nombre", "categoria", "padre", "geometry"]].sort_values("nombre").reset_index(drop=True)
    assert d["id"].is_unique
    return d


def unidades_capa(clave: str) -> gpd.GeoDataFrame:
    if clave == "pueblos_indigenas":
        return unidades_pueblos()
    capa = CAPAS[clave][0]
    g = gpd.read_file(TERR, layer=capa).to_crs(32616)
    attrs = g["attrs_json"].map(json.loads)
    if clave == "areas_protegidas":
        g["id"] = g["code"]
        g["nombre"] = g["label"]
        g["categoria"] = attrs.map(lambda a: a.get("categoria", ""))
        g["padre"] = ""
    elif clave == "municipios":
        g["id"] = g["code"]; g["nombre"] = g["label"]; g["categoria"] = "Municipio"
        g["padre"] = attrs.map(lambda a: a.get("adm1_pcode", ""))
    else:
        g["id"] = g["code"]; g["nombre"] = g["label"]; g["categoria"] = "Departamento"; g["padre"] = ""
    g = g[["id", "nombre", "categoria", "padre", "geometry"]].copy()
    g["geometry"] = shapely.make_valid(g.geometry.values)
    g = g.sort_values("nombre").reset_index(drop=True)
    assert g["id"].is_unique, clave
    return g


def zonal(capas: dict[str, gpd.GeoDataFrame], codigos: list[int]) -> tuple[dict, dict]:
    """Recorre el ráster por franjas: hectáreas por (unidad, clase) y celdas dentro del SINAPH por unidad."""
    idx = np.zeros(65536, np.int32)
    for i, c in enumerate(codigos, start=1):
        idx[c] = i
    nc = len(codigos) + 1
    cuentas = {k: np.zeros((len(g) + 1) * nc, np.int64) for k, g in capas.items()}
    en_ap = {k: np.zeros(len(g) + 1, np.int64) for k, g in capas.items()}
    # Las áreas protegidas pueden solaparse (p. ej. Cerro Azul Meámbar y Lago de Yojoa): cada capa se reparte
    # en subcapas sin solape para que cada unidad cuente su superficie completa, como en los cruces R26.
    formas: dict[str, list[list]] = {}
    for k, g in capas.items():
        subcapas: list[list] = []
        geoms: list[list] = []
        for i, geom in enumerate(g.geometry):
            for sc, gs in zip(subcapas, geoms):
                if not any(geom.intersection(o).area > 1 for o in gs if geom.intersects(o)):
                    sc.append((geom, i + 1)); gs.append(geom); break
            else:
                subcapas.append([(geom, i + 1)]); geoms.append([geom])
        formas[k] = subcapas
        print(f"  {k}: {len(subcapas)} subcapa(s) sin solape", flush=True)
    t0 = time.time()
    with rasterio.open(TIF) as src:
        assert src.crs.to_epsg() == 32616
        alto = 1024
        for f0 in range(0, src.height, alto):
            h = min(alto, src.height - f0)
            win = Window(0, f0, src.width, h)
            tr = src.window_transform(win)
            cls = idx[src.read(1, window=win)]
            dato = cls > 0
            ras = {k: [rasterize(sc, out_shape=(h, src.width), transform=tr, fill=0, dtype="int32") for sc in formas[k]] for k in capas}
            ap = np.zeros((h, src.width), bool)
            for r in ras["areas_protegidas"]:
                ap |= r > 0
            for k, lista in ras.items():
                for r in lista:
                    m = (r > 0) & dato
                    cuentas[k] += np.bincount(r[m].astype(np.int64) * nc + cls[m], minlength=cuentas[k].size)
                    en_ap[k] += np.bincount(r[m & ap], minlength=en_ap[k].size)
            print(f"  filas {f0 + h}/{src.height} · {time.time() - t0:.0f} s", flush=True)
    return ({k: v.reshape(-1, nc) for k, v in cuentas.items()}, en_ap)


def simplificar(g: gpd.GeoDataFrame, tol: float) -> gpd.GeoDataFrame:
    s = g.copy()
    try:
        s["geometry"] = shapely.coverage_simplify(s.geometry.values, tol)
    except Exception:  # capas con solapes (no es cobertura): simplificación por objeto
        s["geometry"] = s.geometry.simplify(tol, preserve_topology=True)
    s["geometry"] = shapely.make_valid(s.geometry.values)
    return s.to_crs(4326)


def escribir_geojson(g: gpd.GeoDataFrame, p: Path, campos: list[str]) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    feats = []
    for _, r in g.iterrows():
        geom = shapely.set_precision(r.geometry, 1e-5)
        feats.append({"type": "Feature", "properties": {k: r[k] for k in campos},
                      "geometry": json.loads(shapely.to_geojson(geom))})
    p.write_text(json.dumps({"type": "FeatureCollection", "features": feats}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    cat = catalogo_clases()
    (OUT / "clases.json").write_text(json.dumps(cat, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    codigos = [c["codigo"] for c in cat["clases"]]

    capas = {k: unidades_capa(k) for k in CAPAS}
    cuentas, en_ap = zonal(capas, codigos)

    cruces = pd.read_csv(R26 / "Control" / "Indicadores_fichas" / "cruces_territoriales.csv", dtype={"territorio": str})
    control = {}
    for clave, g in capas.items():
        tol = CAPAS[clave][2]
        escribir_geojson(simplificar(g, tol), OUT / "limites" / f"{clave}.geojson", ["id", "nombre", "categoria", "padre"])
        unidades = []
        for i, r in g.iterrows():
            fila = cuentas[clave][i + 1]
            pares = [[codigos[j - 1], round(int(fila[j]) * HA, 2)] for j in np.nonzero(fila)[0] if j > 0]
            pares.sort(key=lambda p: -p[1])
            b = gpd.GeoSeries([r.geometry], crs=32616).to_crs(4326).total_bounds
            unidades.append({
                "id": r["id"], "nombre": r["nombre"], "categoria": r["categoria"], "padre": r["padre"],
                "ha": round(int(fila.sum()) * HA, 2),
                "ha_sinaph": round(int(en_ap[clave][i + 1]) * HA, 2),
                "ha_poligono": round(r.geometry.area / 1e4, 2),
                "bbox": [round(float(v), 5) for v in b],
                "clases": pares,
            })
        (OUT / "unidades").mkdir(exist_ok=True)
        (OUT / "unidades" / f"{clave}.json").write_text(json.dumps({"capa": clave, "unidades": unidades}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

        # Contraste con los cruces oficiales de la entrega R26
        if CAPAS[clave][1] is None:
            print(clave, {"unidades": len(unidades), "ha_total": round(sum(u["ha"] for u in unidades), 2)}, flush=True)
            continue
        ref = cruces[cruces.capa == CAPAS[clave][1]]
        clave_ref = "nombre" if clave == "areas_protegidas" else "territorio"
        campo = "nombre" if clave == "areas_protegidas" else "id"
        ref_ha = ref.groupby([clave_ref, "codigo"]).hectareas.sum().to_dict()
        mio = {(u[campo], c): h for u in unidades for c, h in u["clases"]}
        claves = set(ref_ha) | set(mio)
        dif = [abs(ref_ha.get(k, 0) - mio.get(k, 0)) for k in claves]
        control[clave] = {
            "unidades": len(unidades), "ha_total": round(sum(u["ha"] for u in unidades), 2),
            "ha_total_cruces_R26": round(float(ref.hectareas.sum()), 2),
            "pares_clase_unidad": len(mio), "pares_cruces_R26": len(ref_ha),
            "dif_max_ha": round(max(dif), 2), "pares_con_dif_mayor_0_1_ha": sum(d > 0.1 for d in dif),
        }
        print(clave, control[clave], flush=True)

    # Contexto del mapa base: contorno terrestre (unión de departamentos) y límite marino
    tierra = shapely.coverage_union_all(capas["departamentos"].geometry.values)
    mar = gpd.read_file(MARINO).to_crs(32616).union_all()
    ctx = gpd.GeoDataFrame({"tipo": ["tierra", "mar"]}, geometry=[tierra, mar], crs=32616)
    ctx["geometry"] = ctx.geometry.simplify(80, preserve_topology=True)
    escribir_geojson(ctx.to_crs(4326), OUT / "limites" / "contexto.geojson", ["tipo"])

    man = {
        "edicion": "R26", "generado": date.today().isoformat(),
        "raster": {"archivo": TIF.name, "sha256": sha256(TIF), "celda_ha": HA},
        "fuentes": {
            "areas_protegidas": "ICF, Geoportal: áreas protegidas declaradas del SINAPH (75 áreas, 324 zonas; fecha de creación más reciente 2025-02-17)",
            "departamentos": "OCHA/HDX, límites administrativos de Honduras, a partir de SINIT/SEPLAN 2010 (CC BY-IGO)",
            "municipios": "OCHA/HDX, límites administrativos de Honduras, a partir de SINIT/SEPLAN 2010 (CC BY-IGO)",
            "pueblos_indigenas": "UICN-Honduras, capa de pueblos indígenas y afrohondureños (30 polígonos, campo ETNIA_1); los polígonos de un mismo pueblo se unen en una unidad",
            "limite_marino": MARINO.name,
        },
        "control_cruces_R26": control,
    }
    (OUT / "manifiesto.json").write_text(json.dumps(man, ensure_ascii=False, indent=2), encoding="utf-8")
    print("listo")


if __name__ == "__main__":
    sys.exit(main())
