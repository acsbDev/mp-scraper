# MercadoPublico Licitaciones Scraper

Scraper para descargar, procesar y guardar licitaciones publicadas desde MercadoPublico.

El proceso obtiene archivos desde el portal web de MercadoPublico usando Selenium, limpia y transforma la información con pandas, guarda las licitaciones en MongoDB y elimina registros duplicados manteniendo el documento original más antiguo.

---

## ¿Qué hace este scraper?

Este scraper automatiza el siguiente flujo:

1. Ingresa al buscador de licitaciones de MercadoPublico.
2. Descarga el archivo CSV de licitaciones desde la búsqueda.
3. Ingresa a la página principal de MercadoPublico.
4. Descarga el archivo ZIP de licitaciones publicadas.
5. Lee el Excel contenido dentro del ZIP.
6. Lee el CSV complementario de licitaciones.
7. Filtra licitaciones según rango de fechas.
8. Filtra licitaciones según categorías permitidas.
9. Normaliza textos.
10. Agrupa productos por licitación.
11. Calcula cantidad de productos por licitación.
12. Marca licitaciones con demasiados productos como `filtered_out`.
13. Guarda los resultados en MongoDB.
14. Elimina duplicados por `id`, manteniendo el documento más antiguo.
15. Guarda la fecha de última ejecución en un archivo JSON.
16. Limpia los archivos descargados.

---

## Estructura del proyecto

```txt id="3z70mz"
mercadopublico_scraper/
  main.py
  Pipfile
  Pipfile.lock
  .env
  .gitignore
  install.bat
  run_scraper.bat
  install.sh
  run_scraper.sh

  lic_scraper/
    __init__.py
    settings.py
    mp_web_scraper.py
    lic_transformer.py
    lic_repository.py
    lic_runner.py
    run_state.py
```

---

## Módulos principales

### `main.py`

Punto de entrada del scraper.

Se encarga de crear las dependencias principales:

* conexión a MongoDB;
* scraper web;
* transformer;
* repository;
* run state;
* runner.

Luego ejecuta una corrida completa del scraper mediante `runner.run_once()`.

---

### `settings.py`

Carga la configuración desde variables de entorno.

Usa `python-dotenv` para leer el archivo `.env`.

Configuraciones principales:

* URI de MongoDB;
* nombre de la base de datos;
* cantidad máxima de reintentos;
* modo headless para Selenium.

---

### `mp_web_scraper.py`

Módulo encargado de interactuar con MercadoPublico usando Selenium.

Responsabilidades:

* abrir el buscador de licitaciones;
* seleccionar filtros del buscador;
* descargar el CSV;
* abrir la página principal de MercadoPublico;
* obtener la URL de descarga del ZIP;
* descargar el ZIP;
* esperar a que las descargas finalicen;
* limpiar archivos descargados;
* cerrar el navegador.

Este módulo no limpia datos ni accede a MongoDB.

---

### `lic_transformer.py`

Módulo encargado de leer, limpiar y transformar los archivos descargados.

Responsabilidades:

* leer el Excel contenido dentro del ZIP;
* leer el CSV complementario;
* eliminar columnas innecesarias;
* renombrar columnas;
* filtrar licitaciones por fecha;
* filtrar licitaciones por tipo/categoría;
* normalizar textos;
* calcular cantidad de productos;
* agregar presupuesto y moneda;
* agrupar productos por licitación;
* construir el DataFrame final.

Este módulo no descarga archivos ni guarda datos en MongoDB.

---

### `lic_repository.py`

Módulo encargado de interactuar con MongoDB.

Responsabilidades:

* insertar licitaciones en la colección `licitaciones`;
* eliminar duplicados según el campo `id`;
* mantener el documento original más antiguo;
* retornar la cantidad de documentos insertados o eliminados.

Este módulo no transforma datos ni hace scraping.

---

### `lic_runner.py`

Orquestador principal del proceso.

Responsabilidades:

* solicitar la descarga de archivos;
* obtener el rango de fechas desde `RunState`;
* enviar los archivos descargados al transformer;
* guardar licitaciones en MongoDB;
* eliminar duplicados;
* guardar la fecha de última ejecución;
* limpiar archivos temporales;
* cerrar Selenium.

---

### `run_state.py`

Módulo encargado de recordar la última fecha en que el scraper se ejecutó correctamente.

Guarda un archivo JSON local:

```txt id="ixmhk0"
lic_scraper/scraper_state.json
```

Ejemplo:

```json id="jcjue3"
{
  "last_run_date": "2026-06-30"
}
```

Si el archivo existe, el scraper usa esa fecha como inicio del próximo rango de búsqueda.

Si el archivo no existe, usa la lógica original:

* si hoy es lunes, revisa desde 4 días atrás;
* si no es lunes, revisa desde 1 día atrás.

Esto ayuda a no perder licitaciones si el scraper no se ejecutó durante varios días.

---

## Requisitos

* Python 3.10 o superior.
* Pipenv.
* Google Chrome instalado.
* Acceso a internet.
* Acceso a MongoDB Atlas.
* Credenciales válidas en el archivo `.env`.

---

## Variables de entorno

Crear un archivo `.env` en la raíz del proyecto:

```env id="4lzn8y"
ATLAS_URI=mongodb+srv://usuario:password@cluster.mongodb.net/
DB_NAME=arrocera_erp_db
MAX_RETRIES=3
HEADLESS=true
```

### Descripción de variables

| Variable      | Obligatoria | Descripción                                                            |
| ------------- | ----------: | ---------------------------------------------------------------------- |
| `ATLAS_URI`   |          Sí | URI de conexión a MongoDB Atlas.                                       |
| `DB_NAME`     |          No | Nombre de la base de datos. Por defecto: `arrocera_erp_db`.            |
| `MAX_RETRIES` |          No | Cantidad máxima de reintentos para Selenium. Por defecto: `3`.         |
| `HEADLESS`    |          No | Define si Chrome se ejecuta sin interfaz gráfica. Por defecto: `true`. |

---

## Instalación en Windows

Ejecutar una vez:

```bat id="x0cs03"
install.bat
```

Contenido recomendado:

```bat id="fht9x2"
@echo off
cd /d "%~dp0"

py -m pip install --user pipenv

pipenv install

pause
```

Luego ejecutar el scraper con:

```bat id="wynjoz"
run_scraper.bat
```

Contenido recomendado:

```bat id="l4xpvi"
@echo off
cd /d "%~dp0"

pipenv run python main.py

pause
```

Para usarlo con el Programador de tareas de Windows, se recomienda crear una versión sin `pause`:

```bat id="wqk880"
@echo off
cd /d "%~dp0"

pipenv run python main.py
```

---

## Instalación en Linux

Ejecutar una vez:

```bash id="s0tq38"
chmod +x install.sh
./install.sh
```

Contenido recomendado de `install.sh`:

```bash id="c8jpdv"
#!/usr/bin/env bash

set -e

cd "$(dirname "$0")"

python3 -m pip install --user pipenv

export PATH="$HOME/.local/bin:$PATH"

pipenv install
```

Luego ejecutar el scraper con:

```bash id="bhyu71"
chmod +x run_scraper.sh
./run_scraper.sh
```

Contenido recomendado de `run_scraper.sh`:

```bash id="i8z40b"
#!/usr/bin/env bash

cd "$(dirname "$0")"

pipenv run python main.py
```

---

## Ejecución manual

También se puede ejecutar directamente con:

```bash id="dtx4dp"
pipenv run python main.py
```

---

## Flujo de ejecución

El flujo general es:

```txt id="k5nsk6"
main.py
  -> crea MongoClient
  -> crea MPWebScraper
  -> crea LicTransformer
  -> crea LicRepository
  -> crea RunState
  -> crea LicScraperRunner
  -> ejecuta runner.run_once()
```

Luego el runner ejecuta:

```txt id="4twgyq"
1. Descargar CSV desde MercadoPublico.
2. Descargar ZIP desde MercadoPublico.
3. Obtener rango de fechas.
4. Limpiar y transformar archivos.
5. Insertar licitaciones en MongoDB.
6. Eliminar duplicados.
7. Guardar fecha de última ejecución.
8. Limpiar descargas.
9. Cerrar navegador.
```

---

## Rango de fechas

El scraper usa `RunState` para decidir qué fechas procesar.

### Si existe `scraper_state.json`

Usa la última fecha guardada como fecha inicial:

```json id="k0svao"
{
  "last_run_date": "2026-06-30"
}
```

Entonces el scraper buscará desde:

```txt id="bum5ce"
2026-06-30 hasta hoy
```

La fecha inicial se usa de forma inclusiva para evitar perder licitaciones publicadas o actualizadas el mismo día.

### Si no existe `scraper_state.json`

Usa la lógica original:

```txt id="83ft95"
lunes      -> hoy - 4 días
otro día   -> hoy - 1 día
```

---

## Archivo de estado

El archivo de estado se genera automáticamente:

```txt id="73w379"
lic_scraper/scraper_state.json
```

Este archivo no debe subirse al repositorio, porque representa el estado local de ejecución de cada máquina.

Agregar al `.gitignore`:

```gitignore id="jh8oz9"
.env
**/scraper_state.json
```

---

## Datos procesados

El DataFrame final contiene una fila por licitación.

Campos principales:

```txt id="bo55g2"
id
name
organism
region
publishDate
closeDate
prod_count
filtered_out
budget
currency
products
control_lic_obs
selected
link
```

Ejemplo de documento final:

```json id="xhv41k"
{
  "id": "1234-15-L126",
  "name": "compra de alimentos",
  "organism": "municipalidad ejemplo",
  "region": "region metropolitana",
  "publishDate": "2026-06-30T00:00:00",
  "closeDate": "2026-07-05T00:00:00",
  "prod_count": 3,
  "filtered_out": false,
  "budget": 1500000,
  "currency": "CLP",
  "products": [
    {
      "desc": "arroz grado 1",
      "qty": 20,
      "unit": "saco"
    }
  ],
  "control_lic_obs": "",
  "selected": false,
  "link": "http://www.mercadopublico.cl/Procurement/Modules/RFB/DetailsAcquisition.aspx?idlicitacion=1234-15-L126"
}
```

---

## Categorías consideradas

El scraper filtra licitaciones que contengan las siguientes categorías en el número de adquisición:

```txt id="j41wf2"
L1
LE
LP
LQ
LR
CO
B2
H2
I2
```

---

## Regla de filtrado por cantidad de productos

Si una licitación tiene más de 30 productos distintos, se marca como:

```json id="5nn2p2"
{
  "filtered_out": true
}
```

Esto permite mantener la licitación en la base de datos, pero marcarla para revisión o exclusión posterior.

---

## Duplicados

El scraper inserta los documentos obtenidos y luego elimina duplicados por el campo `id`.

La limpieza de duplicados:

1. Agrupa documentos por `id`.
2. Ordena por `_id` ascendente.
3. Mantiene el documento más antiguo.
4. Elimina los documentos repetidos posteriores.

Esto permite conservar el primer registro insertado y remover duplicados generados por corridas posteriores.

---

## Colección MongoDB

La colección utilizada es:

```txt id="m4d94z"
licitaciones
```

Dentro de la base de datos definida por:

```env id="ev37a6"
DB_NAME=arrocera_erp_db
```

---

## Archivos descargados

Durante la ejecución, Selenium descarga archivos en la carpeta del módulo del scraper por defecto.

Archivos esperados:

```txt id="jqr56i"
ListaLicitaciones.csv
Licitacion_Publicada.zip
```

Al finalizar la ejecución, el scraper elimina archivos con extensiones:

```txt id="mbt1gh"
.csv
.xlsx
.zip
```

Esto evita que una ejecución futura reutilice archivos antiguos accidentalmente.

---

## Logs

El scraper registra información durante la ejecución:

* inicio del proceso;
* descarga de CSV;
* descarga de ZIP;
* licitaciones insertadas;
* duplicados eliminados;
* archivos eliminados;
* errores de Selenium;
* errores al cerrar el navegador.

---

## Consideraciones importantes

* Google Chrome debe estar instalado en la máquina donde se ejecuta el scraper.
* `webdriver-manager` administra automáticamente el ChromeDriver.
* El archivo `.env` no debe subirse al repositorio.
* El archivo `scraper_state.json` no debe subirse al repositorio.
* Si el portal de MercadoPublico cambia su estructura HTML, puede ser necesario actualizar los selectores de Selenium.
* Si el scraper falla antes de terminar, no debería guardar la fecha de última ejecución.
* Para Windows, se recomienda usar el Programador de tareas.
* Para Linux, se recomienda usar `cron` o `systemd`.

---

## Problemas comunes

### Falta variable de entorno

Error probable:

```txt id="o47gi9"
Falta la variable de entorno requerida: ATLAS_URI
```

Solución:

Verificar que exista `.env` y que contenga:

```env id="ljtr6x"
ATLAS_URI=mongodb+srv://...
```

---

### Selenium no descarga archivos en modo headless

Verificar que Chrome esté instalado y actualizado.

Si el problema persiste, probar temporalmente con:

```env id="uvs4ml"
HEADLESS=false
```

---

### No se encontraron licitaciones

Puede ocurrir si:

* no hay licitaciones nuevas en el rango de fechas;
* el archivo de estado tiene una fecha reciente;
* el portal no descargó correctamente los archivos;
* las licitaciones no pertenecen a las categorías filtradas.

---

### Se procesan archivos antiguos

El scraper limpia descargas al finalizar, pero si una ejecución fue interrumpida manualmente podrían quedar archivos antiguos.

Solución:

Eliminar manualmente archivos `.csv`, `.xlsx` y `.zip` dentro de la carpeta del scraper.

---

### Duplicados en MongoDB

El scraper elimina duplicados al final de cada corrida. Si el proceso se interrumpe antes de llegar a esa etapa, pueden quedar duplicados temporalmente.

Solución:

Ejecutar nuevamente el scraper o correr el método de eliminación de duplicados desde el repositorio.
