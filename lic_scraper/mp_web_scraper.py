import os
import time
import re
import logging
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException, WebDriverException, NoAlertPresentException
from webdriver_manager.chrome import ChromeDriverManager


class MPWebScraper:

    """
    Clase encargada de interactuar con el portal web de MercadoPublico usando Selenium.

    Su responsabilidad es abrir las páginas necesarias, descargar los archivos de
    licitaciones publicados por MercadoPublico y administrar la limpieza de archivos
    temporales descargados.
    """

    def __init__(self, headless: bool = True, max_retries: int = 3, download_dir: str | None = None,):
        """
        Inicializa el navegador Selenium y configura la carpeta de descargas.

        Configura Chrome, define las opciones de ejecución, establece la carpeta donde se
        guardarán los archivos descargados y crea las instancias de WebDriver y
        WebDriverWait necesarias para interactuar con el sitio.

        Args:
            headless: Indica si Chrome debe ejecutarse sin interfaz gráfica.
            max_retries: Cantidad máxima de reintentos para abrir páginas o realizar
                descargas.
            download_dir: Carpeta donde se guardarán los archivos descargados. Si no se
                entrega, se usa la carpeta del módulo actual.
        """

        self.log = logging.getLogger(self.__class__.__name__)

        self.download_dir = os.path.abspath(
            download_dir or os.path.dirname(os.path.abspath(__file__))
        )

        Path(self.download_dir).mkdir(parents=True, exist_ok=True)

        options = Options()

        if headless:
            options.add_argument("--headless")
            options.add_argument("--window-size=1920,1080")
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")

        prefs = {
            "download.default_directory": self.download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        }

        options.add_experimental_option("prefs", prefs)

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.wait = WebDriverWait(self.driver, 30)
        self.max_retries = max_retries

    def _wait_for_downloads(self, endswith: str, started_at: float, timeout: int = 60):
        """
        Espera hasta que una descarga finalice correctamente.

        Busca en la carpeta de descargas un archivo con la extensión indicada, generado
        después del momento de inicio recibido. También verifica que no existan archivos
        temporales de descarga incompleta.

        Args:
            endswith: Extensión esperada del archivo descargado.
            started_at: Timestamp que indica desde qué momento se considera válida una
                descarga.
            timeout: Tiempo máximo de espera en segundos.

        Returns:
            str: Ruta completa del archivo descargado.

        Raises:
            TimeoutError: Si no se encuentra una descarga completada dentro del tiempo
                máximo configurado.
        """
        end_time = time.time() + timeout

        # 1) Wait for at least one file to show up
        while time.time() < end_time:
            files = os.listdir(self.download_dir)
            # filter out temporary partial downloads

            has_partial_downloads = any(
                file.endswith((".crdownload", ".part"))
                and os.path.getmtime(os.path.join(self.download_dir, file)) >= started_at
                for file in files
            )

            completed_files = [
                file
                for file in files
                if file.endswith(endswith)
                and os.path.getmtime(os.path.join(self.download_dir, file)) >= started_at
            ]

            if completed_files and not has_partial_downloads:
                completed_files.sort(
                    key=lambda file: os.path.getmtime(
                        os.path.join(self.download_dir, file)
                    ),
                    reverse=True,
                )

                return os.path.join(self.download_dir, completed_files[0])

            time.sleep(0.5)

        raise TimeoutError(
            f"No se completó la descarga en {self.download_dir} después de {timeout}s"
        )

    def _dismiss_alert_if_present(self):
        """
        Cierra una alerta del navegador si está presente.

        Intenta aceptar una alerta activa de Selenium. Si no existe ninguna alerta,
        continúa sin realizar ninguna acción.
        """
        try:
            alert = self.driver.switch_to.alert
            alert.accept()
        except NoAlertPresentException:
            pass

    def _open_url_with_retry(self, url: str) -> None:
        """
        Abre una URL en el navegador usando reintentos.

        Intenta cargar la página indicada y cerrar cualquier alerta que aparezca. Si la
        página no puede abrirse correctamente, reintenta hasta alcanzar el máximo
        configurado.

        Args:
            url: URL que se desea abrir en el navegador.

        Raises:
            RuntimeError: Si la URL no puede abrirse después de todos los reintentos.
        """
        for attempt in range(self.max_retries):
            try:
                self.driver.get(url)
                self._dismiss_alert_if_present()
                return
            except WebDriverException as e:
                self.log.warning(
                    f"No se pudo abrir la URL. Intento {attempt + 1}/{self.max_retries}. Error: {e}"
                )
                time.sleep(1)

        raise RuntimeError(
            f"No se pudo abrir la URL después de {self.max_retries} intentos: {url}")

    def get_csv_from_search(self) -> str:
        """
        Descarga el archivo CSV de licitaciones desde el buscador de MercadoPublico.

        Abre el buscador de licitaciones, entra al iframe principal, aplica los filtros
        necesarios, ordena los resultados y presiona el botón de descarga del CSV.

        Returns:
            str: Ruta completa del archivo CSV descargado.

        Raises:
            RuntimeError: Si no se puede iniciar la descarga después de los reintentos.
            TimeoutError: Si el archivo CSV no termina de descargarse dentro del tiempo
                esperado.
        """

        self._open_url_with_retry(
            "https://www.mercadopublico.cl/Home/BusquedaLicitacion"
        )

        self.driver.switch_to.default_content()

        self.wait.until(
            EC.frame_to_be_available_and_switch_to_it((By.ID, "form-iframe"))
        )

        select_el = self.wait.until(
            EC.presence_of_element_located((By.ID, "selectestado"))
        )
        Select(select_el).select_by_value("5")

        select_el = self.wait.until(
            EC.presence_of_element_located((By.ID, "ordenarpor"))
        )
        Select(select_el).select_by_value("3")

        self.wait.until(
            EC.invisibility_of_element_located((By.ID, "preloader"))
        )

        for attempt in range(self.max_retries):
            try:
                download_btn = self.wait.until(
                    EC.presence_of_element_located((By.ID, "descargarCSV"))
                )

                started_at = time.time()

                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center'});",
                    download_btn,
                )

                self.driver.execute_script(
                    "arguments[0].click();",
                    download_btn,
                )

                self.log.info("Descarga CSV iniciada")

                return self._wait_for_downloads(".csv", started_at)

            except (TimeoutException, StaleElementReferenceException) as e:
                self.log.warning(
                    f"No se pudo descargar el CSV. "
                    f"Intento {attempt + 1}/{self.max_retries}. Error: {e}"
                )
                time.sleep(1)

        raise RuntimeError("No se pudo descargar el CSV después de varios intentos")

    def get_zip_from_mainpage(self) -> str:
        """
        Descarga el archivo ZIP de licitaciones publicadas desde la página principal.

        Abre la página principal de MercadoPublico, obtiene la URL de descarga desde el
        botón correspondiente y navega directamente a esa URL para iniciar la descarga.

        Returns:
            str: Ruta completa del archivo ZIP descargado.

        Raises:
            RuntimeError: Si no se puede obtener la URL de descarga del ZIP.
            TimeoutError: Si el archivo ZIP no termina de descargarse dentro del tiempo
                esperado.
        """
        self._open_url_with_retry("https://www.mercadopublico.cl/")

        btn = self.wait.until(
            EC.presence_of_element_located(
                (By.XPATH, "//button[normalize-space(text())='Descargar']")
            )
        )

        onclick = btn.get_attribute("onclick") or ""
        match = re.search(r"'([^']+)'", onclick)

        if not match:
            raise RuntimeError("No se pudo obtener la URL de descarga del ZIP")

        download_url = match.group(1)

        started_at = time.time()

        self.driver.get(download_url)

        self.log.info("Descarga ZIP iniciada")

        return self._wait_for_downloads(".zip", started_at)

    def cleanup_downloads(self) -> None:
        """
        Elimina archivos descargados por el scraper.

        Borra archivos CSV, XLSX y ZIP desde la carpeta de descargas configurada para
        evitar que ejecuciones posteriores reutilicen archivos antiguos.
        """
        p = Path(self.download_dir)

        for pattern in ("*.csv", "*.xlsx", "*.zip"):
            for file in p.glob(pattern):
                try:
                    file.unlink()
                    self.log.info(f"Archivo eliminado: {file.name}")
                except Exception as e:
                    self.log.warning(f"No se pudo eliminar {file.name}: {e}")

    def close(self) -> None:
        """
        Cierra el navegador Selenium.

        Libera los recursos asociados al WebDriver al finalizar la ejecución del
        scraper.
        """
        try:
            self.driver.quit()
        except Exception as e:
            self.log.warning(f"No se pudo cerrar el navegador correctamente: {e}")
