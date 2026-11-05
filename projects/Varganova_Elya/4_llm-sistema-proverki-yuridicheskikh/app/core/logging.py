"""Настройка логирования приложения."""
from __future__ import annotations

import logging

_CONFIGURED = False


def get_logger(name: str = "app") -> logging.Logger:
    global _CONFIGURED
    if not _CONFIGURED:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        )
        _CONFIGURED = True
    return logging.getLogger(name)
