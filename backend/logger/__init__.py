"""Shared logger for the whole backend.

Usage elsewhere: `from logger import GLOBAL_LOGGER as log`.

Importing this package has side effects: it creates a `logs/` folder in the current
directory, registers an exit hook that uploads the log file to Cloud Storage (when a
bucket is configured), and configures Python logging and structlog globally.
"""
# logger/__init__.py
from .custom_logger import CustomLogger

# Create a single shared logger instance
_LOGGER_INSTANCE = CustomLogger()
# `_LOGGER_INSTANCE` is also imported by api/main.py, to flush logs at shutdown.
GLOBAL_LOGGER = _LOGGER_INSTANCE.get_logger("MeridianAI_Backend")