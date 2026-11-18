// Reporte PDF por unidad, generado en el navegador con jsPDF y jspdf-autotable.
import { jsPDF } from "jspdf";
import autoTable from "jspdf-autotable";
import { ha, pct, type Catalogo, type Manifiesto } from "./datos";
import type { Fila, FilaClase, Resumen } from "./resumen";
import { arbolGET, nombreGET, rutaGET } from "./leyenda";

const VERDE: [number, number, number] = [29, 94, 34];
const TINTA: [number, number, number] = [33, 37, 41];
const GRIS: [number, number, number] = [104, 112, 118];
const M = 15; // margen en mm
const ANCHO = 210 - 2 * M;

const rgb = (hex: string): [number, number, number] => [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16)) as [number, number, number];
const corto = (s: string, n: number) => (s.length > n ? s.slice(0, n - 1) + "…" : s);
const fechaHoy = () => new Date().toLocaleDateString("es-HN", { day: "2-digit", month: "long", year: "numeric" });

export interface DatosReporte {
  resumen: Resumen;
  capaNombre: string;
  contexto: string; // p. ej. "Municipio del departamento de Francisco Morazán"
  mapa: string; // dataURL JPEG 4:3
  catalogo: Catalogo;
  manifiesto: Manifiesto;
}

export function crearPDF(d: DatosReporte): jsPDF {
  const { resumen: r, catalogo: cat, manifiesto: man } = d;
  const doc = new jsPDF({ unit: "mm", format: "a4", compress: true });
  doc.setProperties({
    title: `Ecosistemas de ${r.unidad.nombre} · 2026`,
    subject: "Resumen de ecosistemas por unidad territorial",
    author: "Mapa de Ecosistemas de Honduras 2026",
    creator: "Geovisor de Ecosistemas de Honduras",
  });

  const titulo = (t: string, y: number) => {
    doc.setFont("helvetica", "bold").setFontSize(12.5).setTextColor(...VERDE).text(t, M, y);
    doc.setDrawColor(...VERDE).setLineWidth(0.4).line(M, y + 1.8, M + ANCHO, y + 1.8);
    return y + 8;
  };
  const cuerpo = (t: string, y: number, tam = 9.5, color = TINTA) => {
    doc.setFont("helvetica", "normal").setFontSize(tam).setTextColor(...color);
    const lineas = doc.splitTextToSize(t, ANCHO) as string[];
    doc.text(lineas, M, y);
    return y + lineas.length * tam * 0.42 + 2;
  };

  // ---------- Página 1: identificación, cifras clave, mapa y leyenda ----------
  doc.setFillColor(...VERDE).rect(0, 0, 210, 18, "F");
  doc.setFont("helvetica", "bold").setFontSize(9).setTextColor(255, 255, 255).text("MAPA DE ECOSISTEMAS DE HONDURAS 2026", M, 11);
  doc.setFont("helvetica", "normal").text(d.capaNombre.toUpperCase(), 210 - M, 11, { align: "right" });

  doc.setFont("helvetica", "bold").setFontSize(19).setTextColor(...TINTA);
  const nombre = doc.splitTextToSize(r.unidad.nombre, ANCHO) as string[];
  doc.text(nombre, M, 30);
  let y = 30 + (nombre.length - 1) * 7.5 + 6.5;
  doc.setFont("helvetica", "normal").setFontSize(10).setTextColor(...GRIS).text(d.contexto, M, y);
  y += 7;
  if (r.filtro !== null) {
    const t = `Filtro de clases aplicado en el visor: ${r.clases.length} de las ${r.unidad.clases.length} clases de la unidad (${ha(r.seleccion)} ha, ${pct((100 * r.seleccion) / r.total)} de ${ha(r.total)} ha medidas). Los porcentajes se expresan sobre la superficie total de la unidad.`;
    doc.setFontSize(8.5);
    const lineas = doc.splitTextToSize(t, ANCHO - 6) as string[];
    doc.setFillColor(253, 246, 227).roundedRect(M, y - 4, ANCHO, lineas.length * 3.8 + 3.5, 1.2, 1.2, "F");
    doc.setTextColor(122, 90, 20).text(lineas, M + 3, y);
    y += lineas.length * 3.8 + 4;
  }

  const dominante = r.grupos[0];
  const cifras: [string, string][] = [
    r.filtro !== null ? ["Superficie seleccionada", `${ha(r.seleccion)} ha`] : ["Superficie medida", `${ha(r.total)} ha`],
    ["Clases de ecosistema", String(r.clases.length)],
    r.unidad.id === "HN" || d.capaNombre === "Área protegida"
      ? ["Grupos nacionales", String(r.grupos.length)]
      : ["Dentro del SINAPH", pct(r.pctSinaph)],
    ["Grupo dominante", `${corto(dominante?.nombre ?? "-", 44)} (${pct(dominante?.pct ?? 0)})`],
  ];
  const wC = ANCHO / 4;
  cifras.forEach(([et, v], i) => {
    const x = M + i * wC;
    doc.setFillColor(243, 246, 243).roundedRect(x + 0.8, y, wC - 1.6, 17, 1.5, 1.5, "F");
    doc.setFont("helvetica", "normal").setFontSize(7.5).setTextColor(...GRIS).text(et.toUpperCase(), x + 3.5, y + 5.5);
    doc.setFont("helvetica", "bold").setFontSize(i === 3 ? 8.2 : 12).setTextColor(...TINTA);
    doc.text(doc.splitTextToSize(v, wC - 7) as string[], x + 3.5, y + 11.8);
  });
  y += 22;

  const altoMapa = ANCHO * 0.75;
  doc.addImage(d.mapa, "JPEG", M, y, ANCHO, altoMapa, undefined, "FAST");
  doc.setDrawColor(190, 196, 200).setLineWidth(0.3).rect(M, y, ANCHO, altoMapa);
  y += altoMapa + 6;

  // Leyenda: clases principales en dos columnas
  doc.setFont("helvetica", "bold").setFontSize(9).setTextColor(...TINTA).text("Clases principales", M, y);
  y += 4.5;
  const max = 16;
  const lista = r.clases.slice(0, max);
  const col = ANCHO / 2;
  lista.forEach((f, i) => {
    const x = M + (i % 2) * col;
    const yy = y + Math.floor(i / 2) * 5;
    doc.setFillColor(...rgb(f.color)).rect(x, yy - 2.8, 4, 3.2, "F");
    doc.setFont("helvetica", "normal").setFontSize(7.3).setTextColor(...TINTA);
    doc.text(`${f.codigo} ${corto(f.nombre, 52)}`, x + 5.5, yy);
    doc.setTextColor(...GRIS).text(pct(f.pct), x + col - 3, yy, { align: "right" });
  });
  y += Math.ceil(lista.length / 2) * 5 + 1;
  if (r.clases.length > max) {
    const resto = r.clases.slice(max).reduce((s, f) => s + f.pct, 0);
    cuerpo(`Otras ${r.clases.length - max} clases suman ${pct(resto)}. La tabla completa está en las páginas siguientes.`, y, 7.5, GRIS);
  }

  // ---------- Página 2: grupos nacionales y GET-UICN ----------
  doc.addPage();
  y = titulo("Superficie por grupo nacional", 22);
  const etiqueta = 70, barra = ANCHO - etiqueta - 42;
  const maxPct = Math.max(...r.grupos.map((g) => g.pct), 1);
  for (const g of r.grupos) {
    doc.setFont("helvetica", "normal").setFontSize(8.3).setTextColor(...TINTA).text(corto(`${g.codigo} ${g.nombre}`, 44), M, y + 3);
    doc.setFillColor(...rgb(g.color)).rect(M + etiqueta, y, Math.max(0.6, (barra * g.pct) / maxPct), 4, "F");
    doc.setTextColor(...GRIS).text(`${ha(g.ha)} ha · ${pct(g.pct)}`, M + ANCHO, y + 3, { align: "right" });
    y += 6.4;
  }
  y += 4;
  y = titulo("Tipología Global de Ecosistemas (GET-UICN)", y);
  const tabla = (cab: string, filas: Fila[], inicio: number) => {
    autoTable(doc, {
      startY: inicio,
      margin: { left: M, right: M },
      head: [[cab, "Nombre", "Hectáreas", "%"]],
      body: filas.map((f) => [f.codigo, f.nombre, ha(f.ha), pct(f.pct)]),
      styles: { fontSize: 8, cellPadding: 1.4, textColor: TINTA },
      headStyles: { fillColor: VERDE, textColor: 255 },
      columnStyles: { 0: { cellWidth: 20 }, 2: { halign: "right", cellWidth: 28 }, 3: { halign: "right", cellWidth: 18 } },
      theme: "striped",
    });
    return (doc as unknown as { lastAutoTable: { finalY: number } }).lastAutoTable.finalY + 6;
  };
  y = tabla("Reino", r.get1, y);
  y = tabla("Bioma", r.get2, y);
  cuerpo(
    "Las clases con correspondencia a varios grupos funcionales (EFG) se informan como «asignación múltiple» para no contar dos veces la misma superficie.",
    y,
    7.8,
    GRIS,
  );

  // ---------- Páginas 3+: clases presentes con las dos jerarquías ----------
  type FilaJ = { nivel: 0 | 1 | 2; texto: string; ha: number; pct: number } | FilaClase;
  const esClase = (f: FilaJ): f is FilaClase => "clase" in f;
  const suma = (fs: FilaClase[]) => fs.reduce((s, f) => s + f.ha, 0);
  const cab = (nivel: 0 | 1 | 2, texto: string, fs: FilaClase[]): FilaJ => ({ nivel, texto, ha: suma(fs), pct: (100 * suma(fs)) / r.total });
  const porHa = (fs: FilaClase[]) => [...fs].sort((a, b) => b.ha - a.ha);
  const FONDO: [number, number, number][] = [[221, 235, 222], [236, 243, 236], [246, 249, 246]];

  const tablaJerarquica = (tituloTabla: string, nota: string, columnaExtra: string, extra: (f: FilaClase) => string, filas: FilaJ[]) => {
    if (y > 240) {
      doc.addPage();
      y = 22;
    }
    y = titulo(tituloTabla, y);
    y = cuerpo(nota, y, 7.8, GRIS);
    autoTable(doc, {
      startY: y,
      margin: { left: M, right: M, top: 20, bottom: 18 },
      head: [["", "Código", "Clase de ecosistema", columnaExtra, "Hectáreas", "%"]],
      body: filas.map((f) =>
        esClase(f)
          ? ["", f.codigo, f.nombre, extra(f), ha(f.ha, 2), pct(f.pct)]
          : [
              { content: f.texto, colSpan: 4, styles: { fontStyle: f.nivel === 2 ? "italic" : "bold", fillColor: FONDO[f.nivel], cellPadding: { top: 1.4, bottom: 1.4, left: 1.5 + 3 * f.nivel, right: 1 } } },
              { content: ha(f.ha, 2), styles: { fontStyle: "bold", fillColor: FONDO[f.nivel] } },
              { content: pct(f.pct), styles: { fontStyle: "bold", fillColor: FONDO[f.nivel] } },
            ],
      ),
      styles: { fontSize: 7.3, cellPadding: 1.1, textColor: TINTA, valign: "middle" },
      headStyles: { fillColor: VERDE, textColor: 255 },
      columnStyles: {
        0: { cellWidth: 5 },
        1: { cellWidth: 13 },
        3: { cellWidth: 15 },
        4: { halign: "right", cellWidth: 24 },
        5: { halign: "right", cellWidth: 13 },
      },
      theme: "plain",
      didDrawCell: (c) => {
        const f = filas[c.row.index];
        if (c.section === "body" && c.column.index === 0 && esClase(f)) {
          doc.setFillColor(...rgb(f.color)).rect(c.cell.x + 1, c.cell.y + c.cell.height / 2 - 1.6, 3, 3.2, "F");
        }
        if (c.section === "body" && esClase(f)) {
          doc.setDrawColor(232, 235, 237).setLineWidth(0.15).line(c.cell.x, c.cell.y + c.cell.height, c.cell.x + c.cell.width, c.cell.y + c.cell.height);
        }
      },
    });
    y = (doc as unknown as { lastAutoTable: { finalY: number } }).lastAutoTable.finalY + 8;
  };

  // a) Grupos nacionales
  const filasG: FilaJ[] = [];
  for (const g of cat.grupos) {
    const fs = r.clases.filter((f) => f.clase.grupo === g.codigo);
    if (!fs.length) continue;
    filasG.push(cab(0, `${g.codigo} ${g.nombre}`, fs), ...porHa(fs));
  }
  doc.addPage();
  y = 22;
  tablaJerarquica(
    "Clases presentes por grupo nacional",
    "Grupo nacional › unidad ecosistémica. Los porcentajes se expresan sobre la superficie total de la unidad.",
    "GET L3",
    (f) => f.clase.get3 + (f.clase.alt.length ? ` (o ${f.clase.alt.join(", ")})` : ""),
    filasG,
  );

  // b) GET-UICN: Reino › Bioma › Grupo funcional (EFG)
  const filasT: FilaJ[] = [];
  const porCodigo = new Map(r.clases.map((f) => [f.clase.codigo, f]));
  for (const [k1, biomas] of arbolGET(r.clases.map((f) => f.clase))) {
    const fs1 = [...biomas.values()].flatMap((m) => [...m.values()].flat()).map((c) => porCodigo.get(c.codigo)!);
    filasT.push(cab(0, `${k1 === "MULT" ? "" : k1 + " · "}${nombreGET(cat, 0, k1)}`, fs1));
    for (const [k2, efgs] of biomas) {
      const fs2 = [...efgs.values()].flat().map((c) => porCodigo.get(c.codigo)!);
      filasT.push(cab(1, `${k2 === "MULT" ? "" : k2 + " · "}${nombreGET(cat, 1, k2)}`, fs2));
      for (const [k3, cl] of efgs) {
        const fs3 = cl.map((c) => porCodigo.get(c.codigo)!);
        const ctx = cl.some((c) => rutaGET(c)[3]);
        filasT.push(cab(2, `${k3 === "MULT" ? "" : k3 + " · "}${nombreGET(cat, 2, k3)}${ctx ? " (relación contextual)" : ""}`, fs3), ...porHa(fs3));
      }
    }
  }
  tablaJerarquica(
    "Clases presentes por jerarquía GET-UICN",
    "Reino › Bioma › Grupo funcional (EFG) › unidad ecosistémica. Cada clase figura en su clase GET-UICN principal (la más probable); la columna de la primera tabla indica también los otros EFG posibles. La 635 está bajo M3.4 por relación contextual (geoforma).",
    "Grupo",
    (f) => f.clase.grupo,
    filasT,
  );

  // ---------- Nota metodológica ----------
  if (y > 230) {
    doc.addPage();
    y = 22;
  }
  y = titulo("Nota metodológica y fuentes", y);
  const fuente = (clave: string) => man.fuentes[clave] ?? "";
  const capaFuente =
    d.capaNombre === "Área protegida" ? fuente("areas_protegidas") : d.capaNombre === "Pueblo indígena o afrohondureño" ? fuente("pueblos_indigenas") : d.capaNombre === "Departamento" ? fuente("departamentos") : d.capaNombre === "Municipio" ? fuente("municipios") : d.capaNombre === "Cuenca hidrográfica" ? fuente("cuencas") : d.capaNombre === "Subcuenca hidrográfica" ? fuente("subcuencas") : d.capaNombre === "Microcuenca declarada" ? fuente("microcuencas") : "";
  const notas = [
    `Superficies medidas sobre el ráster maestro del Mapa de Ecosistemas de Honduras 2026 (archivo ${man.raster.archivo}), celdas de 30 × 30 m (0,09 ha) en EPSG:32616. Los manglares están ajustados por costa: las celdas de manglar del Golfo de Fonseca llevan las clases del Pacífico (6262, 6272) y las de la costa norte las del Caribe (6261, 6271). Una celda pertenece a la unidad cuando su centro cae dentro del límite.`,
    "Son superficies cartográficas. Los totales nacionales oficiales aplican un ajuste proporcional por dominio (tierra 11.277.700 ha; mar 21.027.713,75 ha) que no se reparte por unidad, por lo que pueden diferir ligeramente de las cifras de este reporte.",
    "Clases y correspondencias GET-UICN según el catálogo oficial del Mapa de Ecosistemas 2026 (115 clases, 14 grupos nacionales).",
    capaFuente ? `Límites de la unidad: ${capaFuente}.` : "",
    r.unidad.id !== "HN" && d.capaNombre !== "Área protegida" ? "El porcentaje dentro del SINAPH usa la unión de las áreas protegidas declaradas del Geoportal ICF." : "",
    `Cita sugerida: Mapa de Ecosistemas de Honduras 2026. SERNA, ICF, UICN ORMACC, CCAD/KfW; consultoría INGTELSIG. Reporte generado el ${fechaHoy()} con datos del ${man.generado}.`,
  ].filter(Boolean);
  for (const n of notas) y = cuerpo(n, y, 8.2) + 1;

  // ---------- Pie de página ----------
  const total = doc.getNumberOfPages();
  for (let p = 1; p <= total; p++) {
    doc.setPage(p);
    doc.setDrawColor(210, 214, 217).setLineWidth(0.2).line(M, 284, 210 - M, 284);
    doc.setFont("helvetica", "normal").setFontSize(7.3).setTextColor(...GRIS);
    doc.text(`${r.unidad.nombre} · Mapa de Ecosistemas de Honduras 2026 · ${fechaHoy()}`, M, 289);
    doc.text(`Página ${p} de ${total}`, 210 - M, 289, { align: "right" });
  }
  return doc;
}
