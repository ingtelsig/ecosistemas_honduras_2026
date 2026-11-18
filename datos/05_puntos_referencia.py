"""Capa de puntos de referencia del R26 y fichas de campo.

Genera:
  public/data/puntos/puntos.geojson   1.228 puntos con sus atributos (fuente, clases, GET y trazabilidad)
  public/data/puntos/fichas/CAM-nnn.pdf  ficha técnica de validación de cada punto de campo (320),
                                          con las fuentes reducidas a los caracteres usados

Fuentes:
  Entrega_final_R26/Complementos_R26/Puntos_de_referencia_y_superficies_jerarquicas_R26.xlsx
  Anexo 1 del Producto 3 (fichas individuales y su base) y la base de registros de campo, que vincula
  cada punto CAM-nnn con su ficha: el número del archivo de ficha de la base es el del punto.
No se publican nombres de técnicos ni fotografías: solo lo que ya trae la ficha oficial.
"""
from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path

import pandas as pd
import pymupdf

AQUI = Path(__file__).resolve().parent
APP = AQUI.parent
R26 = Path(os.environ.get("ECOSYSTEMS_R26_DIR", APP.parent / "Entrega_final_R26"))
XLSX = R26 / "Complementos_R26" / "Puntos_de_referencia_y_superficies_jerarquicas_R26.xlsx"
VAL = Path(os.environ.get("VALIDACION_DIR", "D:/web_D_anctigravity/analisis_ecosistemas/@ARCHIVOS_FINALES/05_ANEXOS_TECNICOS/Validacion_y_clasificacion"))
FICHAS = VAL / "Fichas_Campo_Individuales"
SALIDA = APP / "public" / "data" / "puntos"


def txt(v) -> str | None:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    s = str(v).strip()
    return s or None


def num(v, nd=6):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) else round(f, nd)


def enlace_fichas(cam: list[int]) -> dict[int, dict]:
    """CAM-n -> fila de la base de fichas del Anexo 1 (mismo orden; se comprueba el código de sitio)."""
    base = pd.read_excel(VAL / "BASE_REGISTROS_CAMPO_VALIDACION.xlsx")
    base["n"] = base["ficha_file"].astype(str).str.split("_").str[0].astype(int)
    base = base.set_index("n")
    fichas = pd.read_excel(FICHAS / "BASE_DATOS_FICHAS_CAMPO_PRODUCTO3_2026.xlsx")
    if len(fichas) != len(cam):
        sys.exit(f"Hay {len(fichas)} fichas y {len(cam)} puntos de campo")
    norm = lambda s: "".join(ch for ch in str(s).lower() if ch.isalnum())
    out = {}
    for n, (_, f) in zip(sorted(cam), fichas.iterrows()):
        b = base.loc[n]
        if norm(b["codigo_punto"]) != norm(f["Codigo_Sitio"]) or str(b["municipio_nombre"]).lower() != str(f["Municipio"]).lower():
            sys.exit(f"CAM-{n}: la ficha {f['ID_Sitio']} no coincide ({b['codigo_punto']} / {f['Codigo_Sitio']})")
        out[n] = {
            "ficha_id": int(f["ID_Sitio"]),
            "codigo_sitio": txt(f["Codigo_Sitio"]),
            "fecha": str(f["Fecha"])[:10],
            "departamento": txt(f["Departamento"]),
            "municipio": txt(f["Municipio"]),
            "pdf": f["Archivo_PDF"],
        }
    return out


def comprimir(origen: Path, destino: Path):
    if destino.exists() and destino.stat().st_mtime >= origen.stat().st_mtime:
        return
    d = pymupdf.open(origen)
    d.subset_fonts()
    d.save(destino, garbage=4, deflate=True, clean=True)
    d.close()


def main():
    SALIDA.mkdir(parents=True, exist_ok=True)
    (SALIDA / "fichas").mkdir(exist_ok=True)
    g = pd.read_excel(XLSX, "Base_Puntos_GET_UICN")
    t = pd.read_excel(XLSX, "Trazabilidad_GET_Ref").set_index("ID_Punto")
    cam = [int(i[4:]) for i in g["ID_Punto"] if i.startswith("CAM-")]
    fichas = enlace_fichas(cam)

    feats = []
    for _, r in g.iterrows():
        pid = r["ID_Punto"]
        tr = t.loc[pid] if pid in t.index else None
        p = {
            "id": pid,
            "fuente": txt(r["Fuente_Datos"]),
            "tipo": "campo" if pid.startswith("CAM-") else "secundaria",
            "elev": num(r["Elevacion_DEM_msnm"], 0),
            "piso": txt(r["Piso_Altitudinal"]),
            "ref_original": txt(r["Clase_Original_Referencia"]),
            "ref_homologada": txt(r["Clase_Homologada_Referencia"]),
            "mapa_clase": txt(r["Clase_Original_Mapa"]),
            "mapa_homologada": txt(r["Clase_Homologada_Mapa"]),
            "grupo_ref": txt(r["Grupo_14_Referencia"]),
            "grupo_mapa": txt(r["Grupo_14_Mapa"]),
            "bioma_ref": txt(r["Bioma_Referencia"]),
            "bioma_mapa": txt(r["Bioma_Mapa"]),
        }
        for n in (1, 2, 3):
            p[f"get{n}_ref"] = txt(r[f"GET_L{n}_Referencia"])
            p[f"get{n}_mapa"] = txt(r[f"GET_L{n}_Mapa"])
        if tr is not None:
            p.update({
                "evidencia": txt(tr["Evidencia_Archivada"]),
                "estado": txt(tr["Estado_Referencia_Archivada"]),
                "resultado_get": txt(tr["Resultado_GET_Referencia"]),
                "regla": txt(tr["Regla_Referencia"]),
                "codigos_compatibles": txt(tr["Codigos_Nacionales_Compatibles"]),
                "efg_candidatos": txt(tr["EFG_Candidatos"]),
            })
        if pid.startswith("CAM-"):
            f = fichas[int(pid[4:])]
            comprimir(FICHAS / f.pop("pdf"), SALIDA / "fichas" / f"{pid}.pdf")
            p.update(f)
        p = {k: v for k, v in p.items() if v is not None}
        feats.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [num(r["Longitud_WGS84"]), num(r["Latitud_WGS84"])]},
            "properties": p,
        })

    (SALIDA / "puntos.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": feats}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    peso = sum(f.stat().st_size for f in (SALIDA / "fichas").glob("*.pdf")) / 1e6
    print(f"{len(feats)} puntos; {len(fichas)} fichas de campo ({peso:.1f} MB)")


if __name__ == "__main__":
    main()
