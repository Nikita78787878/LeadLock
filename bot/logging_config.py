"""
Конфигурация логирования.

Схема:
  - Консоль  — цветной human-readable (dev) или JSON (prod), уровень INFO
  - logs/app.log    — все логи DEBUG+, ротация по дням, 30 дней
  - logs/errors.log — только ERROR+, ротация по дням, 90 дней

Использование:
    from bot.logging_config import setup_logging
    setup_logging(log_level="INFO", env="production")
"""

import logging
import logging.handlers
import os
import sys

import structlog


def setup_logging(log_level: str = "INFO", env: str = "production") -> None:
    """Настраивает structlog + stdlib logging с выводом в консоль и файлы."""

    numeric_level = logging.getLevelName(log_level.upper())

    # -------------------------------------------------------------------------
    # 1. Общие процессоры structlog (применяются до рендеринга)
    # -------------------------------------------------------------------------
    shared_processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.ExtraAdder(),
    ]

    # -------------------------------------------------------------------------
    # 2. Настраиваем structlog — делегирует вывод в stdlib
    # -------------------------------------------------------------------------
    structlog.configure(
        processors=shared_processors
        + [structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        cache_logger_on_first_use=True,
    )

    # -------------------------------------------------------------------------
    # 3. Форматтеры
    # -------------------------------------------------------------------------
    if env == "development":
        console_formatter = structlog.stdlib.ProcessorFormatter(
            processor=structlog.dev.ConsoleRenderer(colors=True),
            foreign_pre_chain=shared_processors,
        )
    else:
        console_formatter = structlog.stdlib.ProcessorFormatter(
            processor=structlog.processors.JSONRenderer(),
            foreign_pre_chain=shared_processors,
        )

    # Файлы всегда в JSON — удобно парсить (Grafana Loki, ELK и т.д.)
    file_formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.processors.JSONRenderer(),
        foreign_pre_chain=shared_processors,
    )

    # -------------------------------------------------------------------------
    # 4. Хэндлеры
    # -------------------------------------------------------------------------
    os.makedirs("logs", exist_ok=True)

    # Консоль
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(numeric_level)

    # Все логи в файл с ротацией по дням
    app_file_handler = logging.handlers.TimedRotatingFileHandler(
        filename="logs/app.log",
        when="midnight",
        backupCount=30,
        encoding="utf-8",
    )
    app_file_handler.setFormatter(file_formatter)
    app_file_handler.setLevel(logging.DEBUG)

    # Только ошибки в отдельный файл
    error_file_handler = logging.handlers.TimedRotatingFileHandler(
        filename="logs/errors.log",
        when="midnight",
        backupCount=90,
        encoding="utf-8",
    )
    error_file_handler.setFormatter(file_formatter)
    error_file_handler.setLevel(logging.ERROR)

    # -------------------------------------------------------------------------
    # 5. Root logger
    # -------------------------------------------------------------------------
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)
    root_logger.addHandler(app_file_handler)
    root_logger.addHandler(error_file_handler)
    root_logger.setLevel(logging.DEBUG)

    # -------------------------------------------------------------------------
    # 6. Заглушаем шумные библиотеки
    # -------------------------------------------------------------------------
    logging.getLogger("aiogram").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("aiohttp.access").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
