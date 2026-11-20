# Geovisor del Mapa de Ecosistemas de Honduras 2026

Aplicación web estática que presenta el **Mapa de Ecosistemas de Honduras 2026** (revisión interna R26): 115 clases nacionales en 14 grupos, a 30 m, con su correspondencia a la Tipología Global de Ecosistemas de la UICN (GET).

- Mapa con todas las clases. Un clic identifica la clase del punto.
- Unidades de reporte: áreas protegidas (SINAPH), pueblos indígenas y afrohondureños, departamentos, municipios, cuencas, subcuencas y microcuencas declaradas.
- Resumen por unidad: superficie, grupos, reinos GET y tabla de clases.
- Descarga por unidad: **reporte PDF** (mapa, cifras clave, grupos, GET, clases y nota de fuentes) y **CSV**.
- Filtro de clases y grupos sobre el mapa, y enlaces directos a una unidad (`?capa=municipios&id=HN0801`).
- Leyenda derecha plegable con la jerarquía GET-UICN (Reino › Bioma › EFG › clase). Sus casillas también filtran el mapa, y puede limitarse a las clases de la unidad seleccionada.
- Catálogo de fichas de las 115 unidades ecosistémicas. Se abre desde la pestaña Catálogo o con el botón **i** junto a cada clase: en la leyenda, en la tabla del resumen y en la consulta por clic.
- El PDF lista las clases presentes por grupo nacional y por jerarquía GET-UICN.
- Botón **Mapa base**: mapa base propio o mapas base gratuitos de Esri (imágenes satelitales, topográfico, calles, relieve sombreado, gris claro y gris oscuro) y el mosaico **Sentinel-2 sin nubes 2025** de EOX, con control de opacidad del mapa de ecosistemas. La elección se recuerda en el navegador y se aplica también al mapa de comparación y al PDF.
- **Vista 3D** con el control de terreno de MapLibre (botón bajo el zoom): relieve exagerado ×1.5 y sombreado suave sobre el mapa, también en la comparación. El modelo de elevación son las Terrain Tiles libres de AWS (Mapzen/Tilezen, SRTM).
- Botón **Puntos de referencia**: los 1,228 puntos del mapa en seis grupos de fuentes con símbolos en negro y blanco de formas distintas (triángulo negro para el levantamiento de campo 2026; fotointerpretación de expertos, INF, hábitats marinos, PMP 2012 y sitios de monitoreo 2000), filtrables por grupo. Un clic muestra su tabla de atributos (fuente, estrato de muestreo, clases de referencia y del mapa, GET L1–L3, trazabilidad). Los 320 puntos de campo 2026 (CAM) abren su ficha técnica de validación en PDF.
- Las asignaciones múltiples (**MULT**, «asignación múltiple») indican qué reinos, biomas o EFG reúnen: en la leyenda GET, en la ficha de cada clase y en las columnas `GET_L1_categorias`, `GET_L2_categorias` y `GET_L3_categorias` del CSV; la regla estricta va en la columna `GET_L3_estricto`.
- Zoom máximo fijado a la escala del mapa, 1:50,000 (escala nominal con píxel de 0.28 mm), que se muestra en la esquina inferior izquierda.

No necesita servidores propios. El mapa base por defecto se dibuja con los límites del proyecto, y el ráster va en un único archivo PMTiles que se lee por rangos HTTP. El relieve 3D se lee de `elevation-tiles-prod.s3.amazonaws.com`. Los mapas base opcionales se cargan desde los servicios de teselas de ArcGIS Online (`server.arcgisonline.com`) y de EOX (`tiles.maps.eox.at`, Sentinel-2 cloudless 2025, licencia CC BY-NC-SA 4.0: uso no comercial), con su atribución; están en `src/mapabase.ts`. Cuando EOX publique el mosaico de un año nuevo basta con cambiar el año en la URL de ese archivo.

## Estructura

| Ruta | Contenido |
|---|---|
| `src/` | Código TypeScript: mapa (`mapa.ts`), teselas de clases (`teselas.ts`), panel (`main.ts`), cálculos (`resumen.ts`), PDF (`reporte.ts`) |
| `public/data/ecosistemas_R26.pmtiles` | Ráster R26 en teselas PNG de códigos de clase, zoom 5 a 13 (61 MB) |
| `public/data/clases.json` | Catálogo de las 115 clases: nombre, grupo, GET, color y superficies nacionales |
| `public/data/limites/*.geojson` | Límites simplificados (WGS84) para el mapa |
| `public/data/unidades/*.json` | Hectáreas por clase de cada unidad, calculadas sobre el ráster de 30 m |
| `public/data/manifiesto.json` | Fuentes, huella sha256 del ráster y control de coincidencia con los cruces oficiales R26 |
| `datos/` | Scripts de Python que regeneran todo `public/data` |

## Desarrollo

```bash
npm install
npm run dev
```

```bash
npm run build
```

El resultado queda en `dist/`; `npm run preview` lo sirve en local.

## Regenerar los datos

Requisitos: Python 3.11+ con `rasterio`, `geopandas`, `shapely>=2.1`, `numpy`, `pandas` y `pmtiles`.

Los scripts leen el ráster maestro de la entrega (`Entrega_final_R26/Geodatos/Mapa_Ecosistemas_R26_30m.tif`). Desde el 17 de noviembre de 2026 ese maestro incluye el **ajuste de manglares por costa** (`Entrega_final_R26/scripts/18_ajuste_manglares_R26.py`): el manglar que tenía la clase del Caribe en el Golfo de Fonseca pasó a las del Pacífico (6261 → 6262: 1,459.53 ha; 6271 → 6272: 11.16 ha) y el que tenía la clase del Pacífico en la costa norte pasó a la del Caribe (6272 → 6271: 7.29 ha). Las superficies, los cruces territoriales, los indicadores y los catálogos de la entrega se recalcularon con ese maestro.

```bash
python datos/01_teselas_R26.py
```

```bash
python datos/02_limites_y_resumenes.py
```

```bash
python datos/03_fichas.py
```

El tercer script necesita además `python-docx` y `Pillow`. Extrae las 115 fichas monográficas de `Catalogos/Catalogo_agrupado_1/CATALOGO_GRUPO_*.docx` y los mapas de distribución de `scripts/work/mapas_fichas/`. El resultado va a `public/data/fichas/`: un JSON por clase y los mapas en WebP. Las fotografías de campo y los gráficos de los catálogos no se copian. El script también limpia las referencias (formato APA, la del estudio INGTELSIG / SERNA / UICN siempre como [1]).

```bash
python datos/07_mapas_fichas.py
```

Dibuja los 115 mapas de distribución de las fichas desde el ráster maestro, con el mismo diseño del catálogo (adaptado de `Entrega_final_R26/scripts/pipeline/dibujar_catalogo_R26.py`) y el rótulo «Honduras · 2026 · UTM 16N». Deja los PNG en `datos/raster/mapas_fichas/`, que es la carpeta que lee `03_fichas.py`, y los WebP en `public/data/fichas/mapas/`.

```bash
python datos/06_revision_fichas.py
```

Después de `03_fichas.py` se aplica la revisión técnica del catálogo (Miguel Mendieta, noviembre 2026). El script corrige nombres de lugares (PN Blanca Jeannette Kawas Fernández, Laguna de Guaimoreto, Kruta, Guanchias), «km²», «siempreverde», nombres comunes y especies mal asignadas. Por ejemplo, *Quercus acuta*, que viene del IFN y no tiene registros en Honduras, queda como *Quercus* sp. con una nota. También cambia «subsidio» por «aporte» y «potreros secos» por «pastos naturales o cultivados». En 47 unidades añade la sección «Aportes de la revisión técnica» antes de las referencias, con las especies y localidades que propone el revisor. Se puede ejecutar varias veces. Las observaciones de maquetación del catálogo en Word (numeración y ancho de cuadros) no aplican al visor.

### Capas de comparación (criterios ecológicos y mapa 2002)

```bash
python datos/04_capas_comparacion.py
```

Genera `public/data/capas/<id>.pmtiles` y `capas/capas.json`. Se puede pasar una lista de ids para regenerar solo esas capas (por ejemplo `python datos/04_capas_comparacion.py evi2 lluvia`). Fuentes:

- Capas base iniciales en `D:/web_GPT_proyectos/informe_mapa_ecosistemas/capas_base` (variable `CAPAS_BASE`): cobertura 2024 (HND_02), elevación (HND_01), vertiente (HND_03), HAND (HND_06), grupo de drenaje (HND_10), estacionalidad del agua GSW (HND_08), altura y cobertura arbórea integradas (HND_22 y HND_23). El piso altitudinal se calcula con los umbrales del R26 desde la elevación y la vertiente.
- Clima y fenología en la versión usada en el R26, no las capas iniciales HND_11–16: CHPclim2 1991–2020 (`insumos_GEE/CHPclim2_mensual_1991_2020.tif`) para la lluvia anual y los meses con menos de 60 mm, y Sentinel-2 2019–2025 (amplitud EVI2 P90 − P10) desde `@MAPA_ECOSISTEMAS_V00/35_fenologia_sentinel2_2019_2025` (variable `ANALISIS_DIR`).
- Mapa de Ecosistemas 2002 (`insumos/ecosistemas.geojson`), rasterizado a la malla de las teselas. Cada clase 2002 toma el color de la clase R26 con la que más se superpone; la tabla queda en `datos/correspondencia_2002_R26.csv` y la columna `codigo_r26_color` se puede editar para cambiar un color (el script la respeta al volver a ejecutarse).

Cada píxel guarda un índice de 8 bits: en capas continuas es el valor escalado entre un mínimo y un máximo (lineal o raíz cuadrada), en capas de clases es el código. El navegador colorea los índices y los traduce a valores al hacer clic. Las capas continuas llegan hasta zoom 10–11 (≈ 75–150 m por píxel) y las de clases hasta zoom 12.

El piso altitudinal separa montano y altimontano (≥ 2,000 m, umbral de referencia: el mapa los agrupa en un solo piso). Cada capa tiene un botón **i** con su fuente y su uso en la clasificación (campo `uso` de `CAPAS`), y la cobertura 2024 va al final, antes del mapa 2002.

En el visor, el botón «Comparar» abre el selector de capa y una cortina deslizante: a la izquierda el R26, a la derecha la capa elegida. Al hacer clic en el mapa, «Ver criterios ecológicos en este punto» lee el valor de todas las capas en ese lugar.

### Puntos de referencia y fichas de campo

```bash
python datos/05_puntos_referencia.py
```

Lee `Complementos_R26/Puntos_de_referencia_y_superficies_jerarquicas_R26.xlsx` (hojas `Base_Puntos_GET_UICN` y `Trazabilidad_GET_Ref`) y escribe `public/data/puntos/puntos.geojson`. Para los puntos de campo usa el Anexo 1 del Producto 3 (`Fichas_Campo_Individuales`, variable `VALIDACION_DIR`): la base de registros de campo vincula cada CAM-nnn con su ficha (el número del archivo de ficha es el del punto), y el script comprueba código de sitio y municipio antes de copiarla. Las fichas se guardan como `public/data/puntos/fichas/CAM-nnn.pdf` con las fuentes reducidas a los caracteres usados (de 1.3 GB a unos 54 MB, sin tocar las imágenes). No se publican nombres de técnicos ni fotografías aparte de lo que ya trae la ficha oficial.

### Revisión final de textos y datos

Tras regenerar las fichas, la revisión final se aplica siempre en este orden (cada paso se puede repetir):

```bash
python -X utf8 datos/08_revision_v6.py
```

```bash
python -X utf8 datos/09_correcciones_v7.py
```

```bash
python -X utf8 datos/10_datos_v7.py
```

```bash
python -X utf8 datos/11_formato_numerico.py
```

- `08_revision_v6.py` reescribe las 115 fichas desde `datos/_fichas_pre_v6` (indicadores, equivalencias con el mapa 2002 de `datos/texto_2002.py`, vertiente y entorno). De ellas, 79 conservan la sección de aportes de la revisión técnica.
- `09_correcciones_v7.py` corrige las fichas y `clases.json`: nombres oficiales de los 14 grupos, citas, topónimos (La Mosquitia, Cruta, Leán), Inventario Nacional Forestal (INF), estaciones seca y lluviosa, especies y nombres comunes, alternativas GET (T1.3) y notas de las clases 601, 8121/8131 y 6111/615/6151.
- `10_datos_v7.py` pone tildes y nombres oficiales en unidades, límites y puntos (departamentos, municipios, cuencas, áreas protegidas), y limpia la leyenda del mapa 2002, la capa de régimen climático y el manifiesto.
- `11_formato_numerico.py` deja las cifras de los textos con el formato del informe técnico final: coma de miles y punto decimal (1,234.56). El CSV de descarga usa punto decimal sin separador de miles.

### Nombre del mapa

«R26» es el número de revisión interno. Los textos públicos (visor, PDF, CSV, fichas y capas) nombran el mapa por su año: **Mapa de Ecosistemas de Honduras 2026**. `datos/texto_2026.py` aplica la regla al escribir las fichas y las capas, y `python datos/texto_2026.py` la vuelve a aplicar sobre los JSON ya generados. Los nombres de archivo y de carpeta (p. ej. `Mapa_Ecosistemas_R26_30m.tif`) no cambian.

### Cuencas, subcuencas y microcuencas declaradas

```bash
python datos/02_limites_y_resumenes.py cuencas subcuencas microcuencas
```

Las tres capas vienen de `territorios.gpkg` (`cuencas`, `subcuencas`, `microcuencas_declaradas`). Con argumentos, el script recalcula solo esas capas y conserva el control de las demás en `manifiesto.json`. Las microcuencas se contrastan con los cruces oficiales (`Microcuenca APR`); pueden solaparse y cada una cuenta su superficie completa.

### Nombres ajustados

`datos/nombres_ajustados.json` cambia el nombre de 8 clases en el geovisor (1322–1324, 1332–1334, 8132 y 8133): «seco» pasa a «estacional (semideciduo a deciduo)». Estas clases tienen la misma elevación y lluvia que sus pares estacionales; las separa la mayor deciduidad del dosel (EVI2). Los códigos y superficies R26 no cambian. Lo leen `02_limites_y_resumenes.py` (para `clases.json`) y `03_fichas.py`, que además ajusta las frases de las fichas que describían la unidad como seca y añade una nota de ajuste al inicio de cada una.

Las rutas de origen están al principio de cada script: el ráster maestro R26, el `.qml` de la simbología, el catálogo de clases, `territorios.gpkg` y los cruces territoriales oficiales. El segundo script compara cada unidad con `cruces_territoriales.csv` de la entrega R26 y escribe el resultado en `manifiesto.json` (`control_cruces_R26`). En la versión actual la diferencia es de 0.00 ha en las tres capas.

### Pueblos indígenas y afrohondureños

La capa está en `datos/fuentes/pueblos_indigenas/Pueblos indigenas.shp`: 30 polígonos con el campo `ETNIA_1`. Se puede apuntar a otro archivo con la variable de entorno `PUEBLOS_SHP`.

- **Unidades:** el script une los polígonos con la misma etiqueta y genera una unidad por pueblo. Las variantes de escritura se normalizan en `NOMBRE_PUEBLO`.
- **Categorías:** cada unidad se clasifica como pueblo indígena, pueblo afrohondureño o territorio compartido. Las etiquetas con mestizos o con más de un pueblo cuentan como territorio compartido.
- **Sin control R26:** la entrega R26 no tiene cruces territoriales de esta capa, así que no tiene contraste en `control_cruces_R26`.
- **Superficie:** varios polígonos se extienden fuera del mapa R26, hacia países vecinos o más allá del límite marino. Solo se mide la parte cubierta por el ráster.

## Publicación en GitHub Pages

1. Crear el repositorio y subir esta carpeta. No subir `node_modules`, `dist` ni `datos/_tmp`; ya están en `.gitignore`.
2. En el repositorio, ir a **Settings → Pages → Source** y elegir **GitHub Actions**.
3. Cada `push` a `main` ejecuta `.github/workflows/pages.yml`, que compila y publica.

Límites de GitHub Pages: el sitio publicado no puede pasar de 1 GB y ningún archivo de 100 MB. Este sitio ocupa unos 280 MB.

## Fuentes

- Ecosistemas: Mapa de Ecosistemas de Honduras 2026 (`Mapa_Ecosistemas_R26_30m.tif`).

Cita sugerida: INGTELSIG (2026). Actualización del Mapa de Ecosistemas de Honduras. Informe Técnico Final. Programa de Biodiversidad Enlazando el Paisaje Centroamericano, UICN, y SERNA–DiBio.
- Áreas protegidas: ICF, Geoportal, áreas protegidas declaradas del SINAPH (75 áreas).
- Pueblos indígenas y afrohondureños: UICN-Honduras.
- Departamentos y municipios: OCHA/HDX, límites administrativos a partir de SINIT/SEPLAN 2010 (CC BY-IGO).

Las superficies son cartográficas: celdas de 0.09 ha cuyo centro cae dentro de la unidad. Los totales nacionales oficiales aplican un ajuste proporcional por dominio que no se reparte por unidad.
