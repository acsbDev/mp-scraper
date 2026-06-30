import logging


class LicScraperRunner:
    def __init__(
        self,
        web_scraper,
        transformer,
        repository,
        run_state,
    ):
        self.web_scraper = web_scraper
        self.transformer = transformer
        self.repository = repository
        self.run_state = run_state
        self.log = logging.getLogger(self.__class__.__name__)

    def run_once(self):
        try:
            self.log.info("Iniciando scraper de licitaciones")

            csv_path = self.web_scraper.get_csv_from_search()
            zip_path = self.web_scraper.get_zip_from_mainpage()

            from_date, to_date = self.run_state.get_date_range()

            df = self.transformer.clean_data(
                zip_path=zip_path,
                csv_path=csv_path,
                from_date=from_date,
                to_date=to_date,
            )

            if df.empty:
                self.log.info("No se encontraron licitaciones para guardar")
                return

            inserted_count = self.repository.insert_many(df)
            deleted_count = self.repository.delete_duplicates()

            self.run_state.save_last_run_date()

            self.log.info(
                f"Proceso finalizado. Insertadas: {inserted_count}, "
                f"duplicadas eliminadas: {deleted_count}"
            )

        finally:
            self.web_scraper.cleanup_downloads()
            self.web_scraper.close()