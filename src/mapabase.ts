// Mapas base: el propio (sin conexión externa) o los mapas base gratuitos de Esri (servicios de teselas de ArcGIS Online).
// La capa elegida se coloca debajo del R26 en el mapa principal y en el mapa de comparación.
import type { Map as MapaML } from "maplibre-gl";

export interface MapaBase {
  id: string;
  nombre: string;
  servicios: string[]; // servicios de ArcGIS Online, de abajo arriba (p. ej. imágenes + nombres)
  atribucion: string;
  oscuro?: boolean;
}

const ESRI = "https://server.arcgisonline.com/ArcGIS/rest/services";
export const MAPAS_BASE: MapaBase[] = [
  { id: "propio", nombre: "Mapa base propio (sin conexión externa)", servicios: [], atribucion: "" },
  { id: "imagenes", nombre: "Imágenes satelitales", servicios: ["World_Imagery", "Reference/World_Boundaries_and_Places"], atribucion: "Esri, Maxar, Earthstar Geographics y la comunidad de usuarios de SIG", oscuro: true },
  { id: "topografico", nombre: "Topográfico", servicios: ["World_Topo_Map"], atribucion: "Esri, HERE, Garmin, FAO, NOAA, USGS y colaboradores" },
  { id: "calles", nombre: "Calles", servicios: ["World_Street_Map"], atribucion: "Esri, HERE, Garmin, USGS, NGA y colaboradores" },
  { id: "relieve", nombre: "Relieve sombreado", servicios: ["Elevation/World_Hillshade"], atribucion: "Esri, Airbus, USGS, NGA, NASA, CGIAR, NLS, OS, NMA, Geodatastyrelsen, GSA, GSI y la comunidad de usuarios de SIG" },
  { id: "gris", nombre: "Gris claro", servicios: ["Canvas/World_Light_Gray_Base", "Canvas/World_Light_Gray_Reference"], atribucion: "Esri, HERE, Garmin, FAO, NOAA, USGS y colaboradores" },
  { id: "gris_oscuro", nombre: "Gris oscuro", servicios: ["Canvas/World_Dark_Gray_Base", "Canvas/World_Dark_Gray_Reference"], atribucion: "Esri, HERE, Garmin, FAO, NOAA, USGS y colaboradores", oscuro: true },
];

const CLAVE = "mapa-base";
let actual = leer();
const mapas = new Set<MapaML>();

function leer(): string {
  try {
    const v = localStorage.getItem(CLAVE);
    if (v && MAPAS_BASE.some((b) => b.id === v)) return v;
  } catch {
    /* sin almacenamiento */
  }
  return "propio";
}

export const mapaBaseActual = () => MAPAS_BASE.find((b) => b.id === actual)!;

// Capas del fondo propio que se ocultan bajo un mapa base de Esri
const PROPIAS = ["mar", "tierra"];
// La capa base se inserta justo debajo de esta (la del R26 o la de comparación)
const ENCIMA = ["ecosistemas", "comparacion", "mascara"];

function aplicar(m: MapaML) {
  const b = mapaBaseActual();
  for (const l of m.getStyle().layers.filter((x) => x.id.startsWith("base-"))) m.removeLayer(l.id);
  for (const id of Object.keys(m.getStyle().sources).filter((x) => x.startsWith("base-"))) m.removeSource(id);
  for (const l of PROPIAS) if (m.getLayer(l)) m.setLayoutProperty(l, "visibility", b.servicios.length ? "none" : "visible");
  const antes = ENCIMA.find((id) => m.getLayer(id));
  b.servicios.forEach((s, i) => {
    const id = `base-${i}`;
    m.addSource(id, {
      type: "raster",
      tiles: [`${ESRI}/${s}/MapServer/tile/{z}/{y}/{x}`],
      tileSize: 256,
      maxzoom: 19,
      attribution: i === 0 ? `Mapa base: ${b.atribucion} · Powered by Esri` : undefined,
    });
    m.addLayer({ id, type: "raster", source: id, paint: { "raster-fade-duration": 0 } }, antes);
  });
}

/** Registra un mapa para que reciba el mapa base elegido (ahora y en cada cambio). */
export function registrarMapaBase(m: MapaML) {
  mapas.add(m);
  const hacer = () => aplicar(m);
  if (m.isStyleLoaded()) hacer();
  else m.once("load", hacer);
}

export function elegirMapaBase(id: string) {
  actual = id;
  try {
    localStorage.setItem(CLAVE, id);
  } catch {
    /* sin almacenamiento */
  }
  for (const m of mapas) if (m.isStyleLoaded()) aplicar(m);
}

const esc = (s: string) => s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]!);

/** Botón «Mapa base» con la lista de mapas base y la opacidad del mapa de ecosistemas. */
export class ControlMapaBase {
  private panel!: HTMLDivElement;
  onAdd(m: MapaML) {
    const d = document.createElement("div");
    d.className = "maplibregl-ctrl maplibregl-ctrl-group ctrl-comparar ctrl-mapabase";
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "btn-comparar";
    btn.innerHTML = `<span aria-hidden="true">▦</span> Mapa base`;
    btn.title = "Cambiar el mapa base y la opacidad del mapa de ecosistemas";
    btn.setAttribute("aria-expanded", "false");
    d.appendChild(btn);

    this.panel = document.createElement("div");
    this.panel.className = "cmp-panel mb-panel";
    this.panel.hidden = true;
    const op = 90; // opacidad inicial de la capa «ecosistemas» (mapa.ts)
    this.panel.innerHTML = `<div class="cmp-cab"><b>Mapa base</b><button type="button" class="cmp-cerrar" aria-label="Cerrar">×</button></div>
      <div class="cmp-lista mb-lista" role="radiogroup" aria-label="Mapa base">${MAPAS_BASE.map(
        (b) => `<label class="cmp-op"><input type="radio" name="mapa-base" value="${b.id}"${b.id === actual ? " checked" : ""}> ${esc(b.nombre)}</label>`,
      ).join("")}</div>
      <label class="mb-opacidad">Opacidad del mapa de ecosistemas <output>${op} %</output>
        <input type="range" min="0" max="100" step="5" value="${op}"></label>
      <p class="cmp-ayuda">Los mapas base de Esri se cargan desde ArcGIS Online y necesitan conexión a internet.</p>`;
    m.getContainer().parentElement!.appendChild(this.panel);

    const abrir = (si: boolean) => {
      this.panel.hidden = !si;
      btn.setAttribute("aria-expanded", String(si));
      if (si) document.querySelectorAll<HTMLElement>(".cmp-panel:not(.mb-panel)").forEach((p) => (p.hidden = true));
    };
    btn.addEventListener("click", () => abrir(this.panel.hidden));
    this.panel.querySelector(".cmp-cerrar")!.addEventListener("click", () => abrir(false));
    this.panel.querySelector(".mb-lista")!.addEventListener("change", (ev) => elegirMapaBase((ev.target as HTMLInputElement).value));
    const rango = this.panel.querySelector<HTMLInputElement>("input[type=range]")!;
    const salida = this.panel.querySelector("output")!;
    rango.addEventListener("input", () => {
      m.setPaintProperty("ecosistemas", "raster-opacity", +rango.value / 100);
      salida.textContent = `${rango.value} %`;
    });
    return d;
  }
  onRemove() {
    this.panel?.remove();
  }
}
