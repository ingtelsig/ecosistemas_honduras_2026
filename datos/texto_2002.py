# -*- coding: utf-8 -*-
"""Descripciones del Mapa de Ecosistemas Vegetales de Honduras 2002 (Mejía Ordóñez y House 2002,
manual de consulta, sección VI) y su equivalencia con las clases del Mapa de Ecosistemas 2026.

- DESC: síntesis propia (parafraseada) de cada categoría UNESCO descrita en el manual de 2002.
- clave_2002(nombre, une): asigna cada ecosistema del vector 2002 a una de esas categorías.
- EQUIV: categorías 2002 conceptualmente equivalentes a cada clase 2026, con nota si no hay equivalente.
- coincidencia(codigo): coincidencia espacial (cruce 2026 × 2002 a 90 m, cruce_2026_2002.csv).
"""
import pathlib, re
import pandas as pd

CITA = "Mejía Ordóñez y House (2002)"
REF = ("Mejía Ordóñez, T. M. y House, P. (2002). <i>Mapa de Ecosistemas Vegetales de Honduras. "
       "Manual de consulta</i>. Proyecto de Administración de Áreas Rurales (PAAR), Tegucigalpa.")

# Título, códigos UNESCO, texto (síntesis). Las especies van en cursiva.
DESC = {
    "IA1a": ("Bosque tropical siempreverde latifoliado de tierras bajas", "IA1a(1)(a), IA1a(1)(b)",
             "Bosque lluvioso denso y cerrado de 30–40 m de altura del litoral atlántico, con lluvias de 2.000 a 2.500 mm, "
             "árboles con gambas y raíces tabulares, sotobosque poco denso con palmas (<i>Chamaedorea</i>, <i>Bactris</i>, "
             "<i>Geonoma</i>) y epífitas abundantes. Las variantes se separan por drenaje y suelo (bien drenado, moderadamente "
             "drenado y sobre suelos calcáreos). Especies frecuentes: <i>Vochysia hondurensis</i>, <i>Brosimum alicastrum</i>, "
             "<i>Calophyllum brasiliense</i>, <i>Symphonia globulifera</i>, <i>Terminalia amazonia</i>, <i>Virola koschnyi</i>, "
             "<i>Swietenia macrophylla</i> y <i>Cedrela odorata</i>."),
    "IA1f": ("Bosque tropical siempreverde latifoliado aluvial", "IA1f(1)",
             "Bosque sobre sedimentos aluviales a lo largo de ríos de llanuras y colinas suaves, húmedo todo el año y con suelos "
             "negros ricos en materia orgánica. Especies frecuentes: <i>Carapa guianensis</i>, <i>Dialium guianense</i>, "
             "<i>Pterocarpus rohrii</i>, <i>Prioria copaifera</i>, <i>Schizolobium parahyba</i> y <i>Symphonia globulifera</i>, "
             "con palmas de sotobosque como <i>Astrocaryum</i>, <i>Bactris</i> y <i>Reinhardtia</i>."),
    "IA1g": ("Bosque tropical siempreverde latifoliado pantanoso de tierras bajas", "IA1g(1/3)(b)",
             "Bosque permanentemente inundado de llanuras cercanas a desembocaduras, con <i>Pachira aquatica</i>, "
             "<i>Pterocarpus officinalis</i>, <i>Grias cauliflora</i> y palmas como <i>Roystonea</i>, <i>Acoelorrhaphe wrightii</i> "
             "y <i>Desmoncus orthacanthos</i>; hacia el lago de Yojoa es común <i>Erythrina fusca</i>."),
    "IA1b": ("Bosque tropical siempreverde latifoliado submontano", "IA1b(1)",
             "Bosque de 25–35 m con más de 2.000 mm de lluvia; incluye una variante sobre colinas cársticas escarpadas en la "
             "montaña de Santa Bárbara. Combina especies de tierras bajas (<i>Swietenia macrophylla</i>, <i>Vochysia</i>, "
             "<i>Licania platypus</i>) con elementos de altura como <i>Podocarpus</i>, <i>Hedyosmum mexicanum</i>, "
             "<i>Brunellia mexicana</i> y robles (<i>Quercus</i> spp.)."),
    "IA1c": ("Bosque tropical siempreverde latifoliado montano inferior", "IA1c(1)",
             "Bosque denso de 25–30 m, principalmente en la zona norte y en las colinas cársticas de Santa Bárbara, con lluvias de "
             "hasta 2.500 mm. Especies citadas: <i>Alchornea latifolia</i>, <i>Calophyllum brasiliense</i>, <i>Cyrilla racemiflora</i>, "
             "<i>Magnolia hondurensis</i>, <i>Ilex guianensis</i> y <i>Schefflera morototoni</i>."),
    "IA1d": ("Bosque tropical siempreverde latifoliado montano superior", "IA1d(1)",
             "Bosque nublado de 25–30 m representado por La Tigra, con suelos muy húmedos y gruesa hojarasca, rico en robles "
             "(<i>Quercus cortesii</i>, <i>Q. lancifolia</i>, <i>Q. bumelioides</i>), lauráceas, <i>Ilex</i>, <i>Oreopanax</i>, "
             "<i>Weinmannia</i>, <i>Magnolia hondurensis</i> y helechos arborescentes (<i>Cyathea</i>)."),
    "IA1e": ("Bosque tropical siempreverde latifoliado altimontano (nublado)", "IA1e(1)",
             "Bosque de los picos más altos, con árboles de hasta 40 m, más de 2.000 mm de lluvia y alta humedad casi todo el año. "
             "Reúne especies de altura como <i>Alnus</i>, <i>Abies guatemalensis</i>, <i>Taxus globosa</i>, <i>Podocarpus oleifolius</i>, "
             "<i>Weinmannia</i> y robles, con abundantes orquídeas, bromelias y helechos."),
    "IA1mix": ("Bosque tropical siempreverde mixto montano y altimontano", "IA1c(1/2), IA1d(1/2), IA1e(1/2)",
               "Bosque de latifoliadas con pinos intercalados (<i>Pinus oocarpa</i>, <i>P. maximinoi</i>, <i>P. pseudostrobus</i>, "
               "<i>P. tecunumanii</i>, <i>P. ayacahuite</i> y, en las cumbres, <i>P. hartwegii</i>), de hasta 40 m, en Agalta, Pico "
               "Bonito, Celaque y Santa Bárbara; el componente latifoliado incluye <i>Quercus</i>, <i>Liquidambar styraciflua</i>, "
               "<i>Clethra</i>, <i>Oreopanax</i> y <i>Arbutus xalapensis</i>."),
    "IA2a1": ("Bosque tropical siempreverde estacional latifoliado de tierras bajas", "IA2a(1)(a), IA2a(1)(b)",
              "Bosque mayormente siempreverde en el que varias especies pierden parte del follaje en la estación seca. Incluye "
              "variantes por drenaje y las colinas cársticas onduladas del suroeste de La Mosquitia, con árboles de hasta 35 m "
              "como <i>Swietenia macrophylla</i>, <i>Calophyllum brasiliense</i>, <i>Dialium guianense</i>, <i>Ceiba pentandra</i>, "
              "<i>Castilla elastica</i>, <i>Virola koschnyi</i> y <i>Vochysia</i>."),
    "IA2af": ("Bosque siempreverde estacional aluvial de galería (criques)", "IA2af(1)",
              "Bosques de galería de unos 15 m que bordean los ríos de los llanos de La Mosquitia, inundados en la estación lluviosa, "
              "con <i>Apeiba membranacea</i>, <i>Dendropanax arboreus</i>, <i>Xylopia frutescens</i>, <i>Vismia</i> y palmas de sotobosque."),
    "IA2g": ("Bosque siempreverde estacional pantanoso dominado por palmas", "IA2g",
             "Bosque anegado en la estación lluviosa del oriente de La Mosquitia (Caratasca, Ibans), con <i>Roystonea dunlapiana</i>, "
             "<i>Acoelorrhaphe wrightii</i>, <i>Pachira aquatica</i>, <i>Calophyllum brasiliense</i> y <i>Annona glabra</i>."),
    "IA2b1": ("Bosque tropical siempreverde estacional latifoliado submontano", "IA2b(1)",
              "Bosque de montañas escarpadas, sobre todo en la región de Montaña Entre Ríos, poco estudiado botánicamente; el "
              "manual cita como probables <i>Quercus</i>, <i>Podocarpus guatemalensis</i>, <i>Vochysia hondurensis</i>, "
              "<i>Licania platypus</i> y <i>Schizolobium parahyba</i>, y una variante en colinas cársticas de La Mosquitia."),
    "IA2cd1": ("Bosque tropical siempreverde estacional latifoliado montano", "IA2c(1), IA2d(1)",
               "Bosque montano mayormente siempreverde con algunas especies estacionales, en el borde de Montaña Entre Ríos y en "
               "parches del centro del país (25–30 m), con <i>Quercus cortesii</i>, <i>Carpinus caroliniana</i>, <i>Hedyosmum</i>, "
               "<i>Nectandra</i>, <i>Ilex</i> y <i>Oreopanax</i>."),
    "IA2mix_bajo": ("Bosque siempreverde estacional mixto de tierras bajas (variante <i>Pinus caribaea</i>)", "IA2a(1/2)(b)",
                    "Pinares de <i>Pinus caribaea</i> de 10–20 m mezclados con latifoliadas como <i>Byrsonima crassifolia</i>, "
                    "<i>Quercus oleoides</i>, <i>Miconia albicans</i> y <i>Davilla kunthii</i>, frecuentemente con agrupaciones de "
                    "la palma <i>Acoelorrhaphe wrightii</i> en La Mosquitia."),
    "IA2mix_alto": ("Bosque siempreverde estacional mixto submontano y montano", "IA2b(1/2), IA2c(1/2), IA2d(1/2)",
                    "Bosques de <i>Pinus oocarpa</i> (y en altura <i>P. maximinoi</i>, <i>P. tecunumanii</i> y <i>P. pseudostrobus</i>) "
                    "mezclados con robles (<i>Quercus sapotifolia</i>, <i>Q. peduncularis</i>, <i>Q. oleoides</i>), <i>Liquidambar "
                    "styraciflua</i>, <i>Arbutus xalapensis</i>, <i>Byrsonima crassifolia</i> y la palma <i>Brahea salvadorensis</i>, "
                    "en el centro, sur y occidente del país."),
    "IA2a2": ("Pinar de tierras bajas de <i>Pinus caribaea</i>", "IA2a(2)(a), IA2a(2)(b)",
              "Pinares de 20–25 m sobre planicies sedimentarias, dominados por <i>Pinus caribaea</i>, con <i>Byrsonima crassifolia</i>, "
              "<i>B. verbascifolia</i>, <i>Curatella americana</i>, robles y <i>Acoelorrhaphe wrightii</i>, y un estrato de gramíneas "
              "y del helecho <i>Pteridium aquilinum</i>."),
    "IA2b2": ("Pinar submontano", "IA2b(2)",
              "La mayor extensión de pinares del país (centro, oriente, occidente y sur), densos o ralos y a menudo intervenidos por "
              "ganadería, cultivos y extracción de madera. Domina <i>Pinus oocarpa</i> (con <i>P. caribaea</i> del lago de Yojoa al "
              "norte), acompañado de <i>Quercus</i>, <i>Byrsonima crassifolia</i>, <i>Brahea salvadorensis</i> y <i>Lysiloma auritum</i>."),
    "IA2c2": ("Pinar montano inferior", "IA2c(2)",
              "Pinares de <i>Pinus oocarpa</i>, <i>P. maximinoi</i> y <i>P. pseudostrobus</i>, puros o mezclados, densos o ralos según "
              "suelo e intervención; muy afectados por la extracción de árboles grandes y por los incendios, señalados como la "
              "principal amenaza de los pinares."),
    "IA3": ("Bosque semideciduo de tierras bajas (latifoliado y mixto)", "IA3a(1)(a), IA3a(1/2)(a)",
            "Bosque en el que la mayoría de los árboles del dosel pierden las hojas en la estación seca, sin estratos bien definidos, "
            "con ceibas y cortezas rugosas, epífitas raras y suculentas. La variante mixta combina latifoliadas (<i>Calycophyllum "
            "candidissimum</i>, <i>Enterolobium cyclocarpum</i>, <i>Lysiloma auritum</i>, <i>Simarouba glauca</i>, <i>Quercus "
            "sapotifolia</i>) con <i>Pinus caribaea</i>."),
    "IA3b": ("Bosque semideciduo submontano", "IA3b(1/2), IA3b(1), IA3c(1)",
             "Bosque semideciduo de laderas bajas con <i>Libidibia coriaria</i>, <i>Haematoxylum campechianum</i>, <i>Hymenaea "
             "courbaril</i>, <i>Prosopis juliflora</i> y <i>Quercus sapotifolia</i>."),
    "IA3palm": ("Bosque semideciduo con palmas y pantanoso de tierras bajas", "IA3a(3), IA3g(1)",
                "Bosques cercanos a las lagunas, costas y sabanas de La Mosquitia, inundados en lluvias y de suelo arenoso en "
                "secas, dominados por la palma tique (<i>Acoelorrhaphe wrightii</i>) con <i>Chrysobalanus icaco</i>, "
                "<i>Coccoloba uvifera</i>, <i>Annona glabra</i> y <i>Symphonia globulifera</i>."),
    "IA5a": ("Manglar del Caribe sobre sustrato limoso", "IA5a(1)",
             "Manglares de 5–30 m dominados por <i>Rhizophora mangle</i> y/o <i>Avicennia germinans</i>, con <i>Laguncularia "
             "racemosa</i> y <i>Conocarpus erectus</i>. En el Caribe forman parches poco densos y franjas estrechas en orillas de "
             "lagunas y desembocaduras, con <i>Rhizophora mangle</i> dominante y <i>Acrostichum aureum</i> asociado."),
    "IA5b": ("Manglar del Pacífico (golfo de Fonseca) sobre sustrato limoso", "IA5b(1)",
             "Manglares de 5–30 m dominados por <i>Rhizophora</i> y <i>Avicennia</i>, con <i>Laguncularia racemosa</i>, "
             "<i>Conocarpus erectus</i> y hierbas halófilas como <i>Sesuvium portulacastrum</i> y <i>Sporobolus virginicus</i>; "
             "el manual los separó de los caribeños por sus diferencias en imagen y en campo."),
    "IB1": ("Bosque tropical deciduo latifoliado de tierras bajas", "IB1a(1)",
            "Solo se cartografiaron seis parches en la zona sur, donde quedan islas muy pequeñas de este bosque. Casi todos los "
            "árboles pierden las hojas a la vez en la estación seca; hay troncos abombados, lianas ocasionales y un piso de "
            "gramíneas. Especies: <i>Enterolobium cyclocarpum</i>, <i>Bursera simaruba</i>, <i>Ceiba pentandra</i>, <i>Lysiloma</i>, "
            "<i>Swietenia humilis</i>, <i>Cochlospermum vitifolium</i> y <i>Calycophyllum candidissimum</i>."),
    "IIIB1": ("Arbustal deciduo de tierras bajas", "IIIB1a(1)(a), IIIB1a(4)(a)",
              "Arbustos y árboles pequeños esclerófilos, a menudo espinosos, con cactáceas (<i>Opuntia</i>, <i>Mammillaria</i>, "
              "<i>Pachycereus</i>) y gramíneas; la variante latifoliada incluye <i>Crescentia alata</i>, <i>Acacia pennatula</i>, "
              "<i>Prosopis juliflora</i> y <i>Mimosa tenuiflora</i>. Se cartografió como pequeñas islas."),
    "VC": ("Sabanas de graminoides (VA1, VC1, VC2)", "VA1, VC1, VC2",
           "Herbazales sobre todo de La Mosquitia, diferenciados por el tipo de gramíneas, los árboles presentes y el drenaje "
           "(anegados, inundables o pantanosos). Son comunes ciperáceas (<i>Rhynchospora</i>, <i>Scleria</i>), plantas insectívoras "
           "(<i>Drosera</i>, <i>Utricularia</i>), islotes de tique (<i>Acoelorrhaphe wrightii</i>), <i>Curatella americana</i>, "
           "<i>Byrsonima verbascifolia</i> y, en las sabanas arboladas, <i>Pinus caribaea</i> de hasta 25 m."),
    "VD1": ("Pantano de ciperáceas altas", "VD1a(1)",
            "Pantanos de hierbas de hasta 50 cm dominados por ciperáceas y gramíneas, con <i>Typha domingensis</i>, <i>Phragmites "
            "australis</i> o <i>Thalia geniculata</i> en orillas de ríos y lagunas; muchos alterados por ganadería y drenaje."),
    "VE1": ("Marisma salobre pobre en suculentas", "VE1a(2)",
            "Vegetación baja (menos de 15 cm) con influencia marina, con <i>Sesuvium portulacastrum</i>, <i>Sporobolus</i>, "
            "arbustos de <i>Avicennia germinans</i> y <i>Acrostichum aureum</i> en los bordes; el manual advierte que la información "
            "florística era muy escasa."),
    "VIB": ("Vegetación tropical costera (dunas, playas, suelos recientes y albinas)", "VIB1, VIB3, VIB4, VIB5",
            "Vegetación pionera de la costa norte e Islas de la Bahía con <i>Canavalia rosea</i>, <i>Ipomoea pes-caprae</i>, "
            "<i>Sesuvium portulacastrum</i> y <i>Sporobolus virginicus</i>, y hacia el interior <i>Chrysobalanus icaco</i>, "
            "<i>Coccoloba uvifera</i> e <i>Hibiscus tiliaceus</i>; incluye bancos arenosos y albinas salinas de suelo blanco."),
    "VII": ("Carrizal pantanoso de agua dulce", "VIIB1a",
            "Carrizales de orillas de lagunas de agua dulce y del lago de Yojoa, con <i>Typha domingensis</i>, <i>Phragmites "
            "australis</i> y <i>Thalia geniculata</i>."),
    "SA": ("Sistemas acuáticos (lagos, lagunas y estuarios)", "SA1",
           "Lagos, lagunas costeras y estuarios del Caribe y del Pacífico. El mapa de 2002 los incluyó solo como parte de la "
           "geografía, sin describirlos como ecosistemas, porque no se habían estudiado los sistemas acuáticos."),
    "SPA": ("Sistemas agropecuarios", "SPA",
            "Cultivos intensivos o permanentes y ganadería representados como un solo polígono, con remanentes de especies nativas "
            "en bordes y parches que muestran la fragmentación del bosque original."),
    "SPC1": ("Acuacultura, camaroneras y salineras", "SPC1",
             "Estanques de camarón y salineras, registrados solo en la zona sur."),
    "U1": ("Área urbana", "U1", "Polígonos de las ciudades más grandes del país."),
    "ARR": ("Arrecife coralino del Caribe", "—",
            "Polígonos de arrecife coralino incluidos en la capa digital de 2002 como referencia geográfica; el manual no los describe como ecosistema."),
    "RIO": ("Río de cuenca inferior del Caribe", "—",
            "Tramos anchos de los ríos de la cuenca baja del Caribe incluidos en la capa digital de 2002 como referencia geográfica, sin descripción en el manual."),
}


def clave_2002(nombre, une):
    """Asigna un ecosistema del vector 2002 a una categoría descrita en el manual."""
    n = (nombre or "").lower()
    u = (une or "").replace(" ", "")
    if n.startswith("arrecife"): return "ARR"
    if n.startswith("río") or n.startswith("rio"): return "RIO"
    if u.startswith("SPA"): return "SPA"
    if u.startswith("SPC"): return "SPC1"
    if u.startswith("U1"): return "U1"
    if u.startswith("SA"): return "SA"
    if u.startswith("VII"): return "VII"
    if u.startswith("VIB"): return "VIB"
    if u.startswith("VE"): return "VE1"
    if u.startswith("VD"): return "VD1"
    if u.startswith("VA") or u.startswith("VC"): return "VC"
    if u.startswith("III"): return "IIIB1"
    if u.startswith("IB1"): return "IB1"
    if u.startswith("IA5a"): return "IA5a"
    if u.startswith("IA5b"): return "IA5b"
    if u.startswith("IA3"):
        if "palma" in n or "pantanoso" in n: return "IA3palm"
        if u.startswith("IA3a"): return "IA3"
        return "IA3b"
    if u.startswith("IA1") and "estacional" not in n:
        if u.startswith("IA1f"): return "IA1f"
        if u.startswith("IA1g"): return "IA1g"
        if "mixto" in n: return "IA1mix"
        if u.startswith("IA1a"): return "IA1a"
        if u.startswith("IA1b"): return "IA1b"
        if u.startswith("IA1c"): return "IA1c"
        if u.startswith("IA1d"): return "IA1d"
        if u.startswith("IA1e"): return "IA1e"
    if u.startswith("IA2") or "estacional" in n:
        if "galer" in n: return "IA2af"
        if "pantanoso" in n: return "IA2g"
        if "mixto" in n:
            return "IA2mix_bajo" if "tierras bajas" in n else "IA2mix_alto"
        if "aciculifoliado" in n:
            if "tierras bajas" in n: return "IA2a2"
            if "submontano" in n: return "IA2b2"
            return "IA2c2"
        if "montano" in n and "submontano" not in n: return "IA2cd1"
        if "submontano" in n: return "IA2b1"
        return "IA2a1"
    return None


def _g(*k):
    return list(k)


NOTA_SIN = {
    "marino": "El mapa de 2002 cubría la vegetación terrestre y costera y no describió ecosistemas marinos, por lo que esta unidad no tiene equivalente en él.",
    "rio": "El mapa de 2002 no describió los ríos como ecosistemas; solo su capa digital incluye, como referencia geográfica, los tramos anchos de la cuenca baja del Caribe.",
    "arbustal": "El mapa de 2002 solo describió arbustales deciduos (IIIB1); los arbustales húmedos y estacionales de 2026 corresponden en 2002 a bosques, sabanas o sistemas agropecuarios según el sitio.",
    "cafe": "El mapa de 2002 incluyó los cafetales dentro de los sistemas agropecuarios (SPA) sin separarlos.",
    "pasto": "El mapa de 2002 incluyó pastizales y cultivos en un único sistema agropecuario (SPA).",
    "artificial": "El mapa de 2002 no tenía una clase equivalente; estas superficies quedaban dentro de las unidades vecinas.",
    "seco_montano": "El mapa de 2002 no reconoció bosques secos montanos: la única formación decidua (IB1) se cartografió en seis parches de tierras bajas del sur. La equivalencia es solo fisonómica.",
    "arrecife": "El manual de 2002 no describió ecosistemas marinos; su capa digital solo incluía polígonos de arrecife coralino como referencia geográfica.",
    "abierto": "El mapa de 2002 no tenía una clase de bosque latifoliado abierto o perturbado; la mayor parte de esta superficie estaba en el sistema agropecuario.",
}

EQUIV = {}
for c in (1112,): EQUIV[c] = (_g("IA1a", "IA1f", "IA1g"), None)
for c in (1113, 1114): EQUIV[c] = (_g("IA1a"), None)
for c in (1122, 1123, 1124): EQUIV[c] = (_g("IA1b"), None)
for c in (1132, 1133, 1134): EQUIV[c] = (_g("IA1c", "IA1d", "IA1e"), None)
EQUIV[1212] = (_g("IA2a1", "IA2af", "IA2g", "IA3", "IA3palm"), None)
for c in (1213, 1214): EQUIV[c] = (_g("IA2a1", "IA3"), None)
for c in (1222, 1223, 1224): EQUIV[c] = (_g("IA2b1", "IA3b"), None)
for c in (1232, 1233, 1234): EQUIV[c] = (_g("IA2cd1", "IA3b"), None)
for c in (1312, 1313, 1314): EQUIV[c] = (_g("IB1", "IA3"), None)
for c in (1322, 1323, 1324): EQUIV[c] = (_g("IB1", "IA3b"), None)
for c in (1332, 1333, 1334): EQUIV[c] = (_g("IB1", "IA3b"), "seco_montano")
EQUIV[2110] = (_g("IA2a2", "VC"), None)
EQUIV[2120] = (_g("IA2b2"), None)
EQUIV[2130] = (_g("IA2c2", "IA1mix"), None)
EQUIV[2210] = (_g("IA2a2", "IA2b2"), None)
EQUIV[2220] = (_g("IA2b2"), None)
EQUIV[2230] = (_g("IA2c2"), None)
EQUIV[3110] = (_g("IA2mix_bajo", "IA3"), None)
EQUIV[3210] = (_g("IA2mix_bajo", "IA3"), None)
EQUIV[3120] = (_g("IA2mix_alto", "IA1mix"), None)
EQUIV[3130] = (_g("IA1mix"), None)
EQUIV[3220] = (_g("IA2mix_alto", "IA3b"), None)
EQUIV[3230] = (_g("IA2mix_alto"), None)
for c in (4012, 4013, 4014, 4022, 4023, 4024): EQUIV[c] = ([], "arbustal")
for c in (4032, 4033, 4034): EQUIV[c] = (_g("IIIB1"), None)
EQUIV[601] = (_g("VC", "IA2b2", "IA2c2"), None)
EQUIV[602] = (_g("IA2b2", "VC"), None)
EQUIV[603] = (_g("VC"), None)
EQUIV[604] = (_g("IIIB1"), None)
EQUIV[610] = (_g("VD1", "IA1g", "IA2g", "VC"), None)
EQUIV[630] = (_g("VC", "VD1"), None)
EQUIV[614] = (_g("SPA", "VD1"), None)
EQUIV[615] = (_g("SA"), None)
EQUIV[6151] = (_g("SA", "IA5a", "IA5b"), None)
for c in (617, 618, 634, 635, 6165, 6173, 16201, 16202, 16203, 16204): EQUIV[c] = ([], "marino")
EQUIV[616] = (_g("ARR"), None)  # v7: sin la nota genérica marina, que lo contradecía
EQUIV[634] = ([], "arrecife")  # v7: coincide en parte con los polígonos de arrecife de 2002
EQUIV[624] = (_g("SPC1"), None)
EQUIV[625] = ([], "artificial")
EQUIV[629] = ([], "abierto")
for c in (631, 636, 9101, 9102): EQUIV[c] = (_g("VIB"), None)
for c in (6061, 6062, 6063, 6064, 6065): EQUIV[c] = (_g("RIO"), "rio")
EQUIV[6111] = (_g("SA", "VII"), None)
EQUIV[6112] = (_g("SA", "VII"), None)
EQUIV[6113] = (_g("SA", "VC", "VD1"), None)
EQUIV[7201] = (_g("SA"), None)  # v7: el 68,6 % coincide con sistemas acuáticos (SA1)
EQUIV[6202] = (_g("VE1", "VIB"), None)
EQUIV[6205] = (_g("VIB", "IA1g"), None)
for c in (6261, 6271): EQUIV[c] = (_g("IA5a"), None)
for c in (6262, 6272): EQUIV[c] = (_g("IA5b"), None)
for c in (8111, 8112, 8113, 8121, 8122, 8123, 8131, 8132, 8133): EQUIV[c] = (_g("SPA"), "cafe")
for c in (8212, 8213, 8214, 8222, 8223, 8224, 8232, 8233, 8234): EQUIV[c] = (_g("SPA"), "pasto")
for c in (8301, 8302, 8303, 8305, 8306): EQUIV[c] = (_g("SPA"), None)
EQUIV[9001] = (_g("VIB"), "artificial")
EQUIV[10001] = (_g("U1"), None)

_CRUCE = None


def _cruce():
    global _CRUCE
    if _CRUCE is None:
        f = pathlib.Path(__file__).resolve().parents[2] / "Revision_informe_v6" / "cruce_2026_2002.csv"
        d = pd.read_csv(f)
        d["clave"] = [clave_2002(n, u) if n != "(fuera del mapa 2002)" else None
                      for n, u in zip(d["ecosistema_2002"], d["une_2002"].fillna(""))]
        _CRUCE = d
    return _CRUCE


def coincidencia(codigo):
    """Porcentajes de la superficie 2026 de la clase según categoría 2002."""
    d = _cruce()
    s = d[d["codigo_2026"] == int(codigo)]
    if s.empty:
        return None
    tot = s["ha"].sum()
    por = (s.groupby("clave", dropna=False)["ha"].sum() / tot * 100).sort_values(ascending=False)
    fuera = float(s.loc[s["ecosistema_2002"] == "(fuera del mapa 2002)", "ha"].sum() / tot * 100)
    eq = EQUIV.get(int(codigo), ([], None))[0]
    pe = float(sum(por.get(k, 0) for k in eq))
    return {"total_ha": float(tot), "por_clave": por, "pct_equiv": pe, "pct_fuera": fuera,
            "pct_spa": float(por.get("SPA", 0))}


def fmt(x, dec=1):
    s = f"{x:,.{dec}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def _nom(k):
    t = DESC[k][0]
    return t[0].lower() + t[1:]


def frase_coincidencia(codigo):
    c = coincidencia(codigo)
    eq, nota = EQUIV.get(int(codigo), ([], None))
    if c is None:
        return ""
    if c["pct_fuera"] > 95:
        if [k for k in eq if k != "SPA"] and c["pct_equiv"] >= 0.5:
            return (f"El {fmt(c['pct_equiv'])} % de su superficie de 2026 coincide con esas categorías de 2002; el resto "
                    "queda fuera de la extensión del mapa de 2002, que no abarcaba el ámbito marino.")
        return "Su superficie queda fuera de la extensión del mapa de 2002, que no abarcaba el ámbito marino."
    frases = []
    natural_eq = [k for k in eq if k != "SPA"]
    if natural_eq:
        pe = c["pct_equiv"]
        if pe < 0.5:
            frases.append("Prácticamente ninguna parte de su superficie de 2026 coincide con esas categorías de 2002")
        else:
            frases.append(f"El {fmt(pe)} % de su superficie de 2026 coincide con esas categorías de 2002")
    if "SPA" in eq:
        frases.append(f"El {fmt(c['pct_spa'])} % de su superficie de 2026 estaba en 2002 dentro del sistema agropecuario, que no separaba cultivos, pastos ni cafetales")
    elif c["pct_spa"] >= 5:
        frases.append(f"el {fmt(c['pct_spa'])} % estaba cartografiado como sistema agropecuario")
    otros = [(k, v) for k, v in c["por_clave"].items()
             if isinstance(k, str) and k not in eq and k != "SPA" and v >= 5][:2]
    if otros and not frases:  # v7: sin categoría equivalente, la frase no puede empezar por «el resto»
        frases.append("su superficie coincide sobre todo con " + " y ".join(f"{_nom(k)} ({fmt(v)} %)" for k, v in otros))
        if c["pct_fuera"] >= 5:
            frases.append(f"el {fmt(c['pct_fuera'])} % queda fuera de la extensión del mapa de 2002")
    elif otros:
        frases.append("el resto coincide sobre todo con " + " y ".join(f"{_nom(k)} ({fmt(v)} %)" for k, v in otros))
    if not frases:
        return ""
    t = frases[0][0].upper() + frases[0][1:]
    if len(frases) == 2:
        t += ("; " if "cafetales" in frases[0] else " y ") + frases[1]
    elif len(frases) == 3:
        t += "; " + frases[1] + " y " + frases[2]
    return t + "."


CAUTELA = ("La coincidencia espacial se calculó cruzando ambos mapas en una malla de 90 m. Las diferencias combinan cambios "
           "de leyenda, de fuentes y de escala con cambios reales de cobertura, por lo que no deben leerse como transformación "
           "o pérdida de ecosistemas.")
