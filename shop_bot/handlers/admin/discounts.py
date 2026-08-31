"""
هندلر مدیریت تخفیف‌ها در پنل ادمین
Admin discount management — create, view, toggle, delete discounts
"""
from __future__ import annotations

import logging
from datetime import datetime

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
from repositories.ticket_repository import DiscountRepository
from utils.decorators import admin_only

logger = logging.getLogger(__name__)

(
    DISC_CODE, DISC_TYPE, DISC_VALUE,
    DISC_MIN_ORDER, DISC_MAX_USES, DISC_EXPIRY,
    DISC_CONFIRM,
) = range(7)


@admin_only
async def admin_discounts_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    async with get_db() as session:
        disc_repo = DiscountRepository(session)
        discounts = await disc_repo.get_active_discounts()

    if not discounts:
        buttons = [[InlineKeyboardButton("➕ کد جدید", callback_data="disc:new")]]
        await update.effective_message.reply_html(
            "🎟 <b>کدهای تخفیف</b>\n\nهیچ کد فعالی وجود ندارد.",
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        return

    lines = []
    buttons = []
    for d in discounts:
        val = f"{d.value}%" if d.type == "percentage" else f"{d.value:,} ت"
        used = f"{d.used_count}/{d.max_uses}" if d.max_uses else f"{d.used_count}/∞"
        lines.append(f"🏷 <code>{d.code}</code> — {val} | استفاده: {used}")
        buttons.append([
            InlineKeyboardButton(f"🏷 {d.code}", callback_data=f"disc:detail:{d.id}")
        ])

    buttons.append([InlineKeyboardButton("➕ کد جدید", callback_data="disc:new")])
    await update.effective_message.reply_html(
        "🎟 <b>کدهای تخفیف فعال:</b>\n\n" + "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(buttons),
    )


@admin_only
async def discount_detail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    disc_id = int(query.data.split(":")[2])

    async with get_db() as session:
        disc_repo = DiscountRepository(session)
        d = await disc_repo.get_by_id(disc_id)

    if not d:
        await query.edit_message_text("❌ کد تخفیف یافت نشد.")
        return

    val = f"{d.value}%" if d.type == "percentage" else f"{d.value:,} تومان"
    expiry = d.expire_date.strftime("%Y/%m/%d") if d.expire_date else "بدون محدودیت"
    used = f"{d.used_count}" + (f"/{d.max_uses}" if d.max_uses else "/∞")
    status = "✅ فعال" if d.is_active else "❌ غیرفعال"

    text = (
        f"🏷 <b>کد تخفیف: <code>{d.code}</code></b>\n\n"
        f"💰 مقدار: {val}\n"
        f"🔹 نوع: {'درصدی' if d.type == 'percentage' else 'مبلغ ثابت'}\n"
        f"🛒 حداقل سفارش: {d.min_order_amount:,} تومان\n"
        f"📊 استفاده: {used}\n"
        f"📅 انقضا: {expiry}\n"
        f"🔸 وضعیت: {status}"
    )
    buttons = [
        [
            InlineKeyboardButton(
                "❌ غیرفعال‌کردن" if d.is_active else "✅ فعال‌کردن",
                callback_data=f"disc:toggle:{d.id}",
            ),
            InlineKeyboardButton("🗑 حذف", callback_data=f"disc:delete:{d.id}"),
        ],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="disc:list")],
    ]
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))


@admin_only
async def toggle_discount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    disc_id = int(query.data.split(":")[2])

    async with get_db() as session:
        disc_repo = DiscountRepository(session)
        d = await disc_repo.get_by_id(disc_id)
        if d:
            await disc_repo.update(d, is_active=not d.is_active)
            status = "فعال" if not d.is_active else "غیرفعال"
            await query.answer(f"✅ کد {status} شد", show_alert=True)

    # بازنمایی
    query.data = f"disc:detail:{disc_id}"
    await discount_detail(update, context)


@admin_only
async def delete_discount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    disc_id = int(query.data.split(":")[2])

    async with get_db() as session:
        disc_repo = DiscountRepository(session)
        d = await disc_repo.get_by_id(disc_id)
        if d:
            await disc_repo.delete(d)

    await query.edit_message_text("✅ کد تخفیف حذف شد.")


# ─────────────────────────────────────────────
# ایجاد کد تخفیف — Conversation
# ─────────────────────────────────────────────
@admin_only
async def new_discount_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data["new_discount"] = {}
    await query.edit_message_text(
        "🏷 <b>کد تخفیف جدید</b>\n\n"
        "کد دلخواه را وارد کنید (حروف انگلیسی بزرگ و اعداد):\n"
        "مثال: <code>SUMMER25</code>",
        parse_mode=ParseMode.HTML,
    )
    return DISC_CODE


async def discount_code_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    code = update.message.text.strip().upper()
    if not code.isalnum() or len(code) < 3:
        await update.message.reply_text("❌ کد باید حداقل ۳ کاراکتر حرف یا عدد باشد.")
        return DISC_CODE

    async with get_db() as session:
        disc_repo = DiscountRepository(session)
        existing = await disc_repo.get_by_code(code)
        if existing:
            await update.message.reply_text("❌ این کد قبلاً ثبت شده. کد دیگری وارد کنید:")
            return DISC_CODE

    context.user_data["new_discount"]["code"] = code
    await update.message.reply_text(
        "💰 نوع تخفیف را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📊 درصدی (%)", callback_data="disc_type:percentage"),
                InlineKeyboardButton("💵 مبلغ ثابت (تومان)", callback_data="disc_type:fixed"),
            ]
        ]),
    )
    return DISC_TYPE


async def discount_type_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    disc_type = query.data.split(":")[1]
    context.user_data["new_discount"]["type"] = disc_type
    hint = "درصد (مثلاً 20 برای ۲۰٪)" if disc_type == "percentage" else "مبلغ تخفیف به تومان"
    await query.edit_message_text(f"💰 مقدار تخفیف را وارد کنید ({hint}):")
    return DISC_VALUE


async def discount_value_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        value = int(update.message.text.replace(",", "").strip())
        if value <= 0:
            raise ValueError
        disc = context.user_data["new_discount"]
        if disc["type"] == "percentage" and value > 100:
            await update.message.reply_text("❌ درصد نمی‌تواند بیشتر از ۱۰۰ باشد.")
            return DISC_VALUE
        disc["value"] = value
    except ValueError:
        await update.message.reply_text("❌ عدد معتبر وارد کنید:")
        return DISC_VALUE

    await update.message.reply_text(
        "🛒 حداقل مبلغ سفارش برای استفاده از کد (یا /skip برای بدون محدودیت):"
    )
    return DISC_MIN_ORDER


async def discount_min_order_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if text == "/skip":
        context.user_data["new_discount"]["min_order_amount"] = 0
    else:
        try:
            val = int(text.replace(",", ""))
            context.user_data["new_discount"]["min_order_amount"] = max(0, val)
        except ValueError:
            await update.message.reply_text("❌ عدد وارد کنید (یا /skip):")
            return DISC_MIN_ORDER

    await update.message.reply_text(
        "📊 حداکثر تعداد استفاده کل (یا /skip برای نامحدود):"
    )
    return DISC_MAX_USES


async def discount_max_uses_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if text == "/skip":
        context.user_data["new_discount"]["max_uses"] = None
    else:
        try:
            val = int(text)
            context.user_data["new_discount"]["max_uses"] = max(1, val)
        except ValueError:
            await update.message.reply_text("❌ عدد وارد کنید (یا /skip):")
            return DISC_MAX_USES

    await update.message.reply_text(
        "📅 تاریخ انقضا (فرمت: YYYY-MM-DD مثل 2025-12-31) یا /skip:"
    )
    return DISC_EXPIRY


async def discount_expiry_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if text == "/skip":
        context.user_data["new_discount"]["expire_date"] = None
    else:
        try:
            expire_dt = datetime.strptime(text, "%Y-%m-%d")
            context.user_data["new_discount"]["expire_date"] = expire_dt
        except ValueError:
            await update.message.reply_text("❌ فرمت نادرست. مثال: 2025-12-31 (یا /skip):")
            return DISC_EXPIRY

    d = context.user_data["new_discount"]
    val = f"{d['value']}%" if d["type"] == "percentage" else f"{d['value']:,} تومان"
    text = (
        f"✅ <b>تأیید کد تخفیف</b>\n\n"
        f"🏷 کد: <code>{d['code']}</code>\n"
        f"💰 تخفیف: {val}\n"
        f"🛒 حداقل سفارش: {d.get('min_order_amount', 0):,} تومان\n"
        f"📊 حداکثر استفاده: {d.get('max_uses') or 'نامحدود'}\n"
        f"📅 انقضا: {d.get('expire_date').strftime('%Y/%m/%d') if d.get('expire_date') else 'ندارد'}"
    )
    await update.message.reply_html(
        text,
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ ثبت کد", callback_data="disc_confirm:yes"),
                InlineKeyboardButton("❌ لغو", callback_data="disc_confirm:no"),
            ]
        ]),
    )
    return DISC_CONFIRM


async def discount_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "disc_confirm:no":
        await query.edit_message_text("❌ ثبت کد تخفیف لغو شد.")
        context.user_data.pop("new_discount", None)
        return ConversationHandler.END

    d = context.user_data.pop("new_discount", {})
    async with get_db() as session:
        disc_repo = DiscountRepository(session)
        discount = await disc_repo.create(
            code=d["code"],
            type=d["type"],
            value=d["value"],
            min_order_amount=d.get("min_order_amount", 0),
            max_uses=d.get("max_uses"),
            expire_date=d.get("expire_date"),
            is_active=True,
            created_by=query.from_user.id,
        )

    await query.edit_message_text(
        f"✅ کد تخفیف <code>{discount.code}</code> با موفقیت ثبت شد!",
        parse_mode=ParseMode.HTML,
    )
    return ConversationHandler.END


async def cancel_discount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop("new_discount", None)
    await update.effective_message.reply_text("❌ لغو شد.")
    return ConversationHandler.END


def build_discount_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(new_discount_start, pattern="^disc:new$")],
        states={
            DISC_CODE:      [MessageHandler(filters.TEXT & ~filters.COMMAND, discount_code_received)],
            DISC_TYPE:      [CallbackQueryHandler(discount_type_received, pattern="^disc_type:")],
            DISC_VALUE:     [MessageHandler(filters.TEXT & ~filters.COMMAND, discount_value_received)],
            DISC_MIN_ORDER: [MessageHandler(filters.TEXT, discount_min_order_received)],
            DISC_MAX_USES:  [MessageHandler(filters.TEXT, discount_max_uses_received)],
            DISC_EXPIRY:    [MessageHandler(filters.TEXT, discount_expiry_received)],
            DISC_CONFIRM:   [CallbackQueryHandler(discount_confirm, pattern="^disc_confirm:")],
        },
        fallbacks=[MessageHandler(filters.COMMAND, cancel_discount)],
    )


def register_discount_admin_handlers(app) -> None:
    app.add_handler(build_discount_conversation())
    app.add_handler(CallbackQueryHandler(admin_discounts_list, pattern="^disc:list$"))
    app.add_handler(CallbackQueryHandler(discount_detail, pattern="^disc:detail:"))
    app.add_handler(CallbackQueryHandler(toggle_discount, pattern="^disc:toggle:"))
    app.add_handler(CallbackQueryHandler(delete_discount, pattern="^disc:delete:"))
