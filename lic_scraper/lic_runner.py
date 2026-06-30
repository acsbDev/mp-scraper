import logging


class LicScraperRunner:
    """
    Orquestador principal del scraper de licitaciones.

    Coordina el flujo completo del proceso: descarga los archivos desde
    MercadoPublico, obtiene el rango de fechas a procesar, transforma los datos,
    guarda las licitaciones en MongoDB, elimina duplicados y limpia los archivos
    temporales al finalizar.
    """

    def __init__(
        self,
        web_scraper,
        transformer,
        repository,
        run_state,
    ):
        """
        Inicializa el runner con las dependencias necesarias para ejecutar el scraper.

        Args:
            web_scraper: Componente encargado de descargar los archivos desde
                MercadoPublico.
            transformer: Componente encargado de leer, limpiar y transformar los datos
                descargados.
            repository: Repositorio encargado de guardar las licitaciones y eliminar
                duplicados en MongoDB.
            run_state: Componente encargado de obtener y guardar la fecha de última
                ejecución del scraper.
        """
        self.web_scraper = web_scraper
        self.transformer = transformer
        self.repository = repository
        self.run_state = run_state
        self.log = logging.getLogger(self.__class__.__name__)

    def run_once(self):
        """
        Ejecuta una corrida completa del scraper de licitaciones.

        Descarga el CSV y ZIP desde MercadoPublico, obtiene el rango de fechas a
        procesar, transforma los archivos descargados, inserta las licitaciones en
        MongoDB y elimina registros duplicados. Al finalizar, limpia los archivos
        descargados y cierra el navegador de Selenium.

        Returns:
            None
        """
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