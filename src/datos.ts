// Tipos y carga de los datos estáticos generados por datos/*.py

export interface Clase {
  codigo: number;
  nombre: string;
  grupo: string;
  get1: string;
  get2: string;
  get3: string;
  /** Regla estricta R25 (L1–L3): MULT con varias membresías, SIN_GET con relación solo contextual. */
  estricto: [string, string, string];
  /** Otros EFG (L3) a los que también puede pertenecer la clase. */
  alt: string[];
  /** Criterio de la asignación principal y de cada alternativa ("" si la membresía es única). */
  criterio: string;
  criterios_alt: string;
  color: string;
  efg: [string, string, boolean][];
  ha_ajustada: number;
  ha_cartografiada: number;
}

export interface Catalogo {
  edicion: string;
  clases: Clase[];
  grupos: { codigo: string; nombre: string }[];
  get: Record<"GET_L1" | "GET_L2" | "GET_L3", Record<string, string>>;
}

export interface Unidad {
  id: string;
  nombre: string;
  categoria: string;
  padre: string;
  ha: number;
  ha_sinaph: number;
  ha_poligono: number;
  bbox: [number, number, number, number];
  clases: [number, number][];
}

export type ClaveCapa = "areas_protegidas" | "pueblos_indigenas" | "departamentos" | "municipios" | "cuencas" | "subcuencas" | "microcuencas";

export interface DefCapa {
  clave: ClaveCapa;
  nombre: string;
  singular: string;
  disponible: boolean;
  nota?: string;
}

export const CAPAS: DefCapa[] = [
  { clave: "areas_protegidas", nombre: "Áreas protegidas", singular: "Área protegida", disponible: true },
  {
    clave: "pueblos_indigenas",
    nombre: "Pueblos indígenas",
    singular: "Pueblo indígena o afrohondureño",
    disponible: true,
    nota: "Pueblos indígenas y afrohondureños: una unidad por pueblo",
  },
  { clave: "departamentos", nombre: "Departamentos", singular: "Departamento", disponible: true },
  { clave: "municipios", nombre: "Municipios", singular: "Municipio", disponible: true },
  { clave: "cuencas", nombre: "Cuencas", singular: "Cuenca hidrográfica", disponible: true, nota: "Cuencas hidrográficas de Honduras (25)" },
  { clave: "subcuencas", nombre: "Subcuencas", singular: "Subcuenca hidrográfica", disponible: true, nota: "Subcuencas hidrográficas (133)" },
  {
    clave: "microcuencas",
    nombre: "Microcuencas declaradas",
    singular: "Microcuenca declarada",
    disponible: true,
    nota: "Microcuencas abastecedoras de agua declaradas por acuerdo (ICF)",
  },
];

export interface Manifiesto {
  edicion: string;
  generado: string;
  raster: { archivo: string; sha256: string; celda_ha: number };
  fuentes: Record<string, string | null>;
}

export const url = (ruta: string) => new URL(`data/${ruta}`, document.baseURI).href;

async function json<T>(ruta: string): Promise<T> {
  const r = await fetch(url(ruta));
  if (!r.ok) throw new Error(`No se pudo leer ${ruta} (${r.status})`);
  return r.json() as Promise<T>;
}

export const cargarCatalogo = () => json<Catalogo>("clases.json");
export const cargarManifiesto = () => json<Manifiesto>("manifiesto.json");

const cacheUnidades = new Map<ClaveCapa, Promise<Unidad[]>>();
export function cargarUnidades(capa: ClaveCapa): Promise<Unidad[]> {
  if (!cacheUnidades.has(capa)) {
    cacheUnidades.set(capa, json<{ unidades: Unidad[] }>(`unidades/${capa}.json`).then((d) => d.unidades));
  }
  return cacheUnidades.get(capa)!;
}

// Formatos numéricos con la convención del informe técnico: punto de miles y coma decimal (1.234,56)
const fmt = (d: number) =>
  new Intl.NumberFormat("es-ES", { minimumFractionDigits: d, maximumFractionDigits: d, useGrouping: "always" } as unknown as Intl.NumberFormatOptions);
const f0 = fmt(0), f1 = fmt(1), f2 = fmt(2);
/** Hectáreas; las superficies menores de 10 ha llevan dos decimales para no mostrarse como 0. */
export const ha = (v: number, dec = 0) => (dec === 2 || (v > 0 && v < 10) ? f2 : dec === 1 ? f1 : f0).format(v);
export const pct = (v: number) => (v > 0 && v < 0.05 ? "<0,1 %" : (v >= 10 ? f0 : f1).format(v) + " %");
