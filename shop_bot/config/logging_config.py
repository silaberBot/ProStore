"""تنظیمات لاگ‌گیری پروژه"""
import logging
import logging.handlers
import os
from pathlib import Path


def setup_logging(log_level: str = "INFO", debug: bool = False) -> None:
    """راه‌اندازی سیستم لاگ‌گیری"""
    # ایجاد پوشه logs اگر وجود نداشت
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    level = logging.DEBUG if debug else getattr(logging, log_level.upper(), logging.INFO)

    # فرمت لاگ
    fmt = "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s"
    date_fmt = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(fmt, date_fmt)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler (rotating - max 10MB, keep 5 files)
    file_handler = logging.handlers.RotatingFileHandler(
        logs_dir / "bot.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # Error-only file handler
    error_handler = logging.handlers.RotatingFileHandler(
        logs_dir / "errors.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    root_logger.addHandler(error_handler)

    # کاهش نویز کتابخانه‌ها
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.WARNING)
