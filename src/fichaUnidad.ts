// Ficha web de una unidad de reporte (área protegida, pueblo indígena, departamento, municipio, cuenca…).
// Muestra en pantalla el mismo contenido del reporte PDF; el PDF se descarga solo desde el botón de la ficha.
import { ha, pct, type Catalogo } from "./datos";
import type { FilaClase, Resumen } from "./resumen";
import { arbolGET, nombreGET, rutaGET } from "./leyenda";
import { enlazarGET } from "./fichas";

const esc = (s: string) => s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]!);

export interface ContextoFichaUnidad {
  cat: Catalogo;
  capaNombre: string;
  contexto: string;
  /** Imagen del mapa encuadrado en la unidad (la misma que usa el PDF). */
  mapa: () => Promise<string>;
  pdf: () => Promise<void>;
  csv: () => void;
}

let ctx: ContextoFichaUnidad | null = null;
let iniciado = false;

function dialogo(): HTMLDialogElement {
  const dlg = document.getElementById("ficha-unidad") as HTMLDialogElement;
  if (iniciado) return dlg;
  iniciado = true;
  dlg.addEventListener("click", async (e) => {
    const t = e.target as HTMLElement;
    if (t === dlg || t.closest("[data-cerrar]")) dlg.close();
    if (!ctx) return;
    if (t.closest("[data-csv]")) ctx.csv();
    const b = t.closest<HTMLButtonElement>("[data-pdf-unidad]");
    if (b) {
      b.disabled = true;
      b.textContent = "Generando…";
      try {
        await ctx.pdf();
      } finally {
        b.disabled = false;
        b.textContent = "Descargar reporte (PDF)";
      }
    }
  });
  return dlg;
}

const tabla = (cab: string[], filas: string[][], num: number[] = []) =>
  `<div class="f-tabla"><table><thead><tr>${cab.map((c, i) => `<th${num.includes(i) ? ' class="n"' : ""}>${c}</th>`).join("")}</tr></thead><tbody>${filas
    .map((f) => `<tr>${f.map((c, i) => `<td${num.includes(i) ? ' class="n"' : ""}>${c}</td>`).join("")}</tr>`)
    .join("")}</tbody></table></div>`;

const muestra = (color: string) => `<i class="fu-color" style="background:${color}"></i>`;
const info = (f: FilaClase) =>
  `<button type="button" class="info" data-ficha="${f.clase.codigo}" title="Ver la ficha de la unidad ${f.clase.codigo}" aria-label="Ficha de la unidad ${f.clase.codigo}">i</button>`;

export function abrirFichaUnidad(r: Resumen, c: ContextoFichaUnidad) {
  ctx = c;
  const dlg = dialogo();
  const cuerpo = document.getElementById("ficha-unidad-cuerpo")!;
  const cat = c.cat;
  const dom = r.grupos[0];
  const cifras: [string, string][] = [
    r.filtro !== null ? ["Superficie seleccionada", `${ha(r.seleccion)} ha`] : ["Superficie medida", `${ha(r.total)} ha`],
    ["Clases de ecosistema", String(r.clases.length)],
    r.unidad.id === "HN" || c.capaNombre === "Área protegida" ? ["Grupos nacionales", String(r.grupos.length)] : ["Dentro del SINAPH", pct(r.pctSinaph)],
    ["Grupo dominante", dom ? `${esc(dom.nombre)} (${pct(dom.pct)})` : "-"],
  ];
  const maxG = Math.max(...r.grupos.map((g) => g.pct), 1e-9);
  const barras = r.grupos
    .map(
      (g) => `<div class="barra"><span class="et">${esc(g.codigo)} ${esc(g.nombre)}</span>
        <span class="pista"><span style="width:${Math.max(0.5, (100 * g.pct) / maxG)}%;background:${g.color}"></span></span>
        <span class="val">${ha(g.ha)} ha · ${pct(g.pct)}</span></div>`,
    )
    .join("");
  const filaGET = (f: { codigo: string; nombre: string; ha: number; pct: number }) => [esc(f.codigo), esc(f.nombre), ha(f.ha), pct(f.pct)];

  // clases por grupo nacional
  const porHa = (fs: FilaClase[]) => [...fs].sort((a, b) => b.ha - a.ha);
  const suma = (fs: FilaClase[]) => fs.reduce((s, f) => s + f.ha, 0);
  const cab = (nivel: number, texto: string, fs: FilaClase[]) =>
    `<tr class="fu-n${nivel}"><td colspan="4">${texto}</td><td class="n">${ha(suma(fs), 2)}</td><td class="n">${pct((100 * suma(fs)) / r.total)}</td></tr>`;
  const clase = (f: FilaClase, extra: string) =>
    `<tr><td>${muestra(f.color)}</td><td>${f.codigo}</td><td>${esc(f.nombre)} ${info(f)}</td><td>${extra}</td><td class="n">${ha(f.ha, 2)}</td><td class="n">${pct(f.pct)}</td></tr>`;
  const cabTabla = (extra: string) =>
    `<thead><tr><th></th><th>Código</th><th>Clase de ecosistema</th><th>${extra}</th><th class="n">Hectáreas</th><th class="n">%</th></tr></thead>`;
  let grupos = "";
  for (const g of cat.grupos) {
    const fs = r.clases.filter((f) => f.clase.grupo === g.codigo);
    if (!fs.length) continue;
    grupos += cab(0, `${esc(g.codigo)} ${esc(g.nombre)}`, fs) + porHa(fs).map((f) => clase(f, esc(f.clase.get3) + (f.clase.alt.length ? ` (o ${f.clase.alt.map(esc).join(", ")})` : ""))).join("");
  }
  // clases por jerarquía GET-UICN
  const porCodigo = new Map(r.clases.map((f) => [f.clase.codigo, f]));
  let get = "";
  for (const [k1, biomas] of arbolGET(r.clases.map((f) => f.clase))) {
    const fs1 = [...biomas.values()].flatMap((m) => [...m.values()].flat()).map((x) => porCodigo.get(x.codigo)!);
    get += cab(0, `${k1 === "MULT" ? "" : esc(k1) + " · "}${esc(nombreGET(cat, 0, k1))}`, fs1);
    for (const [k2, efgs] of biomas) {
      const fs2 = [...efgs.values()].flat().map((x) => porCodigo.get(x.codigo)!);
      get += cab(1, `${k2 === "MULT" ? "" : esc(k2) + " · "}${esc(nombreGET(cat, 1, k2))}`, fs2);
      for (const [k3, cl] of efgs) {
        const fs3 = cl.map((x) => porCodigo.get(x.codigo)!);
        const ctxGET = cl.some((x) => rutaGET(x)[3]);
        get += cab(2, `${k3 === "MULT" ? "" : esc(k3) + " · "}${esc(nombreGET(cat, 2, k3))}${ctxGET ? " (relación contextual)" : ""}`, fs3);
        get += porHa(fs3).map((f) => clase(f, esc(f.clase.grupo))).join("");
      }
    }
  }

  cuerpo.innerHTML = enlazarGET(`
    <div class="f-cab">
      <div>
        <p class="f-sobre">${esc(c.capaNombre)} · Mapa de Ecosistemas de Honduras 2026</p>
        <h2 id="ficha-unidad-titulo">${esc(r.unidad.nombre)}</h2>
        <p class="f-meta">${esc(c.contexto)}</p>
      </div>
    </div>
    ${
      r.filtro !== null
        ? `<p class="fu-aviso">Filtro de clases aplicado en el visor: ${r.clases.length} de las ${r.unidad.clases.length} clases de la unidad (${ha(r.seleccion)} ha, ${pct((100 * r.seleccion) / r.total)} de ${ha(r.total)} ha medidas). Los porcentajes se expresan sobre la superficie total de la unidad.</p>`
        : ""
    }
    <dl class="fu-cifras">${cifras.map(([a, b]) => `<div><dt>${a}</dt><dd>${b}</dd></div>`).join("")}</dl>
    <figure class="f-mapa"><div class="fu-mapa"><p class="f-cargando">Preparando el mapa de la unidad…</p></div>
      <figcaption>Ecosistemas de ${esc(r.unidad.nombre)} en el Mapa de Ecosistemas de Honduras 2026.</figcaption></figure>
    <div class="f-texto">
      <h3 class="f-h2">Superficie por grupo nacional</h3>
      <div class="barras fu-barras">${barras}</div>
      <h3 class="f-h2">Tipología Global de Ecosistemas (GET-UICN)</h3>
      ${tabla(["Reino", "Nombre", "Hectáreas", "%"], r.get1.map(filaGET), [2, 3])}
      ${tabla(["Bioma", "Nombre", "Hectáreas", "%"], r.get2.map(filaGET), [2, 3])}
      <p class="f-nota">Las clases con correspondencia a varios grupos funcionales (EFG) se informan como «asignación múltiple» para no contar dos veces la misma superficie.</p>
      <h3 class="f-h2">Clases presentes por grupo nacional</h3>
      <p class="f-nota">Grupo nacional › unidad ecosistémica. Los porcentajes se expresan sobre la superficie total de la unidad. El botón «i» abre la ficha de cada clase.</p>
      <div class="f-tabla"><table class="fu-jer">${cabTabla("GET L3")}<tbody>${grupos}</tbody></table></div>
      <h3 class="f-h2">Clases presentes por jerarquía GET-UICN</h3>
      <p class="f-nota">Reino › Bioma › Grupo funcional (EFG) › unidad ecosistémica. Cada clase figura en su grupo funcional principal (el más probable); la tabla anterior indica también los otros EFG posibles.</p>
      <div class="f-tabla"><table class="fu-jer">${cabTabla("Grupo")}<tbody>${get}</tbody></table></div>
    </div>
    <p class="f-fuente">Superficies medidas sobre el ráster maestro del Mapa de Ecosistemas de Honduras 2026 (celdas de 30 × 30 m). Son superficies cartográficas: los totales nacionales oficiales aplican un ajuste proporcional por dominio que no se reparte por unidad. El reporte PDF incluye la nota metodológica completa y la cita sugerida.</p>`);
  if (!dlg.open) dlg.showModal();
  cuerpo.scrollTop = 0;
  const caja = cuerpo.querySelector<HTMLElement>(".fu-mapa")!;
  c.mapa()
    .then((src) => {
      if (ctx !== c) return; // ya se abrió otra unidad
      caja.innerHTML = `<img src="${src}" alt="Mapa de ecosistemas de ${esc(r.unidad.nombre)}">`;
    })
    .catch(() => (caja.innerHTML = `<p class="f-cargando">No se pudo preparar el mapa.</p>`));
}
