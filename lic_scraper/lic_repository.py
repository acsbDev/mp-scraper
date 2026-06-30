import logging

import pandas as pd
from pymongo.database import Database


class LicRepository:
    """
    Repositorio encargado de administrar la persistencia de licitaciones en MongoDB.

    Centraliza las operaciones contra la colección licitaciones, incluyendo la
    inserción de nuevos documentos y la eliminación de registros duplicados por id.
    Esta clase no transforma datos ni realiza scraping; solo interactúa con la base
    de datos.
    """

    def __init__(self, db: Database):
        """
        Inicializa el repositorio de licitaciones.

        Args:
            db: Instancia de la base de datos de MongoDB utilizada para acceder a la
                colección licitaciones.
        """
        self.lic_col = db.licitaciones
        self.log = logging.getLogger(self.__class__.__name__)

    def insert_many(self, df: pd.DataFrame) -> int:
        """
        Inserta múltiples licitaciones en MongoDB.

        Convierte el DataFrame recibido a una lista de documentos y los inserta en la
        colección licitaciones. Si el DataFrame está vacío o no contiene registros,
        retorna 0 sin realizar operaciones en la base de datos.

        Args:
            df: DataFrame con las licitaciones listas para guardar.

        Returns:
            int: Cantidad de licitaciones insertadas.
        """
        if df.empty:
            return 0

        results = df.to_dict(orient="records")

        if not results:
            return 0

        insert_result = self.lic_col.insert_many(results)

        inserted_count = len(insert_result.inserted_ids)

        self.log.info(f"Se insertaron {inserted_count} licitaciones")

        return inserted_count

    def delete_duplicates(self) -> int:
        """
        Inserta múltiples licitaciones en MongoDB.

        Convierte el DataFrame recibido a una lista de documentos y los inserta en la
        colección licitaciones. Si el DataFrame está vacío o no contiene registros,
        retorna 0 sin realizar operaciones en la base de datos.

        Args:
            df: DataFrame con las licitaciones listas para guardar.

        Returns:
            int: Cantidad de licitaciones insertadas.
        """
        pipeline = [
            {
                "$sort": {
                    "_id": 1,
                }
            },
            {
                "$group": {
                    "_id": "$id",
                    "ids": {"$push": "$_id"},
                    "count": {"$sum": 1},
                }
            },
            {
                "$match": {
                    "count": {"$gt": 1},
                }
            },
        ]

        duplicates = list(self.lic_col.aggregate(pipeline))

        deleted_count = 0

        for doc in duplicates:
            ids_to_remove = doc["ids"][1:]

            result = self.lic_col.delete_many(
                {"_id": {"$in": ids_to_remove}}
            )

            deleted_count += result.deleted_count

            self.log.info(
                f"Se eliminaron {result.deleted_count} duplicados para id={doc['_id']}"
            )

        self.log.info(f"Se eliminaron {deleted_count} licitaciones duplicadas")

        return deleted_count
