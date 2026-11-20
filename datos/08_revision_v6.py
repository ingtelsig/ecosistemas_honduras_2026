# -*- coding: utf-8 -*-
"""Revisión v6 de las fichas del geovisor (noviembre 2026). Se ejecuta después de 03_fichas.py y 06_revision_fichas.py.

1. Coherencia con el mapa final: las secciones «· Referencia» (2, 3, 5, 6 y 7), la Tabla 2 y las filas del cuadro de
   indicadores se recalculan con el mapa final 2026 (Entrega_final_R26/Control/Indicadores_fichas y
   Revision_informe_v6/ambiental_2026.csv). En la síntesis y en las secciones 1, 8 y 9 se quitan las cifras de superficie,
   número de polígonos y porcentajes de la etapa de catálogo, que no coinciden con el mapa final.
2. Observaciones de Oliver Komar (G01–G04), de Miguel Mendieta para G08 y listado de mamíferos y peces con referencias.
3. Equivalencia con el Mapa de Ecosistemas Vegetales de 2002 (Mejía Ordóñez y House 2002): descripción de las categorías
   equivalentes y coincidencia espacial.

Idempotente: la primera vez guarda una copia de las fichas de entrada en datos/_fichas_pre_v6 y siempre parte de ella.
Si se regeneran las fichas con 03 y 06, la copia se renueva sola (las fichas nuevas no llevan la marca «v6»).
"""
from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

import pandas as pd

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import texto_2002 as T2  # noqa: E402

RAIZ = AQUI.parent.parent
FICHAS = AQUI.parent / "public" / "data" / "fichas"
COPIA = AQUI / "_fichas_pre_v6"
IND = RAIZ / "Entrega_final_R26" / "Control" / "Indicadores_fichas"
AMB = RAIZ / "Revision_informe_v6" / "ambiental_2026.csv"
UNI = AQUI.parent / "public" / "data" / "unidades"

ind = pd.read_csv(IND / "indicadores_por_clase.csv").set_index("codigo")
cru = pd.read_csv(IND / "cruces_territoriales.csv")
con = pd.read_csv(IND / "contactos_30m.csv")
amb = pd.read_csv(AMB).set_index("codigo")
NOMBRE = ind["nombre"].to_dict()

TILDES = {"Alubaren": "Alubarén", "Belen": "Belén", "Cabana": "Cabaña", "Cabanas": "Cabañas", "Cane": "Cané",
    "Concepcion": "Concepción", "Maria": "María", "Copan": "Copán", "Corquin": "Corquín", "Curaren": "Curarén",
    "Danli": "Danlí", "Nispero": "Níspero", "Paraiso": "Paraíso", "Esquias": "Esquías", "Goascoran": "Goascorán",
    "Guinope": "Güinope", "Intibuca": "Intibucá", "Jesus": "Jesús", "Jocon": "Jocón", "Jose": "José",
    "Encarnacion": "Encarnación", "Union": "Unión", "Lamani": "Lamaní", "Lejamani": "Lejamaní", "Limon": "Limón",
    "Meambar": "Meámbar", "Morazan": "Morazán", "Moroceli": "Morocelí", "Oropoli": "Oropolí", "Proteccion": "Protección",
    "Cortes": "Cortés", "Quimistan": "Quimistán", "Roatan": "Roatán", "Salama": "Salamá", "Agustin": "Agustín",
    "Andres": "Andrés", "Jeronimo": "Jerónimo", "Caiquin": "Caiquín", "Colon": "Colón", "Matias": "Matías",
    "Nicolas": "Nicolás", "Sebastian": "Sebastián", "Barbara": "Bárbara", "Lucia": "Lucía", "Aguan": "Aguán",
    "Tomala": "Tomalá", "Angeles": "Ángeles", "Yocon": "Yocón", "Yuscaran": "Yuscarán", "Atima": "Atima"}


def tildes(n):
    return " ".join(TILDES.get(w, w) for w in n.split())

MUNI = {u["id"]: tildes(u["nombre"]) for u in json.loads((UNI / "municipios.json").read_text(encoding="utf-8"))["unidades"]}
DEPTO = {"HN01": "Atlántida", "HN02": "Colón", "HN03": "Comayagua", "HN04": "Copán", "HN05": "Cortés", "HN06": "Choluteca",
         "HN07": "El Paraíso", "HN08": "Francisco Morazán", "HN09": "Gracias a Dios", "HN10": "Intibucá",
         "HN11": "Islas de la Bahía", "HN12": "La Paz", "HN13": "Lempira", "HN14": "Ocotepeque", "HN15": "Olancho",
         "HN16": "Santa Bárbara", "HN17": "Valle", "HN18": "Yoro"}
MARINAS = {616, 617, 618, 634, 635, 6165, 6173, 16201, 16202, 16203, 16204}
ANTROPICAS = {624, 625, 614, 629, 7201, 9001, 10001} | {c for c in NOMBRE if 8000 <= c < 9000}
COSTERAS = {615, 631, 636, 6151, 6202, 6205, 6261, 6262, 6271, 6272, 9101, 9102, 624}
CODIGO_VIEJO = {"3330": "3230", "3320": "3220", "2330": "2230", "2320": "2220", "2310": "2210", "3310": "3210"}


def fmt(x, dec=1):
    s = f"{x:,.{dec}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def ha(x):
    return fmt(x, 1) + " ha"


def pct(x):
    return ("< 0,1" if 0 < x < 0.05 else fmt(x, 1)) + " %"


def nom(c):
    n = NOMBRE.get(int(c), "")
    return n[0].lower() + n[1:] if n else ""


# ------------------------------------------------------------------ limpieza de cifras de la etapa de catálogo
CIFRA = re.compile(r"\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+,\d+|\b\d+ ?%|\b\d+ (?:km|ha|polígonos|objetos|parches|celdas|"
                   r"departamentos|municipios|microcuencas|áreas protegidas|unidades|clases)\b")
SUPERLATIVO = re.compile(r"(mayor|menor) (superficie|extensión|huella|envolvente)|más extens|menos extens|"
                         r"de mayor (peso|gravitación) areal|enorme gravitación areal|la red más amplia")
CORTE = re.compile(r"(?<=[\.\]])\s+(?=[A-ZÁÉÍÓÚÑ¿<(])")


def oraciones(t):
    return [o for o in CORTE.split(t.strip()) if o]


def sin_cifras(t, codigos=False):
    """Conserva solo las oraciones sin cifras de superficie, recuentos ni porcentajes."""
    keep = []
    for o in oraciones(t):
        if CIFRA.search(o) or SUPERLATIVO.search(o):
            continue
        if codigos and re.search(r"<i>\d{3,5}</i>|\b\d{3,5}\b", o):
            continue
        keep.append(o)
    out = " ".join(keep)
    out = re.sub(r"\s*\[\d+(?:, ?\d+)*\]\s*(?=\S)", " ", out)  # citas intermedias sueltas
    return out.strip()


def limpiar_frase(t):
    """Quita cifras de la etapa de catálogo dentro de una frase, conservando su sentido (secciones 8 y 9)."""
    for v, n in CODIGO_VIEJO.items():
        t = t.replace(f"<i>{v}</i>", f"<i>{n}</i>")
    t = re.sub(r"\s*\((?:[^()]*?)\b\d[\d\.]*(?:,\d+)? ?(?:%|ha|km)[^()]*\)", "", t)
    t = re.sub(r"(?:los|las) \d[\d\.]*(?:,\d+)? km de (frontera)", r"la \1", t)
    t = re.sub(r"(?:los|las) \d[\d\.]*(?:,\d+)? km de (ecotono|borde|contacto|perímetro)", r"el \1", t)
    t = re.sub(r" y \d[\d\.]*(?:,\d+)? km con", " y con", t)
    t = re.sub(r"(?:el|del) \d[\d\.]*(?:,\d+)? ?% del ", "la parte del ", t)
    t = re.sub(r"el \d[\d\.]*(?:,\d+)? ?% de (?:la )?superficie", "la superficie", t)
    t = re.sub(r"(?:las|los) \d[\d\.]*(?:,\d+)? ha\b", "las superficies", t)
    t = re.sub(r"(las|los) \d+ (microcuencas|parcelas|áreas)", r"\1 \2", t)
    t = re.sub(r"\s{2,}", " ", t).replace(" ,", ",").replace(" .", ".")
    t = t.replace(" de el ", " del ").replace(" a el ", " al ")
    return t


# ------------------------------------------------------------------ textos 2026
def territorios(c, capa, n=3):
    s = cru[(cru.codigo == c) & (cru.capa == capa)].sort_values("hectareas", ascending=False)
    return s


def nombre_terr(r):
    if r.capa == "Departamento":
        return DEPTO.get(r.territorio, r.nombre)
    if r.capa == "Municipio":
        return MUNI.get(r.territorio, r.nombre)
    if r.capa == "SINAPH":
        nm, tipo = (r.territorio.split(" | ") + [""])[:2]
        nm = nm.replace("(Isla Santanilla o del Cisne)", "(Islas del Cisne)")
        return f"{tipo} {nm}".strip()
    return r.nombre


def lista(s, n=3, total=None):
    def det(r):
        extra = f"{DEPTO.get(r.territorio[:4], '')}; " if r.capa == "Municipio" else ""
        return f"{nombre_terr(r)} ({extra}{ha(r.hectareas)}; {pct(r.porcentaje_clase)})"
    partes = [det(r) for r in s.head(n).itertuples()]
    if not partes:
        return ""
    return partes[0] if len(partes) == 1 else ", ".join(partes[:-1]) + " y " + partes[-1]


def vertiente(c):
    if c not in amb.index or amb.loc[c, "vert_n"] < 10:
        return None
    a = amb.loc[c]
    return a["vert_1"], a["vert_2"], a["vert_0"]


def texto_lead(c):
    i = ind.loc[c]
    s = f"En el mapa final 2026 la unidad ocupa {ha(i.area_ha)} en {fmt(i.parches_4, 0)} parches"
    dep = territorios(c, "Departamento")
    if c in MARINAS:
        return s + ", casi en su totalidad en aguas marinas."
    if len(dep):
        s += "; se concentra en " + lista(dep, 3)
    return s + "."


def texto_sec2(c):
    dep, mun = territorios(c, "Departamento"), territorios(c, "Municipio")
    if c in MARINAS:
        tot = dep.porcentaje_clase.sum()
        t = (f"Es una unidad marina: solo el {pct(tot)} de su superficie coincide con límites departamentales, "
             f"sobre todo en {lista(dep, 3)}." if len(dep) else "Es una unidad marina, fuera de los límites departamentales.")
        return t
    t = (f"En el mapa 2026 la unidad está presente en {len(dep)} departamentos y {len(mun)} municipios. Los departamentos con mayor "
         f"superficie son {lista(dep, 3)}; entre los municipios destacan {lista(mun, 3)}.")
    v = vertiente(c)
    if v:
        car, pac, otra = v
        if car < 0.05 or pac < 0.05:
            lado, otro_lado, v_ = (("del Pacífico", "del Caribe", pac) if car < 0.05 else ("del Caribe", "del Pacífico", car))
            t += f" El {pct(v_)} de sus celdas pertenece a la vertiente {lado} y ninguna a la {otro_lado}"
            t += f" (el {pct(otra)} restante está en la franja insular o costera)." if otra >= 0.5 else "."
        else:
            t += f" El {pct(car)} de sus celdas pertenece a la vertiente del Caribe y el {pct(pac)} a la del Pacífico"
            t += f" (el {pct(otra)} restante está en la franja insular o costera)." if otra >= 0.5 else "."
    return t


def p(c, v, q):
    return amb.loc[c, f"{v}_{q}"]


def texto_sec3(c):
    if c not in amb.index or pd.isna(amb.loc[c].get("elev_p50")):
        if c in amb.index and not pd.isna(amb.loc[c].get("bati_p50")):
            return (f"La batimetría de referencia sitúa la unidad entre {fmt(-p(c,'bati','p95'),0)} y {fmt(-p(c,'bati','p05'),0)} m "
                    f"de profundidad (mediana de {fmt(-p(c,'bati','p50'),0)} m).")
        return ""
    t = (f"Cruzada con las capas de referencia, la unidad se sitúa entre {fmt(p(c,'elev','p05'),0)} y {fmt(p(c,'elev','p95'),0)} m "
         f"de altitud (mediana de {fmt(p(c,'elev','p50'),0)} m; máximo de {fmt(p(c,'elev','max'),0)} m), con pendiente mediana de "
         f"{fmt(p(c,'pend','p50'))} grados (P05–P95: {fmt(p(c,'pend','p05'))}–{fmt(p(c,'pend','p95'))}) y una altura mediana sobre "
         f"el cauce más cercano (HAND) de {fmt(p(c,'hand','p50'))} m. La lluvia anual mediana es de {fmt(p(c,'lluvia','p50'),0)} mm "
         f"(P05–P95: {fmt(p(c,'lluvia','p05'),0)}–{fmt(p(c,'lluvia','p95'),0)} mm), con un coeficiente de variación estacional de "
         f"{fmt(p(c,'cv','p50'),0)} %, y la amplitud anual del verdor (EVI2) tiene una mediana de {fmt(p(c,'evi2','p50'),3)}.")
    if not pd.isna(amb.loc[c].get("alt_int_p50")):
        t += (f" La altura integrada del dosel tiene una mediana de {fmt(p(c,'alt_int','p50'))} m ({fmt(p(c,'alt_eth','p50'))} m según "
              f"ETH y {fmt(p(c,'alt_glad','p50'))} m según GLAD/GEDI); la cobertura arbórea mediana es de {fmt(p(c,'cop_arb','p50'),0)} % "
              f"y la arbustiva de {fmt(p(c,'cop_arbu','p50'),0)} % (Copernicus).")
    return t


FILAS_T2 = {"Elevación": ("elev", 1), "Pendiente": ("pend", 1), "Altura relativa": ("hand", 1), "Precipitación": ("lluvia", 1),
            "Variación estacional": ("cv", 1), "Cambio estacional del verdor": ("evi2", 3), "Altura integrada": ("alt_int", 1),
            "Altura del dosel estimada por satélite (ETH)": ("alt_eth", 1), "Altura del dosel estimada por satélite (GLAD": ("alt_glad", 1),
            "Índice de estructura arbórea": ("arb_int", 1), "Índice de cobertura leñosa": ("len_int", 1),
            "Cobertura de copas arbóreas (GFCC)": ("gfcc", 1), "Cobertura de copas arbóreas (Copernicus)": ("cop_arb", 1),
            "Cobertura arbustiva (Copernicus)": ("cop_arbu", 1), "Frecuencia de cobertura arbórea": ("dw_arb", 1),
            "Frecuencia de cobertura arbustiva": ("dw_arbu", 1)}


def tabla2(c, f):
    if c not in amb.index:
        return f
    nueva = [f[0]]
    for fila in f[1:]:
        k = next((v for pre, v in FILAS_T2.items() if fila[0].startswith(pre)), None)
        if k is None:
            nueva.append(fila)
            continue
        var, dec = k
        vals = [amb.loc[c, f"{var}_{q}"] for q in ("p05", "p50", "p95")]
        if any(pd.isna(v) for v in vals):
            nueva.append(fila[:2] + ["—", "—", "—"])
        else:
            nueva.append(fila[:2] + [fmt(v, dec) for v in vals])
    return nueva


def texto_sec5(c):
    i = ind.loc[c]
    t = (f"En el mapa 2026 la unidad forma {fmt(i.parches_4,0)} parches (conectividad de 4 vecinos) con tamaño medio de "
         f"{ha(i.parche_medio_ha) if i.parche_medio_ha >= 0.05 else fmt(i.parche_medio_ha,2) + ' ha'} y mediano de "
         f"{fmt(i.parche_mediano_ha,2)} ha; el 90 % de los parches mide menos de {fmt(i.parche_p90_ha,2)} ha y el mayor alcanza "
         f"{ha(i.parche_max_ha)}. Los parches menores de 1 ha son {fmt(i.parches_menores_1ha,0)} "
         f"({pct(100*i.parches_menores_1ha/i.parches_4)} del número) y suman {ha(i.area_menores_1ha)} "
         f"({pct(100*i.area_menores_1ha/i.area_ha)} del área). El núcleo interior —celdas que no tocan otra clase, es decir, a "
         f"más de 30 m del borde— suma {ha(i.nucleo_ha)} ({pct(i.nucleo_pct)}). El perímetro ecológico es de "
         f"{fmt(i.perimetro_km)} km, con una densidad de borde de {fmt(i.densidad_borde_m_ha)} m/ha.")
    return t


def contactos(c):
    s = con[(con.codigo_a == c) | (con.codigo_b == c)].copy()
    s["otro"] = s.codigo_b.where(s.codigo_a == c, s.codigo_a)
    return s.sort_values("km", ascending=False)


DIF = [("elev", "una altitud mediana de {a} m frente a {b} m", 100, 0), ("lluvia", "una lluvia anual mediana de {a} mm frente a {b} mm", 150, 0),
       ("evi2", "una amplitud del verdor (EVI2) de {a} frente a {b}", 0.03, 3), ("hand", "una altura sobre el cauce (HAND) de {a} m frente a {b} m", 15, 1),
       ("alt_int", "un dosel integrado de {a} m frente a {b} m", 3, 1)]


def y_lista(xs):
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " y " + xs[-1]


def texto_sec6(c):
    i = ind.loc[c]
    s = contactos(c)
    if s.empty:
        return ""
    per = i.perimetro_km
    top = [f"<i>{int(r.otro)}</i> {nom(r.otro)} ({fmt(r.km)} km; {pct(100*r.km/per)} del perímetro)" for r in s.head(4).itertuples()]
    t = (f"Su perímetro ecológico de {fmt(per)} km limita con {int(i.n_vecinos)} clases. Los contactos más largos son con "
         + ", ".join(top[:-1]) + " y " + top[-1] + ".")
    nat = [int(o) for o in s.otro if int(o) not in ANTROPICAS and int(o) not in MARINAS or c in MARINAS]
    nat = [o for o in nat if o != c and o in amb.index]
    if nat and c in amb.index and not pd.isna(amb.loc[c].get("elev_p50")):
        v = nat[0]
        dif = []
        for var, frase, umbral, dec in DIF:
            a, b = amb.loc[c, f"{var}_p50"], amb.loc[v, f"{var}_p50"]
            if not (pd.isna(a) or pd.isna(b)) and abs(a - b) >= umbral:
                dif.append(frase.format(a=fmt(a, dec), b=fmt(b, dec)))
        na, nb = NOMBRE[c].split(", "), NOMBRE[v].split(", ")
        ley = [f"«{x}» frente a «{y}»" for x, y in zip(na, nb) if x != y] if len(na) == len(nb) else []
        t += f" Frente a su principal vecino natural, <i>{v}</i>, "
        if ley:
            t += "la leyenda la separa por " + " y ".join(ley)
            t += ("; en el terreno se distingue por " + ", ".join(dif[:3]) + ".") if dif else (
                "; las medianas ambientales de ambas unidades son parecidas, por lo que el límite depende sobre todo de ese criterio.")
        elif dif:
            t += "se distingue por " + y_lista(dif[:3]) + "."
        else:
            t += "presenta medianas ambientales parecidas."
    return t


def texto_sec7(c):
    i = ind.loc[c]
    s = territorios(c, "SINAPH")
    t = (f"El SINAPH cubre {ha(i.sinaph_ha)} ({pct(i.sinaph_pct)}) de la unidad en el mapa 2026"
         + (f", repartidas en {len(s)} áreas protegidas; las de mayor presencia son {lista(s, 3)}." if len(s) else "."))
    if i.microcuencas_APR_ha > 0:
        t += (f" Las microcuencas abastecedoras de agua declaradas (APR) abarcan {ha(i.microcuencas_APR_ha)} "
              f"({pct(100*i.microcuencas_APR_ha/i.area_ha)}) en {fmt(i.numero_microcuencas_APR,0)} microcuencas.")
    return t


def fila_entorno(c):
    if c not in amb.index or pd.isna(amb.loc[c].get("elev_p50")):
        if c in amb.index and not pd.isna(amb.loc[c].get("bati_p50")):
            return f"Profundidad mediana de {fmt(-p(c,'bati','p50'),0)} m según la batimetría de referencia (mapa 2026)."
        return None
    t = (f"Altitud mediana de {fmt(p(c,'elev','p50'),0)} m (P05–P95: {fmt(p(c,'elev','p05'),0)}–{fmt(p(c,'elev','p95'),0)} m), "
         f"lluvia anual mediana de {fmt(p(c,'lluvia','p50'),0)} mm y pendiente mediana de {fmt(p(c,'pend','p50'))} grados (mapa 2026).")
    return t


def fila_vertiente(c):
    v = vertiente(c)
    if not v:
        return None
    car, pac, otra = v
    return f"Caribe / Atlántico: {pct(car)} · Pacífico: {pct(pac)}" + (f" · Franja insular o costera: {pct(otra)}" if otra >= 0.05 else "")


def fila_2002(c):
    eq, nota = T2.EQUIV.get(c, ([], None))
    if not eq:
        return "Sin equivalente directo en el mapa de 2002. " + T2.NOTA_SIN.get(nota, "")
    return "; ".join(f"{T2.DESC[k][1]} — {T2.DESC[k][0]}" for k in eq).replace("<i>", "").replace("</i>", "") + \
        ". Ver la sección «Equivalencia con el mapa de 2002»."


# ------------------------------------------------------------------ observaciones (Komar, Mendieta G08, fauna)
REGLAS_V6 = [
    (r"componente marino Mapa de Ecosistemas", "componente marino del Mapa de Ecosistemas"),
    (r"Abogado Agustín Córdoba Rodríguez \(Isla Santanilla o del Cisne\)", "Abogado Agustín Córdoba Rodríguez (Islas del Cisne)"),
    (r"(?:en |de |e |y )?Isla Santanilla", lambda m: (m.group(0).replace("Isla Santanilla", "Islas del Cisne")
                                                       .replace("e Islas", "e Islas").replace("y Islas", "e Islas"))),
    (r"Tela y Santanilla", "Tela e Islas del Cisne"),
    (r"(En concordancia con|Bajo|Conforme a|En estricto apego a|Respetando)[^,.]*reserva (científica|taxonómica)[^,.]*,",
     "Como no hay muestreos biológicos nacionales en este ámbito,"),
    (r"Manteniendo estricta reserva frente a cualquier inventario taxonómico local no medido en aguas hondureñas,",
     "Como no hay muestreos biológicos nacionales en este ámbito,"),
    (r"en cumplimiento estricto de la reserva científica [^,]*,", "como no hay muestreos biológicos nacionales en este ámbito,"),
    (r"manteniendo reserva taxonómica puntual desde la imagen", "sin identificar especies desde la imagen"),
    (r" y reserva científica explícita respecto a la verificación acústica o biológica de cada polígono\.",
     "; ningún polígono se ha verificado con sensores acústicos ni con muestreos biológicos."),
    (r", catalogado con estatus potencial en consolidación\.", "; se presenta como ecosistema potencial, pendiente de verificación en campo."),
    (r"Más allá de esta huella caribeña heredada, ", "Además del Caribe, "),
    (r"En el acervo el inventario nacional de verificación solo se registran 2 puntos coincidentes de Hábitats Marinos Surveys sobre "
     r"la huella caribeña \(respaldo de inventarios secundarios de referencia secundaria puntual\), complementados en el Pacífico por el "
     r"antecedente institucional de exploración submarina de la UNAH en Isla Almejas \(2025\), cuyos resultados taxonómicos detallados "
     r"aguardan publicación formal y cartografía poligonal\.",
     "En el inventario nacional de verificación solo hay 2 puntos de Hábitats Marinos Surveys que coinciden con la unidad en el Caribe. "
     "En el Pacífico se cuenta con la exploración submarina de la UNAH en Isla Almejas (2025), cuyos resultados de biodiversidad aún "
     "no se han publicado ni cartografiado."),
    (r"\b(el|en el) (acervo|expediente) el inventario", r"\1 inventario"),
    (r"Este acervo empírico", "Este conjunto de registros"),
    (r"un rico acervo de", "un conjunto amplio de registros de"),
    (r"acervo fotográfico", "archivo fotográfico"),
    (r"Complementan este acervo", "Complementan estos registros"),
    (r"del acervo secundario(?: consolidado)?", "del conjunto de referencias secundarias"),
    (r"acervo secundario", "conjunto de referencias secundarias"),
    (r"de referencia secundaria puntual", "puntuales"),
    (r"inventarios taxonómicos", "inventarios de biodiversidad"),
    (r"inventario taxonómico", "inventario de biodiversidad"),
    (r"Censos estacionales de aves playeras migratorias y densidad infaunal de poliquetos y <i>Anadara tuberculosa</i> en planicies "
     r"no intervenidas frente a bordes de camaroneras\.",
     "Analizar los registros existentes de aves playeras migratorias (por ejemplo, en eBird) y medir la densidad infaunal de poliquetos "
     "y <i>Anadara tuberculosa</i> en planicies fangosas con distinto grado de intervención."),
]

POR_FICHA = {
    6262: [
        ("Ave colonial nidificante que fertiliza el dosel de manglar en el Golfo de Fonseca",
         "Ave colonial común en el manglar; controla las poblaciones de invertebrados del lodo entre las raíces"),
        ("Platalea ajaja (Espátula rosada)", "Vireo pallens (Vireo de manglar)"),
        ("Ave vadeadora colonial asociada a esteros y manglares del sur",
         "Insectívoro que en el sur solo vive en el manglar, sobre todo en el manglar alto; controla insectos herbívoros"),
        ("y la espátula rosada (<i>Platalea ajaja</i>)", "y, en el dosel, el vireo de manglar (<i>Vireo pallens</i>)"),
    ],
    6272: [
        ("a aves vadeadoras y playeras como <i>Himantopus mexicanus</i> y el correlimos menudillo (<i>Calidris minutilla</i>)",
         "a aves propias del manglar como el rascón manglero del golfo de Fonseca (<i>Rallus longirostris berryorum</i>) y la "
         "reinita amarilla de manglar (<i>Setophaga petechia</i>)"),
        ("Calidris minutilla (Correlimos menudillo)", "Rallus longirostris berryorum (Rascón manglero del golfo de Fonseca)"),
        ("Ave playera migratoria de planos hipersalinos abiertos", "Rascón residente del manglar bajo del golfo de Fonseca"),
        ("Himantopus mexicanus (Cigüeñuela)", "Setophaga petechia (Reinita amarilla de manglar)"),
        ("Ave vadeadora en láminas someras entre mangle achaparrado y albinas", "Insectívoro residente del manglar"),
    ],
    1223: [
        ("robles submontanos de gran bellota como Quercus insignis junto a",
         "robles submontanos como Quercus peduncularis y Q. sapotifolia junto a"),
        ("como <i>Quercus insignis</i> y <i>Clethra mexicana</i>", "como <i>Quercus peduncularis</i>, <i>Q. sapotifolia</i> y <i>Clethra mexicana</i>"),
        ("con <i>Quercus insignis</i>, <i>Liquidambar</i>", "con <i>Quercus peduncularis</i>, <i>Q. sapotifolia</i>, <i>Liquidambar</i>"),
        ("regeneración de <i>Quercus insignis</i>", "regeneración de los robles (<i>Quercus</i> spp.)"),
        ("Quercus insignis (Roble)", "Quercus peduncularis (Roble)"),
        ("Roble de gran bellota en bosques estacionales húmedos de montaña media",
         "Roble de laderas submontanas bien drenadas, con Q. sapotifolia y Q. oleoides (revisión técnica 2026)"),
    ],
    615: [
        ("Censos aéreos y acústicos con sonar de barrido lateral para estimar tendencias poblacionales de <i>Trichechus manatus</i> y "
         "rutas críticas por bocanas.",
         "Revisar la cartografía de las lagunas costeras de Atlántida (Zambuco, Cuero y Salado y Laguna de Cacao en Jutiapa), que "
         "el mapa 2026 no separa como lagunas costeras, e incorporarlas en la próxima actualización."),
    ],
}

NOTA_1223 = ("<b>Nota de la revisión técnica.</b> La versión previa citaba <i>Quercus insignis</i>, que en Honduras crece por encima de "
             "los 1.300 msnm (1.350–2.500 msnm). Se sustituyó por los robles más frecuentes en este piso submontano: "
             "<i>Q. peduncularis</i>, <i>Q. sapotifolia</i> y <i>Q. oleoides</i>; también se citan <i>Q. elliptica</i> y "
             "<i>Q. segoviensis</i> (El Paraíso).")

MANGLES = ("Avicennia germinans", "Rhizophora mangle", "Laguncularia racemosa", "Conocarpus erectus")

G08 = {
    2110: ["En la cuenca del río Santiago (San Francisco, Atlántida) hay un rodal de <i>Pinus caribaea</i> var. <i>hondurensis</i> de "
           "más de 10 ha entre 100 y 300 msnm.",
           "<i>Miconia albicans</i> es un arbusto frecuente del sotobosque de los pinares de tierras bajas sobre suelos ácidos y pobres."],
    2120: ["En esta unidad los robles (<i>Quercus</i> spp.) crecen asociados a los pinos."],
    2130: ["La recomendación de proteger y estudiar <i>Pinus hartwegii</i> debe extenderse a los demás pinos de altura: "
           "<i>P. maximinoi</i>, <i>P. pseudostrobus</i>, <i>P. ayacahuite</i> y <i>P. tecunumanii</i>."],
    2210: ["<i>Pinus caribaea</i> crece junto con <i>P. oocarpa</i> en la cuenca del río Santiago y en Morazán (Yoro), a sotavento de la "
           "cordillera Nombre de Dios, en rodales de 10 a 100 ha entre 100 y 400 msnm; también se ha observado en las comunidades "
           "tolupanes de Texiguat y Jimia."],
    2220: ["Especies pirófitas del pinar estacional: <i>Curatella americana</i>, <i>Quercus oleoides</i>, <i>Q. sapotifolia</i>, "
           "<i>Vachellia pennatula</i> (<i>Acacia pennatula</i>), <i>Davilla kunthii</i>, <i>Roupala montana</i> (peralejo) y "
           "<i>Libidibia coriaria</i>.",
           "Además del gorgojo descortezador (<i>Dendroctonus frontalis</i>), atacan al pino descortezadores secundarios del género "
           "<i>Ips</i>.",
           "Localidad de referencia: corredor Yuscarán–Monserrat–Apaguiz–Apapuerta (El Paraíso)."],
}
G08_GENERAL = ("Robles de los pinares: en zonas secas, <i>Q. oleoides</i> (de 0 a 800 msnm) y <i>Q. segoviensis</i>; por encima de "
               "600–800 msnm, <i>Q. peduncularis</i>; <i>Q. sapotifolia</i> en zonas secas, montanas y nubladas.")
FUENTE_G08 = ("Observaciones del revisor técnico Miguel Mendieta (noviembre 2026) al catálogo de bosques de coníferas (G08).")

# --- mamíferos y peces (listado con referencias aportado en la revisión técnica)
REF_FAUNA = {
    "castaneda2011": "Castañeda, F., Herrera, L., Pereira, S. y Sierra, D. (2011). <i>Estado del jaguar (Panthera onca) en el Parque Nacional Jeannette Kawas, Honduras</i>. PANTHERA, PROLANSATE e ICF, Tegucigalpa. 15 p.",
    "portillo2010cs": "Portillo, H. y Carrasco, J. C. (2010). <i>Segundo informe de monitoreo de peces en Cuero y Salado</i>. Refugio de Vida Silvestre Cuero y Salado, Honduras.",
    "portillo2011cs": "Portillo, H. y Carrasco, J. C. (2011). <i>Monitoreo biológico usando trampas cámara en el sendero de las Bujajas, Refugio de Vida Silvestre Cuero y Salado: evaluando el efecto de la visitación turística</i>. Informe final. La Ceiba, Honduras.",
    "turcios2020x": "Turcios-Casco, M. A., Ávila-Palma, H. D., Martínez, M., Trejo-Ordoñez, E. J., Meza-Flores, D. E., Castañeda, F., King, T., Thornton, D. y Superina, M. (2020). Los xenartros de Honduras: nuevos registros, principales amenazas y comentarios sobre su estado de conservación. <i>Edentata</i>, 21, 13–18.",
    "turcios2026": "Turcios-Casco, M. A., Castañeda, F., Wilson, D. E., Miller, B., Gonzalez-Socoloske, D., Ramos, E. A., King, T. W., LaVal, R. K., Ordóñez-Garza, N., Ordoñez, D., Graciolli, G., Thornton, D., Martínez, M., Estrada-Andino, N. M. y Ávila-Palma, H. D. (2026). Taxonomy, natural history, and conservation of the mammals of Honduras. <i>ZooKeys</i>, 1288, 1–193.",
    "gonthier2013": "Gonthier, D. J. y Castañeda, F. E. (2013). Large- and medium-sized mammal survey using camera traps in the Sikre River in the Río Plátano Biosphere Reserve, Honduras. <i>Tropical Conservation Science</i>, 6(4), 584–591.",
    "marineros2015": "Marineros, L. y Portillo Reyes, H. O. (2015). Actualización de la distribución y notas sobre el perezoso de tres garras <i>Bradypus variegatus castaneiceps</i> (Pilosa: Bradypodidae) en Honduras. <i>Revista Mexicana de Mastozoología (Nueva Época)</i>, 5(1), 1–16.",
    "portillo2011j": "Portillo-Reyes, H. y Hernández, J. (2011). Densidad del jaguar (<i>Panthera onca</i>) en Honduras: primer estudio con trampas-cámara en La Mosquitia hondureña. <i>Revista Latinoamericana de Conservación</i>, 2(1), 45–50.",
    "portillo2015e": "Portillo Reyes, H. O., Hernández, J., Manzanares, T., Elvir, F. y Vega, H. (2015). Registros y distribución potencial del murciélago blanco hondureño (<i>Ectophylla alba</i>) en la región de La Moskitia, Honduras. <i>Revista Mexicana de Mastozoología (Nueva Época)</i>, 5(1), 25–32.",
    "turcios2020e": "Turcios-Casco, M. A., Martínez, M., Ávila-Palma, H. D., Rodríguez, J. A., Soler-Orellana, A. y Portillo Reyes, H. O. (2020). Reproductive, morphometric, and roosting description of the Honduran white bat <i>Ectophylla alba</i> (Chiroptera: Phyllostomidae), in Honduras. <i>Mastozoología Neotropical</i>, 27(2), 346–352.",
    "portillo2013a": "Portillo-Reyes, H. O. y Elvir, F. (2013). Composición, estructura y diversidad de mamíferos terrestres grandes y medianos en 16 áreas protegidas en Honduras, usando fotocapturas como evidencia de registro. <i>Revista Mesoamericana de Investigación</i>, 1(1), 15–29.",
    "portillo2013f": "Portillo-Reyes, H. O. y Elvir, F. (2013). Distribución de felinos en áreas naturales protegidas de Honduras. <i>Revista Mexicana de Mastozoología (Nueva Época)</i>, 3(1), 6–15.",
    "portillo2024": "Portillo-Reyes, H. O., Elvir Valle, F. A. y Vega Rodríguez, H. L. (2024). Impacto de los incendios en los ecosistemas de pino y en los mamíferos terrestres medianos y grandes en Honduras. <i>Revista Mexicana de Mastozoología (Nueva Época)</i>, 14(2), 78–90.",
    "turcios2023": "Turcios-Casco, M. A., Hernández, G. S., Mancía, F. E., Molinero, C. F., Muñoz, J., López, C. M. y Ordóñez-Garza, N. (2023). Unseen for 43 years! A new occurrence of <i>Glaucomys volans</i> (Linnaeus, 1758) (Rodentia, Sciuridae) in Honduras. <i>Check List</i>, 19(1), 133–139.",
    "portillo2010v": "Portillo, H., Hernández, J., Elvir, F. y otros (2010). Estimación de la tasa de defecación del venado cola blanca (<i>Odocoileus virginianus</i>) en cautividad en Honduras. <i>Mesoamericana</i>, 14(1), 55–57.",
    "portillo2006": "Portillo, H. (2006). <i>Establecimiento de una línea base para la evaluación de los mamíferos terrestres del Parque Nacional La Tigra usando trampas cámara</i>. Informe final. Tegucigalpa. 31 p.",
    "portillo2026c": "Portillo Reyes, H. O., Elvir Valle, F. A. y Manzanares, T. (2026). Nuevos registros del coyote (<i>Canis latrans</i>) en la sabana de pino de la Moskitia hondureña. <i>Revista Mexicana de Mastozoología (Nueva Época)</i>, 16(1), 39–45. https://doi.org/10.22201/ie.31224814e.2026.16.1.461",
    "portillo2019": "Portillo-Reyes, H. O., Aguirre, Y. y Hernández, J. (2019). Registro de una población del murciélago frutero hondureño (<i>Artibeus inopinatus</i>) (Davis y Carter, 1964), en Nacaome, Valle, Honduras. <i>Scientia Hondurensis</i>, 2(1), 71–75.",
    "portillo2018": "Portillo Reyes, H. O. y Elvir, F. (2018). Mamíferos en dos bosques riparios de la sabana de pino en la Moskitia hondureña. <i>Revista Mexicana de Mastozoología (Nueva Época)</i>, 8(2), 22–30.",
    "portillo2023": "Portillo-Reyes, H. O., Elvir, F., Mejía, D. y Berrocal, M. (2023). Los mamíferos grandes y medianos en la Bahía de Chismuyo, Honduras. Una alerta para su conservación: ¿qué nos indican los modelos de ocupación y detección? <i>Revista Mexicana de Mastozoología (Nueva Época)</i>, 13(2).",
    "matamoros2009": "Matamoros, W. A., Schaefer, J. F. y Kreiser, B. R. (2009). Annotated checklist of the freshwater fishes of continental and insular Honduras. <i>Zootaxa</i>, 2307(1), 1–38.",
    "komar2026": "Komar, O. (2026). Observaciones al catálogo ecológico del Mapa de Ecosistemas de Honduras 2026, grupos G01 a G04. Revisión técnica, Universidad Zamorano, 4 de noviembre de 2026.",
    "mendieta2026": "Mendieta, M. (2026). Observaciones al catálogo ecológico del Mapa de Ecosistemas de Honduras 2026, grupo G08 (bosques de coníferas). Revisión técnica, 19 de noviembre de 2026.",
}

_LAT_HUMEDO = ("Mamíferos registrados en los bosques latifoliados del país: jaguar (<i>Panthera onca</i>), puma (<i>Puma concolor</i>), "
               "ocelote (<i>Leopardus pardalis</i>), tigrillo o caucel (<i>Leopardus wiedii</i>), yaguarundí (<i>Herpailurus "
               "yagouaroundi</i>), danto (<i>Tapirus bairdii</i>), oso hormiguero gigante (<i>Myrmecophaga tridactyla</i>), tamandúa u "
               "oso colmenero (<i>Tamandua mexicana</i>), venado cola blanca (<i>Odocoileus virginianus</i>), quequeo (<i>Dicotyles "
               "tajacu</i>), jagüilla (<i>Tayassu pecari</i>) y perezosos (<i>Choloepus hoffmanni</i>, <i>Bradypus variegatus</i>) y "
               "serafín (<i>Cyclopes dorsalis</i>).")
_EALBA = "En los bosques húmedos de La Moskitia vive el murciélago blanco hondureño (<i>Ectophylla alba</i>), que se refugia bajo hojas de <i>Heliconia</i>."
_LAT_SECO = ("Mamíferos del grupo de bosques latifoliados presentes también en los bosques secos: puma (<i>Puma concolor</i>), ocelote "
             "(<i>Leopardus pardalis</i>), yaguarundí (<i>Herpailurus yagouaroundi</i>), tamandúa (<i>Tamandua mexicana</i>), venado "
             "cola blanca (<i>Odocoileus virginianus</i>) y quequeo (<i>Dicotyles tajacu</i>).")
_R_LAT = ["gonthier2013", "marineros2015", "turcios2020x", "turcios2026", "portillo2011j", "portillo2013a", "portillo2013f"]
_PINO = ("Mamíferos de los bosques de pino: puma (<i>Puma concolor</i>), ocelote (<i>Leopardus pardalis</i>), yaguarundí "
         "(<i>Herpailurus yagouaroundi</i>), tamandúa (<i>Tamandua mexicana</i>), venado cola blanca (<i>Odocoileus virginianus</i>), "
         "coyote (<i>Canis latrans</i>) y ardilla voladora (<i>Glaucomys volans</i>), redescubierta en el país en 2023 tras 43 años "
         "sin registros. Los incendios reducen la presencia de mamíferos medianos y grandes en los pinares.")
_MIXTO = ("Mamíferos de los bosques mixtos: puma (<i>Puma concolor</i>), ocelote (<i>Leopardus pardalis</i>), yaguarundí "
          "(<i>Herpailurus yagouaroundi</i>), coyote (<i>Canis latrans</i>), tamandúa (<i>Tamandua mexicana</i>), venado cola blanca "
          "(<i>Odocoileus virginianus</i>), ardilla voladora (<i>Glaucomys volans</i>), pizote (<i>Nasua narica</i>) y mapache "
          "(<i>Procyon lotor</i>).")
_PASTO = ("Mamíferos de pastizales y herbazales: murciélagos frugívoros del género <i>Carollia</i> (y, en el sur, una población del "
          "murciélago frutero hondureño <i>Artibeus inopinatus</i> en Nacaome, Valle), puma (<i>Puma concolor</i>), coyote "
          "(<i>Canis latrans</i>), venado cola blanca (<i>Odocoileus virginianus</i>) y yaguarundí (<i>Herpailurus yagouaroundi</i>).")
_HUMEDAL = ("Mamíferos de los humedales continentales: jaguar (<i>Panthera onca</i>), venado cola blanca (<i>Odocoileus virginianus</i>), "
            "yaguarundí (<i>Herpailurus yagouaroundi</i>), pizote (<i>Nasua narica</i>), mapache (<i>Procyon lotor</i>) y, en el sur, "
            "coyote (<i>Canis latrans</i>).")
_MANGLAR = ("Mamíferos de los manglares: yaguarundí o gato negro (<i>Herpailurus yagouaroundi</i>), coyote (<i>Canis latrans</i>), "
            "tamandúa u oso colmenero (<i>Tamandua mexicana</i>), mapache (<i>Procyon lotor</i>), guazalos (<i>Didelphis virginiana</i>, "
            "<i>D. marsupialis</i>), zorrillos (<i>Spilogale angustifrons</i>, <i>Mephitis macroura</i>), conejo (<i>Sylvilagus "
            "floridanus</i>) y venado cola blanca (<i>Odocoileus virginianus</i>), registrados en la bahía de Chismuyo.")
_PECES = ("Peces de los ríos: tepemechín (<i>Agonostomus monticola</i>), cuyamel (<i>Joturus pichardi</i>) y el pez endémico "
          "<i>Tlaloc portillorum</i>.")

FAUNA = {}
for c in NOMBRE:
    if 1100 <= c < 1300:
        FAUNA[c] = [(_LAT_HUMEDO, _R_LAT)] + ([(_EALBA, ["portillo2015e", "turcios2020e"])] if 1110 <= c < 1130 else [])
    elif 1300 <= c < 1400:
        FAUNA[c] = [(_LAT_SECO, ["turcios2026", "portillo2013a", "portillo2013f"])]
    elif 2100 <= c < 2300:
        FAUNA[c] = [(_PINO, ["portillo2024", "turcios2026", "turcios2023"])]
    elif 3100 <= c < 3300:
        FAUNA[c] = [(_MIXTO, ["portillo2024", "turcios2026", "turcios2023", "portillo2010v", "portillo2006"])]
    elif 8200 <= c < 8300:
        FAUNA[c] = [(_PASTO, ["portillo2026c", "portillo2019", "portillo2018"])]
    elif c in (610, 630):
        FAUNA[c] = [(_HUMEDAL, ["castaneda2011", "portillo2010cs", "portillo2011cs", "turcios2020x", "turcios2026"])]
    elif c in (6261, 6262, 6271, 6272):
        FAUNA[c] = [(_MANGLAR, ["portillo2023"])]
    elif 6060 <= c < 6070:
        FAUNA[c] = [(_PECES, ["matamoros2009"])]
FAUNA.setdefault(601, []).append(("En la sabana de pino de La Moskitia hay registros recientes de coyote (<i>Canis latrans</i>).",
                                  ["portillo2026c", "portillo2018"]))
FUENTE_FAUNA = "Listado de mamíferos y peces con referencias aportado durante la revisión técnica (noviembre 2026)."


# ------------------------------------------------------------------ utilidades de bloques
def corregir(t):
    for a, b in REGLAS_V6:
        t = re.sub(a, b, t)
    return t


def ref_numero(bs, texto_ref):
    """Devuelve el número de una referencia; la añade al final de la lista principal si no existe."""
    clave = re.sub(r"<[^>]+>", "", texto_ref)[:60]
    nums = []
    for b in bs:
        if b["t"] == "p":
            m = re.match(r"<b>\[(\d+)\]</b>\s*(.*)", b.get("h", ""))
            if m:
                nums.append(int(m.group(1)))
                if re.sub(r"<[^>]+>", "", m.group(2))[:60] == clave:
                    return int(m.group(1))
    n = max(nums, default=0) + 1
    k_ref = next((i for i, b in enumerate(bs) if b["t"] == "h2" and b.get("x", "").startswith("Referencias")), None)
    if k_ref is None:
        bs.append({"t": "h2", "x": "Referencias bibliográficas y cartográficas", "v6": True})
        k_ref = len(bs) - 1
    k = k_ref + 1
    while k < len(bs) and bs[k]["t"] == "p" and bs[k].get("h", "").startswith("<b>["):
        k += 1
    bs.insert(k, {"t": "p", "h": f"<b>[{n}]</b> {texto_ref}", "v6": True})
    return n


def ref_mejia(bs):
    for b in bs:
        if b["t"] == "p" and "Mejía Ordóñez" in b.get("h", "") and b["h"].startswith("<b>["):
            return int(re.match(r"<b>\[(\d+)\]", b["h"]).group(1))
    return ref_numero(bs, T2.REF)


def indice_h3(bs, prefijo):
    return next((i for i, b in enumerate(bs) if b["t"] == "h3" and b.get("x", "").startswith(prefijo)), None)


def parrafos_de(bs, i):
    """Índices de los párrafos que siguen a la h3 i hasta el siguiente encabezado."""
    out = []
    k = i + 1
    while k < len(bs) and bs[k]["t"] not in ("h2", "h3"):
        if bs[k]["t"] == "p":
            out.append(k)
        k += 1
    return out


def reescribir(bs, prefijo, nuevo, conservar=True, codigos=True):
    i = indice_h3(bs, prefijo)
    if i is None or not nuevo:
        return
    ps = parrafos_de(bs, i)
    if not ps:
        bs.insert(i + 1, {"t": "p", "h": nuevo + " [1]", "v6": True})
        return
    resto = " ".join(sin_cifras(bs[k]["h"], codigos=codigos) for k in ps) if conservar else ""
    resto = re.sub(r"\s*\[\d+(?:, ?\d+)*\]\s*$", "", resto).strip()
    bs[ps[0]]["h"] = (nuevo + (" " + resto if resto else "") + " [1]").strip()
    bs[ps[0]]["v6"] = True
    for k in reversed(ps[1:]):
        del bs[k]


def historica(d):
    """True si la monografía conserva la superficie de la etapa de catálogo (difiere más de 0,5 % del mapa final)."""
    c, bs = d["codigo"], d["bloques"]
    if c not in ind.index:
        return False
    k = indice_h3(bs, "1.")
    txt = " ".join(bs[j]["h"] for j in parrafos_de(bs, k)) if k is not None else ""
    m = re.search(r"(\d{1,3}(?:\.\d{3})*,\d+) ha", txt)
    if not m:
        return False
    v = float(m.group(1).replace(".", "").replace(",", "."))
    return abs(v - ind.loc[c, "area_ha"]) / ind.loc[c, "area_ha"] > 0.005


def revisar(d):
    c = d["codigo"]
    bs = d["bloques"]
    i = ind.loc[c] if c in ind.index else None
    # --- correcciones de texto
    for b in bs:
        for k in ("h", "x"):
            if k in b:
                b[k] = corregir(b[k])
        if "f" in b:
            b["f"] = [[corregir(x) for x in fila] for fila in b["f"]]
    for a, n in POR_FICHA.get(c, []):
        for b in bs:
            for k in ("h", "x"):
                if k in b:
                    b[k] = b[k].replace(a, n)
            if "f" in b:
                b["f"] = [[x.replace(a, n) for x in fila] for fila in b["f"]]
    if c == 1223:
        for b in bs:
            if b["t"] == "nota" and "Quercus insignis" in b.get("h", ""):
                b["h"] = NOTA_1223
    # registros de mangle del IFN en clases de tierra adentro
    if c not in COSTERAS:
        for b in bs:
            if b["t"] == "tabla" and b["f"] and b["f"][0][0].startswith("Estrato"):
                b["f"] = [b["f"][0]] + [r for r in b["f"][1:] if not (r[1].split(" (")[0] in MANGLES and "IFN" in r[-1])]
            if b["t"] == "p":
                b["h"] = re.sub(r", <i>(Avicennia germinans|Rhizophora mangle|Laguncularia racemosa)</i>\.",
                                r" y un registro de <i>\1</i>, mangle que fuera de la costa se considera un error de identificación "
                                r"o de enlace en la base del IFN.", b["h"])
    # fila de equivalencia 2002 (todas las fichas)
    for b in bs:
        if b["t"] == "tabla" and b["f"] and b["f"][0][0] == "Indicador clave":
            for fila in b["f"]:
                if fila[0].startswith("Referencia histórica UNESCO"):
                    fila[0], fila[1] = "Equivalencia con el mapa de 2002", fila_2002(c)
    if i is None:
        return d
    if historica(d):
        # --- nota de la cabecera y cuadro de indicadores
        for b in bs:
            if b["t"] == "nota" and b.get("h", "").startswith("La monografía conserva"):
                b["h"] = ("La monografía resume las descripciones, observaciones, fotos y fuentes de la ficha de origen. Las cifras de "
                          "superficie, distribución, entorno ambiental, paisaje, contactos y protección (secciones marcadas «· Referencia», "
                          "Tabla 2 y cuadro de indicadores) se recalcularon con el mapa final 2026. Los recuentos de parcelas del IFN y de "
                          "puntos de verificación citados en las secciones 4 y 8 provienen del enlace espacial hecho durante la elaboración "
                          "del catálogo.")
            if b["t"] == "tabla" and b["f"] and b["f"][0][0] == "Indicador clave":
                for fila in b["f"]:
                    if fila[0].startswith("Referencia histórica UNESCO"):
                        fila[0], fila[1] = "Equivalencia con el mapa de 2002", fila_2002(c)
                    elif fila[0].startswith("Reparto hidrográfico") and fila_vertiente(c):
                        fila[1] = fila_vertiente(c)
                    elif fila[0].startswith("Entorno ambiental") and fila_entorno(c):
                        fila[1] = fila_entorno(c)
            if b["t"] == "tabla" and b["f"] and b["f"][0][0].startswith("Variable ambiental"):
                b["f"] = tabla2(c, b["f"])
            if b["t"] == "nota" and b.get("h", "").startswith("Tabla 4."):
                b["h"] = (f"Tabla 4. Estructura de tamaños de parche en la malla de 30 m del mapa 2026 (perímetro ecológico: "
                          f"{fmt(i.perimetro_km)} km; clases vecinas: {int(i.n_vecinos)}). [1]")
        # --- síntesis y sección 1
        k_mono = next((k for k, b in enumerate(bs) if b["t"] == "h2" and b.get("x", "").startswith("Monografía")), None)
        if k_mono is not None and k_mono + 1 < len(bs) and bs[k_mono + 1]["t"] == "p":
            b = bs[k_mono + 1]
            cuerpo = b["h"].replace("Síntesis de la ficha de origen.", "").strip()
            b["h"] = "Síntesis de la ficha de origen. " + texto_lead(c) + " " + sin_cifras(cuerpo)
        k1 = indice_h3(bs, "1.")
        if k1 is not None:
            for n_, k in enumerate(parrafos_de(bs, k1)):
                t1 = sin_cifras(limpiar_frase(bs[k]["h"]))
                if not t1 and n_ == 0:
                    t1 = f"Corresponde a la clase {c} del mapa 2026: {nom(c)}. [1]"
                bs[k]["h"] = t1 or bs[k]["h"]
        # --- secciones · Referencia
        for b in bs:
            if b["t"] == "p":
                b["h"] = b["h"].replace("con la delimitación cartográfica actual de esta unidad",
                                        "con la delimitación de esta unidad en la etapa de catálogo")
        reescribir(bs, "2.", texto_sec2(c))
        reescribir(bs, "3.", texto_sec3(c))
        reescribir(bs, "5.", texto_sec5(c))
        reescribir(bs, "6.", texto_sec6(c), conservar=False)
        reescribir(bs, "7.", texto_sec7(c))
        # --- secciones 8 y 9
        for pre in ("8.", "9."):
            k = indice_h3(bs, pre)
            if k is None:
                continue
            j = k + 1
            while j < len(bs) and bs[j]["t"] not in ("h2", "h3"):
                if bs[j]["t"] in ("p", "li"):
                    bs[j]["h"] = limpiar_frase(bs[j]["h"])
                    if bs[j]["t"] == "p" and pre == "9." and (SUPERLATIVO.search(bs[j]["h"]) or CIFRA.search(bs[j]["h"])):
                        bs[j]["h"] = (sin_cifras(bs[j]["h"]) or
                                      "Las prioridades de información e investigación para esta unidad son las siguientes.")
                j += 1
    # --- aportes nuevos (G08, Komar, fauna) dentro de «Aportes de la revisión técnica»
    nuevos = []
    if c in G08 or 2100 <= c < 2300:
        nuevos.append({"t": "nota", "h": FUENTE_G08, "v6": True})
        nuevos += [{"t": "li", "h": x + f" [{ref_numero(bs, REF_FAUNA['mendieta2026'])}]", "v6": True} for x in G08.get(c, [])]
        nuevos.append({"t": "li", "h": G08_GENERAL + f" [{ref_numero(bs, REF_FAUNA['mendieta2026'])}]", "v6": True})
    if c in (6262, 6272, 631, 9102, 616, 6173, 16201, 16202, 16203, 16204, 6165, 635, 615, 9101):
        nuevos.append({"t": "nota", "h": "Ajustes de redacción y de especies según las observaciones del revisor técnico Oliver Komar "
                       f"(Universidad Zamorano, noviembre 2026). [{ref_numero(bs, REF_FAUNA['komar2026'])}]", "v6": True})
    if c == 9101:
        s = cru[(cru.codigo == 9101) & (cru.capa == "Departamento") & (cru.territorio.isin(["HN06", "HN17"]))]
        if s.hectareas.sum() > 0:
            nuevos.append({"t": "li", "h": f"El mapa 2026 asigna a esta clase {ha(s.hectareas.sum())} en Choluteca y Valle (golfo de "
                           "Fonseca). Esos polígonos deben reclasificarse como litoral arenoso del Pacífico o, en Amapala y otras "
                           "islas del golfo, como litoral rocoso en la próxima actualización.", "v6": True})
    for texto, refs in FAUNA.get(c, []):
        if not any(x.get("h") == FUENTE_FAUNA for x in nuevos):
            nuevos.append({"t": "nota", "h": FUENTE_FAUNA, "v6": True})
        ns = sorted({ref_numero(bs, REF_FAUNA[r]) for r in refs})
        nuevos.append({"t": "li", "h": texto + " [" + ", ".join(map(str, ns)) + "]", "v6": True})
    if nuevos:
        k_ap = next((k for k, b in enumerate(bs) if b["t"] == "h2" and b.get("x", "") == "Aportes de la revisión técnica"), None)
        if k_ap is None:
            k_ref = next((k for k, b in enumerate(bs) if b["t"] == "h2" and b.get("x", "").startswith("Referencias")), len(bs))
            bs[k_ref:k_ref] = [{"t": "h2", "x": "Aportes de la revisión técnica", "v6": True}] + nuevos
        else:
            k = k_ap + 1
            while k < len(bs) and bs[k]["t"] != "h2":
                k += 1
            bs[k:k] = nuevos
    # --- equivalencia con el mapa de 2002 (antes de los aportes o de las referencias)
    n2 = ref_mejia(bs)
    eq, nota = T2.EQUIV.get(c, ([], None))
    blo = [{"t": "h2", "x": "Equivalencia con el mapa de 2002", "v6": True}]
    if eq:
        blo.append({"t": "p", "h": f"En el Mapa de Ecosistemas Vegetales de Honduras de 2002 [{n2}], esta unidad corresponde "
                    "conceptualmente a las categorías siguientes, cuya descripción se resume a continuación.", "v6": True})
        for k in eq:
            tit, codigos, desc = T2.DESC[k]
            blo.append({"t": "p", "h": f"<b>{tit} ({codigos}).</b> {desc} [{n2}]", "v6": True})
    if nota:
        blo.append({"t": "nota", "h": T2.NOTA_SIN[nota], "v6": True})
    fr = T2.frase_coincidencia(c)
    if fr:
        blo.append({"t": "p", "h": "<b>Coincidencia espacial.</b> " + fr, "v6": True})
        blo.append({"t": "nota", "h": T2.CAUTELA, "v6": True})
    k_dest = next((k for k, b in enumerate(bs) if b["t"] == "h2" and b.get("x", "") == "Aportes de la revisión técnica"), None)
    if k_dest is None:
        k_dest = next((k for k, b in enumerate(bs) if b["t"] == "h2" and b.get("x", "").startswith("Referencias")), len(bs))
    bs[k_dest:k_dest] = blo
    d["bloques"] = bs
    d["v6"] = True
    return d


if __name__ == "__main__":
    COPIA.mkdir(exist_ok=True)
    n = 0
    for r in sorted(FICHAS.glob("*.json")):
        t = r.read_text(encoding="utf-8")
        d = json.loads(t)
        if "bloques" not in d:
            continue
        cop = COPIA / r.name
        if not d.get("v6"):
            shutil.copyfile(r, cop)  # entrada nueva desde 03 + 06
        d = json.loads(cop.read_text(encoding="utf-8"))
        nuevo = json.dumps(revisar(d), ensure_ascii=False, separators=(",", ":"))
        if nuevo != t:
            r.write_text(nuevo, encoding="utf-8")
            n += 1
    print(f"{n} fichas actualizadas (v6)")
