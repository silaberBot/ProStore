"""
APScheduler — جاب‌های پس‌زمینه خودکار
Background scheduled jobs: referral checker, subscription expiry reminder, inventory alerts
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, date

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram import Bot

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(timezone="Asia/Tehran")
    return _scheduler


def setup_jobs(bot: Bot) -> AsyncIOScheduler:
    """ثبت تمام جاب‌های زمان‌بندی‌شده"""
    scheduler = get_scheduler()

    # ۱. بررسی رفرال‌های pending — هر 6 ساعت
    scheduler.add_job(
        check_pending_referrals,
        CronTrigger(hour="0,6,12,18"),
        id="referral_checker",
        replace_existing=True,
        kwargs={"bot": bot},
    )

    # ۲. یادآوری انقضای اشتراک — هر روز ساعت 10 صبح
    scheduler.add_job(
        subscription_expiry_reminder,
        CronTrigger(hour=10, minute=0),
        id="expiry_reminder",
        replace_existing=True,
        kwargs={"bot": bot},
    )

    # ۳. هشدار کمبود انبار — هر روز ساعت 9 صبح
    scheduler.add_job(
        low_inventory_alert,
        CronTrigger(hour=9, minute=0),
        id="low_inventory",
        replace_existing=True,
        kwargs={"bot": bot},
    )

    # ۴. لغو سفارشات منقضی‌شده — هر ساعت
    scheduler.add_job(
        cancel_expired_orders,
        CronTrigger(minute=0),
        id="cancel_expired",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("✅ APScheduler started with all jobs")
    return scheduler


# ─────────────────────────────────────────────
# Jobs
# ─────────────────────────────────────────────
async def check_pending_referrals(bot: Bot) -> None:
    """بررسی و پاداش‌دهی به رفرال‌های آماده"""
    logger.info("Running: check_pending_referrals")
    try:
        from core.database import get_db
        from services.referral_service import ReferralService
        from services.notification_service import NotificationService
        from repositories.user_repository import UserRepository

        async with get_db() as session:
            ref_service = ReferralService(session)
            rewarded = await ref_service.check_and_reward_referrals()

        if rewarded > 0:
            logger.info(f"Referrals rewarded: {rewarded}")
    except Exception as e:
        logger.error(f"Referral check job error: {e}")


async def subscription_expiry_reminder(bot: Bot) -> None:
    """یادآوری انقضای اشتراک به کاربران"""
    logger.info("Running: subscription_expiry_reminder")
    try:
        from core.database import get_db
        from config.settings import settings
        from sqlalchemy import select
        from models.order import Order, OrderItem
        from models.inventory import Inventory
        from models.product import Product
        from services.notification_service import NotificationService
        from sqlalchemy.ext.asyncio import AsyncSession

        days_ahead = settings.REMINDER_DAYS_BEFORE
        target_date = date.today() + timedelta(days=days_ahead)

        async with get_db() as session:
            result = await session.execute(
                select(Inventory, Product)
                .join(Product, Inventory.product_id == Product.id)
                .where(Inventory.expire_date == target_date)
                .where(Inventory.status == "sold")
            )
            expiring = result.all()

        if expiring:
            notif = NotificationService(bot)
            for inv, product in expiring:
                # پیدا کردن کاربر از order_item
                async with get_db() as session:
                    from models.order import OrderItem, Order
                    result = await session.execute(
                        select(OrderItem).where(OrderItem.inventory_id == inv.id)
                    )
                    item = result.scalar_one_or_none()
                    if item:
                        order = await session.get(Order, item.order_id)
                        if order:
                            await notif.subscription_expiring(
                                order.user_id,
                                product.name,
                                days_ahead,
                            )

        logger.info(f"Expiry reminders sent: {len(expiring)}")
    except Exception as e:
        logger.error(f"Expiry reminder job error: {e}")


async def low_inventory_alert(bot: Bot) -> None:
    """هشدار کمبود موجودی انبار به ادمین‌ها"""
    logger.info("Running: low_inventory_alert")
    try:
        from core.database import get_db
        from config.settings import settings
        from services.notification_service import NotificationService
        from repositories.setting_repository import SettingRepository as SR
        from repositories.product_repository import ProductRepository
        from repositories.ticket_repository import SettingRepository

        async with get_db() as session:
            product_repo = ProductRepository(session)
            setting_repo = SettingRepository(session)
            threshold_str = await setting_repo.get("low_inventory_alert", "5")
            threshold = int(threshold_str)

            products = await product_repo.get_all(limit=200)
            notif = NotificationService(bot)

            for p in products:
                if p.has_inventory and 0 < p.available_count <= threshold:
                    for admin_id in settings.admin_ids_list:
                        await notif.admin_low_inventory(admin_id, p.name, p.available_count)
    except Exception as e:
        logger.error(f"Low inventory alert job error: {e}")


async def cancel_expired_orders() -> None:
    """لغو خودکار سفارشات پرداخت‌نشده پس از مدت مشخص"""
    logger.info("Running: cancel_expired_orders")
    try:
        from core.database import get_db
        from config.settings import settings
        from repositories.order_repository import OrderRepository
        from repositories.ticket_repository import SettingRepository
        from sqlalchemy import select, and_
        from models.order import Order

        async with get_db() as session:
            setting_repo = SettingRepository(session)
            expiry_hours = int(await setting_repo.get("order_expiry_hours", "24"))
            expiry_time = datetime.utcnow() - timedelta(hours=expiry_hours)

            result = await session.execute(
                select(Order).where(
                    and_(
                        Order.status == "pending",
                        Order.payment_status == "pending",
                        Order.created_at <= expiry_time,
                    )
                )
            )
            expired_orders = result.scalars().all()

            for order in expired_orders:
                order.status = "cancelled"
                session.add(order)

            if expired_orders:
                logger.info(f"Cancelled {len(expired_orders)} expired orders")
    except Exception as e:
        logger.error(f"Cancel expired orders job error: {e}")
