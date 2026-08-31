"""
Middleware عضویت اجباری کانال + Force Join
Force channel membership check before allowing bot access
"""
from __future__ import annotations

import logging
from typing import Any, Callable

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from config.settings import settings

logger = logging.getLogger(__name__)

# دستوراتی که بدون نیاز به عضویت کار می‌کنند
EXEMPT_COMMANDS = {"/start", "/help"}


async def check_channel_membership(bot, user_id: int) -> bool:
    """بررسی عضویت کاربر در کانال"""
    if not settings.CHANNEL_ID and not settings.CHANNEL_USERNAME:
        return True  # کانال تنظیم نشده — همه مجازند

    channel = settings.CHANNEL_ID or f"@{settings.CHANNEL_USERNAME}"
    try:
        member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
        return member.status in ("member", "administrator", "creator")
    except TelegramError as e:
        logger.warning(f"Channel check failed for user {user_id}: {e}")
        return True  # در صورت خطا، اجازه عبور بده


class ForceJoinMiddleware:
    """Middleware بررسی عضویت اجباری کانال"""

    async def __call__(
        self,
        handler: Callable,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> Any:
        # فقط برای پیام‌ها و callback query‌ها اعمال می‌شود
        if not settings.CHANNEL_ID and not settings.CHANNEL_USERNAME:
            return await handler(update, context)

        tg_user = update.effective_user
        if not tg_user:
            return await handler(update, context)

        # اگر دستور /start بود، چک نکن
        if update.message and update.message.text:
            text = update.message.text.strip()
            for cmd in EXEMPT_COMMANDS:
                if text.startswith(cmd):
                    return await handler(update, context)

        is_member = await check_channel_membership(context.bot, tg_user.id)
        if not is_member:
            channel_username = settings.CHANNEL_USERNAME or ""
            channel_link = f"https://t.me/{channel_username}" if channel_username else ""

            buttons = []
            if channel_link:
                buttons.append([InlineKeyboardButton("📢 عضویت در کانال", url=channel_link)])
            buttons.append([InlineKeyboardButton("✅ عضو شدم", callback_data="check_join")])

            msg = (
                "⚠️ <b>برای استفاده از ربات، ابتدا باید در کانال ما عضو شوید:</b>\n\n"
                f"📢 @{channel_username}\n\n"
                "پس از عضویت، دکمه «عضو شدم» را بزنید."
            )
            if update.callback_query:
                await update.callback_query.answer("⚠️ ابتدا در کانال عضو شوید!", show_alert=True)
            elif update.message:
                await update.message.reply_html(
                    msg, reply_markup=InlineKeyboardMarkup(buttons)
                )
            return  # جلوگیری از اجرای هندلر اصلی

        return await handler(update, context)
