import logging

import pandas as pd
from pymongo.database import Database


class LicRepository:
    def __init__(self, db: Database):
        self.lic_col = db.licitaciones
        self.log = logging.getLogger(self.__class__.__name__)

    def insert_many(self, df: pd.DataFrame) -> int:
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
        pipeline = [
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
            all_ids = doc["ids"]
            ids_to_remove = all_ids[1:]

            result = self.lic_col.delete_many(
                {"_id": {"$in": ids_to_remove}}
            )

            deleted_count += result.deleted_count

            self.log.info(
                f"Se eliminaron {result.deleted_count} duplicados para id={doc['_id']}"
            )

        self.log.info(f"Se eliminaron {deleted_count} licitaciones duplicadas")

        return deleted_count
