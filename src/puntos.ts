// Capa de los 1,228 puntos de referencia del mapa 2026 (campo 2026 y fuentes secundarias), en seis grupos de fuentes.
// Un clic sobre un punto muestra su tabla de atributos; los puntos de campo enlazan a su ficha técnica (PDF).
import type { ExpressionSpecification, Map as MapaML, MapGeoJSONFeature, PointLike } from "maplibre-gl";
import { url, type Catalogo } from "./datos";
import { nombreGET } from "./leyenda";
import { enlazarGET } from "./fichas";

const esc = (s: string) => s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]!);

// Grupos de fuentes. Símbolos en negro y blanco con formas distintas para no confundirse con los colores del mapa.
type Forma = "triangulo" | "circulo" | "cuadrado" | "rombo" | "estrella" | "anillo";
interface Grupo {
  id: string;
  nombre: string;
  forma: Forma;
  relleno: string;
  borde: string;
  fuentes: string[];
}
export const GRUPOS: Grupo[] = [
  { id: "campo", nombre: "Levantamiento de campo 2026", forma: "triangulo", relleno: "#000000", borde: "#ffffff", fuentes: ["Levantamiento de campo 2026"] },
  {
    id: "foto",
    nombre: "Fotointerpretación de expertos",
    forma: "circulo",
    relleno: "#ffffff",
    borde: "#000000",
    fuentes: ["Formulario Kobo 2 (campo de ecosistemas)", "Formulario Kobo 1 (puntos de control, v2)", "Digitalización en pantalla", "Verificación espacial entre rásteres (2014, 2018 y 2024)"],
  },
  { id: "ifn", nombre: "INF (todos los ciclos)", forma: "cuadrado", relleno: "#3a3a3a", borde: "#ffffff", fuentes: ["INF ciclo I, parcelas exclusivas (2005–2006)", "INF ciclo II (2011–2015)", "INF manglares, ciclo IV (2024)"] },
  { id: "marinos", nombre: "Hábitats marinos", forma: "rombo", relleno: "#ffffff", borde: "#000000", fuentes: ["Levantamientos de hábitats marinos"] },
  { id: "pmp", nombre: "PMP Estudio 2012 (ICF/WWF)", forma: "estrella", relleno: "#000000", borde: "#ffffff", fuentes: ["Estudio PMP 2012 (ICF / WWF)"] },
  { id: "monitoreo", nombre: "Sitios de monitoreo de ecosistemas 2000", forma: "anillo", relleno: "#000000", borde: "#ffffff", fuentes: ["Sitios de monitoreo de ecosistemas 2000"] },
];
const GRUPO_DE = new Map(GRUPOS.flatMap((g) => g.fuentes.map((f) => [f, g.id] as [string, string])));
const grupoDe = (fuente: unknown) => GRUPO_DE.get(String(fuente)) ?? "foto";

/** Dibuja el símbolo de un grupo en un lienzo (lado en px lógicos, escala para pantallas densas). */
function dibujar(g: Grupo, lado: number, escala = 2): HTMLCanvasElement {
  const c = document.createElement("canvas");
  c.width = c.height = Math.round(lado * escala);
  const x = c.getContext("2d")!;
  x.scale(escala, escala);
  const m = lado / 2;
  const r = lado / 2 - 2;
  x.lineJoin = "round";
  x.beginPath();
  if (g.forma === "triangulo") {
    x.moveTo(m, 1.5);
    x.lineTo(lado - 1.5, lado - 2);
    x.lineTo(1.5, lado - 2);
    x.closePath();
  } else if (g.forma === "cuadrado") {
    x.rect(m - r * 0.8, m - r * 0.8, r * 1.6, r * 1.6);
  } else if (g.forma === "rombo") {
    x.moveTo(m, m - r);
    x.lineTo(m + r, m);
    x.lineTo(m, m + r);
    x.lineTo(m - r, m);
    x.closePath();
  } else if (g.forma === "estrella") {
    for (let i = 0; i < 10; i++) {
      const a = -Math.PI / 2 + (i * Math.PI) / 5;
      const rr = i % 2 ? r * 0.45 : r;
      if (i) x.lineTo(m + rr * Math.cos(a), m + rr * Math.sin(a));
      else x.moveTo(m + rr * Math.cos(a), m + rr * Math.sin(a));
    }
    x.closePath();
  } else {
    x.arc(m, m, g.forma === "anillo" ? r * 0.85 : r * 0.8, 0, 2 * Math.PI);
  }
  if (g.forma === "anillo") {
    x.lineWidth = 4.2;
    x.strokeStyle = g.borde;
    x.stroke();
    x.lineWidth = 2.4;
    x.strokeStyle = g.relleno;
    x.stroke();
  } else {
    x.fillStyle = g.relleno;
    x.fill();
    x.lineWidth = 1.6;
    x.strokeStyle = g.borde;
    x.stroke();
  }
  return c;
}

function registrarIconos(m: MapaML) {
  for (const g of GRUPOS) {
    const id = `pt-${g.id}`;
    if (m.hasImage(id)) continue;
    const c = dibujar(g, g.id === "campo" ? 18 : 14);
    m.addImage(id, c.getContext("2d")!.getImageData(0, 0, c.width, c.height), { pixelRatio: 2 });
  }
}

let datos: GeoJSON.FeatureCollection | null = null;
let cargando: Promise<GeoJSON.FeatureCollection> | null = null;
let visible = false;
let gruposActivos: Set<string> | null = null; // null = todos
const mapas = new Set<MapaML>();

const cargar = () =>
  (cargando ??= fetch(url("puntos/puntos.geojson"))
    .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`puntos: ${r.status}`))))
    .catch((e) => {
      cargando = null;
      throw e;
    })
    .then((g: GeoJSON.FeatureCollection) => {
      for (const f of g.features) f.properties!.grupo = grupoDe(f.properties!.fuente);
      return (datos = g);
    }));

function filtro(): ExpressionSpecification | null {
  return gruposActivos ? (["in", ["get", "grupo"], ["literal", [...gruposActivos]]] as ExpressionSpecification) : null;
}

function aplicar(m: MapaML) {
  if (!m.isStyleLoaded()) return;
  if (visible && datos) {
    if (!m.getSource("puntos")) m.addSource("puntos", { type: "geojson", data: datos });
    registrarIconos(m);
    if (!m.getLayer("puntos")) {
      m.addLayer({
        id: "puntos",
        type: "symbol",
        source: "puntos",
        layout: {
          "icon-image": ["concat", "pt-", ["get", "grupo"]],
          "icon-size": ["interpolate", ["linear"], ["zoom"], 6, 0.75, 10, 1, 13, 1.25],
          "icon-allow-overlap": true,
          "icon-ignore-placement": true,
          // Los puntos de campo se dibujan encima del resto
          "symbol-sort-key": ["case", ["==", ["get", "grupo"], "campo"], 1, 0],
        },
      });
    }
    m.setFilter("puntos", filtro());
  } else if (m.getLayer("puntos")) m.removeLayer("puntos");
}

const aplicarTodos = () => mapas.forEach(aplicar);

/** Registra un mapa (el de comparación) para que muestre la misma capa de puntos. */
export function registrarPuntos(m: MapaML) {
  mapas.add(m);
  if (m.isStyleLoaded()) aplicar(m);
  else m.once("load", () => aplicar(m));
}

/** Punto de referencia bajo el cursor, si la capa está visible. */
export function puntoEn(m: MapaML, p: PointLike): MapGeoJSONFeature | undefined {
  if (!visible || !m.getLayer("puntos")) return undefined;
  const [x, y] = Array.isArray(p) ? p : [(p as { x: number }).x, (p as { y: number }).y];
  const r = 5;
  return m.queryRenderedFeatures([[x - r, y - r], [x + r, y + r]], { layers: ["puntos"] })[0];
}

// Lo que se ve de entrada: dónde y cuándo, qué se observó y qué dice el mapa en ese punto.
const BASICOS: [string, string][] = [
  ["fuente", "Fuente"],
  ["codigo_sitio", "Código de sitio"],
  ["fecha", "Fecha"],
  ["departamento", "Departamento"],
  ["municipio", "Municipio"],
  ["elev", "Elevación (msnm)"],
  ["piso", "Piso altitudinal"],
];
// Detalle de la homologación (desplegable): las listas de candidatos GET son inferencias, no observaciones.
const DETALLE: [string, string][] = [
  ["ref_homologada", "Clase homologada (referencia)"],
  ["mapa_homologada", "Clase homologada (mapa)"],
  ["bioma_ref", "Bioma operativo (referencia)"],
  ["bioma_mapa", "Bioma operativo (mapa)"],
  ["evidencia", "Evidencia archivada"],
  ["estado", "Estado de la referencia"],
  ["regla", "Regla aplicada"],
  ["resultado_get", "Resultado GET de la referencia"],
  ["codigos_compatibles", "Códigos nacionales compatibles"],
  ["efg_candidatos", "EFG candidatos de la referencia"],
];

const valor = (k: string, v: unknown) => {
  const s = k === "elev" ? new Intl.NumberFormat("en-US", { maximumFractionDigits: 0, useGrouping: "always" } as unknown as Intl.NumberFormatOptions).format(Number(v)) : String(v);
  // Listas «A | B | C» en líneas separadas
  return s.includes(" | ") ? s.split(" | ").map(esc).join("<br>") : esc(s);
};

const hay = (v: unknown) => v !== undefined && v !== null && v !== "";
const fila = (et: string, html: string) => `<tr><th>${et}</th><td>${html}</td></tr>`;
const filas = (p: Record<string, unknown>, ets: [string, string][]) =>
  ets.filter(([k]) => hay(p[k])).map(([k, et]) => fila(et, valor(k, p[k]))).join("");

/** Contenido del popup de un punto: lo observado, la clase del mapa con su grupo GET principal y, plegado, el detalle de la homologación. */
export function htmlPunto(f: MapGeoJSONFeature, cat?: Catalogo): string {
  const p = f.properties as Record<string, unknown>;
  const [lon, lat] = (f.geometry as GeoJSON.Point).coordinates;
  const g = GRUPOS.find((x) => x.id === p.grupo) ?? GRUPOS[1];
  const campo = p.tipo === "campo";
  const claseMapa = cat?.clases.find((c) => c.nombre === p.mapa_clase);
  const efg = claseMapa && !["MULT", "SIN_GET"].includes(claseMapa.get3) ? `${claseMapa.get3} ${esc(nombreGET(cat!, 2, claseMapa.get3))}` : "";
  const coincide = hay(p.grupo_ref) && hay(p.grupo_mapa) ? (p.grupo_ref === p.grupo_mapa ? "Sí, mismo grupo nacional" : "No, grupo nacional distinto") : "";
  const principal =
    filas(p, BASICOS) +
    (hay(p.ref_original) ? fila(campo ? "Clase observada en campo" : "Clase de la referencia", valor("ref_original", p.ref_original)) : "") +
    (hay(p.grupo_ref) ? fila("Grupo nacional observado", valor("grupo_ref", p.grupo_ref)) : "") +
    (hay(p.mapa_clase) ? fila("Clase del mapa en el punto", (claseMapa ? `${claseMapa.codigo} ` : "") + valor("mapa_clase", p.mapa_clase)) : "") +
    (efg ? fila("Grupo GET-UICN del mapa", efg) : "") +
    (coincide ? fila("Concordancia", coincide) : "");
  const detalle = filas(p, DETALLE);
  const ficha = campo
    ? `<a class="btn primario pt-ficha" href="${url(`puntos/fichas/${encodeURIComponent(String(p.id))}.pdf`)}" target="_blank" rel="noopener">Abrir ficha de campo (PDF)</a>`
    : "";
  return enlazarGET(`<div class="pt-cab"><img src="${dibujar(g, 18).toDataURL()}" alt="" width="18" height="18"><div><b>Punto ${esc(String(p.id))}</b>
      <small>${esc(g.nombre)} · ${lat.toFixed(5)}, ${lon.toFixed(5)}</small></div></div>
    ${ficha}
    <div class="pt-tabla-c"><table class="pop-criterios pt-tabla"><tbody>${principal}</tbody></table>
    ${
      detalle
        ? `<details class="pt-detalle"><summary>Detalle de la homologación</summary>
      <p class="pt-nota">Los EFG candidatos son las opciones GET compatibles con la clase registrada por la fuente (inferencia), no observaciones de campo.</p>
      <table class="pop-criterios pt-tabla"><tbody>${detalle}</tbody></table></details>`
        : ""
    }</div>
    <p class="pt-nota">Fuente: Puntos de referencia y superficies jerárquicas del Mapa de Ecosistemas 2026 (1,228 registros).${campo ? " Ficha: Anexo 1 del Producto 3, validación de campo 2026." : ""}</p>`);
}

/** Botón «Puntos de referencia» con el filtro por fuente. */
export class ControlPuntos {
  private panel!: HTMLDivElement;
  onAdd(m: MapaML) {
    mapas.add(m);
    const d = document.createElement("div");
    d.className = "maplibregl-ctrl maplibregl-ctrl-group ctrl-comparar ctrl-puntos";
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "btn-comparar";
    btn.innerHTML = `<span aria-hidden="true">●</span> Puntos de referencia`;
    btn.title = "Mostrar los puntos de referencia (campo y fuentes secundarias)";
    btn.setAttribute("aria-expanded", "false");
    d.appendChild(btn);

    this.panel = document.createElement("div");
    this.panel.className = "cmp-panel pt-panel";
    this.panel.hidden = true;
    this.panel.innerHTML = `<div class="cmp-cab"><b>Puntos de referencia</b><button type="button" class="cmp-cerrar" aria-label="Cerrar">×</button></div>
      <label class="pt-ver"><input type="checkbox" data-ver> Mostrar en el mapa</label>
      <div class="pt-lista">${GRUPOS.map(
        (g) => `<label class="cmp-op" title="${esc(g.fuentes.join("\n"))}"><input type="checkbox" data-grupo="${g.id}" checked><img src="${dibujar(g, 16).toDataURL()}" alt="" width="16" height="16"> <span>${esc(g.nombre)}</span> <small data-n="${g.id}"></small></label>`,
      ).join("")}</div>
      <p class="cmp-ayuda">Haga clic en un punto para ver sus atributos. Los puntos de campo 2026 (CAM) abren su ficha técnica de validación.</p>`;
    m.getContainer().parentElement!.appendChild(this.panel);

    const ver = this.panel.querySelector<HTMLInputElement>("[data-ver]")!;
    const mostrar = async (si: boolean) => {
      visible = si;
      ver.checked = si;
      btn.classList.toggle("activo", si);
      if (si && !datos) {
        btn.disabled = true;
        await cargar();
        btn.disabled = false;
        const cuenta = new Map<string, number>();
        for (const f of datos!.features) cuenta.set(f.properties!.grupo, (cuenta.get(f.properties!.grupo) ?? 0) + 1);
        this.panel.querySelectorAll<HTMLElement>("[data-n]").forEach((s) => (s.textContent = String(cuenta.get(s.dataset.n!) ?? 0)));
      }
      aplicarTodos();
    };
    const abrir = (si: boolean) => {
      this.panel.hidden = !si;
      btn.setAttribute("aria-expanded", String(si));
      if (si) document.querySelectorAll<HTMLElement>(".cmp-panel:not(.pt-panel)").forEach((p) => (p.hidden = true));
    };
    btn.addEventListener("click", () => {
      // El primer clic enciende la capa; después el botón abre y cierra el panel
      if (!visible) void mostrar(true);
      abrir(this.panel.hidden);
    });
    this.panel.querySelector(".cmp-cerrar")!.addEventListener("click", () => abrir(false));
    ver.addEventListener("change", () => void mostrar(ver.checked));
    this.panel.querySelector(".pt-lista")!.addEventListener("change", () => {
      const sel = [...this.panel.querySelectorAll<HTMLInputElement>("[data-grupo]")].filter((i) => i.checked).map((i) => i.dataset.grupo!);
      gruposActivos = sel.length === GRUPOS.length ? null : new Set(sel);
      aplicarTodos();
    });
    m.on("mouseenter", "puntos", () => (m.getCanvas().style.cursor = "pointer"));
    m.on("mouseleave", "puntos", () => (m.getCanvas().style.cursor = ""));
    return d;
  }
  onRemove() {
    this.panel?.remove();
  }
}
