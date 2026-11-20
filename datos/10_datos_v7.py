"""Correcciones v7 de los datos que no regenera 08: topónimos (unidades y límites), puntos, capas y manifiesto.

Idempotente: cada reemplazo produce una forma con tilde o ya corregida, que no vuelve a coincidir.
Uso: python -X utf8 datos/10_datos_v7.py
"""
import json
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent / "public" / "data"

# Palabras de topónimos sin tilde → forma correcta (se respeta la mayúscula inicial)
W = {
    "Aguan": "Aguán", "Aguila": "Águila", "Agustin": "Agustín", "Alubaren": "Alubarén", "Andres": "Andrés",
    "Angeles": "Ángeles", "Animas": "Ánimas", "Anis": "Anís", "Area": "Área", "Atlantida": "Atlántida",
    "Bahia": "Bahía", "Balsamo": "Bálsamo", "Bambu": "Bambú", "Banadero": "Bañadero", "Banaderos": "Bañaderos",
    "Barbara": "Bárbara", "Belen": "Belén", "Berlin": "Berlín", "Boqueron": "Boquerón", "Borbollon": "Borbollón",
    "Borboton": "Borbotón", "Cabana": "Cabaña", "Cabanas": "Cabañas", "Cafe": "Café", "Caidos": "Caídos",
    "Caiman": "Caimán", "Caiquin": "Caiquín", "Cajon": "Cajón", "Camaron": "Camarón", "Canada": "Cañada",
    "Canaveral": "Cañaveral", "Capulin": "Capulín", "Carbon": "Carbón", "Carambano": "Carámbano",
    "Castejon": "Castejón", "Cedron": "Cedrón", "Ceilan": "Ceilán", "Chamelecon": "Chamelecón",
    "Chaguite": "Chagüite", "Chaguitillo": "Chagüitillo", "Chaguiton": "Chagüitón", "Chililon": "Chililón",
    "Chilindrin": "Chilindrín", "Chorreron": "Chorrerón", "Cienega": "Ciénega", "Cienaguita": "Cienagüita",
    "Cipres": "Ciprés", "Cofradia": "Cofradía", "Colon": "Colón", "Comali": "Comalí", "Comun": "Común",
    "Concepcion": "Concepción", "Congolon": "Congolón", "Copan": "Copán", "Corquin": "Corquín", "Cortes": "Cortés",
    "Culmi": "Culmí", "Curaren": "Curarén", "Danli": "Danlí", "Datil": "Dátil", "Dona": "Doña", "Dubon": "Dubón",
    "Eden": "Edén", "Efrain": "Efraín", "Encarnacion": "Encarnación", "Escambron": "Escambrón",
    "Esquias": "Esquías", "Fatima": "Fátima", "Fria": "Fría", "Froylan": "Froylán", "Garcia": "García",
    "Gavilan": "Gavilán", "Goascoran": "Goascorán", "Guayacan": "Guayacán", "Guaymon": "Guaymón",
    "Guinope": "Güinope", "Hernandez": "Hernández", "Intibuca": "Intibucá", "Jalan": "Jalán", "Jazmin": "Jazmín",
    "Jerico": "Jericó", "Jeronimo": "Jerónimo", "Jesus": "Jesús", "Jicaro": "Jícaro", "Jicaros": "Jícaros",
    "Jocon": "Jocón", "Jose": "José", "Julian": "Julián", "Lamani": "Lamaní", "Lazaro": "Lázaro", "Lean": "Leán",
    "Lejamani": "Lejamaní", "Limon": "Limón", "Lucia": "Lucía", "Mangon": "Mangón", "Maranones": "Marañones",
    "Maria": "María", "Marias": "Marías", "Marmol": "Mármol", "Marroquin": "Marroquín", "Martin": "Martín",
    "Martinez": "Martínez", "Masacan": "Masacán", "Matias": "Matías", "Meambar": "Meámbar", "Mendez": "Méndez",
    "Merendon": "Merendón", "Montana": "Montaña", "Montanita": "Montañita", "Montanuela": "Montañuela",
    "Morazan": "Morazán", "Moroceli": "Morocelí", "Murallon": "Murallón", "Murcielagal": "Murciélagal",
    "Murcielago": "Murciélago", "Nicolas": "Nicolás", "Nispero": "Níspero", "Numero": "Número", "Organo": "Órgano",
    "Oropoli": "Orópoli", "Pabellon": "Pabellón", "Pacifico": "Pacífico", "Paraiso": "Paraíso", "Pelon": "Pelón",
    "Pena": "Peña", "Penitas": "Peñitas", "Pericon": "Pericón", "Platano": "Plátano", "Platanos": "Plátanos",
    "Playon": "Playón", "Proteccion": "Protección", "Quebradon": "Quebradón", "Quimistan": "Quimistán",
    "Qumistan": "Quimistán", "Quinton": "Quintón", "Ramirez": "Ramírez", "Raul": "Raúl", "Rincon": "Rincón",
    "Rio": "Río", "Rios": "Ríos", "Roatan": "Roatán", "Salama": "Salamá", "Sanjon": "Sanjón",
    "Sebastian": "Sebastián", "Sensenti": "Sensentí", "Sinai": "Sinaí", "Sion": "Sión", "Tablazon": "Tablazón",
    "Tabano": "Tábano", "Techin": "Techín", "Tilon": "Tilón", "Tio": "Tío", "Tomala": "Tomalá", "Tucan": "Tucán",
    "Tulian": "Tulián", "Ulua": "Ulúa", "Union": "Unión", "Vocacion": "Vocación", "Volcan": "Volcán",
    "Yocon": "Yocón", "Yuscaran": "Yuscarán", "Zanjon": "Zanjón", "Cane": "Cané",
}
FRASES = [
    ("Islas de La Bahía", "Islas de la Bahía"), ("Isleños y Mestizo", "Isleño y Mestizo"), ("Cruta Medio", "Cruta Media"), ("Blanca Janeth Kawas", "Blanca Jeannette Kawas"),
    ('Cerro "El Guanacaure"', "Cerro El Guanacaure"), ("Área de uso múltiple", "Área de Uso Múltiple"),
    ("Microcueca", "Microcuenca"), ("MIcrocuenca", "Microcuenca"), ("FLores", "Flores"), ("PIedrona", "Piedrona"),
    ("LAs ", "Las "), ("Sin numero", "Sin número"), ("sin numero", "sin número"),
]


def _palabra(m):
    w = m.group(0)
    if w in W:
        return W[w]
    if w[:1].islower() and w.capitalize() in W:  # «cuenca ulua», «concepcion»
        return W[w.capitalize()].lower()
    if w.isupper() and len(w) > 2 and w.capitalize() in W:
        return W[w.capitalize()].upper()
    return w


def topo(t):
    if not isinstance(t, str) or not t:
        return t
    t = re.sub(r"[A-Za-zñÑ]+", _palabra, t)
    for a, b in FRASES:
        t = t.replace(a, b)
    return re.sub(r" {2,}", " ", t).strip()


def leer(p):
    return json.loads(p.read_text(encoding="utf-8"))


def escribir(p, d, compacto=True):
    p.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":") if compacto else None), encoding="utf-8")


def compacto(p):
    s = p.read_text(encoding="utf-8")
    return not s.lstrip().startswith("{\n")


# ---------- unidades y límites ----------
for p in sorted((RAIZ / "unidades").glob("*.json")):
    c = compacto(p)
    d = leer(p)
    for u in d["unidades"]:
        for k in ("nombre", "categoria", "padre"):
            u[k] = topo(u.get(k))
    escribir(p, d, c)
for p in sorted((RAIZ / "limites").glob("*.geojson")):
    c = compacto(p)
    d = leer(p)
    for f in d["features"]:
        pr = f["properties"]
        for k in ("nombre", "categoria", "padre"):
            if k in pr:
                pr[k] = topo(pr[k])
    escribir(p, d, c)

# ---------- puntos ----------
GRUPOS = {"G05": "Ríos, lagos y embalses", "G10": "Formaciones arboladas abiertas, sabanas y jicarales",
          "G13": "Sistemas agrícolas, agroforestales y acuícolas"}
FUENTES = {
    "Hábitats Marinos Surveys": "Levantamientos de hábitats marinos",
    "Digitalización en Pantalla": "Digitalización en pantalla",
    "Sitios de Monitoreo Ecosistemas 2000": "Sitios de monitoreo de ecosistemas 2000",
    "Verificación Espacial Inter-Ráster (2014–2018–2024)": "Verificación espacial entre rásteres (2014, 2018 y 2024)",
    "Formulario Kobo-2 (Campo Ecosistemas)": "Formulario Kobo 2 (campo de ecosistemas)",
    "Formulario Kobo-1 (Puntos de control v2)": "Formulario Kobo 1 (puntos de control, v2)",
    "INF Ciclo I Exclusivas (2005–2006)": "INF ciclo I, parcelas exclusivas (2005–2006)",
    "INF Ciclo II (2011–2015)": "INF ciclo II (2011–2015)",
    "INF Mangles Ciclo IV (2024)": "INF manglares, ciclo IV (2024)",
    "PMP Estudio 2012 (ICF / WWF)": "Estudio PMP 2012 (ICF / WWF)",
}
ESTADO = {"RESUELTO_COBERTURA_OPERATIVA": "Resuelto por cobertura operativa",
          "NO_RESUELTO_ETIQUETA_PUENTE": "No resuelto (etiqueta puente)",
          "PROVISIONAL_ETIQUETA_ORIGINAL": "Provisional (etiqueta original)"}
BIOMA = {"Bosques Latifoliados": "Bosques latifoliados", "Bosques de Coníferas y Mixtos": "Bosques de coníferas y mixtos",
         "Ecosistemas Marinos Fóticos": "Ecosistemas marinos fóticos", "Sistemas Antrópicos y Agrícolas": "Sistemas antrópicos y agrícolas",
         "Manglares y Humedales Costeros": "Manglares y humedales costeros", "Matorrales y Pastizales Abiertos": "Matorrales y pastizales abiertos",
         "Humedales Continentales": "Humedales continentales"}
TXT = [("Marino dulceacuícola y terrestre", "Marino, dulceacuícola y terrestre"),
       ("NC. Unidad R25 sin equivalencia", "NC. Unidad sin equivalencia"), ("SD. Celda R25 sin dato", "SD. Celda sin dato"),
       ("Bosque latifoliado abierto / ralo", "Bosque latifoliado abierto y/o perturbado"),
       ("tropic al", "tropical"), ("Urbanizmi", "Urbanismo"), ("decíduo", "deciduo"), ("Decíduo", "Deciduo"),
       ("del pacifico", "del Pacífico")]

pp = RAIZ / "puntos" / "puntos.geojson"
c = compacto(pp)
g = leer(pp)
for f in g["features"]:
    pr = f["properties"]
    for k in ("grupo_ref", "grupo_mapa"):
        v = pr.get(k)
        if v and v[:3] in GRUPOS:
            pr[k] = f"{v[:3]} {GRUPOS[v[:3]]}"
    pr["fuente"] = FUENTES.get(pr.get("fuente"), pr.get("fuente"))
    pr["estado"] = ESTADO.get(pr.get("estado"), pr.get("estado"))
    for k in ("bioma_ref", "bioma_mapa"):
        v = pr.get(k)
        if v:
            for a, b in BIOMA.items():
                v = v.replace(a, b)
            pr[k] = v
    for k, v in list(pr.items()):
        if isinstance(v, str):
            for a, b in TXT:
                v = v.replace(a, b)
            pr[k] = v
    for k in ("departamento", "municipio"):
        pr[k] = topo(pr.get(k))
escribir(pp, g, c)

# ---------- capas ----------
CAPAS = [
    ("Boque ", "Bosque "), ("simpreverde", "siempreverde"), ("siempre verde", "siempreverde"), ("dreanado", "drenado"),
    ("infrerior", "inferior"), ("latifoiado", "latifoliado"), ("lmixto", "mixto"), ("calcareo", "calcáreos"),
    ("tierras bajas,en", "tierras bajas, en"), ("Area urbana", "Área urbana"), ("Pacífico sobre", "del Pacífico sobre"),
    ("manglar Pacífico", "manglar del Pacífico"), ("(Mejía Ordóñez y House 2002)", "(Mejía Ordóñez y House, 2002)"),
    ("m s.n.m.", "m s. n. m."),
    ("; en la clase 629, capa complementaria Geodatos/Complementarias/Regimen_629_R26_30m.tif (scripts 63 y 65)",
     "; en la clase 629, capa complementaria de régimen"),
    ("Desde el 19-11-2026 el régimen seco", "El régimen seco"),
    # leyenda truncada a 100 caracteres en el shapefile de 2002: se corta en la última frase completa
    ("latifoliado pantano de tierras bajas, permanentemente inundado, con pla", "latifoliado pantanoso de tierras bajas, permanentemente inundado"),
]
pc = RAIZ / "capas" / "capas.json"
c = compacto(pc)
s = pc.read_text(encoding="utf-8")
d = json.loads(s)


def lim(o):
    if isinstance(o, dict):
        return {k: lim(v) for k, v in o.items()}
    if isinstance(o, list):
        return [lim(v) for v in o]
    if isinstance(o, str):
        for a, b in CAPAS:
            o = o.replace(a, b)
        o = o.replace("calcáreoss", "calcáreos").replace("del del Pacífico", "del Pacífico")
        return re.sub(r"(?<=\S) {2,}(?=\S)", " ", o)
    return o


d = lim(d)
for k in d["capas"]:
    for cl in k.get("clases", []):
        if isinstance(cl.get("n"), str) and cl["n"].endswith(" con pla"):
            print("aviso: leyenda truncada", k["id"], cl["v"], cl["n"])
escribir(pc, d, c)

# ---------- manifiesto ----------
pm = RAIZ / "manifiesto.json"
c = compacto(pm)
m = leer(pm)
fu = m.get("fuentes", {})
if "pueblos_indigenas" in fu:
    fu["pueblos_indigenas"] = fu["pueblos_indigenas"].replace(", campo ETNIA_1", "")
if fu.get("limite_marino") == "Limite_Territorio_Marino.shp":
    fu["limite_marino"] = "Límite del territorio marino de Honduras (capa oficial del proyecto)"
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def prosa(t):
    return re.sub(r"(?<!\d)(\d{4})-(\d{2})-(\d{2})(?!\d)", lambda x: f"{int(x[3])} de {MESES[int(x[2]) - 1]} de {x[1]}", t)


for k, v in fu.items():
    if isinstance(v, str):
        fu[k] = prosa(v)
escribir(pm, m, c)
print("datos v7 corregidos (unidades, límites, puntos, capas, manifiesto)")
