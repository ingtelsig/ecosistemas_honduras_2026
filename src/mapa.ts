// Mapa MapLibre sin servicios externos: fondo propio (tierra, mar y límites), capa R26 y límites de reporte.
import maplibregl, { type GeoJSONSource, type LngLatBoundsLike, type Map as MapaML } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { url, type ClaveCapa } from "./datos";
import { ZOOM_MAX_DATOS } from "./teselas";
import { espejar } from "./comparar";
import { ControlMapaBase, registrarMapaBase } from "./mapabase";

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
  private fmt = new Intl.NumberFormat("es-ES", { maximumFractionDigits: 0, useGrouping: "always" } as unknown as Intl.NumberFormatOptions);
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

export function crearMapa(contenedor: string): Promise<MapaML> {
  const mapa = new maplibregl.Map({
    container: contenedor,
    maxZoom: ZOOM_MAX_MAPA,
    bounds: HONDURAS,
    fitBoundsOptions: { padding: 20 },
    maxBounds: [[-95, 9], [-76, 21]],
    attributionControl: { compact: true, customAttribution: "Mapa de Ecosistemas de Honduras R26 · Límites: ICF, SINIT/SEPLAN (HDX)" },
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
  mapa.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
  mapa.addControl(new maplibregl.ScaleControl({ unit: "metric" }), "bottom-left");
  mapa.addControl(new ControlEscala(), "bottom-left");
  mapa.addControl(new maplibregl.FullscreenControl(), "top-right");
  mapa.addControl(new ControlMapaBase(), "top-left");
  registrarMapaBase(mapa);
  return new Promise((ok) => mapa.on("load", () => ok(mapa)));
}

const cacheLimites = new Map<ClaveCapa, Promise<GeoJSON.FeatureCollection>>();
export function limites(capa: ClaveCapa): Promise<GeoJSON.FeatureCollection> {
  if (!cacheLimites.has(capa)) cacheLimites.set(capa, fetch(url(`limites/${capa}.geojson`)).then((r) => r.json()));
  return cacheLimites.get(capa)!;
}

export async function mostrarCapa(mapa: MapaML, capa: ClaveCapa) {
  const datos = await limites(capa);
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

/** Captura el mapa encuadrado en la unidad (para el PDF) y devuelve la vista anterior. */
export async function capturar(mapa: MapaML, bbox: [number, number, number, number] | null, ancho = 1600, alto = 1200): Promise<string> {
  const previa = { center: mapa.getCenter(), zoom: mapa.getZoom() };
  const cont = mapa.getContainer();
  const estiloPrevio = cont.getAttribute("style") ?? "";
  // tamaño fijo en píxeles CSS para que el encuadre sea igual en cualquier pantalla
  const ratio = window.devicePixelRatio || 1;
  Object.assign(cont.style, { position: "fixed", left: "-10000px", top: "0", width: `${ancho / ratio}px`, height: `${alto / ratio}px` });
  mapa.resize();
  if (bbox) mapa.fitBounds([[bbox[0], bbox[1]], [bbox[2], bbox[3]]], { padding: 30, animate: false, maxZoom: ZOOM_MAX_MAPA });
  else mapa.fitBounds(HONDURAS, { padding: 10, animate: false });
  await new Promise<void>((ok) => mapa.once("idle", () => ok()));
  const lienzo = mapa.getCanvas();
  const salida = document.createElement("canvas");
  salida.width = lienzo.width;
  salida.height = lienzo.height;
  const ctx = salida.getContext("2d")!;
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, salida.width, salida.height);
  ctx.drawImage(lienzo, 0, 0);
  const datos = salida.toDataURL("image/jpeg", 0.9);
  cont.setAttribute("style", estiloPrevio);
  mapa.resize();
  mapa.jumpTo(previa);
  return datos;
}
