from pymongo import MongoClient

from lic_scraper.settings import settings
from lic_scraper.mp_web_scraper import MPWebScraper
from lic_scraper.lic_transformer import LicTransformer
from lic_scraper.lic_repository import LicRepository
from lic_scraper.lic_runner import LicScraperRunner


def main():
    mongo_client = MongoClient(settings.mongo_uri)
    db = mongo_client[settings.db_name]

    web_scraper = MPWebScraper(
        headless=settings.headless,
        max_retries=settings.max_retries,
    )

    transformer = LicTransformer(
        download_dir=web_scraper.download_dir,
    )

    repository = LicRepository(db)

    runner = LicScraperRunner(
        web_scraper=web_scraper,
        transformer=transformer,
        repository=repository,
    )

    try:
        runner.run_once()
    finally:
        mongo_client.close()


if __name__ == "__main__":
    
    main()