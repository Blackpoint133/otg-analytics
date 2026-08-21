"""Public, project-local logging compatibility layer."""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any


MAX_LOG_BYTES = 20 * 1024 * 1024
BACKUP_COUNT = 4
ENCODING = "utf-8"


class ReadableFormatter(logging.Formatter):
    """Keep the readable format used by the production logger."""

    def format(self, record: logging.LogRecord) -> str:
        timestamp = self.formatTime(record, "%Y-%m-%d %H:%M:%S")
        module_tag = getattr(record, "module_tag", record.name)
        return f"{timestamp} | {record.levelname} | {module_tag} | {record.getMessage()}"


def _default_log_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "logs"


def _log_dir() -> Path:
    configured = os.environ.get("OTG_LOG_DIR", "").strip()
    return Path(configured).expanduser() if configured else _default_log_dir()


def get_module_logger(
    logger_name: str,
    log_file: str | Path | None = None,
    module_tag: str | None = None,
    *,
    level: int = logging.DEBUG,
    max_bytes: int = MAX_LOG_BYTES,
    backup_count: int = BACKUP_COUNT,
) -> logging.Logger:
    """Return an idempotently configured rotating file logger."""
    logger = logging.getLogger(logger_name)
    logger.setLevel(level)
    logger.propagate = False
    target = Path(log_file) if log_file is not None else _log_dir() / f"{logger_name}.log"
    target = target if target.is_absolute() else _log_dir() / target
    target = target.resolve()

    for handler in logger.handlers:
        if isinstance(handler, RotatingFileHandler) and Path(handler.baseFilename).resolve() == target:
            handler.setLevel(level)
            return logger

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(
            target,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding=ENCODING,
            delay=True,
        )
    except OSError:
        # Logging must not prevent the application from starting.
        return logger

    handler.setLevel(level)
    handler.setFormatter(ReadableFormatter())
    handler.addFilter(lambda record: setattr(record, "module_tag", module_tag or logger_name) is None)
    logger.addHandler(handler)
    return logger


_APP_LOGGER = get_module_logger("app_opensea_sales", module_tag="app_opensea_sales")


def debug(message: Any, *args: Any, **kwargs: Any) -> None:
    _APP_LOGGER.debug(message, *args, **kwargs)


def info(message: Any, *args: Any, **kwargs: Any) -> None:
    _APP_LOGGER.info(message, *args, **kwargs)


def warning(message: Any, *args: Any, **kwargs: Any) -> None:
    _APP_LOGGER.warning(message, *args, **kwargs)


def error(message: Any, *args: Any, **kwargs: Any) -> None:
    _APP_LOGGER.error(message, *args, **kwargs)
