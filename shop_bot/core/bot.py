"""
نقطه ورود اصلی ربات (نسخه کامل)
Main bot entry point with APScheduler and webhook server
"""
from __future__ import annotations

import asyncio
import logging

from telegram.ext import Application

from config.settings import settings
from config.logging_config import setup_logging
from core.database import init_engine, init_db
from core.dispatcher import setup_dispatcher

logger = logging.getLogger(__name__)


async def post_init(application: Application) -> None:
    """اجرا بعد از راه‌اندازی Application"""
    await init_db()
    logger.info("✅ Database tables verified")

    # مقادیر پیش‌فرض تنظیمات
    from core.database import get_db
    from services.ticket_service import SettingService
    async with get_db() as session:
        setting_service = SettingService(session)
        await setting_service.initialize_defaults()

    # APScheduler
    from core.scheduler import setup_jobs
    setup_jobs(application.bot)
    logger.info("✅ Scheduler started")

    # Webhook payment server (فقط در تولید)
    if settings.BASE_URL and settings.BASE_URL != "https://your-domain.com":
        from core.webhook_server import start_webhook_server, set_bot
        set_bot(application.bot)
        asyncio.create_task(start_webhook_server(host="0.0.0.0", port=8080))
        logger.info("✅ Payment webhook server started on :8080")


async def post_shutdown(application: Application) -> None:
    """پاکسازی قبل از خاموش شدن"""
    try:
        from core.scheduler import get_scheduler
        scheduler = get_scheduler()
        if scheduler.running:
            scheduler.shutdown(wait=False)
    except Exception:
        pass


def create_app() -> Application:
    """ساخت Application ربات"""
    init_engine(settings.DATABASE_URL)

    app = (
        Application.builder()
        .token(settings.TELEGRAM_BOT_TOKEN or "PLACEHOLDER")
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    setup_dispatcher(app)
    return app


def main() -> None:
    """اجرای اصلی"""
    setup_logging(log_level=settings.LOG_LEVEL, debug=settings.DEBUG)
    logger.info(f"🚀 Starting {settings.BOT_NAME} bot...")

    if not settings.TELEGRAM_BOT_TOKEN:
        logger.critical(
            "❌ TELEGRAM_BOT_TOKEN is not set!\n"
            "   1. Copy .env.example to .env\n"
            "   2. Set TELEGRAM_BOT_TOKEN=your_token\n"
            "   3. Run again"
        )
        return

    app = create_app()

    if settings.WEBHOOK_URL:
        logger.info(f"📡 Webhook mode on port {settings.WEBHOOK_PORT}")
        app.run_webhook(
            listen="0.0.0.0",
            port=settings.WEBHOOK_PORT,
            secret_token=settings.WEBHOOK_SECRET or "",
            webhook_url=f"{settings.WEBHOOK_URL}/webhook",
        )
    else:
        logger.info("🔄 Polling mode (development)...")
        app.run_polling(
            allowed_updates=["message", "callback_query", "inline_query"],
            drop_pending_updates=True,
        )
