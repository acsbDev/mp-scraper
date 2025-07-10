import pandas as pd
import time
import os
import re
import zipfile
import unidecode
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

class MPScraper: 
    def __init__(self, headless:bool = True):

        options = Options()

        self.download_dir = os.path.dirname(os.path.abspath(__file__))

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
        self.max_retries = 3

    def _normalize_text(self, text):
        # Verificar si el texto es una cadena de texto
        if isinstance(text, str):
            # Convertir a minúsculas y eliminar caracteres especiales/acentos
            normalized = unidecode.unidecode(text.lower())

            # Reemplaza multiples espacios en uno solo
            normalized = re.sub(r'\s+', ' ', normalized)

            return normalized.strip()

        return ''

    def _wait_for_downloads(self, endswith, timeout=30):
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

    def _get_csv_from_search(self):
        
        retries = 0
        while retries < self.max_retries:
            try:
                self.driver.get("https://www.mercadopublico.cl/Home/BusquedaLicitacion")
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

    def _get_zip_from_mainpage(self):
        retries = 0
        while retries < self.max_retries:
            try:
                self.driver.get("https://www.mercadopublico.cl/")
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

    def _clean_data(self):

        with zipfile.ZipFile(os.path.join(self.download_dir, "Licitacion_Publicada.zip")) as the_zip:
            for file_name in the_zip.namelist():
                if file_name.endswith('.xlsx'):  # Buscar archivos CSV en el zip
                    with the_zip.open(file_name) as the_xlsx:
                        # Leer el archivo CSV en un DataFrame con las columnas especificadas
                        df = pd.read_excel(the_xlsx, usecols="B:O", header=7)

        df_list = pd.read_csv(os.path.join(self.download_dir, 'ListaLicitaciones.csv'), sep=";", usecols=["IDLicitacion", "Moneda", "MontoLicitacion"])

        df.drop(columns=["Unnamed: 3", "Unnamed: 8", "Tipo Adquisición", "Código ONU", "Descripción"], inplace=True)

        rename_columns = {
            "Numero Adquisición":"id",
            "Nombre Adquisición":"name",
            "Organismo":"organism",
            "Región Compradora":"region",
            "Fecha Publicación":"publishDate",
            "Fecha Cierre":"closeDate",
            "Descripción del producto/servicio":"desc",
            "Unidad de Medida": "unit",
            "Cantidad": "qty"
        }

        categories = ["L1", "LE", "LP", "LQ", "LR"]
        pattern = '|'.join(categories)

        today = pd.Timestamp.today().normalize()

        # If it’s Monday (weekday()==0), go back 3 days; otherwise just 1 day
        if today.weekday() == 0:
            from_date = today - pd.Timedelta(days=4)
        else:
            from_date = today - pd.Timedelta(days=1)

        to_date = today

        df_filtered = df[(df["Fecha Publicación"] >= from_date) & (df["Fecha Publicación"] <= to_date) & (df["Numero Adquisición"].str.contains(pattern))].reset_index(drop=True)

        df_filtered.rename(columns=rename_columns, inplace=True)
        df_list.rename(columns={"IDLicitacion":"id", "MontoLicitacion":"budget", "Moneda":"currency"}, inplace=True)

        prod_count = df_filtered.groupby('id').agg(
            prod_count = pd.NamedAgg(column="desc", aggfunc='nunique')
        ).reset_index()

        df_filtered = df_filtered.merge(prod_count, on="id")

        df_filtered.info()

        df_filtered = df_filtered.merge(df_list, left_on="id", right_on="id", how="left")

        text_columns = ['name', 'organism', 'desc', 'unit', 'region']

        df_normalized = df_filtered.copy()
        df_normalized[text_columns] = df_filtered[text_columns].apply(lambda col: col.apply(self._normalize_text))

        df_normalized["desc"] = df_normalized["desc"].apply(lambda x: self._normalize_text(x))
        df_normalized["name"] = df_normalized["name"].apply(lambda x: self._normalize_text(x))

        df_normalized["filtered_out"] = False

        df_normalized["budget"] = df_normalized["budget"].astype("str").str.replace(".", "")

        df_normalized["budget"] = pd.to_numeric(df_normalized["budget"], errors="coerce").fillna(0).astype(int)

        df_normalized.loc[df_normalized["prod_count"] > 30, "filtered_out"] = True

        products = df_normalized[["id", "desc", "qty", "unit"]]

        prod_group = products.groupby('id')[["desc", "qty", "unit"]].apply(
            lambda x: x[["desc","qty","unit"]].to_dict(orient="records")
        ).reset_index(name="products")

        columns = ['name', 'organism', 'region', 'publishDate', 'closeDate', 'prod_count', 'filtered_out', 'budget', 'currency']
        # Crear un DataFrame final con la información relevante
        df_final = df_normalized.groupby("id")[columns].agg({
            'name': 'first',
            'organism': 'first',
            'region': 'first',
            'publishDate':'first',
            'closeDate': 'first',
            'prod_count':'first',
            'filtered_out':'first',
            'budget':'first',
            'currency':'first',
        }).reset_index()

        df_final_prod = df_final.merge(prod_group, on='id', how='left')

        df_final_prod[["control_lic_obs", "selected"]] = ["", False]

        df_final_prod["link"] = df_final_prod["id"].apply(lambda x: f"http://www.mercadopublico.cl/Procurement/Modules/RFB/DetailsAcquisition.aspx?idlicitacion={x}")

        return df_final_prod
    
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
    
    def request_merge_and_clean_lics(self):

        self._get_csv_from_search()
        self._get_zip_from_mainpage()

        df = self._clean_data()

        return df

