"""Ajuste de los manglares por costa: cada clase de manglar queda en la costa que indica su nombre.

El ráster entregado (Entrega_final_R26/Geodatos/Mapa_Ecosistemas_R26_30m.tif) tenía manglar «del Caribe» en el Golfo de
Fonseca (6261: 1.459,5 ha; 6271: 11,2 ha) y manglar «del Pacífico» en la costa norte (6272: 7,3 ha). Este script copia el
ráster y recodifica solo esas celdas:

  costa del Pacífico (al sur de y = 1.600.000 m, UTM 16N ≈ 14,5° N): 6261 → 6262 · 6271 → 6272
  costa del Caribe e islas (al norte):                                 6262 → 6261 · 6272 → 6271

El corte por latitud es inequívoco porque las dos costas están separadas por más de 200 km; el 97 % de las celdas
recodificadas cae además en la vertiente del Pacífico de HND_03 (el resto, en la franja intermareal sin vertiente).
La estructura (alto y denso / bajo y enano) no cambia. El ráster original no se modifica.

Salida: datos/raster/Mapa_Ecosistemas_2026_30m.tif y datos/ajuste_manglares.json (celdas recodificadas por par de clases).
01_teselas_R26.py, 02_limites_y_resumenes.py y 07_mapas_fichas.py leen el ráster ajustado.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import rasterio

AQUI = Path(__file__).resolve().parent
R26 = Path(os.environ.get("ECOSYSTEMS_R26_DIR", AQUI.parent.parent / "Entrega_final_R26"))
ORIGEN = R26 / "Geodatos" / "Mapa_Ecosistemas_R26_30m.tif"
DESTINO = AQUI / "raster" / "Mapa_Ecosistemas_2026_30m.tif"
REGISTRO = AQUI / "ajuste_manglares.json"
CORTE_Y = 1_600_000  # m (UTM 16N): al sur, costa del Pacífico
AL_PACIFICO = {6261: 6262, 6271: 6272}
AL_CARIBE = {6262: 6261, 6272: 6271}


def main() -> None:
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    cambios: dict[str, int] = {}
    with rasterio.open(ORIGEN) as src:
        perfil = src.profile | {"compress": "deflate", "predictor": 2, "tiled": True, "blockxsize": 512, "blockysize": 512}
        T = src.transform
        with rasterio.open(DESTINO, "w", **perfil) as dst:
            for _, w in src.block_windows(1):
                a = src.read(1, window=w)
                filas = np.arange(w.row_off, w.row_off + w.height)
                sur = (T.f + (filas + 0.5) * T.e < CORTE_Y)[:, None]
                for regla, zona in ((AL_PACIFICO, sur), (AL_CARIBE, ~sur)):
                    for de, a_ in regla.items():
                        m = (a == de) & zona
                        n = int(m.sum())
                        if n:
                            a[m] = a_
                            cambios[f"{de}->{a_}"] = cambios.get(f"{de}->{a_}", 0) + n
                dst.write(a, 1, window=w)
    reg = {
        "origen": ORIGEN.name, "destino": DESTINO.name, "corte_y_utm16n": CORTE_Y,
        "celdas": cambios, "ha": {k: round(v * 0.09, 2) for k, v in cambios.items()},
    }
    REGISTRO.write_text(json.dumps(reg, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(reg, ensure_ascii=False))


if __name__ == "__main__":
    main()
