import logging


class LicScraperRunner:
    def __init__(
        self,
        web_scraper,
        transformer,
        repository,
    ):
        self.web_scraper = web_scraper
        self.transformer = transformer
        self.repository = repository
        self.log = logging.getLogger(self.__class__.__name__)

    def run_once(self):
        try:
            self.log.info("Iniciando scraper de licitaciones")

            self.web_scraper.get_csv_from_search()
            self.web_scraper.get_zip_from_mainpage()

            df = self.transformer.clean_data()

            if df.empty:
                self.log.info("No se encontraron licitaciones para guardar")
                return

            inserted_count = self.repository.insert_many(df)
            deleted_count = self.repository.delete_duplicates()

            self.log.info(
                f"Proceso finalizado. Insertadas: {inserted_count}, "
                f"duplicadas eliminadas: {deleted_count}"
            )

        finally:
            self.web_scraper.cleanup_downloads()
            self.web_scraper.close()