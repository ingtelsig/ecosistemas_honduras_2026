// Ficha de una unidad ecosistémica en PDF, generada en el navegador con jsPDF a partir de la misma ficha JSON del catálogo.
import { jsPDF } from "jspdf";
import autoTable from "jspdf-autotable";
import { ha, type Catalogo, type Clase } from "./datos";
import { nombreGET, rutaGET } from "./leyenda";

const VERDE: [number, number, number] = [29, 94, 34];
const TINTA: [number, number, number] = [33, 37, 41];
const GRIS: [number, number, number] = [104, 112, 118];
const M = 15;
const ANCHO = 210 - 2 * M;
const PIE = 278; // límite inferior del cuerpo

export interface BloqueFicha {
  t: "h2" | "h3" | "p" | "li" | "nota" | "tabla";
  x?: string;
  h?: string;
  f?: string[][];
}
export interface FichaDatos {
  codigo: number;
  nombre: string;
  catalogo: string;
  bloques: BloqueFicha[];
}

/** Texto plano desde el HTML mínimo de la ficha; sustituye los signos que la fuente estándar de jsPDF no tiene. */
export function plano(html: string): string {
  const t = new DOMParser().parseFromString(`<body>${html}</body>`, "text/html").body.textContent ?? "";
  return t
    .replace(/[‐‑‒]/g, "-")
    .replace(/≥/g, ">=")
    .replace(/≤/g, "<=")
    .replace(/≈/g, "~")
    .replace(/[−]/g, "-")
    .replace(/→/g, "->")
    .replace(/[  ]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

export function crearFichaPDF(f: FichaDatos, c: Clase, cat: Catalogo, mapa: string | null, enlace: string): jsPDF {
  const doc = new jsPDF({ unit: "mm", format: "a4", compress: true });
  doc.setProperties({
    title: `Ficha ${c.codigo} · ${c.nombre}`,
    subject: "Ficha de unidad ecosistémica · Mapa de Ecosistemas de Honduras 2026",
    author: "Mapa de Ecosistemas de Honduras 2026",
    creator: "Geovisor de Ecosistemas de Honduras",
  });
  let y = 0;
  const salto = (alto: number) => {
    if (y + alto > PIE) {
      doc.addPage();
      y = 20;
    }
  };
  const texto = (t: string, opc: { tam?: number; color?: [number, number, number]; negrita?: boolean; sangria?: number; vineta?: boolean } = {}) => {
    const tam = opc.tam ?? 9.3;
    const x = M + (opc.sangria ?? 0);
    doc.setFont("helvetica", opc.negrita ? "bold" : "normal").setFontSize(tam).setTextColor(...(opc.color ?? TINTA));
    const lineas = doc.splitTextToSize(t, ANCHO - (opc.sangria ?? 0)) as string[];
    const al = tam * 0.42;
    for (let i = 0; i < lineas.length; i++) {
      salto(al + 1);
      if (i === 0 && opc.vineta) doc.text("•", x - 3.5, y);
      doc.text(lineas[i], x, y);
      y += al;
    }
    y += 1.8;
  };

  // ---------- cabecera ----------
  doc.setFillColor(...VERDE).rect(0, 0, 210, 18, "F");
  doc.setFont("helvetica", "bold").setFontSize(9).setTextColor(255, 255, 255).text("MAPA DE ECOSISTEMAS DE HONDURAS 2026", M, 11);
  doc.setFont("helvetica", "normal").text("FICHA DE UNIDAD ECOSISTÉMICA", 210 - M, 11, { align: "right" });
  const grupo = cat.grupos.find((g) => g.codigo === c.grupo);
  doc.setFillColor(...(c.color.match(/\w\w/g)!.map((h) => parseInt(h, 16)) as [number, number, number])).rect(M, 25, 6, 6, "F");
  doc.setFont("helvetica", "normal").setFontSize(9.5).setTextColor(...GRIS).text(plano(`Unidad ${c.codigo} · ${c.grupo} ${grupo?.nombre ?? ""}`), M + 9, 29.5);
  doc.setFont("helvetica", "bold").setFontSize(16).setTextColor(...TINTA);
  const nom = doc.splitTextToSize(plano(c.nombre), ANCHO) as string[];
  doc.text(nom, M, 39);
  y = 39 + nom.length * 6.6 + 1;
  const [g1, g2, g3, contextual] = rutaGET(c);
  texto(`GET-UICN principal: ${g1} › ${g2} › ${g3} ${plano(nombreGET(cat, 2, c.get3))}${contextual ? " (relación contextual)" : ""}`, { tam: 9, color: GRIS });
  if (c.alt.length) texto(`También puede corresponder a: ${c.alt.map((a) => `${a} ${plano(nombreGET(cat, 2, a))}`).join("; ")}`, { tam: 9, color: GRIS });
  if (c.criterio) texto(`Criterio de asignación: ${plano(c.criterio)}.`, { tam: 9, color: GRIS });
  texto(`Superficie nacional 2026: ${ha(c.ha_ajustada)} ha ajustadas · ${ha(c.ha_cartografiada)} ha cartografiadas`, { tam: 9, color: GRIS, negrita: true });
  y += 1;

  // ---------- mapa de distribución ----------
  if (mapa) {
    const prop = doc.getImageProperties(mapa);
    const w = 130;
    const h = (w * prop.height) / prop.width;
    salto(h + 8);
    doc.addImage(mapa, "JPEG", M + (ANCHO - w) / 2, y, w, h);
    y += h + 4;
    texto(`Distribución de la unidad ${c.codigo} en el Mapa de Ecosistemas 2026.`, { tam: 8, color: GRIS });
  }

  // ---------- contenido de la ficha ----------
  for (const b of f.bloques) {
    if (b.t === "h2") {
      y += 2;
      salto(14);
      doc.setFont("helvetica", "bold").setFontSize(11.5).setTextColor(...VERDE).text(plano(b.x ?? ""), M, y);
      doc.setDrawColor(...VERDE).setLineWidth(0.3).line(M, y + 1.6, M + ANCHO, y + 1.6);
      y += 7;
    } else if (b.t === "h3") {
      salto(12);
      texto(plano(b.x ?? ""), { tam: 10, negrita: true, color: VERDE });
    } else if (b.t === "p") texto(plano(b.h ?? ""));
    else if (b.t === "li") texto(plano(b.h ?? ""), { sangria: 5, vineta: true });
    else if (b.t === "nota") texto(plano(b.h ?? ""), { tam: 8, color: GRIS });
    else if (b.t === "tabla" && b.f?.length) {
      const [cab, ...filas] = b.f;
      salto(16);
      autoTable(doc, {
        startY: y,
        margin: { left: M, right: M, bottom: 297 - PIE },
        head: [cab.map(plano)],
        body: filas.map((r) => r.map(plano)),
        styles: { font: "helvetica", fontSize: 7.8, cellPadding: 1.3, textColor: TINTA },
        headStyles: { fillColor: VERDE, textColor: 255, fontStyle: "bold" },
        alternateRowStyles: { fillColor: [244, 246, 244] },
      });
      y = (doc as unknown as { lastAutoTable: { finalY: number } }).lastAutoTable.finalY + 4;
    }
  }
  y += 2;
  texto(
    `Fuente: Catálogo de unidades ecosistémicas del Mapa de Ecosistemas 2026 (${f.catalogo.replace(/_R26$/, "").replace(/_/g, " ")}). Las fotografías de campo y los gráficos se consultan en el catálogo completo. Ficha en línea: ${enlace}`,
    { tam: 8, color: GRIS },
  );

  // ---------- pie ----------
  const total = doc.getNumberOfPages();
  const hoy = new Date().toLocaleDateString("es-HN", { day: "2-digit", month: "long", year: "numeric" });
  for (let p = 1; p <= total; p++) {
    doc.setPage(p);
    doc.setDrawColor(210, 214, 217).setLineWidth(0.2).line(M, 284, 210 - M, 284);
    doc.setFont("helvetica", "normal").setFontSize(7.3).setTextColor(...GRIS);
    doc.text(`Ficha ${c.codigo} · Mapa de Ecosistemas de Honduras 2026 · ${hoy}`, M, 289);
    doc.text(`Página ${p} de ${total}`, 210 - M, 289, { align: "right" });
  }
  return doc;
}
