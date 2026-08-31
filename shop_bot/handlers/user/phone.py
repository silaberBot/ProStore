"""
هندلر تأیید شماره موبایل
Phone number verification handler (Iranian numbers only)
"""
from __future__ import annotations

import logging

from telegram import (
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.ext import (
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from core.database import get_db
from repositories.user_repository import UserRepository
from utils.helpers import validate_iranian_phone, normalize_phone

logger = logging.getLogger(__name__)

WAITING_PHONE = 1


async def request_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """درخواست شماره موبایل از کاربر"""
    query = update.callback_query
    if query:
        await query.answer()

    share_button = KeyboardButton("📱 اشتراک‌گذاری شماره", request_contact=True)
    keyboard = ReplyKeyboardMarkup(
        [[share_button], ["❌ انصراف"]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    msg_text = (
        "📱 <b>تأیید شماره موبایل</b>\n\n"
        "برای فعال‌سازی این قابلیت، شماره موبایل ایرانی خود را به اشتراک بگذارید.\n\n"
        "⚠️ <i>فقط شماره‌های ایرانی (09xx) قابل تأیید هستند.</i>"
    )
    if query:
        await context.bot.send_message(
            chat_id=query.from_user.id,
            text=msg_text,
            parse_mode="HTML",
            reply_markup=keyboard,
        )
    else:
        await update.message.reply_html(msg_text, reply_markup=keyboard)
    return WAITING_PHONE


async def receive_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """دریافت شماره موبایل از contact یا متن"""
    user_id = update.effective_user.id
    phone = None

    if update.message.contact:
        # اشتراک‌گذاری از طریق تلگرام
        contact = update.message.contact
        if contact.user_id != user_id:
            await update.message.reply_text(
                "❌ لطفاً شماره موبایل <b>خودتان</b> را به اشتراک بگذارید.",
                parse_mode="HTML",
                reply_markup=ReplyKeyboardRemove(),
            )
            return ConversationHandler.END
        phone = contact.phone_number
    elif update.message.text:
        phone = update.message.text.strip()
    else:
        return WAITING_PHONE

    if not validate_iranian_phone(phone):
        await update.message.reply_html(
            "❌ شماره موبایل نامعتبر است.\n"
            "لطفاً یک شماره ایرانی معتبر (مثل 09xxxxxxxxx) وارد کنید.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return ConversationHandler.END

    normalized = normalize_phone(phone)

    async with get_db() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_telegram_id(user_id)
        if user:
            await user_repo.update(
                user,
                phone_number=normalized,
                phone_verified=True,
                phone_is_iranian=True,
            )

    await update.message.reply_html(
        f"✅ <b>شماره موبایل تأیید شد!</b>\n\n"
        f"📱 شماره: <code>{normalized}</code>\n\n"
        f"اکنون می‌توانید از تمام قابلیت‌های ربات استفاده کنید.",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


async def cancel_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("❌ لغو شد.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


async def check_join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """بررسی مجدد عضویت کانال پس از کلیک «عضو شدم»"""
    query = update.callback_query
    from core.force_join import check_channel_membership
    is_member = await check_channel_membership(context.bot, query.from_user.id)
    if is_member:
        await query.answer("✅ عضویت تأیید شد!", show_alert=True)
        from utils.keyboards import main_menu_keyboard
        from config.settings import settings
        kb = main_menu_keyboard()
        await query.message.reply_html("✅ به ربات خوش آمدید! از منوی زیر استفاده کنید:", reply_markup=kb)
    else:
        await query.answer("❌ هنوز عضو نشده‌اید!", show_alert=True)


def build_phone_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(request_phone, pattern="^profile:verify_phone$"),
        ],
        states={
            WAITING_PHONE: [
                MessageHandler(filters.CONTACT, receive_phone),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_phone),
            ]
        },
        fallbacks=[MessageHandler(filters.Regex("^❌"), cancel_phone)],
        conversation_timeout=120,
    )


def register_phone_handlers(app) -> None:
    app.add_handler(build_phone_conversation())
    app.add_handler(CallbackQueryHandler(check_join_callback, pattern="^check_join$"))
