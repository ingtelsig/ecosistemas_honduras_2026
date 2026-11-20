// Mapa MapLibre sin servicios externos: fondo propio (tierra, mar y límites), capa 2026 y límites de reporte.
import maplibregl, { type GeoJSONSource, type LngLatBoundsLike, type Map as MapaML } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { url, type ClaveCapa } from "./datos";
import { ZOOM_MAX_DATOS } from "./teselas";
import { espejar } from "./comparar";
import { ControlMapaBase, registrarMapaBase } from "./mapabase";
import { agregarControl3D } from "./relieve3d";
import { ControlPuntos } from "./puntos";

const HONDURAS: LngLatBoundsLike = [[-89.5, 12.9], [-82.9, 17.5]];
const vacio: GeoJSON.FeatureCollection = { type: "FeatureCollection", features: [] };

// Escala nominal con el píxel estándar OGC (0,28 mm). MapLibre usa teselas de 512 px: a zoom 0, 78.271,517 m/px en el ecuador.
const M_PX_Z0 = 78271.517;
const PIXEL_OGC = 0.00028;
const LAT_REF = 14.8; // latitud central de Honduras
export const escalaEn = (zoom: number, lat: number) => (M_PX_Z0 * Math.cos((lat * Math.PI) / 180)) / 2 ** zoom / PIXEL_OGC;
/** Zoom máximo: escala del mapa de ecosistemas, 1:50.000 (≈ 12,4). */
export const ZOOM_MAX_MAPA = Math.log2((M_PX_Z0 * Math.cos((LAT_REF * Math.PI) / 180)) / (50000 * PIXEL_OGC));

class ControlEscala implements maplibregl.IControl {
  private el = document.createElement("div");
  private mapa?: MapaML;
  private fmt = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0, useGrouping: "always" } as unknown as Intl.NumberFormatOptions);
  private act = () => {
    const m = this.mapa!;
    const n = escalaEn(m.getZoom(), m.getCenter().lat);
    const redondo = n > 5000 ? Math.round(n / 1000) * 1000 : Math.round(n / 100) * 100;
    this.el.textContent = `1:${this.fmt.format(redondo)}`;
  };
  onAdd(m: MapaML) {
    this.mapa = m;
    this.el.className = "maplibregl-ctrl control-escala";
    this.el.title = "Escala nominal (píxel estándar de 0,28 mm). El zoom máximo corresponde a 1:50.000, la escala del mapa.";
    m.on("move", this.act);
    this.act();
    return this.el;
  }
  onRemove() {
    this.mapa?.off("move", this.act);
    this.el.remove();
  }
}

/** Textos de los controles de MapLibre en español. */
const LOCALE_ES: Record<string, string> = {
  "AttributionControl.ToggleAttribution": "Mostrar u ocultar la atribución",
  "AttributionControl.MapFeedback": "Comentarios sobre el mapa",
  "FullscreenControl.Enter": "Pantalla completa",
  "FullscreenControl.Exit": "Salir de pantalla completa",
  "GeolocateControl.FindMyLocation": "Mostrar mi ubicación",
  "GeolocateControl.LocationNotAvailable": "Ubicación no disponible",
  "LogoControl.Title": "Logotipo de MapLibre",
  "Map.Title": "Mapa",
  "Marker.Title": "Marcador",
  "NavigationControl.ResetBearing": "Orientar al norte",
  "NavigationControl.ZoomIn": "Acercar",
  "NavigationControl.ZoomOut": "Alejar",
  "Popup.Close": "Cerrar",
  "ScaleControl.Feet": "pies",
  "ScaleControl.Meters": "m",
  "ScaleControl.Kilometers": "km",
  "ScaleControl.Miles": "mi",
  "ScaleControl.NauticalMiles": "mn",
  "TerrainControl.Enable": "Activar el relieve",
  "TerrainControl.Disable": "Desactivar el relieve",
  "CooperativeGesturesHandler.WindowsHelpText": "Use Ctrl + rueda para acercar el mapa",
  "CooperativeGesturesHandler.MacHelpText": "Use ⌘ + rueda para acercar el mapa",
  "CooperativeGesturesHandler.MobileHelpText": "Use dos dedos para mover el mapa",
};

export function crearMapa(contenedor: string): Promise<MapaML> {
  const mapa = new maplibregl.Map({
    container: contenedor,
    locale: LOCALE_ES,
    maxZoom: ZOOM_MAX_MAPA,
    maxTileCacheSize: 200, // limita la memoria en teléfonos
    bounds: HONDURAS,
    fitBoundsOptions: { padding: 20 },
    maxBounds: [[-95, 9], [-76, 21]],
    attributionControl: { compact: true, customAttribution: "Mapa de Ecosistemas de Honduras 2026 · Límites: ICF, SINIT/SEPLAN (HDX)" },
    canvasContextAttributes: { preserveDrawingBuffer: true }, // necesario para capturar el mapa en el PDF
    style: {
      version: 8,
      sources: {
        contexto: { type: "geojson", data: url("limites/contexto.geojson") },
        eco: { type: "raster", tiles: ["eco://{z}/{x}/{y}?v=1"], tileSize: 256, minzoom: 5, maxzoom: ZOOM_MAX_DATOS, bounds: [-89.6, 12.8, -82.0, 17.6] },
        deptos: { type: "geojson", data: url("limites/departamentos.geojson") },
        unidades: { type: "geojson", data: vacio, promoteId: "id" },
        mascara: { type: "geojson", data: vacio },
        seleccion: { type: "geojson", data: vacio },
      },
      layers: [
        { id: "fondo", type: "background", paint: { "background-color": "#e9edf0" } },
        { id: "mar", type: "fill", source: "contexto", filter: ["==", ["get", "tipo"], "mar"], paint: { "fill-color": "#d3e3ee" } },
        { id: "tierra", type: "fill", source: "contexto", filter: ["==", ["get", "tipo"], "tierra"], paint: { "fill-color": "#f6f5f1" } },
        { id: "ecosistemas", type: "raster", source: "eco", paint: { "raster-opacity": 0.9, "raster-resampling": "nearest", "raster-fade-duration": 0 } },
        { id: "mascara", type: "fill", source: "mascara", paint: { "fill-color": "#f4f6f7", "fill-opacity": 0.78 } },
        { id: "deptos-linea", type: "line", source: "deptos", paint: { "line-color": "#5b6770", "line-width": 0.6, "line-opacity": 0.6 } },
        { id: "unidades-relleno", type: "fill", source: "unidades", paint: { "fill-color": "#000", "fill-opacity": ["case", ["boolean", ["feature-state", "hover"], false], 0.08, 0] } },
        { id: "unidades-linea", type: "line", source: "unidades", paint: { "line-color": "#29323a", "line-width": ["interpolate", ["linear"], ["zoom"], 6, 0.5, 11, 1.4], "line-opacity": 0.75 } },
        { id: "seleccion-halo", type: "line", source: "seleccion", paint: { "line-color": "#ffffff", "line-width": 5, "line-opacity": 0.9 } },
        { id: "seleccion-linea", type: "line", source: "seleccion", paint: { "line-color": "#c2410c", "line-width": 2.2 } },
      ],
    },
  });
  mapa.addControl(new maplibregl.NavigationControl({ showCompass: true, visualizePitch: true }), "top-right");
  mapa.addControl(new maplibregl.ScaleControl({ unit: "metric" }), "bottom-left");
  mapa.addControl(new ControlEscala(), "bottom-left");
  mapa.addControl(new maplibregl.FullscreenControl(), "top-right");
  mapa.addControl(new ControlMapaBase(), "top-left");
  mapa.addControl(new ControlPuntos(), "top-left");
  registrarMapaBase(mapa);
  return new Promise((ok) =>
    mapa.on("load", () => {
      agregarControl3D(mapa);
      ok(mapa);
    }),
  );
}

const cacheLimites = new Map<ClaveCapa, Promise<GeoJSON.FeatureCollection>>();
export function limites(capa: ClaveCapa): Promise<GeoJSON.FeatureCollection> {
  if (!cacheLimites.has(capa)) {
    const p = fetch(url(`limites/${capa}.geojson`)).then((r) => (r.ok ? r.json() : Promise.reject(new Error(`limites ${capa}: ${r.status}`))));
    p.catch(() => cacheLimites.delete(capa));
    cacheLimites.set(capa, p);
  }
  return cacheLimites.get(capa)!;
}

/** Dibuja los límites de la capa de unidades; sin capa (null) no se dibuja ningún límite. */
export async function mostrarCapa(mapa: MapaML, capa: ClaveCapa | null) {
  const datos = capa ? await limites(capa) : vacio;
  (mapa.getSource("unidades") as GeoJSONSource).setData(datos);
  espejar("unidades", datos);
}

/** Delimita la unidad y atenúa todo lo demás con un polígono inverso. */
export function seleccionar(mapa: MapaML, f: GeoJSON.Feature | null) {
  const sel: GeoJSON.FeatureCollection = f ? { type: "FeatureCollection", features: [f] } : vacio;
  (mapa.getSource("seleccion") as GeoJSONSource).setData(sel);
  espejar("seleccion", sel);
  if (!f) {
    (mapa.getSource("mascara") as GeoJSONSource).setData(vacio);
    espejar("mascara", vacio);
    return;
  }
  const g = f.geometry as GeoJSON.Polygon | GeoJSON.MultiPolygon;
  const exteriores = g.type === "Polygon" ? [g.coordinates[0]] : g.coordinates.map((p) => p[0]);
  const mundo = [[-180, -85], [180, -85], [180, 85], [-180, 85], [-180, -85]];
  // anillos interiores con sentido contrario al exterior
  const huecos = exteriores.map((r) => [...r].reverse());
  const masc: GeoJSON.Feature = { type: "Feature", properties: {}, geometry: { type: "Polygon", coordinates: [mundo, ...huecos] } };
  (mapa.getSource("mascara") as GeoJSONSource).setData(masc);
  espejar("mascara", masc);
}

export function encuadrar(mapa: MapaML, bbox: [number, number, number, number], animar = true) {
  mapa.fitBounds([[bbox[0], bbox[1]], [bbox[2], bbox[3]]], { padding: 40, animate: animar, maxZoom: ZOOM_MAX_MAPA });
}

export function refrescarEcosistemas(mapa: MapaML, version: number) {
  (mapa.getSource("eco") as maplibregl.RasterTileSource).setTiles([`eco://{z}/{x}/{y}?v=${version}`]);
}

/** Captura el mapa encuadrado en la unidad (para el PDF) y devuelve la vista anterior.
 *  Se dibuja a 3200 × 2400 píxeles con relación de píxel 1, igual en cualquier pantalla: el encuadre pide un nivel de
 *  teselas más que a 1600 px (más detalle del ráster de 30 m) y en la hoja da unos 450 ppp. Los límites dibujados con
 *  ancho fijo se engruesan al doble mientras dura la captura para que se vean igual que antes. */
let capturando: Promise<string> | null = null;
export function capturar(mapa: MapaML, bbox: [number, number, number, number] | null, ancho = 3200, alto = 2400): Promise<string> {
  // un segundo clic mientras se captura reutiliza la misma captura en lugar de desordenar el lienzo
  capturando ??= capturarMapa(mapa, bbox, ancho, alto).finally(() => (capturando = null));
  return capturando;
}

async function capturarMapa(mapa: MapaML, bbox: [number, number, number, number] | null, ancho: number, alto: number): Promise<string> {
  const previa = { center: mapa.getCenter(), zoom: mapa.getZoom(), pitch: mapa.getPitch(), bearing: mapa.getBearing() };
  const cont = mapa.getContainer();
  const estiloPrevio = cont.getAttribute("style") ?? "";
  const ratioPrevio = mapa.getPixelRatio();
  const ESCALA = ancho / 1600;
  const anchos: [string, number][] = [];
  for (const id of ["deptos-linea", "seleccion-halo", "seleccion-linea"]) {
    const w = mapa.getLayer(id) ? mapa.getPaintProperty(id, "line-width") : undefined;
    if (typeof w === "number") {
      anchos.push([id, w]);
      mapa.setPaintProperty(id, "line-width", w * ESCALA);
    }
  }
  try {
    mapa.jumpTo({ pitch: 0, bearing: 0 });
    mapa.setPixelRatio(1);
    Object.assign(cont.style, { position: "fixed", left: "-10000px", top: "0", width: `${ancho}px`, height: `${alto}px` });
    mapa.resize();
    if (bbox) mapa.fitBounds([[bbox[0], bbox[1]], [bbox[2], bbox[3]]], { padding: 30 * ESCALA, animate: false, maxZoom: ZOOM_MAX_MAPA });
    else mapa.fitBounds(HONDURAS, { padding: 10 * ESCALA, animate: false });
    // espera a que se dibujen todas las teselas, con un máximo de 20 s si alguna no llega
    await new Promise<void>((ok) => {
      const t = setTimeout(ok, 20000);
      mapa.once("idle", () => {
        clearTimeout(t);
        ok();
      });
    });
    const lienzo = mapa.getCanvas();
    const salida = document.createElement("canvas");
    salida.width = lienzo.width;
    salida.height = lienzo.height;
    const ctx = salida.getContext("2d")!;
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, salida.width, salida.height);
    ctx.drawImage(lienzo, 0, 0);
    return salida.toDataURL("image/jpeg", 0.92);
  } finally {
    for (const [id, w] of anchos) mapa.setPaintProperty(id, "line-width", w);
    mapa.setPixelRatio(ratioPrevio);
    cont.setAttribute("style", estiloPrevio);
    mapa.resize();
    mapa.jumpTo(previa);
  }
}
