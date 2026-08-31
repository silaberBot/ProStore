"""
هندلر تنظیمات ربات در پنل ادمین
Admin settings handler — edit all 28 bot messages and config values
"""
from __future__ import annotations

import logging

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode
from telegram.ext import (
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from core.database import get_db
from repositories.ticket_repository import SettingRepository
from utils.decorators import admin_only

logger = logging.getLogger(__name__)

WAITING_SETTING_VALUE = 1

# تمام کلیدهای تنظیمات قابل ویرایش
EDITABLE_SETTINGS = {
    "پیام‌های ربات": {
        "welcome_message":         "پیام خوش‌آمدگویی",
        "shop_description":        "توضیح فروشگاه",
        "payment_success_message": "پیام پرداخت موفق",
        "payment_failed_message":  "پیام پرداخت ناموفق",
        "order_pending_message":   "پیام سفارش در انتظار",
        "delivery_message":        "پیام ارسال اکانت",
        "wallet_charge_message":   "پیام شارژ کیف پول",
        "referral_success_message":"پیام موفقیت رفرال",
        "ticket_created_message":  "پیام ثبت تیکت",
        "ticket_reply_message":    "پیام پاسخ تیکت",
    },
    "اطلاعات تماس": {
        "support_username":        "یوزرنیم پشتیبانی",
        "channel_username":        "یوزرنیم کانال",
        "bot_about":               "درباره ربات",
    },
    "تنظیمات عملیاتی": {
        "min_wallet_charge":       "حداقل شارژ کیف پول (تومان)",
        "referral_reward":         "پاداش رفرال (تومان)",
        "low_inventory_alert":     "هشدار موجودی انبار (عدد)",
        "order_expiry_hours":      "انقضای سفارش (ساعت)",
        "max_discount_percent":    "حداکثر درصد تخفیف",
    },
}


@admin_only
async def admin_settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """منوی اصلی تنظیمات"""
    buttons = []
    for group_name in EDITABLE_SETTINGS:
        buttons.append([InlineKeyboardButton(
            f"⚙️ {group_name}",
            callback_data=f"settings:group:{group_name}",
        )])

    await update.effective_message.reply_html(
        "⚙️ <b>تنظیمات ربات</b>\n\nگروه مورد نظر را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


@admin_only
async def settings_group(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """نمایش تنظیمات یک گروه"""
    query = update.callback_query
    await query.answer()
    group_name = query.data.split(":", 2)[2]
    group = EDITABLE_SETTINGS.get(group_name, {})

    async with get_db() as session:
        setting_repo = SettingRepository(session)
        values = await setting_repo.get_all_as_dict()

    lines = []
    buttons = []
    for key, label in group.items():
        val = values.get(key, "—")
        short_val = val[:30] + "..." if len(val) > 30 else val
        lines.append(f"• <b>{label}:</b> <code>{short_val}</code>")
        buttons.append([InlineKeyboardButton(
            f"✏️ {label}",
            callback_data=f"settings:edit:{key}",
        )])

    buttons.append([InlineKeyboardButton("🔙 بازگشت", callback_data="settings:main")])
    text = f"⚙️ <b>{group_name}</b>\n\n" + "\n".join(lines)
    await query.edit_message_text(
        text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons)
    )


@admin_only
async def settings_edit_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """شروع ویرایش یک تنظیم"""
    query = update.callback_query
    await query.answer()
    key = query.data.split(":", 2)[2]
    context.user_data["editing_setting_key"] = key

    # پیدا کردن label
    label = key
    for group in EDITABLE_SETTINGS.values():
        if key in group:
            label = group[key]
            break

    async with get_db() as session:
        setting_repo = SettingRepository(session)
        current = await setting_repo.get(key, "")

    await query.edit_message_text(
        f"✏️ <b>ویرایش: {label}</b>\n\n"
        f"مقدار فعلی:\n<code>{current}</code>\n\n"
        f"مقدار جدید را وارد کنید (یا /cancel برای لغو):",
        parse_mode=ParseMode.HTML,
    )
    return WAITING_SETTING_VALUE


async def settings_value_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """دریافت و ذخیره مقدار جدید"""
    key = context.user_data.pop("editing_setting_key", None)
    if not key:
        return ConversationHandler.END

    new_value = update.message.text.strip()
    async with get_db() as session:
        setting_repo = SettingRepository(session)
        await setting_repo.set(key, new_value)

    await update.message.reply_html(
        f"✅ تنظیم <b>{key}</b> با موفقیت بروزرسانی شد.\n"
        f"مقدار جدید: <code>{new_value}</code>"
    )
    return ConversationHandler.END


async def cancel_settings_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop("editing_setting_key", None)
    await update.message.reply_text("❌ ویرایش لغو شد.")
    return ConversationHandler.END


def build_settings_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(settings_edit_start, pattern="^settings:edit:")],
        states={
            WAITING_SETTING_VALUE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, settings_value_received),
            ]
        },
        fallbacks=[MessageHandler(filters.Regex("^/cancel$"), cancel_settings_edit)],
    )


def register_settings_admin_handlers(app) -> None:
    app.add_handler(build_settings_conversation())
    app.add_handler(CallbackQueryHandler(admin_settings_menu, pattern="^settings:main$"))
    app.add_handler(CallbackQueryHandler(settings_group, pattern="^settings:group:"))
