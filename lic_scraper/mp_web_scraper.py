import os
import time
import re
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

    def __init__(self, headless:bool = True, max_retries: int = 3, download_dir: str | None = None,):

        options = Options()

        self.download_dir = download_dir or os.path.dirname(os.path.abspath(__file__))

        if headless:
            options.add_argument("--headless")
            options.add_argument("--window-size=1920,1080")
            options.add_argument("--disable-gpu")               # recommended for Linux
            options.add_argument("--no-sandbox")                # recommended in many CI systems
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

    def _wait_for_downloads(self, endswith, timeout=60):
        """
        Wait up to `timeout` seconds for any .crdownload/.part files in
        download_dir to disappear and for at least one new file to appear.
        """
        end_time = time.time() + timeout

        # 1) Wait for at least one file to show up
        while time.time() < end_time:
            files = os.listdir(self.download_dir)
            # filter out temporary partial downloads
            completed = [f for f in files if f.endswith(endswith)]
            if completed:
                # 2) make sure no partials remain
                if not any(f.endswith((".crdownload", ".part")) for f in files):
                    return os.path.join(self.download_dir, completed[0])
            time.sleep(0.5)

        raise TimeoutError(f"No completed download in {self.download_dir} after {timeout}s")
    
    def _dismiss_alert_if_present(self):
        try:
            alert = self.driver.switch_to.alert
            alert.accept()
        except NoAlertPresentException:
            pass

    def get_csv_from_search(self):
        
        retries = 0
        while retries < self.max_retries:
            try:
                self.driver.get("https://www.mercadopublico.cl/Home/BusquedaLicitacion")
                self._dismiss_alert_if_present()
                break
            except WebDriverException:
                retries += 1
                time.sleep(1)

        self.driver.switch_to.frame("form-iframe")

        select_el = self.wait.until(EC.presence_of_element_located((By.ID, "selectestado")))
        Select(select_el).select_by_value("5")

        select_el = self.wait.until(EC.presence_of_element_located((By.ID, "ordenarpor")))
        Select(select_el).select_by_value("3")

        self.wait.until(EC.invisibility_of_element_located((By.ID, "preloader")))

        retries = 0
        while retries < self.max_retries:
            try:
                download_btn = self.wait.until(EC.presence_of_element_located((By.ID, "descargarCSV")))
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", download_btn)
                self.driver.execute_script("arguments[0].click();", download_btn)
                print("Clicked on descargarCSV")
                break
            except (TimeoutException, StaleElementReferenceException):
                retries += 1
                print(f"Attempt {retries} failed; retrying in 1s…")
                time.sleep(1)

        self._wait_for_downloads(".csv")

    def get_zip_from_mainpage(self):
        retries = 0
        while retries < self.max_retries:
            try:
                self.driver.get("https://www.mercadopublico.cl/")
                self._dismiss_alert_if_present()
                break
            except WebDriverException:
                retries += 1
                time.sleep(1)

        btn = self.driver.find_element(By.XPATH, "//button[normalize-space(text())='Descargar']")

        # 2) Extract the URL from its onclick attribute
        onclick = btn.get_attribute("onclick")
        # e.g. "location.href='https://.../att.ashx?id=5'"
        match = re.search(r"'([^']+)'", onclick)

        if not match:
            raise RuntimeError("Couldn't parse download URL")
        
        download_url = match.group(1)

        # 3) Navigate straight to it
        self.driver.get(download_url)

        self._wait_for_downloads(".zip")

    def cleanup_downloads(self):
        """
        Remove all .csv, .xlsx and .zip files in download_dir.
        """
    
        p = Path(self.download_dir)

        for pattern in ("*.csv", "*.xlsx", "*.zip"):
            for f in p.glob(pattern):
                try:
                    f.unlink()
                    print(f"Deleted {f.name}")
                except Exception as e:
                    print(f"Could not delete {f.name}: {e}")

    def close(self):
        self.driver.quit()