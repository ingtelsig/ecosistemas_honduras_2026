# Geovisor de Ecosistemas de Honduras · R26

Aplicación web estática que presenta el **Mapa de Ecosistemas de Honduras, edición R26**: 115 clases nacionales en 14 grupos, a 30 m, con su correspondencia a la Tipología Global de Ecosistemas de la UICN (GET).

- Mapa con todas las clases. Un clic identifica la clase del punto.
- Unidades de reporte: áreas protegidas (SINAPH), pueblos indígenas y afrohondureños, departamentos y municipios.
- Resumen por unidad: superficie, grupos, reinos GET y tabla de clases.
- Descarga por unidad: **reporte PDF** (mapa, cifras clave, grupos, GET, clases y nota de fuentes) y **CSV**.
- Filtro de clases y grupos sobre el mapa, y enlaces directos a una unidad (`?capa=municipios&id=HN0801`).
- Leyenda derecha plegable con la jerarquía GET-UICN (Reino › Bioma › EFG › clase). Sus casillas también filtran el mapa, y puede limitarse a las clases de la unidad seleccionada.
- Catálogo de fichas de las 115 unidades ecosistémicas. Se abre desde la pestaña Catálogo o con el botón **i** junto a cada clase: en la leyenda, en la tabla del resumen y en la consulta por clic.
- El PDF lista las clases presentes por grupo nacional y por jerarquía GET-UICN.
- Zoom máximo fijado a la escala del mapa, 1:50.000 (escala nominal con píxel de 0,28 mm), que se muestra en la esquina inferior izquierda.

No usa servidores ni servicios externos. El mapa base se dibuja con los límites propios del proyecto, y el ráster va en un único archivo PMTiles que se lee por rangos HTTP.

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

### Capas de comparación (criterios ecológicos y mapa 2002)

```bash
python datos/04_capas_comparacion.py
```

Genera `public/data/capas/<id>.pmtiles` y `capas/capas.json`. Se puede pasar una lista de ids para regenerar solo esas capas (por ejemplo `python datos/04_capas_comparacion.py evi2 lluvia`). Fuentes:

- Capas base iniciales en `D:/web_GPT_proyectos/informe_mapa_ecosistemas/capas_base` (variable `CAPAS_BASE`): cobertura 2024 (HND_02), elevación (HND_01), vertiente (HND_03), HAND (HND_06), grupo de drenaje (HND_10), estacionalidad del agua GSW (HND_08), altura y cobertura arbórea integradas (HND_22 y HND_23). El piso altitudinal se calcula con los umbrales del R26 desde la elevación y la vertiente.
- Clima y fenología en la versión usada en el R26, no las capas iniciales HND_11–16: CHPclim2 1991–2020 (`insumos_GEE/CHPclim2_mensual_1991_2020.tif`) para la lluvia anual y los meses con menos de 60 mm, y Sentinel-2 2019–2025 (amplitud EVI2 P90 − P10) desde `@MAPA_ECOSISTEMAS_V00/35_fenologia_sentinel2_2019_2025` (variable `ANALISIS_DIR`).
- Mapa de Ecosistemas 2002 (`insumos/ecosistemas.geojson`), rasterizado a la malla de las teselas. Cada clase 2002 toma el color de la clase R26 con la que más se superpone; la tabla queda en `datos/correspondencia_2002_R26.csv` y la columna `codigo_r26_color` se puede editar para cambiar un color (el script la respeta al volver a ejecutarse).

Cada píxel guarda un índice de 8 bits: en capas continuas es el valor escalado entre un mínimo y un máximo (lineal o raíz cuadrada), en capas de clases es el código. El navegador colorea los índices y los traduce a valores al hacer clic. Las capas continuas llegan hasta zoom 10–11 (≈ 75–150 m por píxel) y las de clases hasta zoom 12.

En el visor, el botón «Comparar» abre el selector de capa y una cortina deslizante: a la izquierda el R26, a la derecha la capa elegida. Al hacer clic en el mapa, «Ver criterios ecológicos en este punto» lee el valor de todas las capas en ese lugar.

### Nombres ajustados

`datos/nombres_ajustados.json` cambia el nombre de 8 clases en el geovisor (1322–1324, 1332–1334, 8132 y 8133): «seco» pasa a «estacional (semideciduo a deciduo)». Estas clases tienen la misma elevación y lluvia que sus pares estacionales; las separa la mayor deciduidad del dosel (EVI2). Los códigos y superficies R26 no cambian. Lo leen `02_limites_y_resumenes.py` (para `clases.json`) y `03_fichas.py`, que además ajusta las frases de las fichas que describían la unidad como seca y añade una nota de ajuste al inicio de cada una.

Las rutas de origen están al principio de cada script: el ráster maestro R26, el `.qml` de la simbología, el catálogo de clases, `territorios.gpkg` y los cruces territoriales oficiales. El segundo script compara cada unidad con `cruces_territoriales.csv` de la entrega R26 y escribe el resultado en `manifiesto.json` (`control_cruces_R26`). En la versión actual la diferencia es de 0,00 ha en las tres capas.

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

Límites de GitHub Pages: el sitio publicado no puede pasar de 1 GB y ningún archivo de 100 MB. Este sitio ocupa unos 67 MB.

## Fuentes

- Ecosistemas: Mapa de Ecosistemas de Honduras R26 (`Mapa_Ecosistemas_R26_30m.tif`). SERNA, ICF, UICN ORMACC, CCAD/KfW; consultoría INGTELSIG.
- Áreas protegidas: ICF, Geoportal, áreas protegidas declaradas del SINAPH (75 áreas).
- Pueblos indígenas y afrohondureños: UICN-Honduras.
- Departamentos y municipios: OCHA/HDX, límites administrativos a partir de SINIT/SEPLAN 2010 (CC BY-IGO).

Las superficies son cartográficas: celdas de 0,09 ha cuyo centro cae dentro de la unidad. Los totales nacionales oficiales aplican un ajuste proporcional por dominio que no se reparte por unidad.
