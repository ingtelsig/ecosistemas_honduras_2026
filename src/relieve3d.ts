// Vista 3D con el terreno de MapLibre (TerrainControl) sobre el modelo de elevación libre de AWS Terrain Tiles
// (Tilezen/Mapzen, SRTM y otras fuentes; codificación terrarium). Se aplica también al mapa de comparación.
import maplibregl, { type Map as MapaML } from "maplibre-gl";

const DEM = "dem";
const EXAGERACION = 1.5;
const mapas = new Set<MapaML>();
let activo = false;

function asegurarFuente(m: MapaML) {
  if (m.getSource(DEM)) return;
  m.addSource(DEM, {
    type: "raster-dem",
    tiles: ["https://elevation-tiles-prod.s3.amazonaws.com/terrarium/{z}/{x}/{y}.png"],
    encoding: "terrarium",
    tileSize: 256,
    maxzoom: 12,
    attribution:
      'Relieve 3D: <a href="https://registry.opendata.aws/terrain-tiles/" target="_blank" rel="noopener">Terrain Tiles</a> (Mapzen/Tilezen, SRTM, NASA)',
  });
}

/** Sombreado suave sobre el mapa de ecosistemas para leer el relieve en 3D. */
function sombreado(m: MapaML, si: boolean) {
  if (si && !m.getLayer("relieve-sombra")) {
    const antes = ["mascara", "deptos-linea"].find((id) => m.getLayer(id));
    m.addLayer(
      {
        id: "relieve-sombra",
        type: "hillshade",
        source: DEM,
        paint: { "hillshade-exaggeration": 0.35, "hillshade-shadow-color": "rgba(0,0,0,0.45)", "hillshade-highlight-color": "rgba(255,255,255,0.25)", "hillshade-accent-color": "rgba(0,0,0,0.15)" },
      },
      antes,
    );
  } else if (!si && m.getLayer("relieve-sombra")) m.removeLayer("relieve-sombra");
}

function aplicar(m: MapaML) {
  asegurarFuente(m);
  sombreado(m, activo);
  const t = m.getTerrain();
  if (activo && !t) m.setTerrain({ source: DEM, exaggeration: EXAGERACION });
  else if (!activo && t) m.setTerrain(null);
}

/** Registra un mapa secundario (el de comparación) para que siga el estado 3D del principal. */
export function registrarRelieve(m: MapaML) {
  mapas.add(m);
  if (m.isStyleLoaded()) aplicar(m);
  else m.once("load", () => aplicar(m));
}

/** Añade al mapa principal el botón 3D de MapLibre y ajusta la inclinación al activarlo. */
export function agregarControl3D(principal: MapaML) {
  asegurarFuente(principal);
  mapas.add(principal);
  principal.setMaxPitch(75);
  principal.addControl(new maplibregl.TerrainControl({ source: DEM, exaggeration: EXAGERACION }), "top-right");
  const titulo = () => {
    const b = principal.getContainer().querySelector<HTMLButtonElement>(".maplibregl-ctrl-terrain, .maplibregl-ctrl-terrain-enabled");
    if (b) b.title = activo ? "Volver a la vista plana (2D)" : "Vista 3D del relieve (arrastre con clic derecho o Ctrl para inclinar y girar)";
  };
  principal.on("terrain", () => {
    const si = !!principal.getTerrain();
    setTimeout(titulo, 0);
    if (si === activo) return;
    activo = si;
    for (const m of mapas) if (m !== principal && m.isStyleLoaded()) aplicar(m);
    sombreado(principal, si);
    if (si && principal.getPitch() < 30) principal.easeTo({ pitch: 60, duration: 900 });
    if (!si) principal.easeTo({ pitch: 0, bearing: 0, duration: 600 });
  });
  titulo();
}
