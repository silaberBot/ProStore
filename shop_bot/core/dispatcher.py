"""
Dispatcher — ثبت تمام هندلرها (نسخه کامل)
Register all handlers and configure bot application
"""
from __future__ import annotations

import logging

from telegram.ext import Application

# User handlers
from handlers.user.start import register_start_handlers
from handlers.user.shop import register_shop_handlers
from handlers.user.profile import register_user_handlers
from handlers.user.phone import register_phone_handlers
from handlers.user.tutorials import register_tutorial_handlers

# Admin handlers
from handlers.admin.dashboard import register_admin_handlers
from handlers.admin.products import register_product_admin_handlers
from handlers.admin.inventory import register_inventory_admin_handlers
from handlers.admin.discounts import register_discount_admin_handlers
from handlers.admin.tutorials import register_tutorial_admin_handlers
from handlers.admin.settings import register_settings_admin_handlers

logger = logging.getLogger(__name__)


def setup_dispatcher(app: Application) -> Application:
    """ثبت تمام هندلرها روی Application به ترتیب اولویت"""

    # ─── گروه ۰: هندلرهای کاربر (اولویت بالا) ───
    register_start_handlers(app)
    register_phone_handlers(app)

    # ─── گروه ۱: فروشگاه ───
    register_shop_handlers(app)

    # ─── گروه ۲: پروفایل، کیف پول، رفرال، تیکت ───
    register_user_handlers(app)

    # ─── گروه ۳: آموزش‌ها ───
    register_tutorial_handlers(app)

    # ─── گروه ۴: ادمین (پایه) ───
    register_admin_handlers(app)

    # ─── گروه ۵: ادمین — محصولات (با Conversation) ───
    register_product_admin_handlers(app)

    # ─── گروه ۶: ادمین — انبار ───
    register_inventory_admin_handlers(app)

    # ─── گروه ۷: ادمین — تخفیف‌ها ───
    register_discount_admin_handlers(app)

    # ─── گروه ۸: ادمین — آموزش‌ها ───
    register_tutorial_admin_handlers(app)

    # ─── گروه ۹: ادمین — تنظیمات ───
    register_settings_admin_handlers(app)

    logger.info("✅ All handlers registered successfully")
    return app
