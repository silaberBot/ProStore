"""
هندلر /start — ورود کاربر و تشخیص رفرال
Start handler with referral detection
"""
from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from config.settings import settings
from core.database import get_db
from repositories.user_repository import UserRepository
from services.referral_service import ReferralService
from services.notification_service import NotificationService
from services.ticket_service import SettingService
from utils.keyboards import main_menu_keyboard, admin_main_menu

logger = logging.getLogger(__name__)


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """هندلر دستور /start"""
    tg_user = update.effective_user
    args = context.args  # آرگومان‌های بعد از /start (مثلاً ref_CODE123)

    async with get_db() as session:
        user_repo = UserRepository(session)
        setting_service = SettingService(session)

        # دریافت یا ایجاد کاربر
        user = await user_repo.get_by_telegram_id(tg_user.id)
        is_new = user is None

        if is_new:
            # پردازش کد رفرال
            referral_code = None
            if args and args[0].startswith("ref_"):
                referral_code_str = args[0][4:]  # حذف پیشوند ref_
                referrer = await user_repo.get_by_referral_code(referral_code_str)
                if referrer and referrer.telegram_id != tg_user.id:
                    referral_code = referral_code_str

            user = await user_repo.create_user(
                telegram_id=tg_user.id,
                first_name=tg_user.first_name,
                username=tg_user.username,
                last_name=tg_user.last_name,
                referred_by=referrer.telegram_id if referral_code and "referrer" in dir() else None,
            )
            logger.info(f"New user registered: {tg_user.id} ({tg_user.username})")

            # ثبت رفرال
            if referral_code:
                ref_service = ReferralService(session)
                success, msg = await ref_service.register_referral(tg_user.id, referral_code)
                if success:
                    # اطلاع به معرف
                    referrer_user = await user_repo.get_by_telegram_id(user.referred_by)
                    if referrer_user:
                        notif = NotificationService(context.bot)
                        await notif.referral_pending(referrer_user.telegram_id, user.full_name)
        else:
            await user_repo.update_activity(tg_user.id)

        # ذخیره در user_data
        context.user_data["registered"] = True
        context.user_data["user_id"] = tg_user.id
        context.user_data["is_admin"] = tg_user.id in settings.admin_ids_list

        # پیام خوش‌آمدگویی
        welcome_msg = await setting_service.get("welcome_message")
        if not welcome_msg:
            welcome_msg = f"🌟 <b>به ربات {settings.BOT_NAME} خوش آمدید!</b>"

        if is_new:
            welcome_msg += f"\n\n👋 {user.first_name} عزیز، به خانواده ما خوش آمدید!"

        is_admin = tg_user.id in settings.admin_ids_list
        keyboard = admin_main_menu() if is_admin else main_menu_keyboard()

        await update.message.reply_html(welcome_msg, reply_markup=keyboard)


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """دستور /help"""
    text = (
        "📖 <b>راهنمای ربات</b>\n\n"
        "🛍 <b>فروشگاه</b> — مشاهده و خرید اشتراک‌ها\n"
        "👤 <b>پروفایل من</b> — اطلاعات و سفارشات\n"
        "💰 <b>کیف پول</b> — شارژ و تاریخچه\n"
        "🔗 <b>دعوت از دوستان</b> — کسب درآمد\n"
        "🎫 <b>پشتیبانی</b> — ثبت تیکت\n"
        "📚 <b>آموزش‌ها</b> — راهنمای نرم‌افزارها\n\n"
        "برای شروع، /start را بزنید."
    )
    await update.message.reply_html(text)


def register_start_handlers(app):
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("help", help_handler))
