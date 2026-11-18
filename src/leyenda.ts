// Leyendas jerárquicas: por grupo nacional y por GET-UICN (Reino › Bioma › Grupo funcional (EFG) › clase nacional).
// GET sigue la regla de R26: una clase cuelga de una rama solo con membresía única en ese nivel.
// Si tiene varias membresías queda en «MULT», y si solo tiene una relación contextual, en «SIN_GET».
import type { Catalogo, Clase } from "./datos";
import { botonInfo } from "./fichas";

const esc = (s: string) => s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]!);
const ORDEN_REINO = ["T", "TF", "F", "FM", "M", "MT", "MFT"];
const especial = (c: string) => (c === "MULT" ? 1 : c === "SIN_GET" ? 2 : 0);
export const ordenarGET = (a: string, b: string) =>
  especial(a) - especial(b) ||
  (ORDEN_REINO.indexOf(a) + 1 || 99) - (ORDEN_REINO.indexOf(b) + 1 || 99) ||
  a.localeCompare(b, "es", { numeric: true });

const NOMBRE_MULT = ["Varios reinos", "Varios biomas", "Varios grupos funcionales"];

// Nombres de EFG que no tienen ninguna clase con membresía (p. ej. M3.4, solo contextual para la 635)
let nombresEFG: Map<string, string> | null = null;

export function nombreGET(cat: Catalogo, nivel: 0 | 1 | 2, cod: string): string {
  if (cod === "MULT") return `${NOMBRE_MULT[nivel]} · pendiente de reparto`;
  if (cod === "SIN_GET") return "Sin correspondencia de membresía";
  nombresEFG ??= new Map(cat.clases.flatMap((c) => c.efg.map((e) => [e[0], e[1]] as [string, string])));
  return cat.get[(["GET_L1", "GET_L2", "GET_L3"] as const)[nivel]][cod] ?? nombresEFG.get(cod) ?? cod;
}

/**
 * Ruta de la clase en el árbol GET. Las clases sin membresía (SIN_GET) con una sola relación contextual se muestran
 * bajo ese EFG, marcadas como contextuales. Las cifras de resúmenes y reportes siguen la tabla R26 (SIN_GET).
 */
export function rutaGET(c: Clase): [string, string, string, boolean] {
  if (c.get1 === "SIN_GET" && c.efg.length === 1) {
    const efg = c.efg[0][0]; // p. ej. "M3.4"
    const bioma = efg.split(".")[0]; // "M3"
    return [bioma.replace(/\d+$/, ""), bioma, efg, true];
  }
  return [c.get1, c.get2, c.get3, false];
}

export type ArbolGET = Map<string, Map<string, Map<string, Clase[]>>>;

/** Agrupa las clases en Reino › Bioma › EFG, con las ramas ya ordenadas. */
export function arbolGET(clases: Clase[]): ArbolGET {
  const a: ArbolGET = new Map();
  for (const c of clases) {
    const [g1, g2, g3] = rutaGET(c);
    const b = a.get(g1) ?? a.set(g1, new Map()).get(g1)!;
    const e = b.get(g2) ?? b.set(g2, new Map()).get(g2)!;
    (e.get(g3) ?? e.set(g3, []).get(g3)!).push(c);
  }
  const ord = <V>(m: Map<string, V>) => new Map([...m.entries()].sort(([x], [y]) => ordenarGET(x, y)));
  return ord(new Map([...a].map(([k1, b]) => [k1, ord(new Map([...b].map(([k2, e]) => [k2, ord(e)])))])));
}

function claseLi(c: Clase): string {
  const contextual = rutaGET(c)[3];
  const rel = c.efg.map((e) => `${e[0]} ${e[1]}${e[2] ? " (principal)" : ""}`).join("\n");
  const titulo = contextual
    ? `Relación contextual con ${rel}. No es membresía: en las superficies R26 figura como «Sin correspondencia de membresía».`
    : rel ? `Correspondencias EFG:\n${rel}` : "";
  return `<li data-li="${c.codigo}" class="${contextual ? "contextual" : ""}" title="${esc(titulo)}"><label><input type="checkbox" data-clase="${c.codigo}" checked>
    <i style="background:${c.color}"></i><span><b>${c.codigo}</b> ${esc(c.nombre)}${contextual ? ' <em class="marca-ctx">relación contextual</em>' : ""}</span></label>${botonInfo(c)}</li>`;
}

/** Árbol por grupos nacionales (G01–G14) › clase nacional. */
export function htmlGrupos(cat: Catalogo, colorGrupo: (g: string) => string): string {
  return cat.grupos
    .map((g) => {
      const cl = cat.clases.filter((c) => c.grupo === g.codigo).sort((a, b) => a.codigo - b.codigo);
      if (!cl.length) return "";
      return `
    <details class="nodo n1">
      <summary><input type="checkbox" data-codigos="${cl.map((c) => c.codigo).join(",")}" checked aria-label="${esc(g.nombre)}">
        <span class="cod">${esc(g.codigo)}</span><i style="background:${colorGrupo(g.codigo)}"></i><span class="nom">${esc(g.nombre)}</span><small>${cl.length}</small></summary>
      <div class="hijos"><ul>${cl.map(claseLi).join("")}</ul></div></details>`;
    })
    .join("");
}

export function htmlLeyenda(cat: Catalogo): string {
  const nodo = (nivel: 0 | 1 | 2, cod: string, clases: Clase[], interior: string, abierto: boolean) => `
    <details class="nodo n${nivel + 1}${especial(cod) ? " especial" : ""}"${abierto ? " open" : ""}>
      <summary><input type="checkbox" data-codigos="${clases.map((c) => c.codigo).join(",")}" checked aria-label="${esc(nombreGET(cat, nivel, cod))}">
        <span class="cod">${cod === "SIN_GET" ? "—" : esc(cod)}</span><span class="nom">${esc(nombreGET(cat, nivel, cod))}</span><small>${clases.length}</small></summary>
      <div class="hijos">${interior}</div></details>`;

  return [...arbolGET(cat.clases)]
    .map(([k1, biomas]) => {
      const cl1 = [...biomas.values()].flatMap((m) => [...m.values()].flat());
      const html2 = [...biomas]
        .map(([k2, efgs]) => {
          const cl2 = [...efgs.values()].flat();
          const html3 = [...efgs]
            .map(([k3, cl]) => {
              const cl3 = [...cl].sort((a, b) => a.codigo - b.codigo);
              return nodo(2, k3, cl3, `<ul>${cl3.map(claseLi).join("")}</ul>`, false);
            })
            .join("");
          return nodo(1, k2, cl2, html3, false);
        })
        .join("");
      return nodo(0, k1, cl1, html2, true);
    })
    .join("");
}
