import re
import os
import zipfile
import unidecode
import pandas as pd


class LicTransformer:

    def __init__(self, download_dir: str):
        self.download_dir = download_dir

    def _normalize_text(self, text):
        # Verificar si el texto es una cadena de texto
        if isinstance(text, str):
            # Convertir a minúsculas y eliminar caracteres especiales/acentos
            normalized = unidecode.unidecode(text.lower())

            # Reemplaza multiples espacios en uno solo
            normalized = re.sub(r'\s+', ' ', normalized)

            return normalized.strip()

        return ''


    def clean_data(self):

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

        categories = ["L1", "LE", "LP", "LQ", "LR", "CO", "B2", "H2", "I2"]
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

        if df_filtered.empty:
            print("No se encontraron licitaciones")
            return pd.DataFrame(columns=df_filtered.columns)
        
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