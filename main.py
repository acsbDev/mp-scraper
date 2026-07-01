from pymongo import MongoClient
import logging
import sys

from lic_scraper.settings import settings
from lic_scraper.mp_web_scraper import MPWebScraper
from lic_scraper.lic_transformer import LicTransformer
from lic_scraper.lic_repository import LicRepository
from lic_scraper.lic_runner import LicScraperRunner
from lic_scraper.run_state import RunState


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )


def main():
    configure_logging()

    mongo_client = MongoClient(settings.mongo_uri)
    db = mongo_client[settings.db_name]

    web_scraper = MPWebScraper(
        headless=settings.headless,
        max_retries=settings.max_retries,
    )

    transformer = LicTransformer()

    repository = LicRepository(db)

    run_state = RunState()

    runner = LicScraperRunner(
        web_scraper=web_scraper,
        transformer=transformer,
        repository=repository,
        run_state=run_state,
    )

    try:
        runner.run_once()
    finally:
        mongo_client.close()


if __name__ == "__main__":

    main()
