import re
import json
import zipfile
import unidecode
import pandas as pd
from pathlib import Path


class LicTransformer:

    def _normalize_text(self, text):
        # Verificar si el texto es una cadena de texto
        if isinstance(text, str):
            # Convertir a minúsculas y eliminar caracteres especiales/acentos
            normalized = unidecode.unidecode(text.lower())

            # Reemplaza multiples espacios en uno solo
            normalized = re.sub(r'\s+', ' ', normalized)

            return normalized.strip()

        return ''

    def _read_lic_xlsx_from_zip(self, zip_path: str) -> pd.DataFrame:
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
        return pd.read_csv(
            csv_path,
            sep=";",
            usecols=["IDLicitacion", "Moneda", "MontoLicitacion"],
        )

    def clean_data(self, zip_path, csv_path, from_date: pd.Timestamp, to_date: pd.Timestamp):

        df = self._read_lic_xlsx_from_zip(zip_path)
        df_list = self._read_lic_csv(csv_path)

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
            df["Numero Adquisición"].str.contains(pattern))].reset_index(drop=True)

        df_filtered.rename(columns=rename_columns, inplace=True)

        if df_filtered.empty:
            print("No se encontraron licitaciones")
            return pd.DataFrame(columns=df_filtered.columns)

        df_list.rename(columns={
                       "IDLicitacion": "id", "MontoLicitacion": "budget", "Moneda": "currency"}, inplace=True)

        prod_count = df_filtered.groupby('id').agg(
            prod_count=pd.NamedAgg(column="desc", aggfunc='nunique')
        ).reset_index()

        df_filtered = df_filtered.merge(prod_count, on="id")

        df_filtered.info()

        df_filtered = df_filtered.merge(
            df_list, left_on="id", right_on="id", how="left")

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

        return df_final_prod
