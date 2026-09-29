from __future__ import annotations

import logging
from pathlib import Path
from platformdirs import user_data_dir, user_log_dir

APP_NAME = "Transcriptor"
DATA_DIR = Path(user_data_dir(APP_NAME, appauthor=False))
MODEL_DIR = DATA_DIR / "models"
LOG_DIR = Path(user_log_dir(APP_NAME, appauthor=False))


def configure_logging() -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    path = LOG_DIR / "transcriptor.log"
    logging.basicConfig(filename=path, level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    return path

