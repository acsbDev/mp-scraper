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

    def __init__(self, headless: bool = True, max_retries: int = 3, download_dir: str | None = None,):

        self.log = logging.getLogger(self.__class__.__name__)
        Path(self.download_dir).mkdir(parents=True, exist_ok=True)

        self.download_dir = download_dir or os.path.dirname(
            os.path.abspath(__file__))

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
        Wait up to `timeout` seconds for any .crdownload/.part files in
        download_dir to disappear and for at least one new file to appear.
        """
        end_time = time.time() + timeout

        # 1) Wait for at least one file to show up
        while time.time() < end_time:
            files = os.listdir(self.download_dir)
            # filter out temporary partial downloads

            has_partial_downloads = any(
                file.endswith((".crdownload", ".part"))
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
            f"No completed download in {self.download_dir} after {timeout}s")

    def _dismiss_alert_if_present(self):
        try:
            alert = self.driver.switch_to.alert
            alert.accept()
        except NoAlertPresentException:
            pass

    def _open_url_with_retry(self, url: str) -> None:
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

    def get_csv_from_search(self):

        self._open_url_with_retry(
            "https://www.mercadopublico.cl/Home/BusquedaLicitacion"
        )

        # self.driver.switch_to.frame("form-iframe")

        self.driver.switch_to.default_content()

        self.wait.until(
            EC.frame_to_be_available_and_switch_to_it((By.ID, "form-iframe"))
        )

        select_el = self.wait.until(
            EC.presence_of_element_located((By.ID, "selectestado")))
        Select(select_el).select_by_value("5")

        select_el = self.wait.until(
            EC.presence_of_element_located((By.ID, "ordenarpor")))
        Select(select_el).select_by_value("3")

        self.wait.until(
            EC.invisibility_of_element_located((By.ID, "preloader")))

        for attempt in range(self.max_retries):
            try:
                download_btn = self.wait.until(
                    EC.presence_of_element_located((By.ID, "descargarCSV")))
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center'});", download_btn)
                self.driver.execute_script(
                    "arguments[0].click();", download_btn)
                print("Clicked on descargarCSV")
                break
            except (TimeoutException, StaleElementReferenceException):
                retries += 1
                print(f"Attempt {retries} failed; retrying in 1s…")
                time.sleep(1)

        self._wait_for_downloads(".csv")

    def get_zip_from_mainpage(self):
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
        p = Path(self.download_dir)

        for pattern in ("*.csv", "*.xlsx", "*.zip"):
            for file in p.glob(pattern):
                try:
                    file.unlink()
                    self.log.info(f"Archivo eliminado: {file.name}")
                except Exception as e:
                    self.log.warning(f"No se pudo eliminar {file.name}: {e}")

    def close(self) -> None:
        try:
            self.driver.quit()
        except Exception as e:
            self.log.warning(f"No se pudo cerrar el navegador correctamente: {e}")
