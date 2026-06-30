import json
from pathlib import Path

import pandas as pd


class RunState:

    def __init__(self, state_path: str | None = None):
        self.state_path = Path(state_path) if state_path else self._default_state_path()

    def _default_state_path(self) -> Path:
        return Path(__file__).resolve().parent / "scraper_state.json"

    def get_date_range(self) -> tuple[pd.Timestamp, pd.Timestamp]:
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
        today = pd.Timestamp.today().normalize()

        data = {
            "last_run_date": today.strftime("%Y-%m-%d"),
        }

        self.state_path.write_text(
            json.dumps(data, indent=2),
            encoding="utf-8",
        )