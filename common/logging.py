from __future__ import annotations

import logging
import os


def configure_logging(level: str | None = None) -> None:
    effective_level = level or os.getenv("LOG_LEVEL", "INFO")
    logging.basicConfig(
        level=effective_level.upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
