import maplibregl, { type Map as MapaML, type MapGeoJSONFeature } from "maplibre-gl";
import { htmlPunto, puntoEn } from "./puntos";
import "./estilos.css";
import { CAPAS, cargarCatalogo, cargarManifiesto, cargarUnidades, fechaLarga, ha, pct, type Catalogo, type ClaveCapa, type Manifiesto, type Unidad } from "./datos";
import { capturar, crearMapa, encuadrar, limites, mostrarCapa, refrescarEcosistemas, seleccionar } from "./mapa";
import { claseDe, colorDeGrupo, csv, descargar, resumir, slug, unidadNacional, type Resumen } from "./resumen";
import { codigoEn, fijarColores, registrarProtocolo } from "./teselas";
import { capaActiva, criteriosEn, iniciarComparacion, registrarProtocoloComparacion, valorEn } from "./comparar";
import { htmlGrupos, htmlLeyenda, nombreGET } from "./leyenda";
import { abrirFicha, actualizarUnidadFicha, botonInfo, descargarFichaPDF, htmlCatalogo, iniciarFichas } from "./fichas";

const $ = <T extends HTMLElement = HTMLElement>(id: string) => document.getElementById(id) as T;
const esc = (s: string) => s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]!);
const plano = (s: string) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

interface Estado {
  cat: Catalogo;
  man: Manifiesto;
  mapa: MapaML;
  capa: ClaveCapa | null; // null: ninguna unidad de reporte elegida, sin límites en el mapa
  unidades: Unidad[];
  deptos: Map<string, string>;
  sel: Unidad | null;
  visibles: Set<number>;
}
let E: Estado;

// ---------------------------------------------------------------- arranque
async function iniciar() {
  registrarProtocolo();
  registrarProtocoloComparacion();
  const [cat, man, mapa, deptos] = await Promise.all([cargarCatalogo(), cargarManifiesto(), crearMapa("mapa"), cargarUnidades("departamentos")]);
  E = {
    cat, man, mapa,
    capa: null,
    unidades: [],
    deptos: new Map(deptos.map((d) => [d.id, d.nombre])),
    sel: null,
    visibles: new Set(cat.clases.map((c) => c.codigo)),
  };
  if (import.meta.env.DEV) (window as unknown as { __mapa: MapaML }).__mapa = mapa; // solo para pruebas locales
  refrescarEcosistemas(mapa, fijarColores(cat.clases, E.visibles));
  void iniciarComparacion(mapa);
  construirCapas();
  construirArbol();
  $("arbol-get").innerHTML = htmlLeyenda(cat);
  $("arbol-grupos").innerHTML = htmlGrupos(cat, (g) => colorDeGrupo(cat, g));
  modoLeyenda(leerModo());
  construirAcerca();
  iniciarFichas({
    cat,
    unidad: null,
    soloEnMapa: (cod) => {
      E.visibles = new Set([cod]);
      aplicarVisibles();
    },
  });
  $("lista-catalogo").innerHTML = htmlCatalogo(cat, "");
  $("buscar-ficha").addEventListener("input", (e) => ($("lista-catalogo").innerHTML = htmlCatalogo(cat, (e.target as HTMLInputElement).value)));
  enlazarEventos();
  plegarLeyenda(true); // el mapa empieza con todo el espacio; la leyenda se abre con su botón

  const q = new URLSearchParams(location.search);
  const capa = q.get("capa") as ClaveCapa | null;
  // sin ?capa= en la dirección no se elige ninguna unidad de reporte: el mapa empieza sin límites
  if (capa && CAPAS.some((c) => c.clave === capa && c.disponible)) await cambiarCapa(capa, false);
  else pintarLista();
  const id = q.get("id");
  const u = id ? E.unidades.find((x) => x.id === id) : null;
  if (u) await elegir(u);
  else pintarResumen();
  // enlaces directos: ?ficha=1112 abre la ficha; &descargar=pdf descarga la ficha o el reporte de la unidad
  const pdf = q.get("descargar") === "pdf";
  const ficha = Number(q.get("ficha"));
  if (pdf) {
    const limpio = new URLSearchParams(location.search);
    limpio.delete("descargar"); // al recargar no se vuelve a descargar
    history.replaceState(null, "", limpio.toString() ? `?${limpio}` : location.pathname);
  }
  if (ficha && claseDe(E.cat, ficha)) {
    await abrirFicha(ficha);
    if (pdf) {
      aviso("Descargando la ficha en PDF…");
      await descargarFichaPDF(ficha);
    }
  } else if (u && pdf) {
    aviso("Generando el reporte PDF de la unidad…");
    $<HTMLButtonElement>("btn-pdf").click();
  }
}

// ---------------------------------------------------------------- capas y lista
function construirCapas() {
  $("selector-capas").innerHTML = CAPAS.map(
    (c) => `<button type="button" data-capa="${c.clave}" ${c.disponible ? "" : 'aria-disabled="true"'} title="${esc(c.nota ?? c.nombre)}">${esc(c.nombre)}${c.disponible ? "" : ' <span class="pendiente">pendiente</span>'}</button>`,
  ).join("");
  const sel = $<HTMLSelectElement>("sel-depto");
  sel.innerHTML = `<option value="">Todos los departamentos</option>` + [...E.deptos].sort((a, b) => a[1].localeCompare(b[1], "es")).map(([id, n]) => `<option value="${id}">${esc(n)}</option>`).join("");
}

async function cambiarCapa(pedida: ClaveCapa, limpiar = true) {
  const def = CAPAS.find((c) => c.clave === pedida)!;
  if (!def.disponible) {
    aviso(def.nota!);
    return;
  }
  // un segundo clic sobre la unidad activa la desactiva y quita sus límites del mapa
  const capa = E.capa === pedida && limpiar ? null : pedida;
  E.capa = capa;
  document.querySelectorAll<HTMLButtonElement>("#selector-capas button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.capa === capa)));
  $("filtro-depto").hidden = capa !== "municipios";
  $("campo-buscar").hidden = !capa;
  const unidades = capa ? await cargarUnidades(capa) : [];
  if (E.capa !== capa) return; // el usuario ya eligió otra capa
  E.unidades = unidades;
  await mostrarCapa(E.mapa, capa);
  if (E.capa !== capa) return;
  if (limpiar) await elegir(null);
  pintarLista();
}

function pintarLista() {
  if (!E.capa) {
    $("lista-filtro").hidden = true;
    $("lista").innerHTML = `<li class="vacio">Elija una unidad de reporte para ver sus límites en el mapa y la lista de unidades.</li>`;
    return;
  }
  const texto = plano($<HTMLInputElement>("buscar").value.trim());
  const depto = E.capa === "municipios" ? $<HTMLSelectElement>("sel-depto").value : "";
  const filtro = E.visibles.size < E.cat.clases.length;
  // con filtro de clases: solo las unidades que contienen alguna clase activa, ordenadas por esa superficie
  const filas = E.unidades
    .filter((u) => (!depto || u.padre === depto) && (!texto || plano(u.nombre).includes(texto)))
    .map((u) => ({ u, sel: filtro ? u.clases.reduce((s, [c, h]) => (E.visibles.has(c) ? s + h : s), 0) : u.ha }))
    .filter((x) => !filtro || x.sel > 0);
  if (filtro) filas.sort((a, b) => b.sel - a.sel);
  const def = CAPAS.find((c) => c.clave === E.capa)!;
  $("lista-filtro").hidden = !filtro;
  $("lista-filtro").textContent = filtro
    ? `Filtro de clases activo: ${filas.length} de ${E.unidades.length} ${def.nombre.toLowerCase()} contienen las clases seleccionadas, ordenadas por su superficie.`
    : "";
  $("lista").innerHTML =
    filas
      .map(
        ({ u, sel }) =>
          `<li><button type="button" data-id="${esc(u.id)}" aria-current="${E.sel?.id === u.id}"><span>${esc(u.nombre)}</span><small>${
            E.capa === "municipios"
              ? esc(E.deptos.get(u.padre) ?? "") + " · "
              : E.capa === "areas_protegidas" || E.capa === "pueblos_indigenas" || E.capa === "subcuencas" || E.capa === "microcuencas"
                ? esc(u.categoria.replace(/^Microcuenca declarada · /, "")) + " · "
                : ""
          }${filtro ? `${ha(sel)} ha de la selección (${pct((100 * sel) / u.ha)})` : `${ha(u.ha)} ha`}</small></button></li>`,
      )
      .join("") ||
    `<li class="vacio">${filtro ? `Ninguna unidad contiene las clases seleccionadas${texto || depto ? " con esos criterios" : ""}.` : `No hay ${def.nombre.toLowerCase()} con ese nombre.`}</li>`;
}

// ---------------------------------------------------------------- selección y resumen
async function elegir(u: Unidad | null) {
  E.sel = u;
  const fc = E.capa ? await limites(E.capa) : null;
  const f = u && fc ? (fc.features.find((x) => x.properties?.id === u.id) ?? null) : null;
  seleccionar(E.mapa, f);
  if (u) encuadrar(E.mapa, u.bbox);
  const q = new URLSearchParams();
  if (u && E.capa) {
    q.set("capa", E.capa);
    q.set("id", u.id);
  }
  history.replaceState(null, "", q.toString() ? `?${q}` : location.pathname);
  $<HTMLButtonElement>("clases-presentes").disabled = !u;
  actualizarUnidadFicha(u);
  marcarPresentes();
  pintarLista();
  document.querySelector('#lista [aria-current="true"]')?.scrollIntoView({ block: "nearest" });
  pintarResumen();
  if (u && matchMedia("(max-width: 800px)").matches) $("resumen").scrollIntoView({ behavior: "smooth" });
}

function contextoDe(u: Unidad): string {
  if (u.id === "HN") return "Territorio nacional, continente, islas y espacio marino";
  if (E.capa === "municipios") return `Municipio del departamento de ${E.deptos.get(u.padre) ?? "-"}`;
  if (E.capa === "departamentos") return "Departamento";
  if (E.capa === "pueblos_indigenas") return `${u.categoria} · Pueblos indígenas y afrohondureños de Honduras`;
  if (E.capa === "cuencas") return "Cuenca hidrográfica";
  if (E.capa === "subcuencas" || E.capa === "microcuencas") return u.categoria;
  return `${u.categoria} · Sistema Nacional de Áreas Protegidas (SINAPH)`;
}

function nombreCapa(u: Unidad) {
  return u.id === "HN" ? "País" : (CAPAS.find((c) => c.clave === E.capa)?.singular ?? "Unidad");
}

function pintarResumen() {
  const u = E.sel ?? unidadNacional(E.cat);
  const r = resumir(E.cat, u, E.visibles);
  const nacional = !E.sel;
  const filtrado = r.filtro !== null;
  const barras = r.grupos
    .map(
      (g) => `<div class="barra" title="${esc(g.nombre)}: ${ha(g.ha)} ha">
        <span class="et">${esc(g.nombre)}</span>
        <span class="pista"><span style="width:${Math.max(0.5, (100 * g.pct) / Math.max(r.grupos[0].pct, 1e-9))}%;background:${g.color}"></span></span>
        <span class="val">${pct(g.pct)}</span></div>`,
    )
    .join("");
  const filas = r.clases
    .map(
      (f, i) => `<tr class="${i >= 10 ? "extra" : ""}"><td><i style="background:${f.color}"></i></td><td>${f.codigo}</td><td>${esc(f.nombre)} ${botonInfo(f.clase)}</td><td class="n">${ha(f.ha)}</td><td class="n">${pct(f.pct)}</td></tr>`,
    )
    .join("");
  const reinos = r.get1.map((g) => `<span class="chip" title="${esc(g.nombre)}">${esc(g.codigo)} · ${pct(g.pct)}</span>`).join("");
  $("resumen").innerHTML = `
    <div class="cab-resumen">
      <p class="sobre">${esc(nombreCapa(u))}</p>
      <h2>${esc(u.nombre)}</h2>
      <p class="sub">${esc(contextoDe(u))}</p>
    </div>
    ${
      filtrado
        ? `<div class="aviso-filtro"><p>Filtro de clases activo: ${r.clases.length} de las ${u.clases.length} clases de la unidad. Los porcentajes son sobre la superficie total.</p><button id="btn-sin-filtro" class="btn enlace">Quitar filtro</button></div>`
        : ""
    }
    <dl class="cifras">
      ${
        filtrado
          ? `<div><dt>Superficie seleccionada</dt><dd>${ha(r.seleccion)} ha</dd><dd class="sub-cifra">${pct((100 * r.seleccion) / r.total)} de ${ha(r.total)} ha</dd></div>`
          : `<div><dt>Superficie medida</dt><dd>${ha(r.total)} ha</dd></div>`
      }
      <div><dt>Clases</dt><dd>${r.clases.length}</dd></div>
      ${nacional || E.capa === "areas_protegidas" ? `<div><dt>Grupos</dt><dd>${r.grupos.length}</dd></div>` : `<div><dt>En el SINAPH</dt><dd>${pct(r.pctSinaph)}</dd></div>`}
    </dl>
    <div class="acciones">
      <button id="btn-pdf" class="btn primario"${r.clases.length ? "" : " disabled"}>Reporte PDF</button>
      <button id="btn-csv" class="btn"${r.clases.length ? "" : " disabled"}>CSV</button>
      ${nacional ? "" : `<button id="btn-quitar" class="btn">Quitar selección</button>`}
    </div>
    <h3>Grupos nacionales</h3>
    <div class="barras">${barras}</div>
    <h3>Reinos GET-UICN</h3>
    <div class="chips">${reinos}</div>
    <h3>Clases <small>(${r.clases.length})</small></h3>
    <table class="tabla-clases"><thead><tr><th></th><th>Cód.</th><th>Clase</th><th class="n">ha</th><th class="n">%</th></tr></thead><tbody>${filas}</tbody></table>
    ${r.clases.length > 10 ? `<button id="btn-mas" class="btn enlace">Ver las ${r.clases.length} clases</button>` : ""}
    ${nacional ? `<p class="nota">Sin unidad seleccionada se muestra el total nacional cartografiado. Elija una unidad en la lista o en el mapa.</p>` : ""}`;
  $("btn-pdf").onclick = () => generarPDF(r);
  $("btn-csv").onclick = () => descargar(new Blob([csv(r, nombreCapa(u), E.cat)], { type: "text/csv;charset=utf-8" }), `ecosistemas_2026_${slug(u.nombre)}.csv`);
  const q = document.getElementById("btn-quitar");
  if (q) q.onclick = () => elegir(null);
  const sf = document.getElementById("btn-sin-filtro");
  if (sf) sf.onclick = () => {
    E.visibles = new Set(E.cat.clases.map((c) => c.codigo));
    aplicarVisibles();
  };
  const m = document.getElementById("btn-mas");
  if (m) m.onclick = () => {
    $("resumen").classList.toggle("todas");
    m.textContent = $("resumen").classList.contains("todas") ? "Ver solo las 10 principales" : `Ver las ${r.clases.length} clases`;
  };
}

async function generarPDF(r: Resumen) {
  const boton = $<HTMLButtonElement>("btn-pdf");
  boton.disabled = true;
  boton.textContent = "Generando…";
  try {
    const [{ crearPDF }, mapa] = await Promise.all([import("./reporte"), capturar(E.mapa, E.sel ? E.sel.bbox : null)]);
    const doc = crearPDF({ resumen: r, capaNombre: nombreCapa(r.unidad), contexto: contextoDe(r.unidad), mapa, catalogo: E.cat, manifiesto: E.man });
    descargar(doc.output("blob"), `Reporte_ecosistemas_2026_${slug(r.unidad.nombre)}.pdf`);
  } catch (e) {
    console.error(e);
    aviso("No se pudo generar el PDF. Intente de nuevo.");
  } finally {
    boton.disabled = false;
    boton.textContent = "Reporte PDF";
  }
}

// ---------------------------------------------------------------- filtro de clases
function construirArbol() {
  const html = E.cat.grupos
    .map((g) => {
      const cl = E.cat.clases.filter((c) => c.grupo === g.codigo);
      return `<details class="grupo"><summary><input type="checkbox" data-codigos="${cl.map((c) => c.codigo).join(",")}" checked aria-label="${esc(g.nombre)}">
        <i style="background:${colorDeGrupo(E.cat, g.codigo)}"></i><span>${g.codigo} ${esc(g.nombre)}</span><small>${cl.length}</small></summary>
        <ul>${cl
          .map(
            (c) => `<li><label><input type="checkbox" data-clase="${c.codigo}" checked><i style="background:${c.color}"></i><span><b>${c.codigo}</b> ${esc(c.nombre)}</span></label>${botonInfo(c)}</li>`,
          )
          .join("")}</ul></details>`;
    })
    .join("");
  $("arbol-clases").innerHTML = html;
}

function aplicarVisibles() {
  document.querySelectorAll<HTMLInputElement>("[data-clase]").forEach((i) => (i.checked = E.visibles.has(+i.dataset.clase!)));
  document.querySelectorAll<HTMLInputElement>("[data-codigos]").forEach((i) => {
    const cl = codigosDe(i);
    const n = cl.filter((c) => E.visibles.has(c)).length;
    i.checked = n === cl.length;
    i.indeterminate = n > 0 && n < cl.length;
  });
  const todas = E.visibles.size === E.cat.clases.length;
  $("ley-todo").textContent = todas ? "Desactivar todo" : "Activar todo";
  $("ley-todo").classList.toggle("primario", todas);
  refrescarEcosistemas(E.mapa, fijarColores(E.cat.clases, E.visibles));
  pintarLista();
  pintarResumen();
}

// ---------------------------------------------------------------- leyenda: jerarquía nacional o GET-UICN
type ModoLeyenda = "grupos" | "get";
function leerModo(): ModoLeyenda {
  try {
    return localStorage.getItem("leyenda-modo") === "grupos" ? "grupos" : "get";
  } catch {
    return "get";
  }
}
function modoLeyenda(modo: ModoLeyenda) {
  document.querySelectorAll<HTMLButtonElement>(".ley-modos button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.modo === modo)));
  document.querySelectorAll<HTMLElement>("#leyenda [data-para]").forEach((el) => (el.hidden = el.dataset.para !== modo));
  try {
    localStorage.setItem("leyenda-modo", modo);
  } catch {
    /* sin almacenamiento: no se recuerda la elección */
  }
}
const arbolActivo = () => document.querySelector<HTMLElement>("#leyenda .arbol:not([hidden])")!;

const codigosDe = (i: HTMLInputElement) => i.dataset.codigos!.split(",").map(Number);

/** Casillas de clase o de grupo (pestaña Clases y leyenda GET comparten el mismo estado). */
function alCambiarCasilla(e: Event) {
  const i = e.target as HTMLInputElement;
  if (i.dataset.clase) i.checked ? E.visibles.add(+i.dataset.clase) : E.visibles.delete(+i.dataset.clase);
  else if (i.dataset.codigos) for (const c of codigosDe(i)) i.checked ? E.visibles.add(c) : E.visibles.delete(c);
  else return;
  aplicarVisibles();
}

/** Marca en la leyenda las clases ausentes de la unidad seleccionada. */
function marcarPresentes() {
  const pres = E.sel ? new Set(E.sel.clases.map(([c]) => c)) : null;
  document.querySelectorAll<HTMLElement>("#leyenda [data-li]").forEach((li) => li.classList.toggle("ausente", !!pres && !pres.has(+li.dataset.li!)));
  const solo = $<HTMLInputElement>("ley-solo");
  solo.disabled = !pres;
  if (!pres) solo.checked = false;
  $("leyenda").classList.toggle("solo", solo.checked);
}

// ---------------------------------------------------------------- acerca de
function construirAcerca() {
  const f = E.man.fuentes;
  $("acerca").innerHTML = `
    <h2>Acerca de este geovisor</h2>
    <p>Presenta el <b>Mapa de Ecosistemas de Honduras 2026</b>: 115 clases nacionales en 14 grupos, cartografiadas a 30 m, con su correspondencia a la Tipología Global de Ecosistemas de la UICN.</p>
    <p>Elija una unidad (área protegida, pueblo indígena, departamento, municipio, cuenca, subcuenca o microcuenca declarada) para ver qué ecosistemas contiene y descargar su reporte en PDF o sus cifras en CSV. Un clic en el mapa identifica la clase de ecosistema de ese punto.</p>
    <h3>Cómo se calculan las superficies</h3>
    <p>Se cuentan las celdas de 30 × 30 m (0.09 ha) del ráster maestro cuyo centro cae dentro de cada unidad. Son superficies cartográficas. Los totales nacionales oficiales aplican un ajuste proporcional por dominio que no se reparte por unidad.</p>
    <h3>Fuentes</h3>
    <ul>
      <li>Ecosistemas: ${esc(E.man.raster.archivo)} (sha256 ${E.man.raster.sha256.slice(0, 12)}…).</li>
      <li>Manglares ajustados por costa: 1,459.5 ha de manglar alto (6261 → 6262) y 11.2 ha de manglar bajo (6271 → 6272) del Golfo de Fonseca pasan a las clases del Pacífico, y 7.3 ha de la costa norte (6272 → 6271) a la del Caribe. El ajuste está incluido en el ráster maestro de la entrega.</li>
      <li>Áreas protegidas: ${esc(f.areas_protegidas ?? "")}.</li>
      <li>Departamentos y municipios: ${esc(f.municipios ?? "")}.</li>
      <li>Pueblos indígenas y afrohondureños: ${esc(f.pueblos_indigenas ?? "")}. La superficie se mide solo dentro del mapa 2026 (territorio y espacio marino de Honduras).</li>
      <li>Cuencas y subcuencas: ${esc(f.cuencas ?? "")}; ${esc(f.subcuencas ?? "")}.</li>
      <li>Microcuencas declaradas: ${esc(f.microcuencas ?? "")}. Pueden solaparse; cada una cuenta su superficie completa.</li>
    </ul>
    <h3>Créditos</h3>
    <div class="creditos-logos">
      <img src="logos/logos_institucionales.png" alt="Cooperación alemana (BMZ), KfW, UICN, CCAD y SICA" />
      <img src="logos/logo_serna.png" alt="Secretaría de Recursos Naturales y Ambiente (SERNA), Dirección General de Biodiversidad (DiBio)" />
    </div>
    <p>Estudio realizado en el marco del <b>Programa de Biodiversidad Enlazando el Paisaje Centroamericano</b>, financiado por el Gobierno de la República Federal de Alemania por medio del Ministerio Federal de Cooperación Económica y Desarrollo (BMZ) y el KfW, implementado por la Unión Internacional para la Conservación de la Naturaleza (UICN), con el apoyo de UICN Honduras, y coordinado regionalmente con la Comisión Centroamericana de Ambiente y Desarrollo (CCAD) del SICA.</p>
    <p>Contraparte nacional oficial: Secretaría de Recursos Naturales y Ambiente (SERNA), Dirección General de Biodiversidad (DiBio).</p>
    <p>Elaborado bajo contrato por:</p>
    <div class="creditos-logos"><img class="logo-ing" src="logos/logo_intelsig.png" alt="INGTELSIG" /></div>
    <h3>Cita sugerida</h3>
    <p>INGTELSIG (2026). Actualización del Mapa de Ecosistemas de Honduras. Informe Técnico Final. Programa de Biodiversidad Enlazando el Paisaje Centroamericano, UICN, y SERNA–DiBio.</p>
    <p class="nota">Datos generados el ${esc(fechaLarga(E.man.generado))}. La aplicación es estática y sus datos se sirven desde este mismo sitio; los mapas base (Esri y EOX) y el relieve 3D (teselas de elevación de AWS) se cargan desde servicios externos.</p>`;
}

// ---------------------------------------------------------------- eventos
let popup: maplibregl.Popup | null = null;
let hover: string | number | undefined;

function enlazarEventos() {
  document.querySelectorAll<HTMLButtonElement>('[role="tab"]').forEach((t) =>
    t.addEventListener("click", () => {
      document.querySelectorAll<HTMLButtonElement>('[role="tab"]').forEach((o) => {
        o.setAttribute("aria-selected", String(o === t));
        $(o.getAttribute("aria-controls")!).hidden = o !== t;
      });
    }),
  );
  $("selector-capas").addEventListener("click", (e) => {
    const b = (e.target as HTMLElement).closest<HTMLButtonElement>("button[data-capa]");
    if (b) cambiarCapa(b.dataset.capa as ClaveCapa);
  });
  $("buscar").addEventListener("input", pintarLista);
  $("sel-depto").addEventListener("change", pintarLista);
  $("lista").addEventListener("click", (e) => {
    const b = (e.target as HTMLElement).closest<HTMLButtonElement>("button[data-id]");
    if (b) elegir(E.unidades.find((u) => u.id === b.dataset.id) ?? null);
  });
  $("btn-panel").addEventListener("click", () => {
    const p = $("panel");
    p.classList.toggle("oculto");
    $("btn-panel").setAttribute("aria-expanded", String(!p.classList.contains("oculto")));
    setTimeout(() => E.mapa.resize(), 250);
  });

  // filtro de clases
  for (const id of ["arbol-clases", "arbol-get", "arbol-grupos"]) {
    $(id).addEventListener("change", alCambiarCasilla);
    // la casilla dentro de <summary> no debe abrir ni cerrar el grupo
    $(id).addEventListener("click", (e) => {
      if ((e.target as HTMLElement).matches("summary input")) e.stopPropagation();
    });
  }

  // leyenda derecha
  $("btn-leyenda").addEventListener("click", () => plegarLeyenda(!$("leyenda").classList.contains("plegada")));
  $("ley-solo").addEventListener("change", marcarPresentes);
  $("ley-expandir").onclick = () => arbolActivo().querySelectorAll("details").forEach((d) => (d.open = true));
  $("ley-contraer").onclick = () => {
    const get = arbolActivo().id === "arbol-get"; // en GET-UICN los reinos quedan abiertos
    arbolActivo().querySelectorAll("details").forEach((d) => (d.open = get && d.classList.contains("n1")));
  };
  document.querySelector(".ley-modos")!.addEventListener("click", (e) => {
    const b = (e.target as HTMLElement).closest<HTMLButtonElement>("button[data-modo]");
    if (b) modoLeyenda(b.dataset.modo as ModoLeyenda);
  });
  $("ley-todo").onclick = () => {
    E.visibles = E.visibles.size === E.cat.clases.length ? new Set() : new Set(E.cat.clases.map((c) => c.codigo));
    aplicarVisibles();
  };
  $("clases-todas").onclick = () => {
    E.visibles = new Set(E.cat.clases.map((c) => c.codigo));
    aplicarVisibles();
  };
  $("clases-ninguna").onclick = () => {
    E.visibles.clear();
    aplicarVisibles();
  };
  $("clases-presentes").onclick = () => {
    if (!E.sel) return;
    E.visibles = new Set(E.sel.clases.map(([c]) => c));
    aplicarVisibles();
  };
  const opacidad = $<HTMLInputElement>("opacidad");
  opacidad.addEventListener("input", () => {
    E.mapa.setPaintProperty("ecosistemas", "raster-opacity", +opacidad.value);
    document.dispatchEvent(new CustomEvent("opacidad-eco", { detail: { valor: +opacidad.value, origen: "panel" } }));
  });
  document.addEventListener("opacidad-eco", (ev) => {
    const { valor, origen } = (ev as CustomEvent<{ valor: number; origen: string }>).detail;
    if (origen !== "panel") opacidad.value = String(Math.max(0.2, valor));
  });

  // mapa: resaltar unidades y consultar la clase
  const m = E.mapa;
  m.on("mousemove", "unidades-relleno", (e) => {
    const id = e.features?.[0]?.id;
    if (id === hover) return;
    if (hover !== undefined) m.setFeatureState({ source: "unidades", id: hover }, { hover: false });
    hover = id;
    if (id !== undefined) m.setFeatureState({ source: "unidades", id }, { hover: true });
  });
  m.on("mouseleave", "unidades-relleno", () => {
    if (hover !== undefined) m.setFeatureState({ source: "unidades", id: hover }, { hover: false });
    hover = undefined;
  });
  m.on("click", async (e) => {
    const pt = puntoEn(m, e.point);
    if (pt) {
      popup?.remove();
      popup = new maplibregl.Popup({ maxWidth: "min(360px, calc(100vw - 24px))", className: "pop-punto" }).setLngLat((pt.geometry as GeoJSON.Point).coordinates as [number, number]).setHTML(htmlPunto(pt)).addTo(m);
      return;
    }
    const [cod, f] = await Promise.all([
      codigoEn(e.lngLat.lng, e.lngLat.lat, m.getZoom()),
      Promise.resolve(m.queryRenderedFeatures(e.point, { layers: ["unidades-relleno"] })[0] as MapGeoJSONFeature | undefined),
    ]);
    const c = cod ? claseDe(E.cat, cod) : undefined;
    const act = capaActiva();
    const vAct = act ? await valorEn(act, e.lngLat.lng, e.lngLat.lat, m.getZoom()).catch(() => null) : null;
    const nomU = f?.properties?.nombre as string | undefined;
    const html = `${
      c
        ? `<div class="pop-clase"><i style="background:${c.color}"></i><div><b>${c.codigo} · ${esc(c.nombre)}</b> ${botonInfo(c)}
           <small>Grupo ${c.grupo} · GET ${esc(c.get3)} ${esc(nombreGET(E.cat, 2, c.get3))}${c.alt.length ? ` (también ${esc(c.alt.join(", "))})` : ""}</small></div></div>`
        : `<p class="pop-vacio">Sin clase de ecosistema en este punto.</p>`
    }${act ? `<p class="pop-cmp"><span>${esc(act.nombre)}:</span> ${vAct ? `${vAct.color ? `<i style="background:${vAct.color}"></i>` : ""}<b>${esc(vAct.texto)}</b>` : "sin dato"}</p>` : ""}<p class="pop-crit"><button class="btn enlace" data-criterios>Ver criterios ecológicos en este punto</button></p><div class="pop-crit-tabla"></div>${nomU ? `<p class="pop-unidad">${esc(nomU)} <button class="btn enlace" data-ver="${esc(String(f!.properties!.id))}">Ver resumen</button></p>` : ""}`;
    popup?.remove();
    popup = new maplibregl.Popup({ maxWidth: "min(320px, calc(100vw - 24px))" }).setLngLat(e.lngLat).setHTML(html).addTo(m);
    const pe = popup.getElement();
    pe.querySelector<HTMLButtonElement>("[data-criterios]")?.addEventListener("click", async (ev) => {
      const b = ev.currentTarget as HTMLButtonElement;
      b.disabled = true;
      b.textContent = "Leyendo capas…";
      pe.querySelector(".pop-crit-tabla")!.innerHTML = await criteriosEn(e.lngLat.lng, e.lngLat.lat, m.getZoom());
      b.parentElement!.remove();
    });
    pe.querySelector<HTMLButtonElement>("[data-ver]")?.addEventListener("click", (ev) => {
      const id = (ev.currentTarget as HTMLButtonElement).dataset.ver;
      popup?.remove();
      elegir(E.unidades.find((u) => u.id === id) ?? null);
    });
  });
}

function plegarLeyenda(plegar: boolean) {
  $("leyenda").classList.toggle("plegada", plegar);
  $("btn-leyenda").setAttribute("aria-expanded", String(!plegar));
  setTimeout(() => E.mapa.resize(), 220);
}

let tAviso: number | undefined;
function aviso(t: string) {
  const a = $("aviso");
  a.textContent = t;
  a.hidden = false;
  clearTimeout(tAviso);
  tAviso = window.setTimeout(() => (a.hidden = true), 5000);
}

iniciar().catch((e) => {
  console.error(e);
  aviso("No se pudieron cargar los datos del geovisor.");
});
