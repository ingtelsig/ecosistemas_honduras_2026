// Teselas ráster 2026 con el código de clase por píxel (R = código >> 8, G = código & 255; alfa 0 = sin dato).
// El protocolo "eco://" lee la tesela del PMTiles, guarda los códigos y devuelve una imagen pintada
// con la paleta oficial; las clases ocultas se pintan transparentes.
import { addProtocol } from "maplibre-gl";
import { PMTiles } from "pmtiles";
import { url, type Clase } from "./datos";

export const ZOOM_MAX_DATOS = 13;
const LADO = 256;

const archivo = new PMTiles(url("ecosistemas_R26.pmtiles"));
const codigos = new Map<string, Promise<Uint16Array | null>>();
const ORDEN: string[] = [];
const MAX_CACHE = 600;

// Tabla de colores por código: RGBA, alfa 0 = clase oculta
const lut = new Uint8ClampedArray(65536 * 4);
let version = 0;

export function fijarColores(clases: Clase[], visibles: Set<number>): number {
  lut.fill(0);
  for (const c of clases) {
    if (!visibles.has(c.codigo)) continue;
    const i = c.codigo * 4;
    lut[i] = parseInt(c.color.slice(1, 3), 16);
    lut[i + 1] = parseInt(c.color.slice(3, 5), 16);
    lut[i + 2] = parseInt(c.color.slice(5, 7), 16);
    lut[i + 3] = 255;
  }
  return ++version;
}

let lienzo: OffscreenCanvas | HTMLCanvasElement | null = null;
function contexto() {
  if (!lienzo) lienzo = typeof OffscreenCanvas !== "undefined" ? new OffscreenCanvas(LADO, LADO) : Object.assign(document.createElement("canvas"), { width: LADO, height: LADO });
  return lienzo.getContext("2d", { willReadFrequently: true }) as CanvasRenderingContext2D | OffscreenCanvasRenderingContext2D;
}

async function decodificar(z: number, x: number, y: number, signal?: AbortSignal): Promise<Uint16Array | null> {
  const r = await archivo.getZxy(z, x, y, signal);
  if (!r) return null;
  const bmp = await createImageBitmap(new Blob([r.data], { type: "image/png" }), {
    premultiplyAlpha: "none",
    colorSpaceConversion: "none",
  });
  const ctx = contexto();
  ctx.clearRect(0, 0, LADO, LADO);
  ctx.drawImage(bmp, 0, 0);
  bmp.close();
  const px = ctx.getImageData(0, 0, LADO, LADO).data;
  const out = new Uint16Array(LADO * LADO);
  for (let i = 0, j = 0; i < out.length; i++, j += 4) out[i] = px[j + 3] ? (px[j] << 8) | px[j + 1] : 0;
  return out;
}

export function codigosTesela(z: number, x: number, y: number): Promise<Uint16Array | null> {
  const k = `${z}/${x}/${y}`;
  let p = codigos.get(k);
  if (!p) {
    p = decodificar(z, x, y).catch((e) => {
      codigos.delete(k);
      throw e;
    });
    codigos.set(k, p);
    ORDEN.push(k);
    if (ORDEN.length > MAX_CACHE) codigos.delete(ORDEN.shift()!);
  }
  return p;
}

let vacia: ImageBitmap | null = null;

export function registrarProtocolo() {
  addProtocol("eco", async (params) => {
    const m = /eco:\/\/(\d+)\/(\d+)\/(\d+)/.exec(params.url);
    if (!m) throw new Error("URL de tesela no válida");
    const cod = await codigosTesela(+m[1], +m[2], +m[3]);
    if (!cod) {
      vacia ??= await createImageBitmap(new ImageData(1, 1));
      return { data: vacia };
    }
    const img = new ImageData(LADO, LADO);
    const d = img.data;
    for (let i = 0, j = 0; i < cod.length; i++, j += 4) {
      const c = cod[i];
      if (!c) continue;
      const l = c * 4;
      d[j] = lut[l];
      d[j + 1] = lut[l + 1];
      d[j + 2] = lut[l + 2];
      d[j + 3] = lut[l + 3];
    }
    return { data: await createImageBitmap(img) };
  });
}

/** Código de clase bajo una coordenada, leído en la tesela más detallada disponible. */
export async function codigoEn(lng: number, lat: number, zoomMapa: number): Promise<number> {
  const z = Math.max(5, Math.min(ZOOM_MAX_DATOS, Math.floor(zoomMapa) + 1));
  const n = 2 ** z;
  const xf = ((lng + 180) / 360) * n;
  const s = Math.sin((lat * Math.PI) / 180);
  const yf = (0.5 - Math.log((1 + s) / (1 - s)) / (4 * Math.PI)) * n;
  const x = Math.floor(xf), y = Math.floor(yf);
  const cod = await codigosTesela(z, x, y);
  if (!cod) return 0;
  const px = Math.min(LADO - 1, Math.floor((xf - x) * LADO));
  const py = Math.min(LADO - 1, Math.floor((yf - y) * LADO));
  return cod[py * LADO + px];
}
