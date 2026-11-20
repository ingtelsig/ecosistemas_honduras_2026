"""Correcciones v7 de las fichas y de clases.json (revisión final del sitio, 20-11-2026).

Se ejecuta después de 08_revision_v6.py, sobre public/data/fichas/*.json y public/data/clases.json.
Aplica el plan Revision_web_final/Plan_correcciones_sitio.md (fase 1 y decisiones D2–D5):
celdas truncadas, instrucciones internas, notas de revisión fuera de lugar, especies, códigos
del mapa 2002, estación seca/lluviosa, encabezados de grupo, referencia [1], nombres comunes,
rutas internas, notas de decisión y cursivas en las tablas de especies.

Los cambios son idempotentes: volver a ejecutarlo no duplica notas ni filas.
"""
import glob
import json
import os
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DATA = RAIZ / "public" / "data"
FICHAS = DATA / "fichas"
LOG = []


def log(*a):
    LOG.append(" ".join(str(x) for x in a))


# ---------------------------------------------------------------- grupos oficiales (Tabla 2.1)
GRUPOS = {
    "G01": "Ecosistemas marinos y ambientes potenciales",
    "G02": "Litorales naturales",
    "G03": "Manglares",
    "G04": "Humedales costeros y sistemas de transición",
    "G05": "Ríos, lagos y embalses",
    "G06": "Humedales continentales",
    "G07": "Bosques latifoliados",
    "G08": "Bosques de coníferas",
    "G09": "Bosques mixtos",
    "G10": "Formaciones arboladas abiertas, sabanas y jicarales",
    "G11": "Arbustales",
    "G12": "Pastizales y herbazales intervenidos",
    "G13": "Sistemas agrícolas, agroforestales y acuícolas",
    "G14": "Litorales artificiales, superficies urbanas y suelo desnudo",
}
MARINAS_REV = {16201, 16202, 16203, 16204, 616, 617, 618, 6173, 634, 635}
ALT_T13 = ("T1.3 (Bosques lluviosos montanos tropicales/subtropicales): si el sitio está en el piso montano "
           "o en el submontano superior con nubosidad frecuente")
ALT_T13_CLASES = {1122, 1123, 1124, 1222, 1223, 1224, 2220, 3120, 3220, 8112}
CRIT_2230 = ("pinar de piso montano: bosque montano tropical con coníferas, con estación seca marcada")
CRIT_2230_VIEJO = "pinar de régimen pluvial o de piso montano: bosque montano tropical con coníferas"
REF1 = ("<b>[1]</b> INGTELSIG (2026). <i>Actualización del Mapa de Ecosistemas de Honduras. Informe Técnico "
        "Final</i>. Programa de Biodiversidad Enlazando el Paisaje Centroamericano, UICN, y SERNA–DiBio.")


# ---------------------------------------------------------------- utilidades
def txt(b):
    return b.get("h") if "h" in b else b.get("x", "")


def set_txt(b, v):
    if "h" in b:
        b["h"] = v
    else:
        b["x"] = v


def cuadro(bs):
    for b in bs:
        if b["t"] == "tabla" and b["f"] and b["f"][0][0] == "Indicador clave":
            return b
    return None


def fila(bs, prefijo):
    c = cuadro(bs)
    if c:
        for r in c["f"]:
            if r[0].startswith(prefijo):
                return r
    return None


def tabla_especies(bs):
    for b in bs:
        if b["t"] == "tabla" and len(b["f"][0]) == 4 and b["f"][0][1].startswith("Especie"):
            return b
    return None


def indice_h3(bs, num):
    for i, b in enumerate(bs):
        if b["t"] == "h3" and txt(b).startswith(f"{num}."):
            return i
    return None


def tiene(bs, marca):
    return any(marca in (txt(b) or "") for b in bs if b["t"] != "tabla")


def sub(rx, rep, s, flags=0):
    return re.sub(rx, rep, s, flags=flags)


# ---------------------------------------------------------------- reemplazos generales
# (regex, reemplazo) aplicados a todo texto (párrafos, notas, títulos y celdas).
GENERALES = [
    # rutas internas y regla estricta
    (r"; la regla estricta, que deja en MULT o SIN_GET las clases con varias membresías o solo contextuales, "
     r"se conserva en Superficies_ajustadas_R26_por_codigo\.csv\.", "."),
    (r"\s*Detalle en Control/\S+?\.(?:csv|gpkg|json)(?:; las zonas sin evidencia suficiente están en Control/\S+?\.gpkg)?\.", ""),
    (r"; están en la capa de revisión Control/\S+?\.gpkg\.", "."),
    (r" \(63 % de la superficie de la clase; Control/GET_principal_evidencia_R26\.json\)", " (63 % de la superficie de la clase)"),
    (r"La leyenda no cambia: la clase conserva su código y el régimen se publica en Geodatos/\S+?\.tif, con cifras en "
     r"Clasificacion/\S+?\.csv\.", "La leyenda no cambia: la clase conserva su código y el régimen se publica como capa "
     "complementaria del mapa."),
    # enlaces rotos de la bibliografía (fase 6): se conserva la cita sin URL
    (r"\s+https://(?:doi\.org/10\.15517/rev\.biol\.trop\.v71i1\.53627|www\.salamandra-journal\.com/\S+"
     r"|www\.cambridge\.org/core/journals/journal-of-tropical-ecology/article/8E676ED96AAA0E727D1BC92722154C18"
     r"|www\.sgjd\.gob\.hn/\S+|seea\.un\.org/file/26308/\S+|enee\.hn/sobre-nosotros)", ""),
    # cifras y redacción
    (r"\bel < 0,1 % a la", "menos del 0,1 % a la"),
    (r" celdas de 30 m Área ajustada", " celdas de 30 m · área ajustada"),
    (r"\ben esta unidad recibió", "esta unidad recibió"),
    (r"cover\?\.", "cover?"),
    (r"\ben Producto 3\b", "en la evaluación diagnóstica (Producto 3)"),
    (r"(?:verificación|validación|respaldo) de verificación directa en campo", "verificación directa en campo"),
    (r"verificación directa en campo por campo exacto coherente", "verificación directa en campo"),
    (r"verificación directa en campo por coincidencia exacta de campo", "verificación directa en campo"),
    (r"\bposee verificación directa", "cuenta con verificación directa"),
    (r"\bPosee verificación directa", "Cuenta con verificación directa"),
    # topónimos y nombres
    (r"Blanca Janeth Kawas", "Blanca Jeannette Kawas"),
    (r"Guaymoreto", "Guaimoreto"),
    (r"\bArea de\b", "Área de"),
    (r"Lutjanus mahogani", "Lutjanus mahogoni"),
    # unidades y abreviaturas
    (r"\s?\bmsnm\b", " m s. n. m."),
    (r"\bm s\.n\.m\.", "m s. n. m."),
    (r"(\d) grados\b", r"\1°"),
    (r"Especie \(científico y común\)", "Especie (nombre científico y común)"),
    (r"<i>([A-Z][a-z]+) sp\d\d\.?</i>", r"<i>\1</i> sp."),
    (r"\b([A-Z][a-z]+) sp\d\d\b\.?", r"\1 sp."),
    (r"var\. hond\b(?!urensis)", "var. hondurensis"),
    (r"(?<![.\w])sp\.\.", "sp."),
    (r"(?<!\.)\.\.(?!\.)", "."),
]
# Solo fuera de la bibliografía
FUERA_REF = [
    (r"Moskitia", "Mosquitia"),
    (r"\bIFN\b", "INF"),
    (r"Inventario Forestal Nacional", "Inventario Nacional Forestal"),
    (r"\bKruta\b", "Cruta"),
    (r"\bLean\b", "Leán"),
]

# Estación seca / lluviosa (sustituye «estival» e «invernal» según el sentido de cada frase)
ESTACIONES = [
    ("déficit hídrico estival", "déficit hídrico de la estación seca"),
    ("la hipoxia invernal y el agrietamiento arcilloso estival",
     "la hipoxia de la estación lluviosa y el agrietamiento arcilloso de la estación seca"),
    ("como forraje estival", "como forraje de la estación seca"),
    ("humedad edáfica estival", "humedad edáfica en la estación seca"),
    ("el estrés estival", "el estrés de la estación seca"),
    ("marcadas por estiaje estival", "marcadas por el estiaje"),
    ("el caudal estival", "el caudal de la estación seca"),
    ("déficit hídrico invernal-primaveral", "déficit hídrico de la estación seca (nov.–abr.)"),
    ("caudales estivales", "caudales de la estación seca"),
    ("sequía atmosférica invernal-primaveral", "sequía atmosférica de la estación seca (nov.–abr.)"),
    ("cuya floración estival marca el estiaje", "cuya floración marca el estiaje"),
    ("encharcamiento temporal de verano", "encharcamiento temporal de la estación lluviosa (may.–oct.)"),
    ("la duración del anegamiento estival y la profundidad del nivel freático estival",
     "la duración del anegamiento de la estación lluviosa y la profundidad del nivel freático en la estación seca"),
    ("caudal base estival", "caudal base de la estación seca"),
    ("déficit hídrico atmosférico invernal", "déficit hídrico atmosférico de la estación seca (nov.–abr.)"),
    ("sometidas a estiaje invernal", "sometidas al estiaje de la estación seca"),
    ("cinco meses de sequía invernal-primaveral", "cinco meses de estación seca (nov.–abr.)"),
    ("donde el invierno astronómico trae consigo", "donde la estación seca (nov.–abr.) trae consigo"),
    ("suelos húmedos de invierno y desecación estival",
     "suelos húmedos de la estación lluviosa y desecación en la estación seca"),
    ("donde la sequía invernal modula", "donde la estación seca modula"),
    ("el exceso de humedad invernal", "el exceso de humedad de la estación lluviosa"),
    ("al encharcamiento invernal pasajero como a la aridez estival intensa",
     "al encharcamiento pasajero de la estación lluviosa como a la aridez intensa de la estación seca"),
    ("resistentes al barro invernal", "resistentes al barro de la estación lluviosa"),
    ("barro pesado invernal", "barro pesado de la estación lluviosa"),
    ("hacinamiento estival", "hacinamiento de la estación seca"),
    ("lagunas invernales del sur", "lagunas estacionales del sur"),
    ("el achicamiento estival", "el achicamiento de la estación seca"),
    ("sobrepastoreo estival", "sobrepastoreo de la estación seca"),
    ("desecación estival", "desecación de la estación seca"),
    ("Amortiguan desbordamientos invernales", "Amortiguan desbordamientos de la estación lluviosa"),
    ("la pérdida estival de verdor", "la pérdida de verdor de la estación seca"),
    ("la radiación y la sequía estival", "la radiación y la sequía de la estación seca"),
    ("donde el periodo seco invernal-primaveral provoca", "donde la estación seca (nov.–abr.) provoca"),
    ("barrizales invernales y grietas estivales", "barrizales de la estación lluviosa y grietas de la estación seca"),
    ("lagunas invierno-estivales", "lagunas estacionales"),
]

# Códigos del mapa 2002 en la monografía que no coinciden con el cuadro y el Anexo A
COD2002 = {
    610: [(r", verificada frente al código VA1a\(1\) del manual nacional de 2002\.", ".")],
    615: [(r", equivalente al código UNESCO SA2c\(1\)\.", "; en el mapa de 2002 corresponde a los sistemas acuáticos (SA1).")],
    616: [(r" y al código UNESCO SA2a\(6\)\.", "."),
          (r" y se articulan con la categoría SA2a\(6\) de la leyenda centroamericana heredada para formaciones biogénicas "
           r"someras de plataforma\.", ".")],
    617: [(r" y al código UNESCO SA2a\(2\)\.", "."),
          (r" y se vinculan con la clase SA2a\(2\) del sistema acuático centroamericano para fondos arenosos someros y "
           r"sedimentos gruesos\.", ".")],
    618: [(r" y al código centroamericano UNESCO SA2a\(3\)\.", "."),
          (r", equivalente a la unidad SA2a\(3\) de la nomenclatura acuática centroamericana\.", ".")],
    630: [(r"VA1 / VA1a\(2\) del manual UNESCO 2002", "VA1 del mapa de 2002")],
    631: [(r"con el código UNESCO VIB5 \(variante VIB2a\(1\), Albina con escasa vegetación, ecosistema 109 de Mejía y "
           r"House, 2002\)", "con el código VIB5 de Mejía y House (2002)")],
    634: [(r" y al código UNESCO SA2a\(4\)\.", "."),
          (r" y corresponden al código SA2a\(4\) de la leyenda UNESCO centroamericana\.", ".")],
    1122: [(r"el bosque montano inferior siempreverde UNESCO IA1c\(1\)",
            "el bosque tropical siempreverde latifoliado submontano del mapa de 2002 (IA1b(1))")],
    1123: [(r"el bosque siempreverde montano inferior UNESCO IA1c\(1\)",
            "el bosque tropical siempreverde latifoliado submontano del mapa de 2002 (IA1b(1))")],
    1124: [(r"el bosque montano inferior UNESCO IA1c\(1\)",
            "el bosque tropical siempreverde latifoliado submontano del mapa de 2002 (IA1b(1))")],
    1212: [(r"el complejo estacional basal UNESCO IB1a\(1\)\(a\)",
            "los bosques siempreverde estacional y semideciduo de tierras bajas del mapa de 2002 (IA2a(1) e IA3a(1))")],
    1213: [(r"al dominio estacional basal UNESCO IB1a\(1\)\(a\)",
            "a los bosques siempreverde estacional y semideciduo de tierras bajas (IA2a(1) e IA3a(1))")],
    1232: [(r"el bosque montano húmedo UNESCO IA1c\(1\)",
            "el bosque tropical siempreverde estacional latifoliado montano del mapa de 2002 (IA2c(1) e IA2d(1))")],
    1314: [(r"\(código UNESCO IB1a\(1\)\(a\) verificado en Mejía y House\)", "(código IB1a(1) de Mejía y House, 2002)")],
    2110: [(r"con IA1 \(<i>Bosque Tropical Siempreverde</i>, variante IA1a\(2\)\)", "con el pinar de tierras bajas IA2a(2)")],
    2130: [(r"enlaza con IA1 \(IA1c\(2\)\)", "enlaza con el pinar montano inferior IA2c(2) y con los bosques mixtos "
            "montanos IA1c(1/2) a IA1e(1/2)")],
    2210: [(r"se vincula a IA1 \(IA1a\(2\)\)", "se vincula a los pinares de tierras bajas y submontanos IA2a(2) e IA2b(2)")],
    2220: [(r"con la formación IA1 \(IA1c\(2\)\) de Mejía", "con el pinar submontano IA2b(2) de Mejía")],
    3110: [(r"a la formación IA1 \(variante mixta basal IA1a\(1/2\)\)", "al bosque mixto de tierras bajas IA2a(1/2)(b)")],
    3210: [(r"con IA1 \(variante mixta basal IA1a\(1/2\)\)", "con el bosque mixto de tierras bajas IA2a(1/2)(b)")],
    3220: [(r"homologada con el código verificado IA1c\(1/2\) \(<i>Bosque tropical siempreverde mixto montano inferior</i>\)",
            "homologada con los bosques mixtos estacionales IA2b(1/2) e IA2c(1/2)")],
    3230: [(r"bajo el código IA1c\(1/2\)", "bajo los códigos IA2b(1/2), IA2c(1/2) e IA2d(1/2)"),
           (r" \(estado MULTIPLE\)", "")],
    6202: [(r"afín al código UNESCO VE1 del manual de 2002", "afín a la categoría VE1a(2) del manual de 2002")],
    6205: [(r"con afinidad hacia formaciones palustres costeras VE1 del manual de 2002",
            "con afinidad hacia las formaciones costeras del manual de 2002 (VIB1 a VIB5)")],
}

# Sección 8 de los pinares 2120 y 2230 (D2: T1.3 principal, T4.2 alternativa)
SEC8 = {
    2120: (r"^En el marco funcional GET-UICN, la clase 2120 presenta correspondencia parcial dual T4\.2 / T1\.3 .*?"
           r"sin depender de regímenes térmicos templados \(T2\.1\)\.",
           "En la tipología GET-UICN, la clase 2120 se asigna a T1.3 (Bosques lluviosos montanos tropicales/"
           "subtropicales) como grupo funcional principal, con T4.2 (Sabanas pirófilas de gramíneas cespitosas) como "
           "membresía alternativa; en el mapa de 2002 corresponde al pinar submontano IA2b(2) (Mejía y House, 2002). "
           "La asignación recoge una bifurcación ecológica real en las laderas húmedas hondureñas: las hondonadas "
           "expuestas a bancos frecuentes de niebla y colonizadas por <i>Clethra</i>, briófitos y epífitas funcionan "
           "como bosque montano húmedo propio de T1.3, mientras que los filos ventilados con sotobosque graminoide o "
           "de helecho pirófito siguen la dinámica de fuego recurrente de T4.2, sin depender de regímenes térmicos "
           "templados (T2.1)."),
    2230: (r"^En la tipología GET-UICN mantiene correspondencia parcial con el par funcional T4\.2 / T1\.3, .*?"
           r"se aproximan a T1\.3\.",
           "En la tipología GET-UICN se asigna a T1.3 (Bosques lluviosos montanos tropicales/subtropicales) como "
           "grupo funcional principal, por su piso montano, con T4.2 (Sabanas pirófilas de gramíneas cespitosas) como "
           "membresía alternativa; en el mapa de 2002 corresponde al pinar montano inferior IA2c(2) (Mejía y House, "
           "2002). Las vaguadas superiores con <i>Pinus maximinoi</i>, <i>Liquidambar</i> y condensación estacional "
           "de niebla sustentan la asignación a T1.3, mientras que los rodales estacionales de solana con "
           "<i>Muhlenbergia</i> y fuegos recurrentes se acercan a T4.2."),
}

# Correcciones de especies y de contenido por ficha: (regex, reemplazo)
ESPECIES = {
    9101: [(r"Uniola pittieri", "Uniola paniculata")],
    9102: [(r"<i>Uniola paniculata</i>, ", "")],
    618: [(r"el bagre cuatete \(<i>Ariopsis guatemalensis</i>\)", "el bagre bandera (<i>Bagre marinus</i>) y los "
           "bagres del género <i>Cathorops</i>"),
          (r"^Ariopsis guatemalensis \(Bagre cuatete\)$", "Bagre marinus (bagre bandera)"),
          (r"Pez siluriforme demersal de fondos blandos estuarino-costeros",
           "Bagre marino demersal de fondos blandos estuarino-costeros del Caribe")],
    1332: [(r" con <i>Quercus oleoides</i> en mesetas y depresiones de drenaje impedido y el fresno", " y el fresno")],
    1333: [(r"Robles de esta unidad: <i>Q\. oleoides</i>, (.*?)\.$",
            r"Robles de esta unidad: \1; <i>Q. oleoides</i> solo aparece de forma marginal en sus bordes más bajos.")],
    1312: [(r"colonias de palma real \(<i>Sabal mexicana</i>\) indicadoras de encharcamiento estacional",
            "colonias de palmas (<i>Brahea dulcis</i>, el suyate de Olancho y del Guayape; <i>Sabal mexicana</i> solo "
            "en el sur de La Paz)"),
          (r"<i>Albizia niopoides</i> y <i>Sabal mexicana</i>", "<i>Albizia niopoides</i> y <i>Brahea dulcis</i>"),
          (r"^Sabal mexicana \(Palma real\)$", "Brahea dulcis (suyate)"),
          (r"^Palma freatófita de planicies secas estacionalmente encharcadas$",
           "Palma de vegas y laderas secas de Olancho y del Guayape; Sabal mexicana la sustituye en el sur de La Paz")],
    1313: [(r" \(dosel emergente reportado de 40,0 m\)",
            " (la altura de 40 m reportada para el dosel emergente requiere verificación)")],
    1314: [(r"\(Santa Bárbara, con emergentes de 40,0 m\)",
            "(Santa Bárbara; la altura de 40 m reportada para los emergentes requiere verificación)"),
           (r"(<i>Vochysia guatemalensis</i>, <i>Mangifera indica</i>\.)",
            r"\1 Son especies de bosque húmedo o cultivadas, lo que indica subparcelas atípicas o mal enlazadas; "
            r"no se usan como diagnósticas de la unidad.")],
    631: [(r"(cuyas madrigueras oxigenan el suelo\.)(?! En los fangos del Caribe)",
           r"\1 En los fangos del Caribe, que concentran la mayor parte de la unidad, cumplen ese papel el cangrejo de "
           r"manglar (<i>Ucides cordatus</i>) y el cangrejo azul (<i>Cardisoma guanhumi</i>).")],
    2130: [(r"se establece <i>Pinus hartwegii</i>, tolerante", "aparece de forma puntual <i>Pinus hartwegii</i>, tolerante"),
           (r"^Pino altimontano de las cumbres más altas \(> 2300 m, Celaque y Santa Bárbara\)$",
            "Elemento puntual de las cumbres más altas (> 2.300 m, Celaque); no es diagnóstico de la unidad, cuyo "
            "percentil 95 de altitud es de 1.741 m")],
    3220: [(r", mientras en el dosel opera activamente la chara ocotera o azulona \(<i>Cyanocitta stelleri</i>\), córvido "
            r"territorial responsable de dispersar y esconder bellotas y semillas de pino a través de los fragmentos de "
            r"ladera\.", ".")],
    4033: [(r"Colibrí endémico crítico cuyo hábitat", "Colibrí endémico en peligro cuyo hábitat")],
    6062: [(r"^Tepemechín \(Dajaus monticola\)$", "Agonostomus monticola (tepemechín)")],
    6063: [(r"^Tepemechín \(Dajaus monticola\)$", "Agonostomus monticola (tepemechín)")],
    635: [(r"colinas abisales", "mesetas submarinas")],
    8131: [(r"hierbas rastreras xerotolerantes", "hierbas rastreras heliófilas"),
           (r"Hierba rastrera xerotolerante de entrecalles", "Hierba rastrera heliófila de entrecalles"),
           (r"dentro del árido relieve disectado", "dentro del relieve disectado"),
           (r"frutales xerotolerantes", "frutales")],
    6262: [(r"\(alto y denso / bajo y enano\): en esta unidad", "(alto y denso / bajo y enano): esta unidad")],
}
# Filas de especies que se retiran: (código, especie al inicio de la celda)
QUITAR_FILAS = {(1332, "Quercus oleoides"), (3220, "Cyanocitta stelleri")}
# Filas que se añaden a la tabla de especies
NUEVAS_FILAS = {
    601: [["Dosel / Estrato superior", "Pinus caribaea var. hondurensis (pino caribe)",
           "Pino de las sabanas de tierras bajas de La Mosquitia, donde está cerca de un tercio de la unidad", "Nacional [2]"]],
    631: [["Fauna diagnóstica asociada", "Ucides cordatus (cangrejo de manglar)",
           "Cangrejo excavador de fangos de manglar del Caribe", "Caribe"],
          ["Fauna diagnóstica asociada", "Cardisoma guanhumi (cangrejo azul)",
           "Cangrejo terrestre de bordes fangosos y manglares del Caribe", "Caribe"]],
}

# Celdas «Biota y estructura diagnóstica» que se reescriben a mano (el resto se corta en un límite de frase)
BIOTA = {
    2130: "Reemplaza gradualmente al ocote (Pinus oocarpa) de su franja inferior por coníferas montanas esbeltas de "
          "acícula fina y porte elevado: Pinus maximinoi y Pinus pseudostrobus entre 1.100 y 2.200 m; Pinus hartwegii "
          "solo aparece de forma puntual en las cumbres más altas.",
    3230: "El dosel alcanza una mediana integrada de 22,50 m (28,00 m en ETH y percentil 95 de 36,00 m) y congrega un "
          "ensamble diverso de coníferas montanas encabezado por Pinus maximinoi, mezclado con robles y otras latifoliadas.",
    4032: "Está dominado por leguminosas espinosas tolerantes tanto al encharcamiento pasajero de la estación lluviosa "
          "como a la aridez intensa de la estación seca: Prosopis juliflora (carbón blanco o mezquite) y Parkinsonia "
          "aculeata (palo verde).",
    630: "Estructurada por densos pajonales y juncales hidromórficos de Rhynchospora barbata y cortaderas de Cladium "
         "mariscus subsp. jamaicense.",
    1133: "En su bóveda nebulosa coexisten Podocarpus oleifolius, Quercus benthamii y Persea americana var. nubigena.",
    2210: "El estrato arbóreo está gobernado por procedencias interiores de Pinus caribaea var. hondurensis tolerantes "
          "a la sequía estacional.",
    3210: "El dosel alcanza una mediana integrada de 17,50 m (22,00 m en ETH) y articula una mezcla codominante de "
          "Pinus caribaea var. hondurensis con latifoliadas.",
    1332: "El dosel superior está protagonizado por robles y encinos montanos caducifolios y esclerófilos (Quercus "
          "spp.), acompañados en las cañadas frescas por el fresno (Fraxinus uhdei).",
    6262: "Reúne la mayor riqueza taxonómica arbórea de mangles verdaderos del país al sumar a Rhizophora mangle, "
          "Avicennia germinans, Laguncularia racemosa y Conocarpus erectus dos especies exclusivas del Pacífico: el "
          "mangle rojo caballero (Rhizophora racemosa) y el curumo (Avicennia bicolor).",
    9101: "Exhibe una secuencia psamófila halotolerante ordenada desde el frente móvil de berma colonizado por "
          "estolones fijadores de Ipomoea pes-caprae, Canavalia rosea, cojines suculentos de Sesuvium portulacastrum y "
          "macollas de avena de mar (Uniola paniculata).",
    610: "Integra bosques pantanosos de agua dulce caracterizados por raíces tabulares, zancos y neumatóforos de "
         "Pterocarpus officinalis, Symphonia globulifera, Carapa guianensis, Erythrina fusca y Pachira aquatica.",
    614: "Monocultivo estacional de arroz (Oryza sativa) acompañado por una comunidad especializada de arvenses "
         "hidrófilas y helófitas adaptadas a fangos saturados, como el arrocillo (Echinochloa colona).",
    2220: "El dosel está ampliamente dominado por Pinus oocarpa (18,00 m de altura integrada; 24,00 m en ETH), "
          "acompañado en el estrato medio por arbolitos pirófitos como Byrsonima crassifolia y la leguminosa Lysiloma "
          "auritum.",
    8214: "Dominan gramíneas macolladoras altas adaptadas a suelos bien aireados como el zacate guinea o mombaza "
          "(Megathyrsus maximus) y gramas nativas rastreras de suelos ácidos (Paspalum conjugatum).",
    8232: "Estrato herbáceo denso dominado por gramíneas forrajeras naturalizadas o implantadas resistentes tanto al "
          "estiaje severo como al encharcamiento temporal de suelos pesados, en particular el pasto estrella (Cynodon "
          "nlemfuensis).",
    8301: "Dominada por cereales y leguminosas alimentarias esenciales: maíz (Zea mays), frijol común (Phaseolus "
          "vulgaris) y maicillo o sorgo (Sorghum bicolor) en regiones secas, además de papa y hortalizas en tierras altas.",
    8303: "Monocultivos densos de híbridos industriales de caña de azúcar (Saccharum spp., derivados principalmente de "
          "Saccharum officinarum), acompañados en entrecalles y bordes mecanizados por arvenses graminoides y ciperáceas.",
    16202: "En la capa superficial oceánica iluminada que corona esta huella (alcance conceptual M2.1), la fijación "
           "fotosintética depende de picoplancton autótrofo adaptado a aguas azules oligotróficas permanentemente "
           "estratificadas.",
    16204: "Confinada a oscuridad solar perpetua bajo varios kilómetros de columna de agua oceánica, carece por completo "
           "de fitoplancton viable o producción primaria fotosintética vegetal.",
    6261: "Estructurado por rodales arbóreos vigorosos de mangle rojo (Rhizophora mangle), mangle blanco (Laguncularia "
          "racemosa) y mangle negro (Avicennia germinans), con botoncillo (Conocarpus erectus) hacia los márgenes internos.",
}
VACIAS = {"y", "e", "o", "u", "de", "del", "la", "el", "los", "las", "en", "con", "por", "a", "al", "como", "que",
          "entre", "mientras", "junto", "hacia", "sobre", "se", "su", "sus", "un", "una", "menos", "más", "cuyo", "cuya"}


def cortar_biota(s):
    """Corta una celda truncada en un límite de frase y cierra paréntesis."""
    s = s.replace("*", "").strip()
    if len(s) < 200:
        return s if s.endswith(".") else s + "."
    if not re.search(r"\bspp?\.$", s):
        s = s.rstrip(".").rstrip()
    palabras = s.split(" ")
    quitada = False
    while palabras and palabras[-1].lower().strip(",;—(") in VACIAS:
        quitada = quitada or palabras[-1].lower() not in ("y", "e", "o", "u")
        palabras.pop()
    s = " ".join(palabras).rstrip(",;— ")
    if quitada:  # frase cortada a medias: volver al último límite de nivel 0
        prof, corte = 0, -1
        for i, ch in enumerate(s):
            if ch == "(":
                prof += 1
            elif ch == ")":
                prof -= 1
            elif prof == 0 and (s[i:i + 2] in (", ", "; ") or ch == "—"):
                corte = i
        if corte > 80:
            s = s[:corte].rstrip(",;— ")
            palabras = s.split(" ")
            while palabras and palabras[-1].lower() in VACIAS:
                palabras.pop()
            s = " ".join(palabras).rstrip(",;— ")
    abiertos = s.count("(") - s.count(")")
    s = s + ")" * max(0, abiertos)
    if s.count("—") % 2 == 1:
        s = s[:s.rfind("—")].rstrip(",;: ")
    return s if s.endswith(".") else s + "."


# ---------------------------------------------------------------- nombres comunes en mayúsculas
SIGLAS = {"SRTM", "EVI2", "GFCC", "HAND", "GLAD/GEDI", "ETH", "JRC", "IIIB1", "ETOPO1", "CITES II", "MOCNESS"}
TILDES_COMUN = {
    "HONDURENO": "hondureño", "AMARILLON": "amarillón", "ALFENIQUE": "alfeñique", "RAMON": "ramón",
    "SELILLON": "selillón", "TOSTASON": "tostasón", "CANELÓN": "canelón", "PINO CARIBAEA": "pino caribe",
    "DESCONOCIDO": "sin nombre común",
}


def comun_minusculas(m):
    s = m.group(1)
    if s.strip() in SIGLAS:
        return m.group(0)
    letras = [c for c in s if c.isalpha()]
    if not letras or sum(c.isupper() for c in letras) < 0.8 * len(letras):
        return m.group(0)
    s = re.sub(r",(?=\S)", ", ", s)
    partes = []
    for p in s.split(", "):
        p = p.strip()
        q = TILDES_COMUN.get(p)
        if q is None:
            q = " ".join(TILDES_COMUN.get(w, w.lower()) for w in p.split(" "))
        partes.append(q)
    return "(" + ", ".join(partes) + ")"


ALCANCE = {
    "NACIONAL": "Nacional", "ENDEMICO_HONDURAS": "Endémica de Honduras", "ENDEMICO_CUSUCO": "Endémica de Cusuco",
    "ENDEMICO_AGUAN_COCHINOS": "Endémica del Aguán y Cayos Cochinos", "ENDEMICO_MONTANA_YORO": "Endémica de Montaña de Yoro",
    "ENDEMICO_CELAQUE": "Endémica de Celaque", "INSULAR_UTILA": "Insular (Utila)",
}


def cursiva_especie(c):
    """Pone en cursiva el nombre científico de la columna de especies: «Genus species (común)»."""
    if "<i>" in c:
        return c
    m = re.match(r"^([A-Z][a-z]+(?: (?!spp?\.)[a-z][a-z-]+)?(?: (?:var|subsp)\. [a-z-]+)?)( spp?\.)?(.*)$", c)
    if not m:
        return c
    cient, sp, resto = m.group(1), m.group(2) or "", m.group(3)
    if resto.strip() and not resto.startswith((" (", ",", " /", " y ")):
        return c
    cient = re.sub(r" (var|subsp)\. ", r"</i> \1. <i>", cient)
    return "<i>" + cient + "</i>" + sp + resto


# ---------------------------------------------------------------- notas de decisión
NOTA_601 = ("<b>Nota sobre el nombre de la unidad.</b> Se conserva el nombre oficial de la clase. Un 34 % de su "
            "superficie está en Gracias a Dios, en las sabanas de pino de tierras bajas de La Mosquitia, dominadas por "
            "<i>Pinus caribaea</i> var. <i>hondurensis</i>; allí el calificativo «montano-húmedo» describe el régimen "
            "húmedo de la clase, no el piso altitudinal.")
NOTA_REGIMEN = ("<b>Criterio de régimen climático.</b> El régimen de los cafetales ({reg}) se asignó con la fenología "
                "de la vegetación (caída estacional del verdor en Sentinel-2) y la duración de la estación seca, no con "
                "la lluvia anual. Por eso 8121 y 8131 tienen una lluvia anual parecida, cercana a 1.950 mm según "
                "WorldClim 2.1; la clase no cambia.")
NOTA_AGUA = ("Los límites departamentales y municipales de referencia (OCHA/HDX) excluyen la mayor parte del espejo de "
             "agua, por lo que los porcentajes por departamento y municipio suman bastante menos del 100 %.")
NOTA_BIOTA_MARINA = "La biota es de referencia conceptual y no constituye un inventario local verificado."


def procesar(d):
    c = d["codigo"]
    bs = d["bloques"]
    n0 = json.dumps(bs, ensure_ascii=False)

    # 1. retirar notas de revisión de suelos de Sula/Aguán y bahía de Trujillo en fichas marinas
    if c in MARINAS_REV:
        bs[:] = [b for b in bs if not (b["t"] == "li" and (
            b["h"].startswith("Suelos de los bordes costeros de los valles de Sula y Aguán")
            or b["h"].startswith("Considerar también la bahía de Trujillo")))]
        limpio = []
        for i, b in enumerate(bs):
            sig = bs[i + 1] if i + 1 < len(bs) else None
            if (b["t"] == "nota" and b["h"].startswith("Observaciones del revisor técnico Miguel Mendieta")
                    and (sig is None or sig["t"] != "li")):
                continue
            limpio.append(b)
        bs[:] = [b for i, b in enumerate(limpio)
                 if not (b["t"] == "h2" and txt(b).startswith("Aportes de la revisión técnica")
                         and (i + 1 >= len(limpio) or limpio[i + 1]["t"] == "h2"))]

    # 2. instrucciones internas en las notas de la Tabla 3
    for b in bs:
        if b["t"] == "nota":
            h = b["h"]
            h = sub(r"; no adjudicar biota local no verificada como inventario puntual\.\)", ". " + NOTA_BIOTA_MARINA + ")", h)
            h = sub(r"; mantener alcance conceptual GET-UICN (M[\d.]+(?:/M[\d.]+)?)\.\)", r", \1. " + NOTA_BIOTA_MARINA + ")", h)
            h = sub(r"; mantener reserva explícita sobre extensión bentónica local\.\)",
                    ". La extensión bentónica local no está verificada.)", h)
            h = sub(r" NO adjudicar comunidades coralinas o bentónicas locales no verificadas\.\)",
                    " No se atribuyen comunidades coralinas ni bentónicas locales sin verificación.)", h)
            b["h"] = h

    # 3. encabezado de grupo oficial
    for b in bs[:3]:
        if b["t"] == "p" and b["h"].startswith(f"Unidad {c} · Grupo "):
            num = int(d["grupo"][1:])
            b["h"] = f"Unidad {c} · Grupo {num} ({GRUPOS[d['grupo']]}) · Mapa de Ecosistemas de Honduras 2026"

    # 4. reemplazos de texto
    en_ref = False
    reglas = GENERALES + [(re.escape(a), b) for a, b in ESTACIONES] + COD2002.get(c, []) + ESPECIES.get(c, [])
    for b in bs:
        if b["t"] == "h2":
            en_ref = txt(b).startswith("Referencias") or en_ref
        if b["t"] == "tabla":
            for r in b["f"]:
                for j, x in enumerate(r):
                    for rx, rep in reglas:
                        x = re.sub(rx, rep, x)
                    for rx, rep in FUERA_REF:
                        x = re.sub(rx, rep, x)
                    r[j] = x
            continue
        s = txt(b)
        for rx, rep in reglas:
            s = re.sub(rx, rep, s)
        if not en_ref and not s.startswith("<b>["):
            for rx, rep in FUERA_REF:
                s = re.sub(rx, rep, s)
        if s.startswith("<b>[1]</b> INGTELSIG"):
            s = REF1
        set_txt(b, s)

    # 5. sección 8 de los pinares (D2)
    if c in SEC8:
        rx, rep = SEC8[c]
        for b in bs:
            if b["t"] == "p" and re.search(rx, b["h"], flags=re.S):
                b["h"] = re.sub(rx, rep, b["h"], flags=re.S)
        r = fila(bs, "Correspondencia GET-UICN")
        if r:
            r[1] = r[1].replace("T4.2 / T1.3", "T1.3 / T4.2")
    if c == 2230:
        for b in bs:
            if b["t"] == "p" and "Asignación GET-UICN principal" in b["h"]:
                b["h"] = b["h"].replace(CRIT_2230_VIEJO, CRIT_2230)

    # 6. alternativa T1.3 en el párrafo de asignación GET
    if c in ALT_T13_CLASES:
        for b in bs:
            if b["t"] == "p" and "Asignación GET-UICN principal" in b["h"] and "T1.3 (Bosques lluviosos montanos" not in b["h"]:
                h = b["h"]
                alt = "T1.3 (Bosques lluviosos montanos tropicales/subtropicales), si el sitio está en el piso montano o en el submontano superior con nubosidad frecuente"
                corte = h.find(" La superficie de la unidad se reporta")
                if corte < 0:
                    corte = len(h)
                cuerpo, cola = h[:corte], h[corte:]
                if "También puede pertenecer a" in cuerpo:
                    cuerpo = cuerpo.rstrip(".") + "; " + alt + "."
                else:
                    cuerpo = cuerpo.rstrip() + " También puede pertenecer a " + alt + "."
                b["h"] = cuerpo + cola

    # 7. cuadro de indicadores: biota truncada y fuente de la lluvia (D5)
    r = fila(bs, "Biota y estructura diagnóstica")
    if r:
        r[1] = BIOTA.get(c) or cortar_biota(r[1])
    r = fila(bs, "Entorno ambiental")
    if r and "WorldClim" not in r[1]:
        r[1] = re.sub(r"(lluvia anual mediana de [\d.]+ mm)", r"\1 (WorldClim 2.1)", r[1])
    for b in bs:
        if b["t"] == "p" and "La lluvia anual mediana es de" in b["h"] and "WorldClim" not in b["h"]:
            b["h"] = b["h"].replace("La lluvia anual mediana es de", "La lluvia anual mediana (WorldClim 2.1, 1970–2000) es de")
        if b["t"] == "tabla" and b["f"][0][0].startswith("Variable ambiental"):
            for f in b["f"]:
                if f[0] == "Precipitación media anual":
                    f[0] = "Precipitación media anual (WorldClim 2.1)"
                elif f[0] == "Variación estacional de la lluvia (CV)":
                    f[0] = "Variación estacional de la lluvia (CV, WorldClim 2.1)"
                if f[1] == "grados":
                    f[1] = "°"

    # 8. tabla de especies: filas, alcance, nombres comunes y cursivas
    te = tabla_especies(bs)
    if te:
        filas = [te["f"][0]]
        for f in te["f"][1:]:
            if any(c == k and f[1].startswith(sp) for k, sp in QUITAR_FILAS):
                continue
            filas.append(f)
        for nueva in NUEVAS_FILAS.get(c, []):
            if not any(re.sub(r"<[^>]+>", "", f[1]).startswith(nueva[1].split(" (")[0])
                       for f in filas if f[0].lower() != "dosel / sotobosque"):
                filas.insert(1, list(nueva))
        for f in filas[1:]:
            if f[0] == "dosel / sotobosque":
                f[0] = "Dosel / sotobosque"
            if f[2] == "especie registrada":
                f[2] = "Especie registrada"
            f[1] = re.sub(r"\(([^()]*)\)", comun_minusculas, f[1])
            f[1] = cursiva_especie(f[1])
            f[3] = re.sub(r"^([A-Z_]+)\b", lambda m: ALCANCE.get(m.group(1), m.group(1)), f[3])
        te["f"] = filas

    # 9. notas de decisión
    def insertar_tras(i, nota):
        if not tiene(bs, nota[:60]):
            bs.insert(i + 1, {"t": "nota", "h": nota})

    if c == 601:
        i = next(i for i, b in enumerate(bs) if b["t"] == "p" and "Asignación GET-UICN principal" in b["h"])
        insertar_tras(i, NOTA_601)
    if c in (8121, 8131):
        i = indice_h3(bs, 3)
        insertar_tras(i + 1, NOTA_REGIMEN.format(reg="estacional en 8121, seco en 8131"))
    if c in (6111, 615, 6151):
        i = indice_h3(bs, 2)
        insertar_tras(i + 1, NOTA_AGUA)

    return json.dumps(bs, ensure_ascii=False) != n0


def clases():
    p = DATA / "clases.json"
    c = json.loads(p.read_text(encoding="utf-8"))
    for g in c["grupos"]:
        g["nombre"] = GRUPOS[g["codigo"]]
    c["get"]["GET_L1"]["MFT"] = "Marino, dulceacuícola y terrestre"
    c["get"]["GET_L1"]["MULT"] = "Asignación múltiple"
    for x in c["clases"]:
        k = x["codigo"]
        if k in ALT_T13_CLASES and "T1.3" not in x["alt"]:
            x["alt"].append("T1.3")
            x["criterios_alt"] = (x["criterios_alt"] + " | " if x["criterios_alt"] else "") + ALT_T13
        if k == 635 and not any(e[0] == "M1.6" for e in x["efg"]):
            x["efg"].append(["M1.6", "Arrecifes rocosos submareales", False])
        if k == 629:
            x["criterio"] = x["criterio"].replace("; Control/GET_principal_evidencia_R26.json", "")
        if k == 2230:
            x["criterio"] = x["criterio"].replace(CRIT_2230_VIEJO, CRIT_2230)
    p.write_text(json.dumps(c, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def main():
    fs = sorted(glob.glob(str(FICHAS / "[0-9]*.json")), key=lambda x: int(os.path.basename(x)[:-5]))
    n = 0
    for f in fs:
        d = json.loads(Path(f).read_text(encoding="utf-8"))
        if procesar(d):
            n += 1
            Path(f).write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    clases()
    print(f"{n} fichas corregidas (v7); clases.json actualizado")
    # avisos: restos que el plan quería eliminar
    for f in fs:
        s = Path(f).read_text(encoding="utf-8")
        for pat in ["estival", "Control/", "NO adjudicar", "mantener alcance", "Superficies_ajustadas", "*"]:
            if pat in s:
                print("  aviso", os.path.basename(f), pat)


if __name__ == "__main__":
    main()
