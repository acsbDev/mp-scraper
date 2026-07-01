import re
import zipfile
import unidecode
import logging
import pandas as pd


class LicTransformer:
    """
    Clase encargada de leer, limpiar y transformar los archivos descargados de licitaciones.

    Procesa el archivo ZIP con el Excel de licitaciones publicadas y el CSV con datos
    complementarios, filtra las licitaciones según rango de fechas y categorías
    permitidas, normaliza textos, calcula cantidad de productos y construye el
    DataFrame final listo para ser guardado en MongoDB.

    Esta clase no realiza scraping ni operaciones contra la base de datos.
    """

    def __init__(self):
        self.log = logging.getLogger(self.__class__.__name__)

    def _normalize_text(self, text):
        """
        Normaliza un valor de texto.

        Convierte strings a minúsculas, elimina tildes o caracteres especiales y reduce
        múltiples espacios a uno solo. Si el valor recibido no es un string, retorna una
        cadena vacía.

        Args:
            text: Valor a normalizar.

        Returns:
            str: Texto normalizado.
        """
        if isinstance(text, str):
            normalized = unidecode.unidecode(text.lower())

            normalized = re.sub(r'\s+', ' ', normalized)

            return normalized.strip()

        return ''

    def _read_lic_xlsx_from_zip(self, zip_path: str) -> pd.DataFrame:
        """
        Lee el archivo Excel de licitaciones contenido dentro de un ZIP.

        Busca el primer archivo .xlsx dentro del ZIP descargado desde MercadoPublico y
        lo carga en un DataFrame usando las columnas y encabezado esperados.

        Args:
            zip_path: Ruta del archivo ZIP descargado.

        Returns:
            pd.DataFrame: DataFrame con la información base de licitaciones.

        Raises:
            FileNotFoundError: Si no se encuentra ningún archivo .xlsx dentro del ZIP.
        """
        with zipfile.ZipFile(zip_path) as the_zip:
            xlsx_files = [
                file_name
                for file_name in the_zip.namelist()
                if file_name.endswith(".xlsx")
            ]

            if not xlsx_files:
                raise FileNotFoundError(
                    "No se encontró archivo .xlsx dentro del ZIP")

            with the_zip.open(xlsx_files[0]) as the_xlsx:
                return pd.read_excel(the_xlsx, usecols="B:O", header=7)

    def _read_lic_csv(self, csv_path: str) -> pd.DataFrame:
        """
        Lee el archivo CSV complementario de licitaciones.

        Carga los campos necesarios del CSV descargado desde MercadoPublico, incluyendo
        el ID de licitación, moneda y monto de licitación.

        Args:
            csv_path: Ruta del archivo CSV descargado.

        Returns:
            pd.DataFrame: DataFrame con los datos complementarios de licitaciones.
        """
        return pd.read_csv(
            csv_path,
            sep=";",
            usecols=["IDLicitacion", "Moneda", "MontoLicitacion"],
        )

    def clean_data(self, zip_path, csv_path, from_date: pd.Timestamp, to_date: pd.Timestamp):
        """
        Limpia y transforma los archivos descargados de licitaciones.

        Lee el Excel contenido en el ZIP y el CSV complementario, elimina columnas no
        utilizadas, filtra licitaciones por fecha y tipo, renombra columnas, normaliza
        textos, calcula la cantidad de productos por licitación, incorpora presupuesto y
        moneda, marca licitaciones con demasiados productos y agrupa los productos en una
        lista por cada licitación.

        Args:
            zip_path: Ruta del archivo ZIP descargado.
            csv_path: Ruta del archivo CSV descargado.
            from_date: Fecha inicial del rango de publicación a considerar.
            to_date: Fecha final del rango de publicación a considerar.

        Returns:
            pd.DataFrame: DataFrame final con una fila por licitación, incluyendo datos
            generales, presupuesto, moneda, productos asociados, campos de control y link
            directo a MercadoPublico.
        """

        self.log.info("Leyendo archivo ZIP: %s", zip_path)
        df = self._read_lic_xlsx_from_zip(zip_path)

        self.log.info("Leyendo archivo CSV: %s", csv_path)
        df_list = self._read_lic_csv(csv_path)

        self.log.info(
            "Filtrando licitaciones desde %s hasta %s",
            from_date,
            to_date,
        )

        df.drop(
            columns=[
                "Unnamed: 3",
                "Unnamed: 8",
                "Tipo Adquisición",
                "Código ONU",
                "Descripción",
            ],
            inplace=True,
            errors="ignore",
        )

        rename_columns = {
            "Numero Adquisición": "id",
            "Nombre Adquisición": "name",
            "Organismo": "organism",
            "Región Compradora": "region",
            "Fecha Publicación": "publishDate",
            "Fecha Cierre": "closeDate",
            "Descripción del producto/servicio": "desc",
            "Unidad de Medida": "unit",
            "Cantidad": "qty",
        }

        categories = ["L1", "LE", "LP", "LQ", "LR", "CO", "B2", "H2", "I2"]
        pattern = '|'.join(categories)

        df["Fecha Publicación"] = pd.to_datetime(
            df["Fecha Publicación"],
            errors="coerce",
        )

        df_filtered = df[(df["Fecha Publicación"] >= from_date) & (df["Fecha Publicación"] <= to_date) & (
            df["Numero Adquisición"].str.contains(pattern, na=False))].reset_index(drop=True)

        df_filtered.rename(columns=rename_columns, inplace=True)

        if df_filtered.empty:
            self.log.info("No se encontraron licitaciones")
            return pd.DataFrame(columns=df_filtered.columns)

        df_list.rename(columns={
                       "IDLicitacion": "id", "MontoLicitacion": "budget", "Moneda": "currency"}, inplace=True)

        prod_count = df_filtered.groupby('id').agg(
            prod_count=pd.NamedAgg(column="desc", aggfunc='nunique')
        ).reset_index()

        df_filtered = df_filtered.merge(prod_count, on="id")

        df_filtered = df_filtered.merge(
            df_list, left_on="id", right_on="id", how="left")
        
        self.log.info("Licitaciones filtradas: %s filas", len(df_filtered))
        self.log.info("Licitaciones únicas: %s", df_filtered["id"].nunique())

        text_columns = ['name', 'organism', 'desc', 'unit', 'region']

        df_normalized = df_filtered.copy()
        df_normalized[text_columns] = df_filtered[text_columns].apply(
            lambda col: col.apply(self._normalize_text))

        df_normalized["desc"] = df_normalized["desc"].apply(
            lambda x: self._normalize_text(x))
        df_normalized["name"] = df_normalized["name"].apply(
            lambda x: self._normalize_text(x))

        df_normalized["filtered_out"] = False

        df_normalized["budget"] = df_normalized["budget"].astype(
            "str").str.replace(".", "")

        df_normalized["budget"] = pd.to_numeric(
            df_normalized["budget"], errors="coerce").fillna(0).astype(int)

        df_normalized.loc[df_normalized["prod_count"]
                          > 30, "filtered_out"] = True

        products = df_normalized[["id", "desc", "qty", "unit"]]

        prod_group = products.groupby('id')[["desc", "qty", "unit"]].apply(
            lambda x: x[["desc", "qty", "unit"]].to_dict(orient="records")
        ).reset_index(name="products")

        columns = ['name', 'organism', 'region', 'publishDate',
                   'closeDate', 'prod_count', 'filtered_out', 'budget', 'currency']
        # Crear un DataFrame final con la información relevante
        df_final = df_normalized.groupby("id")[columns].agg({
            'name': 'first',
            'organism': 'first',
            'region': 'first',
            'publishDate': 'first',
            'closeDate': 'first',
            'prod_count': 'first',
            'filtered_out': 'first',
            'budget': 'first',
            'currency': 'first',
        }).reset_index()

        df_final_prod = df_final.merge(prod_group, on='id', how='left')

        df_final_prod[["control_lic_obs", "selected"]] = ["", False]

        df_final_prod["link"] = df_final_prod["id"].apply(
            lambda x: f"http://www.mercadopublico.cl/Procurement/Modules/RFB/DetailsAcquisition.aspx?idlicitacion={x}")
        
        self.log.info(
            "Transformación finalizada: %s licitaciones listas para guardar",
            len(df_final_prod),
        )

        return df_final_prod
