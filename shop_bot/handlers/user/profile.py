"""
هندلرهای پروفایل، کیف پول، رفرال و پشتیبانی کاربر
"""
from __future__ import annotations

import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from config.settings import settings
from core.database import get_db
from repositories.user_repository import UserRepository
from repositories.order_repository import WalletRepository
from services.referral_service import ReferralService
from services.ticket_service import TicketService
from utils.keyboards import (
    profile_keyboard,
    orders_list_keyboard,
    wallet_keyboard,
    wallet_charge_amounts_keyboard,
    support_keyboard,
    ticket_detail_keyboard,
    back_keyboard,
)

logger = logging.getLogger(__name__)

# ConversationHandler states
TICKET_SUBJECT, TICKET_MESSAGE = range(2)


# ─────────────────────────────────────────────
# پروفایل
# ─────────────────────────────────────────────
async def profile_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    async with get_db() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_telegram_id(user_id)

    if not user:
        await update.message.reply_text("⚠️ لطفاً /start را بزنید.")
        return

    level_icons = {"silver": "🥈", "gold": "🥇", "platinum": "💎"}
    text = (
        f"👤 <b>پروفایل شما</b>\n\n"
        f"📛 نام: {user.full_name}\n"
        f"🆔 شناسه: <code>{user.telegram_id}</code>\n"
        f"📱 موبایل: {user.phone_number or '— ثبت نشده'}\n"
        f"⭐ سطح: {level_icons.get(user.level, '🥈')} {user.level.upper()}\n"
        f"💰 موجودی کیف پول: <b>{user.wallet_balance:,} تومان</b>\n"
        f"📅 تاریخ عضویت: {user.created_at.strftime('%Y/%m/%d')}"
    )
    await update.message.reply_html(text, reply_markup=profile_keyboard())


async def user_orders_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    async with get_db() as session:
        user_repo = UserRepository(session)
        from services.order_service import OrderService
        order_service = OrderService(session)
        orders = await order_service.get_user_orders(user_id)

    if not orders:
        await query.edit_message_text("📦 شما هنوز سفارشی ثبت نکرده‌اید.")
        return

    await query.edit_message_text(
        "📦 <b>سفارشات شما</b>:",
        parse_mode=ParseMode.HTML,
        reply_markup=orders_list_keyboard(orders),
    )


# ─────────────────────────────────────────────
# کیف پول
# ─────────────────────────────────────────────
async def wallet_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    async with get_db() as session:
        wallet_repo = WalletRepository(session)
        wallet = await wallet_repo.get_or_create(user_id)

    text = (
        f"💰 <b>کیف پول شما</b>\n\n"
        f"💵 موجودی: <b>{wallet.balance:,} تومان</b>\n"
        f"➕ کل شارژ: {wallet.total_deposited:,} تومان\n"
        f"➖ کل خرید: {wallet.total_spent:,} تومان\n"
        f"🎁 پاداش رفرال: {wallet.total_referral_earned:,} تومان"
    )
    await update.message.reply_html(text, reply_markup=wallet_keyboard())


async def wallet_charge_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "💳 <b>شارژ کیف پول</b>\n\nمبلغ مورد نظر را انتخاب کنید:",
        parse_mode=ParseMode.HTML,
        reply_markup=wallet_charge_amounts_keyboard(),
    )


async def wallet_charge_amount_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    amount_str = query.data.split(":")[1]

    if amount_str == "custom":
        context.user_data["waiting_for_custom_amount"] = True
        await query.edit_message_text(
            "✏️ مبلغ دلخواه را به تومان وارد کنید:",
            reply_markup=back_keyboard("back:wallet"),
        )
        return

    amount = int(amount_str)
    await query.edit_message_text(
        f"💳 <b>شارژ {amount:,} تومان</b>\n\nروش پرداخت را انتخاب کنید:",
        parse_mode=ParseMode.HTML,
        reply_markup=None,
    )


# ─────────────────────────────────────────────
# رفرال
# ─────────────────────────────────────────────
async def referral_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    async with get_db() as session:
        ref_service = ReferralService(session)
        stats = await ref_service.get_referral_stats(user_id)

    text = (
        f"🔗 <b>دعوت از دوستان</b>\n\n"
        f"🔑 کد اختصاصی شما: <code>{stats['referral_code']}</code>\n"
        f"🌐 لینک دعوت:\n{stats['referral_link']}\n\n"
        f"📊 <b>آمار:</b>\n"
        f"👥 کل دعوت‌ها: {stats['total']}\n"
        f"✅ موفق: {stats['success']}\n"
        f"⏳ در انتظار: {stats['pending']}\n"
        f"💰 کل پاداش: {stats['earned']:,} تومان\n\n"
        f"📌 <b>شرایط دریافت پاداش:</b>\n"
        f"• دوست شما باید {settings.REFERRAL_MIN_ACTIVITIES} بار با ربات تعامل داشته باشد\n"
        f"• حداقل {settings.REFERRAL_DELAY_WITH_PHONE} روز از عضویت گذشته باشد"
    )
    await update.message.reply_html(text)


# ─────────────────────────────────────────────
# پشتیبانی / تیکت
# ─────────────────────────────────────────────
async def support_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "🎫 <b>پشتیبانی</b>\n\n"
        "برای ثبت درخواست جدید یا پیگیری تیکت‌های قبلی از منوی زیر استفاده کنید."
    )
    await update.message.reply_html(text, reply_markup=support_keyboard())


async def new_ticket_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("📝 موضوع تیکت را وارد کنید:")
    return TICKET_SUBJECT


async def ticket_subject_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["ticket_subject"] = update.message.text
    await update.message.reply_text("💬 حالا توضیحات مشکل خود را بنویسید:")
    return TICKET_MESSAGE


async def ticket_message_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    subject = context.user_data.get("ticket_subject", "بدون موضوع")
    message = update.message.text

    async with get_db() as session:
        ticket_service = TicketService(session)
        success, msg, ticket_id = await ticket_service.create_ticket(
            user_id=user_id, subject=subject, first_message=message
        )

        if success:
            # اطلاع به ادمین
            for admin_id in settings.admin_ids_list:
                try:
                    user_repo = UserRepository(session)
                    user = await user_repo.get_by_telegram_id(user_id)
                    from services.notification_service import NotificationService
                    notif = NotificationService(context.bot)
                    await notif.admin_new_ticket(admin_id, ticket_id, user.full_name if user else "کاربر", subject)
                except Exception:
                    pass

    if success:
        await update.message.reply_text(
            f"✅ تیکت #{ticket_id} ثبت شد!\nبه‌زودی پاسخ می‌دهیم.",
            reply_markup=support_keyboard(),
        )
    else:
        await update.message.reply_text(f"❌ خطا: {msg}")

    return ConversationHandler.END


async def ticket_list_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    async with get_db() as session:
        ticket_service = TicketService(session)
        tickets = await ticket_service.get_user_tickets(user_id)

    if not tickets:
        await query.edit_message_text("🎫 شما هیچ تیکتی ندارید.")
        return

    from telegram import InlineKeyboardMarkup, InlineKeyboardButton
    status_icons = {"open": "🔴", "in_progress": "🟡", "answered": "🟢", "closed": "⚫"}
    buttons = []
    for t in tickets:
        icon = status_icons.get(t.status, "❓")
        buttons.append([
            InlineKeyboardButton(
                f"{icon} #{t.id} — {t.subject[:30]}",
                callback_data=f"ticket:detail:{t.id}",
            )
        ])
    buttons.append([InlineKeyboardButton("🔙 بازگشت", callback_data="back:support")])
    await query.edit_message_text(
        "🎫 <b>تیکت‌های شما:</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("❌ لغو شد.", reply_markup=support_keyboard())
    return ConversationHandler.END


def register_user_handlers(app) -> None:
    # Profile
    app.add_handler(MessageHandler(filters.Regex("^👤 پروفایل من$"), profile_handler))
    app.add_handler(CallbackQueryHandler(user_orders_handler, pattern="^profile:orders$"))

    # Wallet
    app.add_handler(MessageHandler(filters.Regex("^💰 کیف پول$"), wallet_handler))
    app.add_handler(CallbackQueryHandler(wallet_charge_handler, pattern="^wallet:charge$"))
    app.add_handler(CallbackQueryHandler(wallet_charge_amount_handler, pattern="^charge_amount:"))

    # Referral
    app.add_handler(MessageHandler(filters.Regex("^🔗 دعوت از دوستان$"), referral_handler))

    # Support / Ticket
    app.add_handler(MessageHandler(filters.Regex("^🎫 پشتیبانی$"), support_handler))
    app.add_handler(CallbackQueryHandler(ticket_list_handler, pattern="^ticket:list$"))

    # Ticket creation conversation
    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(new_ticket_start, pattern="^ticket:new$")],
        states={
            TICKET_SUBJECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ticket_subject_received)],
            TICKET_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ticket_message_received)],
        },
        fallbacks=[MessageHandler(filters.Regex("^❌"), cancel_conversation)],
    )
    app.add_handler(conv)
