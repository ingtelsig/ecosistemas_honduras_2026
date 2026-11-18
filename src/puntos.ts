// Capa de los 1.228 puntos de referencia del R26 (campo 2026 y fuentes secundarias).
// Un clic sobre un punto muestra su tabla de atributos; los puntos de campo enlazan a su ficha técnica (PDF).
import type { ExpressionSpecification, Map as MapaML, MapGeoJSONFeature, PointLike } from "maplibre-gl";
import { url } from "./datos";

const esc = (s: string) => s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]!);

// Colores por fuente: el levantamiento de campo 2026 destaca; las demás en tonos distinguibles
const COLORES: [string, string][] = [
  ["Levantamiento de campo 2026", "#e4572e"],
  ["Formulario Kobo-2 (Campo Ecosistemas)", "#f3a712"],
  ["Formulario Kobo-1 (Puntos de control v2)", "#c9a227"],
  ["INF Ciclo II (2011–2015)", "#2e86ab"],
  ["INF Ciclo I Exclusivas (2005–2006)", "#5fa8d3"],
  ["INF Mangles Ciclo IV (2024)", "#1b998b"],
  ["Hábitats Marinos Surveys", "#3d348b"],
  ["Sitios de Monitoreo Ecosistemas 2000", "#8f2d56"],
  ["PMP Estudio 2012 (ICF / WWF)", "#6a994e"],
  ["Digitalización en Pantalla", "#7d7d7d"],
  ["Verificación Espacial Inter-Ráster (2014–2018–2024)", "#b5838d"],
];
const OTRO = "#444444";
const colorExpr: ExpressionSpecification = ["match", ["get", "fuente"], ...COLORES.flat(), OTRO] as unknown as ExpressionSpecification;

let datos: GeoJSON.FeatureCollection | null = null;
let cargando: Promise<GeoJSON.FeatureCollection> | null = null;
let visible = false;
let fuentesActivas: Set<string> | null = null; // null = todas
const mapas = new Set<MapaML>();

const cargar = () => (cargando ??= fetch(url("puntos/puntos.geojson")).then((r) => r.json()).then((g) => (datos = g)));

function filtro(): ExpressionSpecification | null {
  return fuentesActivas ? (["in", ["get", "fuente"], ["literal", [...fuentesActivas]]] as ExpressionSpecification) : null;
}

function aplicar(m: MapaML) {
  if (!m.isStyleLoaded()) return;
  if (visible && datos) {
    if (!m.getSource("puntos")) m.addSource("puntos", { type: "geojson", data: datos });
    if (!m.getLayer("puntos")) {
      m.addLayer({
        id: "puntos",
        type: "circle",
        source: "puntos",
        paint: {
          "circle-color": colorExpr,
          "circle-radius": ["interpolate", ["linear"], ["zoom"], 6, ["case", ["==", ["get", "tipo"], "campo"], 3.6, 2.8], 11, ["case", ["==", ["get", "tipo"], "campo"], 7, 5.5]],
          "circle-stroke-color": "#ffffff",
          "circle-stroke-width": ["interpolate", ["linear"], ["zoom"], 6, 0.8, 11, 1.5],
          "circle-pitch-alignment": "map",
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

const ETIQUETAS: [string, string][] = [
  ["fuente", "Fuente"],
  ["codigo_sitio", "Código de sitio"],
  ["fecha", "Fecha"],
  ["departamento", "Departamento"],
  ["municipio", "Municipio"],
  ["elev", "Elevación (msnm)"],
  ["piso", "Piso altitudinal"],
  ["ref_original", "Clase original de la referencia"],
  ["ref_homologada", "Clase homologada (referencia)"],
  ["mapa_clase", "Clase del mapa en el punto"],
  ["mapa_homologada", "Clase homologada (mapa)"],
  ["grupo_ref", "Grupo nacional (referencia)"],
  ["grupo_mapa", "Grupo nacional (mapa)"],
  ["bioma_ref", "Bioma operativo (referencia)"],
  ["bioma_mapa", "Bioma operativo (mapa)"],
  ["get1_ref", "GET L1 · reino (referencia)"],
  ["get1_mapa", "GET L1 · reino (mapa)"],
  ["get2_ref", "GET L2 · bioma (referencia)"],
  ["get2_mapa", "GET L2 · bioma (mapa)"],
  ["get3_ref", "GET L3 · EFG (referencia)"],
  ["get3_mapa", "GET L3 · EFG (mapa)"],
  ["evidencia", "Evidencia archivada"],
  ["estado", "Estado de la referencia"],
  ["resultado_get", "Resultado GET de la referencia"],
  ["regla", "Regla aplicada"],
  ["codigos_compatibles", "Códigos nacionales compatibles"],
  ["efg_candidatos", "EFG candidatos"],
];

const valor = (k: string, v: unknown) => {
  const s = k === "elev" ? new Intl.NumberFormat("es-ES", { maximumFractionDigits: 0, useGrouping: "always" } as unknown as Intl.NumberFormatOptions).format(Number(v)) : String(v);
  // Listas «A | B | C» en líneas separadas
  return s.includes(" | ") ? s.split(" | ").map(esc).join("<br>") : esc(s);
};

/** Contenido del popup de un punto: encabezado, botón de ficha de campo y tabla de atributos. */
export function htmlPunto(f: MapGeoJSONFeature): string {
  const p = f.properties as Record<string, unknown>;
  const [lon, lat] = (f.geometry as GeoJSON.Point).coordinates;
  const color = COLORES.find(([n]) => n === p.fuente)?.[1] ?? OTRO;
  const filas = ETIQUETAS.filter(([k]) => p[k] !== undefined && p[k] !== null && p[k] !== "")
    .map(([k, et]) => `<tr><th>${et}</th><td>${valor(k, p[k])}</td></tr>`)
    .join("");
  const ficha =
    p.tipo === "campo"
      ? `<a class="btn primario pt-ficha" href="${url(`puntos/fichas/${encodeURIComponent(String(p.id))}.pdf`)}" target="_blank" rel="noopener">Abrir ficha de campo (PDF)</a>`
      : "";
  return `<div class="pt-cab"><i style="background:${color}"></i><div><b>Punto ${esc(String(p.id))}</b>
      <small>${p.tipo === "campo" ? "Punto de campo" : "Referencia secundaria"} · ${lat.toFixed(5)}, ${lon.toFixed(5)}</small></div></div>
    ${ficha}
    <div class="pt-tabla-c"><table class="pop-criterios pt-tabla"><tbody>${filas}</tbody></table></div>
    <p class="pt-nota">Fuente: Puntos de referencia y superficies jerárquicas R26 (1.228 registros).${p.tipo === "campo" ? " Ficha: Anexo 1 del Producto 3, validación de campo 2026." : ""}</p>`;
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
      <div class="pt-lista">${COLORES.map(
        ([n, c]) => `<label class="cmp-op"><input type="checkbox" data-fuente="${esc(n)}" checked><i style="background:${c}"></i> <span>${esc(n)}</span> <small data-n="${esc(n)}"></small></label>`,
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
        for (const f of datos!.features) cuenta.set(f.properties!.fuente, (cuenta.get(f.properties!.fuente) ?? 0) + 1);
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
      const sel = [...this.panel.querySelectorAll<HTMLInputElement>("[data-fuente]")].filter((i) => i.checked).map((i) => i.dataset.fuente!);
      fuentesActivas = sel.length === COLORES.length ? null : new Set(sel);
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
