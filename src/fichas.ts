// Catálogo de fichas monográficas por unidad ecosistémica (generadas por datos/03_fichas.py desde los catálogos 2026).
import { ha, pct, url, type Catalogo, type Clase, type Unidad } from "./datos";
import { claseDe } from "./resumen";
import { altHTML, nombreGET, rutaGET } from "./leyenda";

interface Bloque {
  t: "h2" | "h3" | "p" | "li" | "nota" | "tabla";
  x?: string;
  h?: string; // HTML mínimo (<i>, <b>) generado y escapado por el script
  f?: string[][];
}
interface Ficha {
  codigo: number;
  nombre: string;
  titulo: string;
  grupo: string;
  catalogo: string;
  mapa: string | null;
  bloques: Bloque[];
}

const esc = (s: string) => s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]!);
const cache = new Map<number, Promise<Ficha>>();
const cargar = (cod: number) => {
  if (!cache.has(cod)) cache.set(cod, fetch(url(`fichas/${cod}.json`)).then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status))))));
  return cache.get(cod)!;
};

/** Botón pequeño de información que abre la ficha de la clase. */
export const botonInfo = (c: { codigo: number; nombre: string }) =>
  `<button type="button" class="info" data-ficha="${c.codigo}" title="Ver la ficha de ${esc(c.nombre)}" aria-label="Ver la ficha de ${esc(c.nombre)}">i</button>`;

function bloquesHTML(bs: Bloque[]): string {
  let html = "";
  let lista = false;
  let refs = false;
  for (const b of bs) {
    if (b.t !== "li" && lista) {
      html += "</ul>";
      lista = false;
    }
    switch (b.t) {
      case "h2":
        refs = /^Referencias/i.test(b.x!);
        html += `<h3 class="f-h2">${esc(b.x!)}</h3>`;
        break;
      case "h3":
        html += `<h4 class="f-h3">${esc(b.x!)}</h4>`;
        break;
      case "p":
        html += `<p class="${refs ? "f-ref" : ""}">${b.h}</p>`;
        break;
      case "nota":
        html += `<p class="f-nota">${b.h}</p>`;
        break;
      case "li":
        if (!lista) html += "<ul>";
        lista = true;
        html += `<li>${b.h}</li>`;
        break;
      case "tabla": {
        const [cab, ...filas] = b.f!;
        html += `<div class="f-tabla"><table><thead><tr>${cab.map((c) => `<th>${esc(c)}</th>`).join("")}</tr></thead><tbody>${filas
          .map((r) => `<tr>${r.map((c) => `<td>${esc(c)}</td>`).join("")}</tr>`)
          .join("")}</tbody></table></div>`;
        break;
      }
    }
  }
  return html + (lista ? "</ul>" : "");
}

export interface ContextoFicha {
  cat: Catalogo;
  unidad: Unidad | null;
  /** Muestra solo esta clase en el mapa. */
  soloEnMapa: (codigo: number) => void;
}

let ctx: ContextoFicha;
let orden: number[] = [];
let actual = 0;

export function iniciarFichas(c: ContextoFicha) {
  ctx = c;
  // orden de navegación: por grupo nacional y código
  orden = [...c.cat.clases].sort((a, b) => a.grupo.localeCompare(b.grupo) || a.codigo - b.codigo).map((x) => x.codigo);
  const dlg = document.getElementById("ficha") as HTMLDialogElement;
  dlg.addEventListener("click", (e) => {
    const t = e.target as HTMLElement;
    if (t === dlg) dlg.close(); // clic en el fondo
    if (t.closest("[data-cerrar]")) dlg.close();
    const nav = t.closest<HTMLButtonElement>("[data-nav]");
    if (nav) abrirFicha(orden[(orden.indexOf(actual) + Number(nav.dataset.nav) + orden.length) % orden.length]);
    if (t.closest("[data-solo]")) {
      ctx.soloEnMapa(actual);
      dlg.close();
    }
  });
  dlg.addEventListener("keydown", (e) => {
    if (e.key === "ArrowRight" && !(e.target as HTMLElement).closest("input")) abrirFicha(orden[(orden.indexOf(actual) + 1) % orden.length]);
    if (e.key === "ArrowLeft" && !(e.target as HTMLElement).closest("input")) abrirFicha(orden[(orden.indexOf(actual) - 1 + orden.length) % orden.length]);
  });
  // cualquier botón de información de la página abre la ficha
  document.addEventListener("click", (e) => {
    const b = (e.target as HTMLElement).closest<HTMLElement>("[data-ficha]");
    if (!b) return;
    e.preventDefault();
    e.stopPropagation();
    abrirFicha(Number(b.dataset.ficha));
  }, true);
}

export function actualizarUnidadFicha(u: Unidad | null) {
  if (ctx) ctx.unidad = u;
}

function cabecera(c: Clase): string {
  const [g1, g2, g3, contextual] = rutaGET(c);
  const get = [g1, g2, g3]
    .map((cod, i) => `<span title="${esc(nombreGET(ctx.cat, i as 0 | 1 | 2, cod))}">${esc(cod)}</span>`)
    .join(" › ");
  const grupo = ctx.cat.grupos.find((g) => g.codigo === c.grupo);
  const u = ctx.unidad;
  const enU = u?.clases.find(([k]) => k === c.codigo);
  const totalU = u ? u.clases.reduce((s, [, h]) => s + h, 0) : 0;
  return `
    <div class="f-cab">
      <i class="f-color" style="background:${c.color}"></i>
      <div>
        <p class="f-sobre">Unidad ecosistémica ${c.codigo} · ${esc(c.grupo)} ${esc(grupo?.nombre ?? "")}</p>
        <h2 id="ficha-titulo">${esc(c.nombre)}</h2>
        <p class="f-meta">GET-UICN principal: ${get} ${esc(nombreGET(ctx.cat, 2, c.get3))}${contextual ? " · relación contextual" : ""}${
          c.alt.length ? ` · también puede corresponder a ${altHTML(ctx.cat, c)}` : ""
        }</p>${c.criterio ? `<p class="f-meta" title="${esc(c.criterios_alt.split(" | ").join("\n"))}">Criterio de asignación: ${esc(c.criterio)}.</p>` : ""}
        <p class="f-meta">Superficie nacional 2026: <b>${ha(c.ha_ajustada)} ha</b> ajustadas · ${ha(c.ha_cartografiada)} ha cartografiadas${
          u && enU ? ` · En ${esc(u.nombre)}: <b>${ha(enU[1])} ha</b> (${pct((100 * enU[1]) / totalU)})` : ""
        }</p>
      </div>
    </div>`;
}

export async function abrirFicha(cod: number) {
  const dlg = document.getElementById("ficha") as HTMLDialogElement;
  const cuerpo = document.getElementById("ficha-cuerpo")!;
  const c = claseDe(ctx.cat, cod);
  if (!c) return;
  actual = cod;
  cuerpo.innerHTML = cabecera(c) + `<p class="f-cargando">Cargando la ficha…</p>`;
  if (!dlg.open) dlg.showModal();
  cuerpo.scrollTop = 0;
  try {
    const f = await cargar(cod);
    if (actual !== cod) return; // el usuario ya pasó a otra ficha
    cuerpo.innerHTML =
      cabecera(c) +
      (f.mapa ? `<figure class="f-mapa"><img src="${url(f.mapa)}" alt="Mapa de distribución de la unidad ${cod} en Honduras" loading="lazy"><figcaption>Distribución de la unidad ${cod} en el Mapa de Ecosistemas 2026.</figcaption></figure>` : "") +
      `<div class="f-texto">${bloquesHTML(f.bloques)}</div>
       <p class="f-fuente">Fuente: Catálogo de unidades ecosistémicas del Mapa de Ecosistemas 2026 (${esc(f.catalogo.replace(/_R26$/, "").replace(/_/g, " "))}). Las fotografías de campo y los gráficos se consultan en el catálogo completo.</p>`;
    cuerpo.scrollTop = 0;
  } catch {
    cuerpo.querySelector(".f-cargando")!.textContent = "No se pudo cargar la ficha.";
  }
}

/** Lista del catálogo (pestaña Catálogo): grupos nacionales con sus fichas. */
export function htmlCatalogo(cat: Catalogo, filtro: string): string {
  const plano = (s: string) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  const q = plano(filtro.trim());
  return cat.grupos
    .map((g) => {
      const cl = cat.clases
        .filter((c) => c.grupo === g.codigo && (!q || plano(`${c.codigo} ${c.nombre}`).includes(q)))
        .sort((a, b) => a.codigo - b.codigo);
      if (!cl.length) return "";
      return `<h3 class="cat-grupo">${esc(g.codigo)} ${esc(g.nombre)} <small>${cl.length}</small></h3><ul class="cat-lista">${cl
        .map(
          (c) =>
            `<li><button type="button" data-ficha="${c.codigo}"><i style="background:${c.color}"></i><span><b>${c.codigo}</b> ${esc(c.nombre)}</span><span class="info" aria-hidden="true">i</span></button></li>`,
        )
        .join("")}</ul>`;
    })
    .join("") || `<p class="nota">Ninguna ficha coincide con la búsqueda.</p>`;
}
