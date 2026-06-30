import json
from pathlib import Path

import pandas as pd


class RunState:
    """
    Clase encargada de administrar el estado de ejecución del scraper.

    Guarda y recupera la última fecha en que el scraper se ejecutó correctamente,
    permitiendo calcular el rango de fechas a consultar en la siguiente corrida.
    Si no existe un estado guardado, utiliza la lógica por defecto del scraper.
    """

    def __init__(self, state_path: str | None = None):
        """
        Inicializa el administrador de estado del scraper.

        Args:
            state_path: Ruta opcional del archivo JSON donde se guardará el estado.
                Si no se entrega, se usa scraper_state.json dentro del módulo actual.
        """
        self.state_path = Path(state_path) if state_path else self._default_state_path()

    def _default_state_path(self) -> Path:
        """
        Obtiene la ruta por defecto del archivo de estado.

        Returns:
            Path: Ruta del archivo scraper_state.json ubicado en la carpeta del módulo.
        """
        return Path(__file__).resolve().parent / "scraper_state.json"

    def get_date_range(self) -> tuple[pd.Timestamp, pd.Timestamp]:
        """
        Obtiene el rango de fechas que debe procesar el scraper.

        Si existe un archivo de estado con una fecha válida de última ejecución, utiliza
        esa fecha como inicio del rango. Si no existe estado previo, aplica la lógica por
        defecto: desde 4 días atrás si es lunes, o desde 1 día atrás para el resto de los
        días.

        Returns:
            tuple[pd.Timestamp, pd.Timestamp]: Fecha inicial y fecha final del rango a
            procesar.
        """
        today = pd.Timestamp.today().normalize()

        if self.state_path.exists():
            data = json.loads(self.state_path.read_text(encoding="utf-8"))

            last_run_date = pd.to_datetime(
                data.get("last_run_date"),
                errors="coerce",
            )

            if not pd.isna(last_run_date):
                return last_run_date.normalize(), today

        if today.weekday() == 0:
            from_date = today - pd.Timedelta(days=4)
        else:
            from_date = today - pd.Timedelta(days=1)

        return from_date, today

    def save_last_run_date(self) -> None:
        """
        Guarda la fecha actual como última ejecución del scraper.

        Actualiza o crea el archivo JSON de estado con la fecha del día actual en formato
        YYYY-MM-DD.

        Returns:
            None
        """
        today = pd.Timestamp.today().normalize()

        data = {
            "last_run_date": today.strftime("%Y-%m-%d"),
        }

        self.state_path.write_text(
            json.dumps(data, indent=2),
            encoding="utf-8",
        )