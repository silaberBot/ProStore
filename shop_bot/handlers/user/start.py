"""
هندلر /start — ورود کاربر و تشخیص رفرال (اصلاح‌شده)
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
    tg_user = update.effective_user
    args = context.args

    async with get_db() as session:
        user_repo = UserRepository(session)
        setting_service = SettingService(session)

        user = await user_repo.get_by_telegram_id(tg_user.id)
        is_new = user is None
        referrer = None

        if is_new:
            referral_code = None
            if args and args[0].startswith("ref_"):
                referral_code_str = args[0][4:]
                referrer = await user_repo.get_by_referral_code(referral_code_str)
                if referrer and referrer.telegram_id != tg_user.id:
                    referral_code = referral_code_str
                else:
                    referrer = None

            user = await user_repo.create_user(
                telegram_id=tg_user.id,
                first_name=tg_user.first_name,
                username=tg_user.username,
                last_name=tg_user.last_name,
                referred_by=referrer.telegram_id if referrer else None,
            )
            logger.info(f"New user registered: {tg_user.id} ({tg_user.username})")

            if referral_code and referrer:
                ref_service = ReferralService(session)
                success, msg = await ref_service.register_referral(tg_user.id, referral_code)
                if success:
                    notif = NotificationService(context.bot)
                    await notif.referral_pending(referrer.telegram_id, user.full_name)
        else:
            await user_repo.update_activity(tg_user.id)

        context.user_data["registered"] = True
        context.user_data["user_id"] = tg_user.id

        is_admin = tg_user.id in settings.admin_ids_list
        context.user_data["is_admin"] = is_admin

        welcome_msg = await setting_service.get("welcome_message")
        if not welcome_msg:
            welcome_msg = f"🌟 <b>به ربات {settings.BOT_NAME} خوش آمدید!</b>"

        if is_new:
            welcome_msg += f"\n\n👋 {user.first_name} عزیز، به خانواده ما خوش آمدید!"

        if is_admin:
            welcome_msg += "\n\n🔧 <i>شما دسترسی ادمین دارید. برای تغییر به منوی کاربری /user و برای پنل ادمین /admin را بزنید.</i>"

        keyboard = admin_main_menu() if is_admin else main_menu_keyboard()
        await update.message.reply_html(welcome_msg, reply_markup=keyboard)


async def switch_to_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """تغییر به منوی کاربری"""
    await update.message.reply_html(
        "📱 <b>منوی کاربری فعال شد.</b>\nبرای بازگشت به پنل ادمین /admin را بزنید.",
        reply_markup=main_menu_keyboard(),
    )


async def switch_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """تغییر به پنل ادمین"""
    if update.effective_user.id not in settings.admin_ids_list:
        await update.message.reply_text("❌ شما دسترسی ادمین ندارید.")
        return
    await update.message.reply_html(
        "🔧 <b>پنل ادمین فعال شد.</b>\nبرای منوی کاربری /user را بزنید.",
        reply_markup=admin_main_menu(),
    )


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
    app.add_handler(CommandHandler("user", switch_to_user))
    app.add_handler(CommandHandler("admin", switch_to_admin))
