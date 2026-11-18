"""Extrae las fichas monográficas de las 115 unidades ecosistémicas de los catálogos R26 (Word) para el geovisor.

Entrada:  Entrega_final_R26/Catalogos/Catalogo_agrupado_1/CATALOGO_GRUPO_*.docx (una ficha por título de nivel 1)
          Entrega_final_R26/scripts/work/mapas_fichas/<codigo>.png (mapa de distribución de cada clase)
Salida:   public/data/fichas/<codigo>.json  y  public/data/fichas/mapas/<codigo>.webp
          public/data/fichas/indice.json (códigos con ficha y su catálogo de origen)

Cada ficha conserva el orden del documento como bloques: títulos, párrafos (con cursivas y negritas), listas y tablas.
Las figuras y la galería de fotos de campo no se copian; solo el mapa de distribución.
"""
from __future__ import annotations

import sys as _sys
_sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
from texto_2026 import a_2026_obj  # «R26» -> «2026» en los textos públicos
import html
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

import docx
from docx.table import Table
from docx.text.paragraph import Paragraph
from PIL import Image

AQUI = Path(__file__).resolve().parent
APP = AQUI.parent
R26 = Path(os.environ.get("ECOSYSTEMS_R26_DIR", APP.parent / "Entrega_final_R26"))
CATALOGOS = R26 / "Catalogos" / "Catalogo_agrupado_1"
MAPAS = AQUI / "raster" / "mapas_fichas"  # 07_mapas_fichas.py (rótulo 2026)
OUT = APP / "public" / "data" / "fichas"

FIGURA = re.compile(r"^(Figura|Foto|Fotograf|Lámina|Imagen|Mapa)\b", re.I)
SECCIONES_SIN_TEXTO = re.compile(r"Galería fotográfica", re.I)


def html_parrafo(p: Paragraph) -> str:
    """Texto del párrafo como HTML mínimo (<i>, <b>); el resto se escapa."""
    partes = []
    try:
        contenido = list(p.iter_inner_content())
    except AttributeError:  # python-docx < 1.0
        contenido = list(p.runs)
    for r in contenido:
        if hasattr(r, "runs") and not hasattr(r, "italic"):  # hipervínculo
            t = "".join(x.text for x in r.runs)
            it = bo = False
        else:
            t, it, bo = r.text, bool(r.italic), bool(r.bold)
        if not t:
            continue
        t = html.escape(t)
        if it:
            t = f"<i>{t}</i>"
        if bo:
            t = f"<b>{t}</b>"
        partes.append(t)
    s = "".join(partes)
    return re.sub(r"</i><i>|</b><b>", "", s).strip()


def texto_celda(c) -> str:
    return re.sub(r"\s+", " ", c.text).strip()


def tabla(t: Table) -> list[list[str]]:
    filas = []
    for r in t.rows:
        celdas = []
        previo = None
        for c in r.cells:
            if c._tc is previo:  # celdas combinadas repetidas por python-docx
                continue
            previo = c._tc
            celdas.append(texto_celda(c))
        if any(celdas):
            filas.append(celdas)
    return filas


# ----------------------------------------------------------------------------- referencias (formato APA)
# Referencia institucional única del estudio: sustituye cualquier entrada que mencione a INGTELSIG
# (incluido el «Capítulo 9» del equipo técnico, que se integra en ella).
REF_ESTUDIO = "INGTELSIG / SERNA / UICN (2026). <i>Estudio de actualización del Mapa de Ecosistemas de Honduras 2026</i>. Informe técnico institucional."

# Anotaciones internas de trazabilidad que no forman parte de una referencia APA (van tras « — » al final)
ANOTACION = re.compile(
    r"\s*—\s*(?:Documento local|Fuente documentada|Resumen científico|Texto completo|Secciones pertinentes|Contenido de la fuente"
    r"|Registro bibliográfico|Registro local|Perfil funcional|Información taxonómica|Información institucional|Referencia candidata).*$",
    re.S,
)
# Notas de verificación dentro de la referencia
NOTAS = [
    re.compile(r"\s*Alcance:.*$", re.S),
    re.compile(r"\s*\[[^\]]*(?:verific|indexad|HTTP|pendiente|acceso|no empleada|comanejador|referencia bibliográfica)[^\]]*\]", re.I),
    re.compile(r"\s*\((?:respaldo técnico consultado|atributos de vigencia|capa base normalizada)[^)]*\)", re.I),
    re.compile(r";?\s*fecha de compilación original no acreditada", re.I),
    re.compile(r"\s*(?:Versión institucional )?[Cc]onsultad[ao] el \d{1,2} de \w+ de \d{4}\.", re.I),
    re.compile(r"\s*Fecha original no acreditada\.", re.I),
    re.compile(r"\s*Antecedente histórico nacional\.", re.I),
    re.compile(r";?\s*fecha cartográfica original no acreditada en metadatos", re.I),
    re.compile(r",\s*copia local (?:consultada|inspeccionada|verificada) (?:para este catálogo|en el catálogo Mapa de Ecosistemas de Honduras 2026)(?=[.;)])", re.I),
    re.compile(r"\s*Cartografía facilitada para el estudio,?", re.I),
    re.compile(r"\s*capa Cuencas, \d+ unidades\.?", re.I),
]
CITA = re.compile(r"\[(\d+(?:\s*[,–-]\s*\d+)*)\]")
CITA_CLAVE = re.compile(r"\[([A-Z]\d+(?:\s*[;,]\s*[A-Z]\d+)*)\]")


def limpiar_ref(h: str) -> str:
    """Deja solo los elementos APA: autor, fecha, título, fuente y DOI/URL."""
    h = re.sub(r"^\s*•\s*", "", h)
    if "INGTELSIG" in h.upper() or "Equipo de revisión ecológica del proyecto" in h:
        return REF_ESTUDIO
    h = ANOTACION.sub("", h)
    for r in NOTAS:
        h = r.sub("", h)
    h = re.sub(r"\s{2,}", " ", h).strip()
    h = re.sub(r"\s+([.,;])", r"\1", h)
    h = re.sub(r"\.\.+$", ".", h)
    h = re.sub(r"(https?://\S+?)\.$", r"\1", h)  # APA: sin punto tras DOI/URL
    if not re.search(r"[.)]$|https?://\S+$", h):
        h += "."
    return h


def expandir(lista: str) -> list[int]:
    out: list[int] = []
    for parte in re.split(r"\s*,\s*", lista):
        m = re.match(r"(\d+)\s*[–-]\s*(\d+)$", parte)
        out += list(range(int(m.group(1)), int(m.group(2)) + 1)) if m else [int(parte)]
    return out


def ordenar_referencias(bloques: list[dict]) -> None:
    """Limpia las referencias numeradas [n], une las duplicadas (p. ej. las de INGTELSIG) y renumera las citas del texto."""
    en_refs = False
    numeradas: list[tuple[int, int | str, str]] = []  # (índice de bloque, número o clave original, texto limpio)
    for i, b in enumerate(bloques):
        if b["t"] in ("h2", "h3"):
            en_refs = b["x"].startswith("Referencias") if b["t"] == "h2" else en_refs
            continue
        if not en_refs or b["t"] not in ("p", "li"):
            continue
        m = re.match(r"^(?:<b>)?\[(\d+)\]\s*(?:</b>)?\s*(.*)$", b["h"], re.S)
        k = re.match(r"^(?:<b>)?\[([A-Z]\d+)\]\s*(?:</b>)?\s*(.*?)(?:</b>)?$", b["h"], re.S)
        if m:
            numeradas.append((i, int(m.group(1)), limpiar_ref(m.group(2))))
        elif k:  # referencias con clave (p. ej. [M01]): se integran a la lista numerada
            numeradas.append((i, k.group(1), limpiar_ref(k.group(2))))
            b["t"] = "p"
        else:
            b["h"] = limpiar_ref(b["h"])
            b["t"] = "p"
    if not numeradas:
        return
    # Las de clave ([M01]…) van detrás de la lista numerada original, para que [1] siga siendo el estudio
    con_clave = [bloques[i] for i, v, _ in numeradas if isinstance(v, str)]
    numericas = [i for i, v, _ in numeradas if isinstance(v, int)]
    objeto = {id(bloques[i]): (v, t) for i, v, t in numeradas}
    if con_clave and numericas:
        ultimo = bloques[max(numericas)]
        for b in con_clave:
            bloques.remove(b)
        pos = next(j for j, b in enumerate(bloques) if b is ultimo) + 1
        bloques[pos:pos] = con_clave
        numeradas = [(j, *objeto[id(b)]) for j, b in enumerate(bloques) if id(b) in objeto]
    nuevo: dict[int | str, int] = {}
    por_texto: dict[str, int] = {}
    quitar: set[int] = set()
    n = 0
    for i, viejo, texto in numeradas:
        clave = re.sub(r"<[^>]+>", "", texto).lower()
        if clave in por_texto:  # duplicada: sus citas pasan a la primera
            nuevo[viejo] = por_texto[clave]
            quitar.add(i)
            continue
        n += 1
        nuevo[viejo] = por_texto[clave] = n
        bloques[i]["h"] = f"<b>[{n}]</b> {texto}"
    for i in sorted(quitar, reverse=True):
        del bloques[i]

    def recita(m: re.Match) -> str:
        nums = expandir(m.group(1))
        if not all(x in nuevo for x in nums):
            return m.group(0)  # no es una cita a la lista numerada
        vistos: list[int] = []
        for x in nums:
            if nuevo[x] not in vistos:
                vistos.append(nuevo[x])
        return "[" + ", ".join(map(str, sorted(vistos))) + "]"

    def recita_clave(m: re.Match) -> str:
        claves = re.split(r"\s*[;,]\s*", m.group(1))
        if not all(x in nuevo for x in claves):
            return m.group(0)
        return "[" + ", ".join(map(str, sorted({nuevo[x] for x in claves}))) + "]"

    def citas(x: str) -> str:
        return CITA_CLAVE.sub(recita_clave, CITA.sub(recita, x))

    en_refs = False
    for b in bloques:
        if b["t"] == "h2":
            en_refs = b["x"].startswith("Referencias")
        if en_refs:
            continue
        if b.get("h"):
            b["h"] = citas(b["h"])
        if b.get("f"):
            b["f"] = [[citas(c) for c in fila] for fila in b["f"]]


def leer_catalogo(p: Path, estilos: Counter) -> list[dict]:
    d = docx.Document(p)
    fichas: list[dict] = []
    actual: dict | None = None
    omitir_seccion = False
    for el in d.element.body.iterchildren():
        tag = el.tag.rsplit("}", 1)[-1]
        if tag == "p":
            par = Paragraph(el, d)
            est = par.style.name if par.style is not None else ""
            txt = par.text.strip()
            if est == "Heading 1":
                actual = {"nombre": txt, "bloques": [], "codigo": None}
                fichas.append(actual)
                omitir_seccion = False
                continue
            if actual is None or not txt:
                continue
            estilos[est] += 1
            if est in ("Heading 2", "Heading 3", "Heading 4"):
                omitir_seccion = bool(SECCIONES_SIN_TEXTO.search(txt))
                if not omitir_seccion:
                    actual["bloques"].append({"t": "h2" if est == "Heading 2" else "h3", "x": txt})
                continue
            if omitir_seccion:
                continue
            if est == "Caption" or est.startswith("Caption"):
                if FIGURA.match(txt):
                    continue
                actual["bloques"].append({"t": "nota", "h": html_parrafo(par)})
            elif "List" in est or est.startswith("Lista"):
                actual["bloques"].append({"t": "li", "h": html_parrafo(par)})
            else:
                actual["bloques"].append({"t": "p", "h": html_parrafo(par)})
        elif tag == "tbl" and actual is not None and not omitir_seccion:
            f = tabla(Table(el, d))
            if not f:
                continue
            if actual["codigo"] is None:
                for fila in f:
                    m = re.match(r"^(\d{3,5})\s*·", fila[-1]) if len(fila) > 1 else None
                    if m:
                        actual["codigo"] = int(m.group(1))
                        break
            actual["bloques"].append({"t": "tabla", "f": f})
    # quitar títulos que quedaron sin contenido
    for fi in fichas:
        b = fi["bloques"]
        fi["bloques"] = [x for i, x in enumerate(b) if not (x["t"] in ("h2", "h3") and (i + 1 == len(b) or b[i + 1]["t"] in ("h2",) or (x["t"] == "h3" and b[i + 1]["t"] == "h3")))]
    return fichas


# ----------------------------------------------------------------------------- nombres ajustados (ver datos/nombres_ajustados.json)
# Prefijos de los nombres oficiales sustituidos (sirven para todas las variantes de drenaje)
PREFIJOS = [
    ("Bosque latifoliado seco / deciduo, submontano", "Bosque latifoliado estacional (semideciduo a deciduo), submontano"),
    ("Bosque latifoliado seco / deciduo, montano / altimontano", "Bosque latifoliado estacional (semideciduo a deciduo), montano / altimontano"),
    ("Sistema agroforestal cafetalero en clima seco, submontano", "Sistema agroforestal cafetalero en clima estacional (entorno semideciduo a deciduo), submontano"),
    ("Sistema agroforestal cafetalero en clima seco, montano / altimontano", "Sistema agroforestal cafetalero en clima estacional (entorno semideciduo a deciduo), montano / altimontano"),
]
BOSQUES_AJ = {1322, 1323, 1324, 1332, 1333, 1334}
CAFES_AJ = {8132, 8133}
SECO = re.compile(r"\b(?:clima )?(sec[oa]s?)(?: (?:o|/) deciduos?)?\b")
COD = re.compile(r"(?<![\d.,])(\d{3,4})(?![\d.,]?\d)")


def ajustar_nombres(x: str) -> str:
    """Aplica los nombres ajustados a los nombres completos y a las menciones en prosa (p. ej. «bosque seco submontano 1324»)."""
    for viejo, nuevo in PREFIJOS:
        x = x.replace(viejo, nuevo).replace(viejo[0].lower() + viejo[1:], nuevo[0].lower() + nuevo[1:])
    salida, pos = [], 0
    for m in SECO.finditer(x):
        # la mención debe ir seguida, en la misma frase y a menos de 70 caracteres, por el código de la clase
        tramo = re.split(r"[.;:]\s|—", x[m.end():m.end() + 70])[0]
        m2 = COD.search(tramo)
        if not m2:
            continue
        lista = re.split(r"\)|;", tramo[m2.start():])[0]  # p. ej. «1314, 1324, 1334»
        cods = {int(c) for c in COD.findall(lista)}
        if re.search(r"[a-záéíóúñ]{4,}", re.sub(r"</?i>|\by\b", "", lista)):  # texto tras el código: solo vale el primero
            cods = {int(m2.group(1))}
        if cods <= BOSQUES_AJ:
            plural = m.group(1).endswith("s")
            rep = "semideciduos a deciduos" if plural else "semideciduo a deciduo"
        elif cods <= CAFES_AJ:
            rep = "clima estacional de entorno semideciduo a deciduo" if m.group(0).startswith("clima") else "de entorno semideciduo a deciduo"
        else:
            continue
        salida.append(x[pos:m.start()] + rep)
        pos = m.end()
    salida.append(x[pos:])
    return "".join(salida)


# Frases que describen a la propia unidad (o su paisaje) como «seca» en las fichas de las clases ajustadas.
# No se tocan los microhábitats (laderas, crestas, galerías secas…), la estación seca ni los nombres de otras clases.
PROSA_UNIDAD = [
    (r"\b([Bb]osques?) latifoliados? secos? (hondureño|de Honduras)", lambda m: f"{m.group(1)} latifoliado{'s' if m.group(1).endswith('s') else ''} deciduo{'s' if m.group(1).endswith('s') else ''} {m.group(2)}"),
    (r"\bbosque latifoliado seco\b", "bosque latifoliado estacional (semideciduo a deciduo)"),
    (r"\b([Bb]osque|dosel|ecosistema) seco (submontano|montano)", r"\1 semideciduo a deciduo \2"),
    (r"\b([Bb]osques) secos (submontanos|montanos)", r"\1 semideciduos a deciduos \2"),
    (r"\bbosque seco(?! mesoamericano)\b", "bosque semideciduo a deciduo"),
    (r"\bbosques secos del país", "bosques deciduos del país"),
    (r"\bserie seca nacional", "serie deciduo-estacional nacional"),
    (r"\b(piso|cinturón) seco submontano", r"\1 submontano estacional"),
    (r"\bencinares (abiertos )?secos( montanos)?", lambda m: f"encinares {m.group(1) or ''}estacionales{m.group(2) or ''}"),
    (r"\bencinares xéricos caducifolios", "encinares caducifolios"),
    (r"\b(ecotonos montanos|parches agroforestales montanos) secos", lambda m: m.group(1) + (" estacionales" if m.group(1).startswith("eco") else " de entorno semideciduo a deciduo")),
    (r"\b(valles submontanos|piedemontes) secos( submontanos)?", lambda m: f"{m.group(1)} estacionales{m.group(2) or ''}"),
    (r"\bserranías (?:estacionalmente )?secas", "serranías estacionales"),
    (r"\b(montaña|vaguada montana) seca\b", r"\1 estacional"),
    (r"\bpisos altos secos", "pisos altos estacionales"),
]


def nota_ajuste(cod: int, antes: str, ahora: str) -> dict:
    par = {13: "el bosque latifoliado estacional / semideciduo submontano (1222–1224)",
           133: "el bosque latifoliado estacional / semideciduo montano (1232–1234)",
           8132: "el cafetal en clima estacional submontano (8122)",
           8133: "el cafetal en clima estacional montano (8123)"}
    par = "e" + (par.get(cod) or par[133 if cod // 10 == 133 else 13])[1:]  # «del …»
    return {"t": "nota", "h": (
        f"<b>Nota de ajuste del nombre.</b> Esta unidad se denominaba «{antes}». En la cartografía R26 no se distingue d{par} "
        "por un clima más seco —ambas comparten elevación y precipitación—, sino por la mayor deciduidad estacional del dosel "
        "(cambio estacional del verdor EVI2). Por coherencia con el mapa se denomina ahora «" + ahora + "». "
        "La descripción procede de la ficha original: las especies y referencias asociadas al bosque seco deben verificarse en campo.")}


def ajustar_descripcion(cod: int, bloques: list[dict]) -> None:
    en_refs = False
    for b in bloques:
        if b["t"] == "h2":
            en_refs = b["x"].startswith("Referencias")
        if en_refs:
            continue
        for k in ("h", "x"):
            if b.get(k):
                for patron, rep in PROSA_UNIDAD:
                    b[k] = re.sub(patron, rep, b[k])
        if b.get("f"):
            for patron, rep in PROSA_UNIDAD:
                b["f"] = [[re.sub(patron, rep, c) for c in fila] for fila in b["f"]]


def ajustar_bloques(bloques: list[dict]) -> None:
    for b in bloques:
        for k in ("h", "x"):
            if b.get(k):
                b[k] = ajustar_nombres(b[k])
        if b.get("f"):
            b["f"] = [[ajustar_nombres(c) for c in fila] for fila in b["f"]]


def main() -> None:
    clases = json.loads((APP / "public" / "data" / "clases.json").read_text(encoding="utf-8"))["clases"]
    validos = {c["codigo"]: c for c in clases}
    (OUT / "mapas").mkdir(parents=True, exist_ok=True)
    estilos: Counter = Counter()
    indice = {}
    sin_codigo = []
    for p in sorted(CATALOGOS.glob("CATALOGO_GRUPO_*.docx")):
        n = 0
        for fi in leer_catalogo(p, estilos):
            cod = fi["codigo"]
            if cod not in validos:
                sin_codigo.append((p.name, fi["nombre"], cod))
                continue
            assert cod not in indice, f"ficha repetida {cod}"
            c = validos[cod]
            ordenar_referencias(fi["bloques"])
            ajustar_bloques(fi["bloques"])
            if int(cod) in BOSQUES_AJ | CAFES_AJ:
                ajustar_descripcion(int(cod), fi["bloques"])
                fi["bloques"].insert(0, nota_ajuste(int(cod), fi["nombre"], c["nombre"]))
            salida = {"codigo": cod, "nombre": c["nombre"], "titulo": ajustar_nombres(fi["nombre"]), "grupo": c["grupo"],
                      "catalogo": p.stem, "mapa": None, "bloques": fi["bloques"]}
            png = MAPAS / f"{cod}.png"
            if png.exists():
                with Image.open(png) as im:
                    im = im.convert("RGB")
                    im.thumbnail((960, 960))
                    im.save(OUT / "mapas" / f"{cod}.webp", "WEBP", quality=78, method=6)
                salida["mapa"] = f"fichas/mapas/{cod}.webp"
            (OUT / f"{cod}.json").write_text(json.dumps(a_2026_obj(salida), ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
            indice[cod] = p.stem
            n += 1
        print(f"{p.name}: {n} fichas", flush=True)
    (OUT / "indice.json").write_text(json.dumps({str(k): v for k, v in sorted(indice.items())}, ensure_ascii=False), encoding="utf-8")
    faltan = sorted(set(validos) - set(indice))
    print("fichas:", len(indice), "· faltan:", faltan)
    print("títulos sin código válido:", sin_codigo)
    print("estilos:", dict(estilos.most_common(15)))
    tam = sum(f.stat().st_size for f in OUT.rglob("*") if f.is_file())
    print(f"tamaño total: {tam / 1e6:.1f} MB")


if __name__ == "__main__":
    sys.exit(main())
