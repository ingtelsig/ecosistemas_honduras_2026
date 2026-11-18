// Comparación del mapa R26 con los criterios ecológicos base y con el Mapa de Ecosistemas 2002.
// Cada capa es un PMTiles con un índice de 8 bits por píxel (canal rojo; 0 = sin dato) que el navegador
// colorea con su tabla. Un segundo mapa, sincronizado y recortado, muestra la capa al otro lado de una cortina.
import maplibregl, { addProtocol, type Map as MapaML, type StyleSpecification } from "maplibre-gl";
import { PMTiles } from "pmtiles";
import { url } from "./datos";

const esc = (s: string) => s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]!);

export interface ClaseCmp { v: number; n: string; c: string; une?: string; r26?: number }
export interface CapaCmp {
  id: string;
  nombre: string;
  grupo: string;
  fuente: string;
  tipo: "continua" | "clases";
  zmax: number;
  archivo: string;
  unidad?: string;
  min?: number;
  max?: number;
  f?: "lineal" | "raiz";
  decimales?: number;
  umbrales?: { v: number; n: string }[];
  nota?: string;
  rampa?: string[];
  lut?: string[];
  clases?: ClaseCmp[];
  desplazamiento?: number;
  MB?: number;
}

const LADO = 256;
let capas: CapaCmp[] = [];
const porId = new Map<string, CapaCmp>();
const archivos = new Map<string, PMTiles>();
const luts = new Map<string, Uint8ClampedArray>();
const cache = new Map<string, Promise<Uint8Array | null>>();
const ORDEN: string[] = [];

export async function cargarCapas(): Promise<CapaCmp[]> {
  if (capas.length) return capas;
  try {
    const r = await fetch(url("capas/capas.json"));
    if (!r.ok) return [];
    capas = (await r.json()).capas as CapaCmp[];
  } catch {
    return [];
  }
  for (const c of capas) {
    porId.set(c.id, c);
    const lut = new Uint8ClampedArray(256 * 4);
    const pon = (i: number, hex: string) => {
      lut[i * 4] = parseInt(hex.slice(1, 3), 16);
      lut[i * 4 + 1] = parseInt(hex.slice(3, 5), 16);
      lut[i * 4 + 2] = parseInt(hex.slice(5, 7), 16);
      lut[i * 4 + 3] = 255;
    };
    if (c.tipo === "continua") c.lut!.forEach((hex, k) => pon(k + 1, hex));
    else for (const k of c.clases!) pon(k.v + (c.desplazamiento ?? 0), k.c);
    luts.set(c.id, lut);
  }
  return capas;
}

let lienzo: OffscreenCanvas | HTMLCanvasElement | null = null;
function contexto() {
  if (!lienzo) lienzo = typeof OffscreenCanvas !== "undefined" ? new OffscreenCanvas(LADO, LADO) : Object.assign(document.createElement("canvas"), { width: LADO, height: LADO });
  return lienzo.getContext("2d", { willReadFrequently: true }) as CanvasRenderingContext2D | OffscreenCanvasRenderingContext2D;
}

function indicesTesela(id: string, z: number, x: number, y: number): Promise<Uint8Array | null> {
  const k = `${id}/${z}/${x}/${y}`;
  let p = cache.get(k);
  if (!p) {
    p = (async () => {
      let pm = archivos.get(id);
      if (!pm) archivos.set(id, (pm = new PMTiles(url(porId.get(id)!.archivo))));
      const r = await pm.getZxy(z, x, y);
      if (!r) return null;
      const bmp = await createImageBitmap(new Blob([r.data], { type: "image/png" }), { premultiplyAlpha: "none", colorSpaceConversion: "none" });
      const ctx = contexto();
      ctx.clearRect(0, 0, LADO, LADO);
      ctx.drawImage(bmp, 0, 0);
      bmp.close();
      const px = ctx.getImageData(0, 0, LADO, LADO).data;
      const out = new Uint8Array(LADO * LADO);
      for (let i = 0, j = 0; i < out.length; i++, j += 4) out[i] = px[j + 3] ? px[j] : 0;
      return out;
    })().catch((e) => {
      cache.delete(k);
      throw e;
    });
    cache.set(k, p);
    ORDEN.push(k);
    if (ORDEN.length > 500) cache.delete(ORDEN.shift()!);
  }
  return p;
}

let vacia: ImageBitmap | null = null;
export function registrarProtocoloComparacion() {
  addProtocol("cmp", async (params) => {
    const m = /cmp:\/\/([\w-]+)\/(\d+)\/(\d+)\/(\d+)/.exec(params.url);
    if (!m) throw new Error("URL de tesela no válida");
    const idx = await indicesTesela(m[1], +m[2], +m[3], +m[4]);
    const lut = luts.get(m[1]);
    if (!idx || !lut) {
      vacia ??= await createImageBitmap(new ImageData(1, 1));
      return { data: vacia };
    }
    const img = new ImageData(LADO, LADO);
    const d = img.data;
    for (let i = 0, j = 0; i < idx.length; i++, j += 4) {
      const v = idx[i];
      if (!v) continue;
      const l = v * 4;
      d[j] = lut[l];
      d[j + 1] = lut[l + 1];
      d[j + 2] = lut[l + 2];
      d[j + 3] = lut[l + 3];
    }
    return { data: await createImageBitmap(img) };
  });
}

const numero = (v: number, dec = 0) =>
  v.toLocaleString("es-ES", { minimumFractionDigits: dec, maximumFractionDigits: dec, useGrouping: "always" } as unknown as Intl.NumberFormatOptions);

/** Texto del valor de una capa en un punto (o null si no hay dato). */
export async function valorEn(c: CapaCmp, lng: number, lat: number, zoomMapa: number): Promise<{ texto: string; color?: string } | null> {
  const z = Math.max(5, Math.min(c.zmax, Math.floor(zoomMapa) + 1));
  const n = 2 ** z;
  const xf = ((lng + 180) / 360) * n;
  const s = Math.sin((lat * Math.PI) / 180);
  const yf = (0.5 - Math.log((1 + s) / (1 - s)) / (4 * Math.PI)) * n;
  const x = Math.floor(xf), y = Math.floor(yf);
  const idx = await indicesTesela(c.id, z, x, y);
  if (!idx) return null;
  const i = idx[Math.min(LADO - 1, Math.floor((yf - y) * LADO)) * LADO + Math.min(LADO - 1, Math.floor((xf - x) * LADO))];
  if (!i) return null;
  if (c.tipo === "continua") {
    let t = (i - 1) / 254;
    if (c.f === "raiz") t = t * t;
    const v = c.min! + t * (c.max! - c.min!);
    const sat = i === 255 ? "≥ " : i === 1 && c.min! > 0 ? "≤ " : "≈ ";
    return { texto: `${sat}${numero(v, c.decimales ?? 0)}${c.unidad ? " " + c.unidad : ""}`, color: c.lut![i - 1] };
  }
  const k = c.clases!.find((q) => q.v === i - (c.desplazamiento ?? 0));
  return k ? { texto: k.n, color: k.c } : null;
}

/** Tabla con el valor de todas las capas en un punto. */
export async function criteriosEn(lng: number, lat: number, zoom: number): Promise<string> {
  const filas = await Promise.all(capas.map(async (c) => [c, await valorEn(c, lng, lat, zoom).catch(() => null)] as const));
  return `<table class="pop-criterios"><tbody>${filas
    .map(([c, v]) => `<tr><th>${esc(c.nombre)}</th><td>${v ? `${v.color ? `<i style="background:${v.color}"></i>` : ""}${esc(v.texto)}` : "<span class='sd'>sin dato</span>"}</td></tr>`)
    .join("")}</tbody></table><p class="pop-nota">Valores aproximados (remuestreados para el visor).</p>`;
}

// ----------------------------------------------------------------------------- mapa espejo y cortina
let principal: MapaML;
let espejo: MapaML | null = null;
let activa: CapaCmp | null = null;
let fraccion = 0.5;
let completa = false;
const el = {} as { capaEspejo: HTMLDivElement; cortina: HTMLDivElement; panel: HTMLDivElement; leyenda: HTMLDivElement; sel: HTMLButtonElement; lista: HTMLDivElement; etiq: HTMLSpanElement; btn: HTMLButtonElement; completa: HTMLInputElement };

export function capaActiva() {
  return activa;
}

function estiloEspejo(): StyleSpecification {
  const st = principal.getStyle();
  const sources = { ...st.sources };
  delete (sources as Record<string, unknown>).eco;
  sources.cmp = { type: "raster", tiles: ["cmp://ninguna/{z}/{x}/{y}"], tileSize: 256, minzoom: 5, maxzoom: 12, bounds: [-89.6, 12.8, -82.0, 17.6] };
  const layers = st.layers
    .filter((l) => l.id !== "unidades-relleno")
    .map((l) => (l.id === "ecosistemas" ? { ...l, id: "comparacion", source: "cmp" } : l)) as StyleSpecification["layers"];
  return { version: 8, sources, layers };
}

function sincronizar() {
  espejo?.jumpTo({ center: principal.getCenter(), zoom: principal.getZoom(), bearing: principal.getBearing(), pitch: principal.getPitch() });
}

function recortar() {
  if (!espejo) return;
  const ancho = principal.getContainer().clientWidth;
  const x = completa ? 0 : Math.round(ancho * fraccion);
  el.capaEspejo.style.clipPath = `inset(0 0 0 ${x}px)`;
  el.cortina.style.left = `${x}px`;
}

/** Datos de las fuentes GeoJSON que el espejo copia del mapa principal. */
export function espejar(fuente: string, datos: GeoJSON.GeoJSON) {
  (espejo?.getSource(fuente) as maplibregl.GeoJSONSource | undefined)?.setData(datos);
}

function crearEspejo() {
  if (espejo) return espejo;
  const cont = principal.getContainer().parentElement!;
  el.capaEspejo = document.createElement("div");
  el.capaEspejo.className = "mapa-espejo";
  el.capaEspejo.setAttribute("aria-hidden", "true");
  cont.insertBefore(el.capaEspejo, principal.getContainer().nextSibling);
  espejo = new maplibregl.Map({
    container: el.capaEspejo,
    style: estiloEspejo(),
    interactive: false,
    attributionControl: false,
    center: principal.getCenter(),
    zoom: principal.getZoom(),
    maxZoom: principal.getMaxZoom(),
  });
  principal.on("move", sincronizar);
  principal.on("resize", () => {
    espejo?.resize();
    recortar();
  });
  // cortina arrastrable
  el.cortina = document.createElement("div");
  el.cortina.className = "cortina";
  el.cortina.innerHTML = `<span class="cort-lado izq">R26</span><button type="button" class="cort-asa" aria-label="Mover la cortina de comparación" title="Arrastra para comparar">⇔</button><span class="cort-lado der"></span>`;
  el.etiq = el.cortina.querySelector(".der")!;
  cont.appendChild(el.cortina);
  const asa = el.cortina.querySelector<HTMLButtonElement>(".cort-asa")!;
  const mover = (ev: PointerEvent) => {
    const r = cont.getBoundingClientRect();
    fraccion = Math.min(0.98, Math.max(0.02, (ev.clientX - r.left) / r.width));
    recortar();
  };
  asa.addEventListener("pointerdown", (ev) => {
    asa.setPointerCapture(ev.pointerId);
    asa.addEventListener("pointermove", mover);
    const fin = () => {
      asa.removeEventListener("pointermove", mover);
      asa.removeEventListener("pointerup", fin);
      asa.removeEventListener("pointercancel", fin);
    };
    asa.addEventListener("pointerup", fin);
    asa.addEventListener("pointercancel", fin);
  });
  asa.addEventListener("keydown", (ev) => {
    if (ev.key === "ArrowLeft" || ev.key === "ArrowRight") {
      fraccion = Math.min(0.98, Math.max(0.02, fraccion + (ev.key === "ArrowLeft" ? -0.05 : 0.05)));
      recortar();
      ev.preventDefault();
    }
  });
  return espejo;
}

function leyendaHTML(c: CapaCmp): string {
  if (c.tipo === "continua") {
    const t = (v: number) => {
      let q = Math.min(1, Math.max(0, (v - c.min!) / (c.max! - c.min!)));
      if (c.f === "raiz") q = Math.sqrt(q);
      return q * 100;
    };
    const u = c.unidad ? " " + c.unidad : "";
    const marcas = (c.umbrales ?? []).map((m) => `<span class="cmp-marca" style="left:${t(m.v)}%" title="${esc(m.n)}"></span>`).join("");
    const etiquetas = [c.min!, (c.min! + c.max!) / 2, c.max!]
      .map((v, i) => `<span style="left:${t(c.f === "raiz" && i === 1 ? c.min! + (c.max! - c.min!) / 4 : v)}%">${numero(c.f === "raiz" && i === 1 ? c.min! + (c.max! - c.min!) / 4 : v, c.decimales ?? 0)}</span>`)
      .join("");
    return `<div class="cmp-rampa" style="background:linear-gradient(90deg,${c.rampa!.join(",")})">${marcas}</div>
      <div class="cmp-ejes">${etiquetas}</div><p class="cmp-unidad">${esc(c.unidad ?? "")}${c.f === "raiz" ? " (escala de raíz cuadrada)" : ""}</p>
      ${c.umbrales?.length ? `<ul class="cmp-umbrales">${c.umbrales.map((m) => `<li><span class="cmp-marca-mini"></span>${esc(m.n)}</li>`).join("")}</ul><p class="cmp-pista">Las marcas son los umbrales usados en la clasificación${u ? "" : ""}.</p>` : ""}`;
  }
  return `<ul class="cmp-clases">${c.clases!
    .map((k) => `<li><i style="background:${k.c}"></i><span>${esc(k.n)}${k.r26 ? ` <small>→ color de ${k.r26}</small>` : ""}</span></li>`)
    .join("")}</ul>`;
}

function elegir(id: string) {
  activa = porId.get(id) ?? null;
  const on = !!activa;
  el.panel.classList.toggle("activa", on);
  el.btn.classList.toggle("activo", on);
  if (!on) {
    el.capaEspejo && (el.capaEspejo.hidden = true);
    el.cortina && (el.cortina.hidden = true);
    el.leyenda.innerHTML = "";
    return;
  }
  crearEspejo();
  // la fuente se vuelve a crear con el zoom máximo propio de la capa
  const ponerCapa = () => {
    const m = espejo!;
    if (m.getLayer("comparacion")) m.removeLayer("comparacion");
    if (m.getSource("cmp")) m.removeSource("cmp");
    m.addSource("cmp", { type: "raster", tiles: [`cmp://${activa!.id}/{z}/{x}/{y}`], tileSize: 256, minzoom: 5, maxzoom: activa!.zmax, bounds: [-89.6, 12.8, -82.0, 17.6] });
    m.addLayer(
      { id: "comparacion", type: "raster", source: "cmp", paint: { "raster-opacity": 0.92, "raster-resampling": activa!.tipo === "clases" ? "nearest" : "linear", "raster-fade-duration": 0 } },
      "mascara",
    );
  };
  if (espejo!.isStyleLoaded()) ponerCapa();
  else espejo!.once("load", ponerCapa);
  el.capaEspejo.hidden = false;
  el.cortina.hidden = completa;
  el.etiq.textContent = activa!.nombre;
  el.leyenda.innerHTML = `${leyendaHTML(activa!)}<p class="cmp-fuente"><b>Fuente:</b> ${esc(activa!.fuente)}</p>${activa!.nota ? `<p class="cmp-fuente">${esc(activa!.nota)}</p>` : ""}`;
  sincronizar();
  espejo!.resize();
  recortar();
  try {
    localStorage.setItem("comparar-capa", id);
  } catch {
    /* sin almacenamiento */
  }
}

class ControlComparar implements maplibregl.IControl {
  onAdd() {
    const d = document.createElement("div");
    d.className = "maplibregl-ctrl maplibregl-ctrl-group ctrl-comparar";
    el.btn = document.createElement("button");
    el.btn.type = "button";
    el.btn.className = "btn-comparar";
    el.btn.innerHTML = `<span aria-hidden="true">◧</span> Comparar`;
    el.btn.title = "Comparar el mapa con los criterios ecológicos o con el mapa 2002";
    el.btn.setAttribute("aria-expanded", "false");
    el.btn.addEventListener("click", () => {
      const abrir = el.panel.hidden;
      el.panel.hidden = !abrir;
      el.btn.setAttribute("aria-expanded", String(abrir));
    });
    d.appendChild(el.btn);
    return d;
  }
  onRemove() {}
}

export async function iniciarComparacion(mapa: MapaML) {
  principal = mapa;
  const lista = await cargarCapas();
  if (!lista.length) return;
  const cont = mapa.getContainer().parentElement!;
  el.panel = document.createElement("div");
  el.panel.className = "cmp-panel";
  el.panel.hidden = true;
  const grupos = [...new Set(lista.map((c) => c.grupo))];
  el.panel.innerHTML = `<div class="cmp-cab"><b>Comparar con</b><button type="button" class="cmp-cerrar" aria-label="Cerrar">×</button></div>
    <button type="button" class="cmp-sel" aria-expanded="true" aria-controls="cmp-lista"><span>Elige una capa</span><span class="cmp-flecha" aria-hidden="true">▾</span></button>
    <div id="cmp-lista" class="cmp-lista" role="radiogroup" aria-label="Capa de comparación">
      <label class="cmp-op"><input type="radio" name="cmp-capa" value="" checked> Ninguna</label>${grupos
        .map((g) => `<p class="cmp-grupo">${esc(g)}</p>${lista.filter((c) => c.grupo === g).map((c) => `<label class="cmp-op"><input type="radio" name="cmp-capa" value="${c.id}"> ${esc(c.nombre)}</label>`).join("")}`)
        .join("")}
    </div>
    <label class="cmp-completa"><input type="checkbox"> Ver la capa completa (sin cortina)</label>
    <p class="cmp-ayuda">Arrastra la cortina: a la izquierda el mapa R26, a la derecha la capa elegida. Al hacer clic en el mapa verás el valor de todos los criterios en ese punto.</p>
    <div class="cmp-leyenda"></div>`;
  cont.appendChild(el.panel);
  el.sel = el.panel.querySelector(".cmp-sel")!;
  el.lista = el.panel.querySelector(".cmp-lista")!;
  const desplegar = (abrir: boolean) => {
    el.lista.hidden = !abrir;
    el.sel.setAttribute("aria-expanded", String(abrir));
  };
  el.sel.addEventListener("click", () => desplegar(el.lista.hidden));
  el.leyenda = el.panel.querySelector(".cmp-leyenda")!;
  el.completa = el.panel.querySelector(".cmp-completa input")!;
  el.lista.addEventListener("change", (ev) => {
    const v = (ev.target as HTMLInputElement).value;
    elegir(v);
    el.sel.querySelector("span")!.textContent = v ? porId.get(v)!.nombre : "Elige una capa";
    if (v) desplegar(false);
  });
  el.completa.addEventListener("change", () => {
    completa = el.completa.checked;
    if (el.cortina) el.cortina.hidden = completa || !activa;
    recortar();
  });
  el.panel.querySelector(".cmp-cerrar")!.addEventListener("click", () => {
    el.panel.hidden = true;
    el.btn.setAttribute("aria-expanded", "false");
  });
  mapa.addControl(new ControlComparar(), "top-left");
}
