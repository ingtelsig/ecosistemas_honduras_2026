"""Arbustales secos o deciduos (4032–4034): grupo funcional principal T3.1 → T1.2, y T3.1 fuera de las relaciones de 4022–4034.

Mismo cambio que Entrega_final_R26/scripts/69_arbustal_seco_T12_R26.py y 70_catalogos_T12_enlaces_GET.py: el perfil de
T3.1 en la GET v2.1 describe matorrales esclerófilos de suelos oligotróficos (campos rupestres, tepuyes) sin presencia
documentada en Centroamérica; los arbustales secos hondureños son matorrales deciduos y espinosos de T1.2.
Va después de 11_formato_numerico.py (los textos nuevos no llevan cifras). Es idempotente.
Uso: python -X utf8 datos/12_arbustal_seco_T12.py
"""
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent / "public" / "data"
SECOS, ESTAC = (4032, 4033, 4034), (4022, 4023, 4024)
NOM = {"T1.2": "Bosques secos y matorrales tropicales/subtropicales", "T7.1": "Cultivos anuales",
       "T7.5": "Pastizales seminaturales derivados y antiguos campos"}
ALT = {"T1.2": "si domina la estacionalidad: dosel semideciduo o deciduo y varios meses secos",
       "T7.1": "si es tierra agrícola en barbecho, preparación o con cultivos anuales",
       "T7.5": "si deriva de desmonte, quemas o abandono agrícola (vegetación seminatural derivada)"}
CRIT = ("arbustal de régimen seco / deciduo: matorral espinoso deciduo de los valles secos y la llanura pacífica, "
        "fracción de matorral (thicket) del bosque seco tropical")
COLA = (" La superficie de la unidad se reporta en la rama principal; la regla estricta, que deja en MULT o SIN_GET las clases "
        "con varias membresías o solo contextuales, se conserva en Superficies_ajustadas_R26_por_codigo.csv.")
NO31 = (" T3.1 (Arbustales tropicales estacionalmente secos) no se aplica: su perfil en la GET v2.1 describe matorrales "
        "esclerófilos siempreverdes de suelos oligotróficos (campos rupestres, tepuyes), sin presencia documentada en Centroamérica.")
NOTA_SECO = ("<b>Asignación GET-UICN principal. </b>T1.2 (Bosques secos y matorrales tropicales/subtropicales) es el grupo funcional "
             f"principal, el más probable para la unidad: {CRIT}. También puede pertenecer a T7.5 (Pastizales seminaturales "
             "derivados y antiguos campos), si deriva de desmonte, quemas o abandono agrícola (vegetación seminatural derivada); "
             "T7.1 (Cultivos anuales), si es tierra agrícola en barbecho, preparación o con cultivos anuales." + NO31 + COLA)
ALT31 = ("; T3.1 (Arbustales tropicales estacionalmente secos), si es matorral natural de clima estacional o seco sobre suelos "
         "someros, no derivado de desmonte")
FRASES = [
    (", matorrales condicionados por suelos pesados e hídricamente oscilantes (T3.1)", ""),
    ("subhúmedos (T1.2), comunidades arbustivas condicionadas por lajas ignimbríticas delgadas (T3.1) y paisajes",
     "subhúmedos, incluidas las comunidades arbustivas sobre lajas ignimbríticas delgadas (T1.2), y paisajes"),
    ("bosques estacionales (T1.2), formaciones arbustivas calcícolas o litosólicas permanentes sobre afloramientos Sulaco y Cocona (T3.1), guamiles",
     "bosques estacionales y formaciones arbustivas calcícolas o litosólicas permanentes sobre afloramientos Sulaco y Cocona (T1.2), guamiles"),
    ("para delimitar los núcleos edáficos primarios atribuibles a T3.1.", "para delimitar los núcleos edáficos primarios de matorral seco (T1.2)."),
    ("espinales tropófilos bajos (T1.2), matorrales freatófitos gobernados por aridez y arcillas pesadas (T3.1) y carbones",
     "espinales tropófilos bajos y matorrales freatófitos gobernados por aridez y arcillas pesadas (T1.2) y carbones"),
    ("matorrales espinosos tropófilos (T1.2), cactales xerófitos persistentes sobre sustratos áridos (T3.1) y matorrales",
     "matorrales espinosos tropófilos y cactales xerófitos persistentes sobre sustratos áridos (T1.2) y matorrales"),
    ("los espinales primarios T3.1 y T1.2 respecto a", "los espinales primarios (T1.2) respecto a"),
    ("bosques bajos tropófilos en sucesión (T1.2), cactales rupícolas primarios sobre calizas y litosoles (T3.1) y laderas",
     "bosques bajos tropófilos en sucesión y cactales rupícolas primarios sobre calizas y litosoles (T1.2) y laderas"),
    ("los cactales rupícolas primarios (T3.1) sobre", "los cactales rupícolas primarios (T1.2) sobre"),
    ("T1.2 / T3.1 / T7.1 / T7.5", "T1.2 / T7.1 / T7.5"),
    ("T1.2, T3.1, T7.1, T7.5", "T1.2, T7.1, T7.5"),
    (ALT31, ""),
]

# --- catálogo de clases
p = RAIZ / "clases.json"
c = json.loads(p.read_text(encoding="utf-8"))
for x in c["clases"]:
    if x["codigo"] in SECOS:
        alts = ["T7.5", "T7.1"]
        x.update(get2="T1", get3="T1.2", criterio=CRIT)
    elif x["codigo"] in ESTAC:
        alts = [a for a in x["alt"] if a != "T3.1"]
    else:
        continue
    x["alt"] = alts
    x["criterios_alt"] = " | ".join(f"{a} ({NOM[a]}): {ALT[a]}" for a in alts)
    x["efg"] = [[e, n, e == x["get3"]] for e, n, _ in x["efg"] if e != "T3.1"]
p.write_text(json.dumps(c, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


# --- fichas
def tratar(o):
    if isinstance(o, dict):
        return {k: tratar(v) for k, v in o.items()}
    if isinstance(o, list):
        return [tratar(v) for v in o]
    if isinstance(o, str):
        if o.startswith("<b>Asignación GET-UICN principal. </b>T3.1 (Arbustales tropicales estacionalmente secos) es el grupo"):
            return NOTA_SECO
        for a, b in FRASES:
            o = o.replace(a, b)
    return o


n = 0
for cod in SECOS + ESTAC:
    f = RAIZ / "fichas" / f"{cod}.json"
    s = f.read_text(encoding="utf-8")
    nuevo = json.dumps(tratar(json.loads(s)), ensure_ascii=False, separators=(",", ":"))
    if nuevo != s:
        f.write_text(nuevo, encoding="utf-8")
        n += 1
resto = [f.name for f in (RAIZ / "fichas").glob("*.json")
         if "T3.1" in f.read_text(encoding="utf-8").replace("MT3.1", "").replace("T3.1 Seasonally", "").replace("T3.1 (Arbustales tropicales estacionalmente secos) no se aplica", "").replace("groups/T3.1", "").replace("EFGs/T3.1", "")]
print(f"clases.json actualizado · {n} fichas cambiadas · fichas con T3.1 pendiente: {resto}")
