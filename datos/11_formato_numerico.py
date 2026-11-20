"""Formato numérico del informe técnico final en los textos de datos: coma de miles y punto decimal (1,234.56).

Último paso de la cadena (08 → 09 → 10 → 11). Solo cambia cadenas de texto (no números JSON) e intercambia '.' y ','
dentro de cifras con formato español; respeta URL, DOI, rutas y citas [1,2]. Es idempotente: las cifras ya
convertidas (1,234.5) no vuelven a coincidir.
Uso: python -X utf8 datos/11_formato_numerico.py
"""
import json
import re
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent / "public" / "data"
MILES = re.compile(r"(?<![\d.,])([1-9]\d{0,2}(?:\.\d{3})+)(,\d+)?(?![\d])")
DECIMAL = re.compile(r"(?<![\d.,])(\d+),(\d{1,2})(?![\d])|(?<![\d.,])(0),(\d{3,})(?![\d])")
stats = Counter()


def protegido(t, ini, fin):
    a = max(t.rfind(" ", 0, ini), t.rfind(">", 0, ini)) + 1
    b = t.find(" ", fin)
    tok = t[a: b if b >= 0 else len(t)]
    if any(x in tok.lower() for x in ("/", "http", "www", "doi", "@", "\\", "isbn", "issn")):
        return True
    izq = t.rfind("[", 0, ini)
    if izq >= 0 and t.find("]", izq) >= fin and re.fullmatch(r"[\d,\s–-]*", t[izq + 1:t.find("]", izq)]):
        return True
    # paginación y volúmenes de referencias: «pp. 12,34», «45(2),»
    if re.search(r"(pp?\.|vol\.|n\.º|\))\s*$", t[max(0, ini - 6):ini]):
        return True
    return False


def convertir(t):
    pos = set()
    for m in MILES.finditer(t):
        if not protegido(t, m.start(), m.end()):
            pos.update(i for i in range(m.start(), m.end()) if t[i] in ".,")
            stats["miles"] += 1
    for m in DECIMAL.finditer(t):
        i = t.index(",", m.start())
        if i not in pos and not protegido(t, m.start(), m.end()):
            pos.add(i)
            stats["decimal"] += 1
    if not pos:
        return t
    return "".join(("," if c == "." else ".") if i in pos else c for i, c in enumerate(t))


def recorrer(o, clave=None):
    if isinstance(o, dict):
        return {k: recorrer(v, k) for k, v in o.items()}
    if isinstance(o, list):
        return [recorrer(v, clave) for v in o]
    if isinstance(o, str) and clave not in ("id", "c", "color", "archivo", "mapa", "sha256", "une", "lut", "rampa"):
        return convertir(o)
    return o


def tratar(p):
    s = p.read_text(encoding="utf-8")
    compacto = not s.lstrip().startswith("{\n")
    d = recorrer(json.loads(s))
    p.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":") if compacto else None, indent=None if compacto else 1),
                 encoding="utf-8")


archivos = sorted((RAIZ / "fichas").glob("*.json")) + [RAIZ / "clases.json", RAIZ / "capas" / "capas.json",
                                                       RAIZ / "manifiesto.json", RAIZ / "puntos" / "puntos.geojson"]
for p in archivos:
    tratar(p)
print(f"formato numérico aplicado en {len(archivos)} archivos: {dict(stats)}")
