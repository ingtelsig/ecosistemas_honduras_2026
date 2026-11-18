"""Aplica la revisión técnica de las fichas (Miguel Mendieta, noviembre 2026) a public/data/fichas/*.json.

Se ejecuta después de 03_fichas.py. Hace dos cosas:
1. Correcciones de texto: nombres de lugares (PN Blanca Jeannette Kawas Fernández, Laguna de Guaimoreto, Kruta,
   Guanchias), km², «siempreverde», nombres comunes y especies mal asignadas (Quercus acuta, Alchornea latifolia,
   suyate), términos de redacción («subsidio», «potreros secos») y paréntesis sin cerrar.
2. Un bloque «Aportes de la revisión técnica» por unidad, antes de las referencias, con las especies, localidades y
   precisiones que propone el revisor. Se presentan como aportes del revisor, no como resultados del mapa.

Las observaciones de maquetación del catálogo en Word (numerar cuadros, ancho de tablas) no aplican al visor.
Es idempotente: se puede ejecutar varias veces.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

FICHAS = Path(__file__).resolve().parent.parent / "public" / "data" / "fichas"
TITULO = "Aportes de la revisión técnica"
FUENTE = ("Observaciones del revisor técnico Miguel Mendieta (noviembre 2026) al catálogo ecológico. Complementan la ficha "
          "con especies, nombres comunes y localidades conocidas en campo; no forman parte de los cálculos del mapa.")

# ------------------------------------------------------------------ 1. correcciones de texto (todas las fichas)
REGLAS: list[tuple[str, str]] = [
    (r"Blanca Jan[eé]th Kawas", "Blanca Jeannette Kawas"),
    (r"Guaymoreto", "Guaimoreto"),
    (r"\bCruta\b", "Kruta"),
    (r"\bCanchias\b", "Guanchias"),
    (r"\bkm2\b", "km²"),
    (r"\b([Ss])iempre [Vv]erde\b", r"\1iempreverde"),
    (r"mapa de ecosistemas de honduras", "Mapa de Ecosistemas de Honduras"),
    # nombres comunes y especies
    (r"Alchornea latifolia \(Canelillo / tambor\)", "Alchornea latifolia (Cuajada / tapa tamal)"),
    (r"Sabal mexicana \(Palma real / suyate\)", "Sabal mexicana (Palma real)"),
    (r"<i>Quercus acuta</i>", "<i>Quercus</i> sp. (registrada en el IFN como <i>Q. acuta</i>)"),
    (r"Quercus acuta \(ROBLE\)", "Quercus sp. (ROBLE; registrada en el IFN como Q. acuta)"),
    # redacción
    (r"el subsidio abundante de lluvias pluviales", "la precipitación abundante"),
    (r"\bsubsidio(s?)\b", r"aporte\1"),
    (r"invadidas por potreros secos", "ocupadas por pastos naturales o cultivados"),
    (r"potreros secos", "pastos naturales o cultivados"),
    (r"Lysiloma auritum \(quebracho\.", "Lysiloma auritum (quebracho)."),
    (r"\(característica de El Picacho\.", "(característica de El Picacho)."),
]

NOTA_ESPECIE = {
    1224: ("<b>Nota de la revisión técnica.</b> <i>Quercus acuta</i> es una especie de Asia oriental (Japón, Corea, Taiwán "
           "y sur de China) sin registros en Honduras; el nombre proviene de la base de subparcelas del IFN y debe "
           "verificarse. Según el revisor, posiblemente corresponde a otro roble de altura registrado en Uyuca, La Tigra, "
           "San Matías, Zambrano y Amarateca. Los «robles blancos o barcinos» de estas laderas probablemente son "
           "<i>Q. peduncularis</i>, <i>Q. polymorpha</i>, <i>Q. oocarpa</i> o <i>Q. copeyensis</i> (700–2.000 msnm)."),
    1322: ("<b>Nota de la revisión técnica.</b> <i>Quercus acuta</i> es una especie de Asia oriental sin registros en "
           "Honduras; el nombre proviene de la base de subparcelas del IFN y debe verificarse. En el pinar-robledal de "
           "<i>Pinus oocarpa</i> (700–1.800 msnm) se documentan <i>Q. sapotifolia</i>, <i>Q. acutifolia</i>, "
           "<i>Q. conspersa</i>, <i>Q. crassifolia</i>, <i>Q. elliptica</i> y <i>Q. rugosa</i>; en tierras bajas, "
           "<i>Albizia saman</i> convive con <i>Q. oleoides</i>, <i>Q. segoviensis</i> y <i>Q. sapotifolia</i>."),
    1223: ("<b>Nota de la revisión técnica.</b> <i>Quercus insignis</i> se sitúa en Honduras por encima de los 1.300 msnm "
           "(1.350–2.500 msnm); su presencia en este piso submontano debe revisarse. Los robles y encinos más frecuentes "
           "a estas altitudes son <i>Q. oleoides</i>, <i>Q. peduncularis</i>, <i>Q. sapotifolia</i>, <i>Q. elliptica</i> "
           "y <i>Q. segoviensis</i> (El Paraíso)."),
    1312: ("<b>Nota de la revisión técnica.</b> <i>Sabal mexicana</i> (palma real) se distribuye de México a El Salvador y "
           "se observa en el sur de La Paz (Santa Elena, Yarula, Opatoro, Marcala, Cabañas). La palma llamada «suyate» de "
           "Talanga, Montaña de La Flor, Marale, Cedros y Orica (Francisco Morazán), de las montañas de Olancho y de los "
           "valles del Guayape, Guayambre, Jamastrán y Minas de Oro es <i>Brahea dulcis</i>."),
}

# ------------------------------------------------------------------ 2. aportes por unidad
_ARRECIFE = [
    "Suelos de los bordes costeros de los valles de Sula y Aguán: además de la serie Jacaleapa, en la costa norte se "
    "registran las series Cocona, Tomalá, Toyos y Yaruca, suelos rojizos arcillosos (mapas FAO y Simmons y Castellanos).",
    "Considerar también la bahía de Trujillo en la estructura del sistema y, entre las cuencas prioritarias, las de los "
    "ríos Sico o Tinto, Plátano, Patuca y Coco.",
]
_MANGLAR_CARIBE = [
    "Además de las especies descritas, son frecuentes <i>Chrysobalanus icaco</i>, <i>Bactris major</i>, "
    "<i>Roystonea dunlapiana</i>, <i>Attalea cohune</i> y <i>Cocos nucifera</i> (Punta Izopo, Cuero y Salado, La Lagarta, "
    "Boca Vieja, Laguna de Cacao, Bajos de Balfate, Laguna de Guaimoreto y sistemas lagunares de La Mosquitia).",
]
_MANGLAR_PACIFICO = ["También es muy frecuente <i>Sesuvium portulacastrum</i> (hierba barrilla)."]
_HUMEDAL_COLON = [
    "Considerar los humedales costeros de Colón y Atlántida: desembocadura del río Aguán, Laguna de Guaimoreto, Bajos de "
    "Balfate, Boca Vieja del río Cangrejal, Laguna de Cacao, La Lagarta, Cuero y Salado, Zambuco, Bajos de Hicaque, "
    "desembocadura del río Leán, Punta Izopo, Laguna de Los Micos y desembocaduras de los ríos Ulúa y Chamelecón.",
    "Kruta es una aldea en las riberas del río Patuca, cerca de su desembocadura; la subcuenca se cita como Kruta Baja.",
]
_LAURACEAS = (
    "Otras lauráceas asociadas a <i>Persea americana</i> var. <i>nubigena</i>, registradas en Pico Pijol, Pico Bonito, "
    "Montaña de Yoro, Cusuco, Montserrat, La Muralla, Agalta, Montecillos, Montaña Verde, Puca, Erapuca, Mixcure, Opalaca, "
    "Cerro Azul Meámbar, Cerro Azul Copán y Montaña de Santa Bárbara: <i>Persea caerulea</i>, <i>P. schiediana</i>, "
    "<i>Ocotea helicterifolia</i>, <i>O. whitei</i>, <i>O. sinuata</i>, <i>O. rivularis</i>, <i>O. meziana</i>, "
    "<i>Damburneya coriacea</i>, <i>Nectandra martinicensis</i>, <i>N. salicifolia</i>, <i>N. gentlei</i> y "
    "<i>Phoebe longicaudata</i>. Son importantes en la dieta de aves (quetzal, coas, pavas), mamíferos (guatusa, "
    "tepezcuintle, pizote, conejos) y murciélagos."
)
_AGUACATE = ("El aguacate de montaña (aguacate anís) de los pisos submontano a montano y de los valles intermontanos de "
             "altura es <i>Persea americana</i> var. <i>nubigena</i>; también se encuentra <i>P. americana</i> var. "
             "<i>drymifolia</i>.")
_ROBLES_MONTANO = (
    "Robles y encinos de estos pisos: <i>Quercus sapotifolia</i> (bosques húmedos y nubosos), <i>Q. cortesii</i> "
    "(Celaque, El Pital, El Volcán, Guajiquiro, Puca), <i>Q. segoviensis</i> (transición pino-roble-encino: La Botija, "
    "Montserrat, Dipilto), <i>Q. lancifolia</i> (Uyuca, Cantagallo, La Tigra, El Chile, Corralitos), <i>Q. laurina</i> "
    "(La Tigra, Uyuca, El Chile, Corralitos, El Armado, La Muralla, Agalta), <i>Q. bumelioides</i> (La Tigra, Montserrat, "
    "Montecillos) y <i>Q. rugosa</i> (Guajiquiro, El Jilguero, Yerbabuena)."
)
_NECTANDRA = (
    "Especies de <i>Nectandra</i> del bosque submontano (400–1.200 msnm) en la Cordillera Nombre de Dios: "
    "<i>N. gentlei</i> (aguacatillo de montaña, jigua; río Cangrejal, río Yaruca, PN Pico Bonito, RVS Texiguat, La Muralla), "
    "<i>N. hihua</i> (tierras bajas y premontano), <i>N. nitida</i>, <i>N. reticulata</i>, <i>N. salicifolia</i> y "
    "<i>N. martinicensis</i> (pisos premontano y montano)."
)
_QUERCUS_1222 = ("Robles a precisar en estas altitudes: <i>Quercus oleoides</i>, <i>Q. peduncularis</i>, "
                 "<i>Q. sapotifolia</i>, <i>Q. elliptica</i>, <i>Q. conspersa</i>, <i>Q. cortesii</i>, "
                 "<i>Q. lancifolia</i> y <i>Q. skinneri</i>.")
_ROBLES_1232 = (
    "Robles de estos pisos: <i>Quercus corrugata</i> (Celaque, 1.600–2.800 msnm), <i>Q. skinneri</i> (1.000–2.400 msnm, "
    "bosques húmedos y nubosos maduros), <i>Q. peduncularis</i> (pino-roble-encino, 1.000–2.800 msnm), "
    "<i>Q. sapotifolia</i> (1.500–2.800 msnm) y <i>Q. benthamii</i>, el más notorio de los bosques nublados; también "
    "<i>Q. cortesii</i>, <i>Q. bumelioides</i>, <i>Q. lancifolia</i>, <i>Q. laurina</i> y <i>Q. segoviensis</i> "
    "(Sierra de Dipilto, Trojes)."
)
_ILEX_1232 = (
    "<i>Ilex</i> del subdosel: <i>I. hondurensis</i> y <i>I. discolor</i> (bosques húmedos de montaña), <i>I. pallida</i> "
    "(bosques montanos y nubosos sobre 700 msnm), <i>I. williamsii</i> (rara, de bosques nubosos) e <i>I. guianensis</i> "
    "(acompañante en bosques de altura). Fauna asociada: tucancillo verde (<i>Aulacorhynchus prasinus</i>)."
)
_SECO_PIONERAS = (
    "Especies pioneras de este bosque seco: <i>Acacia pennatula</i> (chaperno), <i>Byrsonima crassifolia</i> (nance), "
    "<i>Acacia deamii</i> (biscuite), <i>Albizia adinocephala</i> (chaperno blanco, gavilán), <i>Bursera simaruba</i> "
    "(indio desnudo), <i>Ceiba pentandra</i>, <i>Pithecellobium dulce</i> (guamúchil, pico de zope), "
    "<i>Acacia picachensis</i> (espino blanco), <i>Cecropia peltata</i> y <i>C. obtusifolia</i> (guarumo), "
    "<i>Lonchocarpus</i> spp. (chapernos: <i>L. rugosus</i>, <i>L. yoroensis</i>, <i>L. minimiflorus</i>, "
    "<i>L. phlebophyllus</i>, entre otros), <i>Lysiloma divaricatum</i> y <i>L. acapulcense</i> (quebracho), "
    "<i>Luehea candida</i> (guácimo blanco), <i>L. seemannii</i> (caulote), <i>Zanthoxylum fagara</i> (uña de gato), "
    "<i>Heliocarpus</i> sp. (majagua, masicarán) y <i>Guazuma ulmifolia</i> (guácimo)."
)
_QUERCUS_SECO_MONTANO = (
    "Las especies de <i>Quercus</i> de Honduras no toleran suelos permanentemente encharcados o pantanosos: en suelos con "
    "mal drenaje temporal o arcillas de tierras altas los robles se limitan a crestas o micrositios con mejor escorrentía, "
    "o son desplazados por vegetación de humedad extrema."
)

APORTES: dict[int, list[str]] = {
    616: [*_ARRECIFE, "<i>Lutjanus mahogoni</i> (pargo ojón)."],
    617: _ARRECIFE,
    618: _ARRECIFE,
    634: [*_ARRECIFE, "Localidades de referencia: Punta Sal y bahía de Tela."],
    6165: ["Considerar los bancos de Coralia en la isla de Roatán, uno de los bancos mejor documentados."],
    631: ["Entre 1985 y 2011 las camaroneras ocuparon antiguas albinas (lagunas albinas) del Golfo de Fonseca.",
          "Tortugas marinas del litoral: baula o laúd (<i>Dermochelys coriacea</i>), registrada en Plaplaya (Gracias a "
          "Dios), y verde o peje blanco (<i>Chelonia mydas</i>), frecuente en los arrecifes de Roatán y Guanaja."],
    636: ["Aves de costas rocosas en Islas del Cisne y cayos del Caribe: <i>Sula leucogaster</i>, <i>S. sula</i>, "
          "<i>Fregata magnificens</i>, <i>Leucophaeus atricilla</i> y <i>Nannopterum brasilianum</i>; además "
          "Scolopacidae y Charadriidae en ambas costas (Isla de los Pájaros, Punta Condega, Punta Ratón, Isla del Tigre, "
          "Amapala y sus islotes en el Golfo de Fonseca)."],
    9101: ["Especies de playa: lirio de mar (<i>Hymenocallis littoralis</i>) y verdolaga de playa "
           "(<i>Sesuvium portulacastrum</i>).",
           "En el litoral arenoso caribeño son frecuentes coco (<i>Cocos nucifera</i>), corozo (<i>Attalea cohune</i>), "
           "tique (<i>Acoelorraphe wrightii</i>), majagua (<i>Hibiscus tiliaceus</i>), jobo (<i>Spondias mombin</i>), "
           "nance (<i>Byrsonima crassifolia</i>), marañón (<i>Anacardium occidentale</i>) y mango (<i>Mangifera indica</i>).",
           "Tortugas marinas: baula o laúd (<i>Dermochelys coriacea</i>), registrada en Plaplaya (Gracias a Dios), y verde "
           "o peje blanco (<i>Chelonia mydas</i>)."],
    9102: ["Composición florística: también <i>Sesuvium portulacastrum</i>, <i>Uniola paniculata</i>, <i>Spartina</i> spp., "
           "<i>Conocarpus erectus</i>, <i>Opuntia</i> spp. y <i>Melocactus curvispinus</i> (cactus playeros y pitahayas)."],
    6261: _MANGLAR_CARIBE,
    6271: _MANGLAR_CARIBE,
    6262: _MANGLAR_PACIFICO,
    6272: _MANGLAR_PACIFICO,
    615: [*_HUMEDAL_COLON,
          "Composición florística en Laguna de Cacao, Bajos de Balfate y Bajos de Hicaque: <i>Pistia stratiotes</i>, "
          "<i>Eichhornia crassipes</i> y <i>Gynerium sagittatum</i>."],
    6151: ["En esteros y canales de marea son frecuentes y abundantes <i>Pterocarpus officinalis</i>, <i>Crudia cauliflora</i>, "
           "<i>Roystonea dunlapiana</i>, <i>Annona glabra</i>, <i>Bactris guineensis</i>, <i>Astrocaryum standleyanum</i>, "
           "<i>A. mexicanum</i>, <i>Gynerium sagittatum</i> y <i>Hibiscus elatus</i> (Bajos de Hicaque, Cuero y Salado, "
           "Bajos de Balfate, Laguna de Guaimoreto)."],
    6202: ["También pastos de <i>Spartina alterniflora</i>, <i>Typha domingensis</i>, <i>Pistia stratiotes</i> y "
           "<i>Eichhornia crassipes</i>."],
    6205: _HUMEDAL_COLON,
    1112: ["Nombres comunes: <i>Virola koschnyi</i> (sangre real), <i>Vochysia guatemalensis</i> (San Juan de pozo, San Juan "
           "peludo), <i>Pterocarpus officinalis</i> (sangre), <i>Bactris guineensis</i> (biscoyol), <i>Pachira aquatica</i> "
           "(zapotón), <i>Pinus caribaea</i> var. <i>hondurensis</i> (pino caribeño, costanero u hondureño).",
           "<i>Carapa guianensis</i> se ha encontrado hasta en Colón; rara vez se registra en Atlántida."],
    1113: ["En esta unidad hay registros de inventarios forestales con <i>Carapa guianensis</i> (cedro macho, caobilla, «swa» "
           "en miskito) y <i>Terminalia amazonia</i> (guayabón). <i>Henriettea succosa</i> (Melastomataceae) se conoce "
           "como manzanillo, capirote o cirín.",
           "Zorra o tambor es <i>Schizolobium parahyba</i>. Evaluar la regeneración de corozo (<i>Attalea cohune</i>) "
           "también en Colón, y los rodales insulares de Cayos Cochinos e Islas del Cisne."],
    1114: ["Biota indicadora: <i>Virola koschnyi</i>, <i>Hieronyma alchorneoides</i> y <i>Vochysia ferruginea</i>. "
           "Suelos Toyos, muy abundantes en Atlántida, Colón y Yoro.",
           "Nombres comunes: <i>Brosimum alicastrum</i> (masica, ramón, ojoche), <i>Dialium guianense</i> (paleto, tamarindo "
           "de montaña), <i>Vochysia guatemalensis</i> (emergente de flores amarillas); el come-negro es "
           "<i>Lonchocarpus ferrugineus</i> (madera muy dura). La palma trepadora <i>Desmoncus</i> sp. se conoce como "
           "bayal o balaire en Atlántida y Colón y tiene usos artesanales.",
           "Conviene diferenciar florística y funcionalmente los bosques basales sobre suelos Toyos y Choloma (Atlántida, "
           "Colón, Cortés, Yoro)."],
    1122: ["<i>Clethra macrophylla</i>, <i>C. lanata</i> y <i>C. hondurensis</i> son las pioneras típicas de la Cordillera "
           "Nombre de Dios. <i>Guarea grandifolia</i> (marapolán, carbón colorado) es maderable de alto potencial comercial "
           "(no confundir con <i>G. trichilioides</i>).",
           "<i>Alchornea latifolia</i> (Euphorbiaceae) se conoce como cuajada o tapa tamal; «tambor» es "
           "<i>Schizolobium parahyba</i>. El «pronto alivio» es un arbusto medicinal aromático (<i>Lippia alba</i>) "
           "registrado en Atlántida, Colón, Yoro, Olancho y Gracias a Dios.",
           "Restaurar franjas de amortiguamiento también en Olancho y El Paraíso."],
    1123: ["Suelos Toyos y Choloma. Además, <i>Magnolia yoroconte</i> (cuenca del río Cangrejal, muy explotada) y "
           "<i>Magnolia ciroorum</i> (identificada recientemente); <i>Clethra macrophylla</i>, <i>C. lanata</i> y "
           "<i>C. hondurensis</i>.",
           "<i>Alchornea latifolia</i> se conoce como cuajada o tapa tamal; «tambor» es <i>Schizolobium parahyba</i>."],
    1124: ["Suelos Toyos y Choloma; <i>Clethra macrophylla</i>, <i>C. lanata</i> y <i>C. hondurensis</i>.",
           "<i>Dendropanax arboreus</i> se conoce como zapotillo, palo de agua o palo de danta; crece en bosques húmedos y "
           "nublados de Comayagua, Cortés, Santa Bárbara y Yoro.",
           "<i>Alchornea latifolia</i> se conoce como cuajada o tapa tamal; «tambor» es <i>Schizolobium parahyba</i>."],
    1132: [_ROBLES_MONTANO, _AGUACATE, _LAURACEAS],
    1133: [_ROBLES_MONTANO, _AGUACATE, _LAURACEAS],
    1134: ["<i>Weinmannia</i>: <i>W. balbisiana</i> (Pico Pijol, Cusuco, La Muralla, Botaderos, sobre 1.800 msnm) y "
           "<i>W. pinnata</i> (Agalta, El Armado, La Muralla), entre otras en Montserrat (El Paraíso).",
           "<i>Ilex</i> de bosques nubosos y montanos superiores: <i>I. chiapensis</i> (Celaque, El Pital, El Volcán, "
           "Guisayote, Cerro Azul Copán, Montecristo, Puca, Opalaca, Erapuca), <i>I. williamsii</i> (alto valor de "
           "conservación; PN La Tigra, RVS Puca), <i>I. guianensis</i> (menor elevación y transición) e "
           "<i>I. tectonica</i> (maderable de alto valor de conservación; El Carbón, Malacate, Botaderos, Cordillera Entre "
           "Ríos, Nombre de Dios). Suelen asociarse a <i>Liquidambar styraciflua</i>, <i>Oreopanax xalapensis</i> y "
           "<i>Saurauia selerorum</i>, con coníferas, robles y encinos.",
           _LAURACEAS],
    1212: ["Biota indicadora: también <i>Enterolobium cyclocarpum</i> y <i>Cordia alliodora</i>. Considerar el valle del río "
           "Guayambre (zonas cálidas y subhúmedas) y, en la dinámica del paisaje, los ríos Ulúa, Guayambre y Sico, Tinto o "
           "Negro (Gualaco, San Esteban).",
           "<i>Cordia</i> de zonas cálidas subhúmedas: <i>C. alliodora</i>, <i>C. gerascanthus</i>, <i>C. dentata</i>, "
           "<i>C. alba</i>; de zonas más secas del Pacífico: <i>C. curassavica</i>, <i>C. globosa</i>, <i>C. inermis</i>, "
           "<i>C. salvadorensis</i>, <i>C. seleriana</i>.",
           "Para restaurar servidumbres fluviales, además de <i>Inga vera</i>, usar especies de raíces profundas, tolerantes "
           "a crecidas y a sequías prolongadas: <i>Andira inermis</i>, <i>Tabebuia rosea</i>, <i>Ceiba pentandra</i>, "
           "<i>Salix humboldtiana</i>, <i>Ficus insipida</i>, <i>F. obtusifolia</i> e <i>Inga spuria</i>. "
           "<i>Anacardium excelsum</i>, <i>Albizia saman</i> y <i>Pseudosamanea guachapele</i> son de bosque seco."],
    1213: ["Considerar también los valles de Santa Bárbara (Quimistán, Macuelizo y Naco), con relictos de maderables "
           "valiosos: <i>Swietenia macrophylla</i>, <i>S. humilis</i>, <i>Cedrela odorata</i>, <i>Vochysia guatemalensis</i>, "
           "<i>Handroanthus chrysanthus</i>, <i>Enterolobium cyclocarpum</i>, <i>Albizia saman</i> y "
           "<i>Cybistax donnell-smithii</i> (San Juan guayapeño).",
           "En el desmonte del valle del Guayape se talaron San Juan guayapeño, caoba (<i>Swietenia humilis</i>, "
           "<i>S. macrophylla</i>), granadillo (<i>Dalbergia retusa</i>, <i>D. cubilquitzensis</i>), cedro "
           "(<i>Cedrela odorata</i>) y carreto (<i>Albizia saman</i>, <i>Pseudosamanea guachapele</i>); conviene "
           "promoverlas en restauración y conservación."],
    1214: ["En las laderas del valle de Agalta (Gualaco: San Antonio de Saguay y Río del Oro; Guata y San Esteban; cuencas "
           "de los ríos Negro, El Barniz, Grande, Tonjagua y Tayaco) hay manchas de teocinte (<i>Dioon mejiae</i>) en el "
           "sotobosque, con <i>Acacia picachensis</i>, <i>Eugenia hondurensis</i>, <i>Lysiloma acapulcense</i> y "
           "<i>L. divaricatum</i>; allí se refugia el colibrí esmeralda hondureño (<i>Amazilia luciae</i>)."],
    1222: [_QUERCUS_1222, _NECTANDRA],
    1223: [_NECTANDRA],
    1224: [_NECTANDRA],
    1232: [_ROBLES_1232, _ILEX_1232],
    1233: [_ROBLES_1232, _ILEX_1232,
           "<i>Epidendrum radicans</i> crece también sobre rocas a pleno sol en bosque mesófilo, robledales y pinares, "
           "vegetación riparia y matorrales perennifolios, además de taludes."],
    1234: [_ROBLES_1232, _ILEX_1232,
           "También reportado en bosques mixtos de montaña y transiciones a bosque nublado de Comayagua, Ocotepeque, Copán, "
           "Santa Bárbara, Cortés y La Paz."],
    1313: ["Para ambas vertientes, incluir en las estrategias otras especies valiosas tradicionales como "
           "<i>Cedrela odorata</i> e <i>Hymenaea courbaril</i>."],
    1314: ["Para ambas vertientes, incluir en las estrategias otras especies valiosas tradicionales como "
           "<i>Cedrela odorata</i> e <i>Hymenaea courbaril</i>."],
    1323: [_SECO_PIONERAS],
    1332: ["Además de <i>Q. oleoides</i>, en esta unidad se citan <i>Quercus sapotifolia</i>, <i>Q. bumelioides</i>, "
           "<i>Q. benthamii</i>, <i>Q. conspersa</i>, <i>Q. cortesii</i>, <i>Q. pilicaulis</i>, <i>Q. salicifolia</i>, "
           "<i>Q. skinneri</i> y <i>Q. peduncularis</i>.", _QUERCUS_SECO_MONTANO],
    1333: ["Robles de esta unidad: <i>Q. oleoides</i>, <i>Q. sapotifolia</i>, <i>Q. peduncularis</i>, <i>Q. bumelioides</i>, "
           "<i>Q. benthamii</i> y <i>Q. xalapensis</i>.", _QUERCUS_SECO_MONTANO],
    1334: ["Robles de esta unidad: <i>Q. oleoides</i>, <i>Q. sapotifolia</i>, <i>Q. peduncularis</i>, <i>Q. bumelioides</i>, "
           "<i>Q. benthamii</i> y <i>Q. xalapensis</i>.", _QUERCUS_SECO_MONTANO],
}
for z in (16201, 16202, 16203, 16204, 635, 6173):
    APORTES.setdefault(z, _ARRECIFE)


def corregir(t: str) -> str:
    for patron, nuevo in REGLAS:
        t = re.sub(patron, nuevo, t)
    return t


def revisar(d: dict) -> dict:
    bs = [b for b in d["bloques"] if not b.get("revision")]  # idempotente: quita lo añadido antes
    for b in bs:
        if "h" in b:
            b["h"] = corregir(b["h"])
        if "x" in b:
            b["x"] = corregir(b["x"])
        if "f" in b:
            b["f"] = [[corregir(c) for c in fila] for fila in b["f"]]
    cod = d["codigo"]
    nuevos = []
    if cod in NOTA_ESPECIE:
        nuevos.append({"t": "nota", "h": NOTA_ESPECIE[cod], "revision": True})
    for a in APORTES.get(cod, []):
        nuevos.append({"t": "li", "h": a, "revision": True})
    if nuevos:
        nuevos = [{"t": "h2", "x": TITULO, "revision": True}, {"t": "nota", "h": FUENTE, "revision": True}, *nuevos]
        k = next((i for i, b in enumerate(bs) if b["t"] == "h2" and b.get("x", "").startswith("Referencias")), len(bs))
        bs[k:k] = nuevos
    if cod in MANGLARES:
        bs.insert(0, {"t": "nota", "h": nota_manglar(cod), "revision": True})
    d["bloques"] = bs
    return d


# ------------------------------------------------------------------ 3. ajuste de manglares por costa (00_ajuste_manglares.py)
MANGLARES = (6261, 6262, 6271, 6272)


def nota_manglar(cod: int) -> str:
    datos = FICHAS.parent
    aj = json.loads((Path(__file__).resolve().parent / "ajuste_manglares.json").read_text(encoding="utf-8"))["ha"]
    clase = next(c for c in json.loads((datos / "clases.json").read_text(encoding="utf-8"))["clases"] if c["codigo"] == cod)
    fmt = lambda x: f"{x:,.2f}".replace(",", " ").replace(".", ",").replace(" ", ".")
    mov = []
    for par, ha in aj.items():
        de, a = map(int, par.split("->"))
        if cod == de:
            mov.append(f"pasan {fmt(ha)} ha a la clase {a}")
        elif cod == a:
            mov.append(f"recibe {fmt(ha)} ha de la clase {de}")
    return ("<b>Ajuste por costa (2026).</b> En el ráster entregado algunas celdas de manglar quedaron con la clase de la "
            "otra costa (manglar «del Caribe» en el Golfo de Fonseca y «del Pacífico» en la costa norte). El geovisor las "
            "asigna a la clase de su costa sin cambiar la estructura (alto y denso / bajo y enano): en esta unidad "
            f"{' y '.join(mov)}. Superficie cartografiada actualizada: <b>{fmt(clase['ha_cartografiada'])} ha</b> "
            f"({fmt(clase['ha_ajustada'])} ha ajustadas). El mapa de distribución ya muestra el ajuste; las cifras de la "
            "monografía corresponden al ráster entregado.")


if __name__ == "__main__":
    n = 0
    for r in sorted(FICHAS.glob("*.json")):
        t = r.read_text(encoding="utf-8")
        d = json.loads(t)
        if "bloques" not in d:
            continue
        nuevo = json.dumps(revisar(d), ensure_ascii=False, separators=(",", ":"))
        if nuevo != t:
            r.write_text(nuevo, encoding="utf-8")
            n += 1
    print(f"{n} fichas revisadas; aportes en {len(APORTES)} unidades")
