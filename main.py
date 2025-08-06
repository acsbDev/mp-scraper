import os
from mp_scraper.mp_scraper import MPScraper
from pymongo import MongoClient

def main():
    
    atlas_uri = os.getenv("MONGODB_URI")
    client = MongoClient(atlas_uri)
    db = client.arrocera_erp_db
    lic_col = db.licitaciones

    scraper = MPScraper()

    df = scraper.request_merge_and_clean_lics()

    if df.empty:
        return

    results = df.to_dict(orient='records')

    lic_col.insert_many(results)
    
    print(f"Se insertaron {len(results)} licitaciones")

    pipeline = [
        {
            "$group": {
                "_id": "$id",            # group by the custom 'id' field
                "ids": {"$push": "$_id"}, # collect all MongoDB _ids for each id
                "count": {"$sum": 1}      # count documents in each group
            }
        },
        {
            "$match": {
                "count": {"$gt": 1}       # only groups with more than one doc
            }
        }
    ]

    duplicates = lic_col.aggregate(pipeline)

    for doc in duplicates:
        all_ids = doc["ids"]
        # Decide which one to keep. Here we keep the first in the list:
        ids_to_remove = all_ids[1:]
        result = lic_col.delete_many({"_id": {"$in": ids_to_remove}})
        print(f"Removed {result.deleted_count} duplicates for id={doc['_id']}")

    print(f"Se eliminaron {len(list(duplicates))} licitaciones duplicadas")

    scraper.cleanup_downloads()

if __name__ == "__main__": 
    
    main()