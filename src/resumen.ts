// Cálculos compartidos por el panel y los reportes a partir de las hectáreas por clase de una unidad.
import type { Catalogo, Clase, Unidad } from "./datos";
import { detalleGET } from "./leyenda";

export interface Fila {
  codigo: string;
  nombre: string;
  ha: number;
  pct: number;
  color: string;
}

export interface FilaClase extends Fila {
  clase: Clase;
}

export interface Resumen {
  unidad: Unidad;
  total: number;
  clases: FilaClase[];
  grupos: Fila[];
  get1: Fila[];
  get2: Fila[];
  get3: Fila[];
  pctSinaph: number;
  /** Hectáreas de las clases que pasan el filtro (igual a total si no hay filtro). */
  seleccion: number;
  /** Número de clases activas en el filtro del visor, o null si están todas. */
  filtro: number | null;
}

const NOMBRE_ESPECIAL: Record<string, string> = {
  MULT: "Asignación múltiple (pendiente de reparto entre EFG)",
  SIN_GET: "Sin correspondencia GET",
};

let indice: Map<number, Clase> | null = null;
let colorGrupo: Map<string, string> | null = null;

export function claseDe(cat: Catalogo, codigo: number): Clase | undefined {
  indice ??= new Map(cat.clases.map((c) => [c.codigo, c]));
  return indice.get(codigo);
}

/** Color representativo de cada grupo: el de su clase de mayor superficie nacional. */
export function colorDeGrupo(cat: Catalogo, grupo: string): string {
  if (!colorGrupo) {
    colorGrupo = new Map();
    const mayor = new Map<string, Clase>();
    for (const c of cat.clases) if (!mayor.has(c.grupo) || c.ha_ajustada > mayor.get(c.grupo)!.ha_ajustada) mayor.set(c.grupo, c);
    for (const [g, c] of mayor) colorGrupo.set(g, c.color);
  }
  return colorGrupo.get(grupo) ?? "#999999";
}

function agrupar(cat: Catalogo, filas: FilaClase[], clave: (c: Clase) => string, nombres: Record<string, string>, total: number): Fila[] {
  const m = new Map<string, number>();
  for (const f of filas) m.set(clave(f.clase), (m.get(clave(f.clase)) ?? 0) + f.ha);
  return [...m.entries()]
    .map(([codigo, h]) => ({ codigo, nombre: nombres[codigo] ?? NOMBRE_ESPECIAL[codigo] ?? codigo, ha: h, pct: (100 * h) / total, color: colorDeGrupo(cat, codigo) }))
    .sort((a, b) => b.ha - a.ha);
}

/** Resumen de la unidad. Con `visibles` se limita a esas clases; los porcentajes siguen siendo sobre la unidad completa. */
export function resumir(cat: Catalogo, u: Unidad, visibles?: Set<number>): Resumen {
  const total = u.clases.reduce((s, [, h]) => s + h, 0) || 1;
  const filtrar = !!visibles && visibles.size < cat.clases.length;
  const base = filtrar ? u.clases.filter(([c]) => visibles!.has(c)) : u.clases;
  const clases: FilaClase[] = base
    .map(([cod, h]) => {
      const c = claseDe(cat, cod)!;
      return { codigo: String(cod), nombre: c.nombre, ha: h, pct: (100 * h) / total, color: c.color, clase: c };
    })
    .sort((a, b) => b.ha - a.ha);
  const nombresGrupo = Object.fromEntries(cat.grupos.map((g) => [g.codigo, g.nombre]));
  return {
    unidad: u,
    total,
    clases,
    grupos: agrupar(cat, clases, (c) => c.grupo, nombresGrupo, total),
    get1: agrupar(cat, clases, (c) => c.get1, cat.get.GET_L1, total),
    get2: agrupar(cat, clases, (c) => c.get2, cat.get.GET_L2, total),
    get3: agrupar(cat, clases, (c) => c.get3, cat.get.GET_L3, total),
    pctSinaph: (100 * u.ha_sinaph) / total,
    seleccion: clases.reduce((s, f) => s + f.ha, 0),
    filtro: filtrar ? visibles!.size : null,
  };
}

/** Unidad sintética con todo el país (superficie cartografiada a 30 m de cada clase). */
export function unidadNacional(cat: Catalogo): Unidad {
  const clases = cat.clases.map((c) => [c.codigo, c.ha_cartografiada] as [number, number]).filter(([, h]) => h > 0);
  return {
    id: "HN",
    nombre: "Honduras",
    categoria: "País (tierra y mar)",
    padre: "",
    ha: clases.reduce((s, [, h]) => s + h, 0),
    ha_sinaph: 0,
    ha_poligono: 0,
    bbox: [-89.4, 12.9, -82.4, 17.5],
    clases,
  };
}

export function csv(r: Resumen, capa: string, cat: Catalogo): string {
  const q = (s: string) => `"${s.replace(/"/g, '""')}"`;
  const filas = [["capa", "unidad_id", "unidad", "codigo", "clase", "grupo", "GET_L1", "GET_L2", "GET_L3", "GET_L1_categorias", "GET_L2_categorias", "GET_L3_categorias", "hectareas_30m", "porcentaje_unidad"].join(",")];
  for (const f of r.clases) {
    filas.push([q(capa), q(r.unidad.id), q(r.unidad.nombre), f.codigo, q(f.nombre), f.clase.grupo, f.clase.get1, f.clase.get2, f.clase.get3, ...([0, 1, 2] as const).map((n) => q(detalleGET(cat, f.clase, n))), f.ha.toFixed(2), f.pct.toFixed(4)].join(","));
  }
  return "﻿" + filas.join("\r\n");
}

export function descargar(contenido: Blob, nombre: string) {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(contenido);
  a.download = nombre;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 2000);
}

export const slug = (s: string) =>
  s.normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^A-Za-z0-9]+/g, "_").replace(/^_|_$/g, "").slice(0, 60);
