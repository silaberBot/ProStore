"""
Dispatcher — ثبت تمام هندلرها (نسخه اصلاح‌شده)
Register all handlers — conversations FIRST, generic text handler LAST
"""
from __future__ import annotations

import logging

from telegram.ext import Application, MessageHandler, filters

# User handlers
from handlers.user.start import register_start_handlers
from handlers.user.shop import register_shop_handlers
from handlers.user.profile import register_user_handlers
from handlers.user.phone import register_phone_handlers
from handlers.user.tutorials import register_tutorial_handlers

# Admin handlers
from handlers.admin.dashboard import register_admin_handlers, admin_text_input_handler
from handlers.admin.products import register_product_admin_handlers
from handlers.admin.inventory import register_inventory_admin_handlers
from handlers.admin.discounts import register_discount_admin_handlers
from handlers.admin.tutorials import register_tutorial_admin_handlers
from handlers.admin.settings import register_settings_admin_handlers

logger = logging.getLogger(__name__)


def setup_dispatcher(app: Application) -> Application:
    """ثبت تمام هندلرها روی Application به ترتیب اولویت"""

    # ─── ConversationHandlerها اول ثبت میشن ───
    # (اینا اولویت بالاتر دارن و نباید توسط هندلر جنریک مسدود بشن)

    # هندلرهای کاربر
    register_start_handlers(app)
    register_phone_handlers(app)
    register_shop_handlers(app)
    register_user_handlers(app)
    register_tutorial_handlers(app)

    # ادمین — ConversationHandlerها (محصول، انبار، تخفیف، آموزش، تنظیمات)
    register_product_admin_handlers(app)
    register_inventory_admin_handlers(app)
    register_discount_admin_handlers(app)
    register_tutorial_admin_handlers(app)
    register_settings_admin_handlers(app)

    # ادمین — هندلرهای پایه (داشبورد، سفارشات، کاربران، ...)
    register_admin_handlers(app)

    # ─── هندلر جنریک متنی ادمین — حتماً آخر از همه ───
    # این فقط وقتی فعال میشه که ادمین منتظر ورودی متنی باشه
    # (جستجوی کاربر یا پیام همگانی)
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE,
        admin_text_input_handler,
    ))

    logger.info("All handlers registered successfully")
    return app
