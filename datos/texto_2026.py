"""«R26» es el número de revisión interno; en los textos públicos el mapa se nombra por su año: Mapa de Ecosistemas 2026.

Se usa al escribir las fichas (03), las capas de comparación (04) y los puntos de referencia (05).
Los nombres de archivo (p. ej. Mapa_Ecosistemas_R26_30m.tif) no se tocan.
"""
from __future__ import annotations

import re

_REGLAS = [
    (r"Mapa de Ecosistemas de Honduras\s*·\s*R26", "Mapa de Ecosistemas de Honduras 2026"),
    (r"Mapa de Ecosistemas de Honduras,? (?:edición )?R26", "Mapa de Ecosistemas de Honduras 2026"),
    (r"Mapa de Ecosistemas R26", "Mapa de Ecosistemas 2026"),
    (r"(?i)\b(la |de la |en la )?cartografía R26", lambda m: f"{m.group(1) or ''}{'C' if m.group(0)[0] == 'C' else 'c'}artografía 2026"),
    (r"identificados con R26", "identificados con el mapa 2026"),
    (r"\bdel R26\b", "del mapa 2026"),
    (r"\bel R26\b", "el mapa 2026"),
    (r"\ben R26\b", "en el mapa 2026"),
    (r"\bclase R26\b", "clase del mapa 2026"),
    (r"\bleyenda R26\b", "leyenda del mapa 2026"),
    (r"\bCatálogo R26\b", "Catálogo del Mapa de Ecosistemas 2026"),
    (r"(?<![_A-Za-z0-9])R26(?![_A-Za-z0-9])", "2026"),
]


def a_2026(texto: str) -> str:
    """Cambia las menciones de «R26» por el año del mapa, sin tocar nombres de archivo con guion bajo."""
    for patron, nuevo in _REGLAS:
        texto = re.sub(patron, nuevo, texto)
    return texto


def a_2026_obj(o):
    """Aplica a_2026 a todas las cadenas de una estructura JSON."""
    if isinstance(o, str):
        return a_2026(o)
    if isinstance(o, list):
        return [a_2026_obj(x) for x in o]
    if isinstance(o, dict):
        return {k: a_2026_obj(v) for k, v in o.items()}
    return o


if __name__ == "__main__":
    # Aplica la regla a los JSON ya generados en public/data (fichas, capas y puntos)
    import json
    import sys
    from pathlib import Path

    datos = Path(__file__).resolve().parent.parent / "public" / "data"
    rutas = sys.argv[1:] or [*sorted((datos / "fichas").glob("*.json")), datos / "capas" / "capas.json", datos / "puntos" / "puntos.geojson"]
    n = 0
    for r in map(Path, rutas):
        t = r.read_text(encoding="utf-8")
        o = a_2026_obj(json.loads(t))
        nuevo = json.dumps(o, ensure_ascii=False, separators=(",", ":"))
        if nuevo != t:
            r.write_text(nuevo, encoding="utf-8")
            n += 1
    print(f"{n} archivos actualizados")
