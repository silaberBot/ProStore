"""
دکوراتورهای کمکی
Helper decorators for handlers
"""
from __future__ import annotations

import logging
from functools import wraps
from typing import Callable

from telegram import Update
from telegram.ext import ContextTypes

from config.settings import settings

logger = logging.getLogger(__name__)


def admin_only(func: Callable) -> Callable:
    """فقط ادمین‌ها مجاز به استفاده هستند"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id not in settings.admin_ids_list:
            await update.effective_message.reply_text("⛔ شما دسترسی به این بخش را ندارید.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper


def user_registered(func: Callable) -> Callable:
    """بررسی ثبت‌نام کاربر در دیتابیس"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if not context.user_data.get("registered"):
            # کاربر باید از /start شروع کند
            await update.effective_message.reply_text(
                "⚠️ لطفاً ابتدا /start را بزنید."
            )
            return
        return await func(update, context, *args, **kwargs)
    return wrapper


def rate_limit(seconds: int = 3):
    """محدودیت نرخ برای جلوگیری از اسپم"""
    import time

    def decorator(func: Callable) -> Callable:
        user_last_call: dict = {}

        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            user_id = update.effective_user.id
            now = time.time()
            last = user_last_call.get(user_id, 0)
            if now - last < seconds:
                remaining = int(seconds - (now - last))
                await update.effective_message.reply_text(
                    f"⏳ لطفاً {remaining} ثانیه صبر کنید."
                )
                return
            user_last_call[user_id] = now
            return await func(update, context, *args, **kwargs)

        return wrapper
    return decorator


def log_action(action_name: str = ""):
    """لاگ‌گیری عملیات کاربر"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            user = update.effective_user
            name = action_name or func.__name__
            logger.info(f"User {user.id} ({user.username}) → {name}")
            return await func(update, context, *args, **kwargs)
        return wrapper
    return decorator
