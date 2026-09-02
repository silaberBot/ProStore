"""
هندلرهای پروفایل، کیف پول، رفرال و پشتیبانی (اصلاح‌شده — تمام هندلرهای گمشده اضافه شد)
"""
from __future__ import annotations
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode
from telegram.ext import (
    CallbackQueryHandler, ContextTypes, ConversationHandler, MessageHandler, filters,
)
from config.settings import settings
from core.database import get_db
from repositories.user_repository import UserRepository
from repositories.order_repository import WalletRepository, OrderRepository
from services.referral_service import ReferralService
from services.ticket_service import TicketService
from services.notification_service import NotificationService
from utils.keyboards import (
    profile_keyboard, orders_list_keyboard, wallet_keyboard,
    wallet_charge_amounts_keyboard, support_keyboard, ticket_detail_keyboard, back_keyboard,
)

logger = logging.getLogger(__name__)
TICKET_SUBJECT, TICKET_MESSAGE, TICKET_REPLY_MSG = range(3)


# ─── پروفایل ───
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


async def profile_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """بازگشت به پروفایل از طریق callback"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    async with get_db() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_telegram_id(user_id)
    if not user:
        await query.edit_message_text("⚠️ لطفاً /start را بزنید.")
        return
    text = (
        f"👤 <b>پروفایل شما</b>\n\n"
        f"📛 نام: {user.full_name}\n"
        f"🆔 شناسه: <code>{user.telegram_id}</code>\n"
        f"💰 موجودی: <b>{user.wallet_balance:,} تومان</b>"
    )
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=profile_keyboard())


# ─── سفارشات کاربر ───
async def user_orders_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    async with get_db() as session:
        from services.order_service import OrderService
        order_service = OrderService(session)
        orders = await order_service.get_user_orders(user_id)
    if not orders:
        await query.edit_message_text(
            "📦 شما هنوز سفارشی ثبت نکرده‌اید.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="back:profile")]]),
        )
        return
    await query.edit_message_text(
        "📦 <b>سفارشات شما</b>:", parse_mode=ParseMode.HTML, reply_markup=orders_list_keyboard(orders),
    )


async def order_detail_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """جزئیات یک سفارش کاربر"""
    query = update.callback_query
    await query.answer()
    order_id = int(query.data.split(":")[1])
    async with get_db() as session:
        order_repo = OrderRepository(session)
        order = await order_repo.get_by_id(order_id)
    if not order:
        await query.edit_message_text("❌ سفارش یافت نشد.")
        return
    status_map = {"completed": "✅ تکمیل‌شده", "pending": "⏳ در انتظار پرداخت", "cancelled": "❌ لغو‌شده", "waiting": "🔄 در انتظار ارسال"}
    text = (
        f"📦 <b>سفارش #{order.order_number}</b>\n\n"
        f"📌 وضعیت: {status_map.get(order.status, order.status)}\n"
        f"💰 مبلغ: <b>{order.final_amount:,} تومان</b>\n"
        f"💳 روش پرداخت: {order.payment_method or '—'}\n"
        f"📅 تاریخ: {order.created_at.strftime('%Y/%m/%d %H:%M')}"
    )
    await query.edit_message_text(
        text, parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="profile:orders")]]),
    )


# ─── کیف پول ───
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


async def wallet_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """بازگشت به کیف پول از callback"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    async with get_db() as session:
        wallet_repo = WalletRepository(session)
        wallet = await wallet_repo.get_or_create(user_id)
    text = f"💰 <b>کیف پول</b>\n\n💵 موجودی: <b>{wallet.balance:,} تومان</b>"
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=wallet_keyboard())


async def wallet_charge_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "💳 <b>شارژ کیف پول</b>\n\nمبلغ مورد نظر را انتخاب کنید:",
        parse_mode=ParseMode.HTML, reply_markup=wallet_charge_amounts_keyboard(),
    )


async def wallet_charge_amount_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    amount_str = query.data.split(":")[1]
    if amount_str == "custom":
        context.user_data["waiting_for_custom_amount"] = True
        await query.edit_message_text("✏️ مبلغ دلخواه را به تومان وارد کنید:", reply_markup=back_keyboard("back:wallet"))
        return

    amount = int(amount_str)
    # نمایش روش‌های پرداخت برای شارژ
    buttons = [
        [InlineKeyboardButton("🏦 زرین‌پال", callback_data=f"charge_pay:zarinpal:{amount}")],
        [InlineKeyboardButton("💳 آیدی‌پی", callback_data=f"charge_pay:idpay:{amount}")],
        [InlineKeyboardButton("🪙 رمزارز", callback_data=f"charge_pay:crypto:{amount}")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="wallet:charge")],
    ]
    await query.edit_message_text(
        f"💳 <b>شارژ {amount:,} تومان</b>\n\nروش پرداخت را انتخاب کنید:",
        parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons),
    )


async def wallet_charge_pay(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """پرداخت شارژ کیف پول"""
    query = update.callback_query
    await query.answer()
    parts = query.data.split(":")
    method = parts[1]
    amount = int(parts[2])
    user_id = query.from_user.id

    if method == "zarinpal":
        async with get_db() as session:
            from services.payment_service import PaymentService
            pay_service = PaymentService(session)
            ok, url, authority = await pay_service.zarinpal_request(
                user_id=user_id, amount=amount, description=f"شارژ کیف پول {amount:,} تومان",
            )
            if ok:
                kb = InlineKeyboardMarkup([[InlineKeyboardButton("💳 پرداخت", url=url)]])
                await query.edit_message_text(f"🏦 مبلغ: <b>{amount:,} تومان</b>\n\nروی دکمه زیر کلیک کنید:", parse_mode=ParseMode.HTML, reply_markup=kb)
            else:
                await query.edit_message_text(f"❌ {url}")
    else:
        await query.edit_message_text(f"⚙️ درگاه «{method}» در حال راه‌اندازی است.")


async def wallet_history_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """تاریخچه تراکنش‌ها"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    async with get_db() as session:
        from repositories.order_repository import PaymentRepository
        pay_repo = PaymentRepository(session)
        payments = await pay_repo.get_user_payments(user_id, limit=10)
    if not payments:
        await query.edit_message_text("📋 تراکنشی ثبت نشده.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="back:wallet")]]))
        return
    lines = []
    for p in payments:
        icon = {"success": "✅", "pending": "⏳", "failed": "❌"}.get(p.status, "❓")
        lines.append(f"{icon} {p.amount:,} ت | {p.gateway} | {p.created_at.strftime('%m/%d')}")
    text = "📋 <b>تاریخچه تراکنش‌ها:</b>\n\n" + "\n".join(lines)
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="back:wallet")]]))


# ─── رفرال ───
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
        f"💰 کل پاداش: {stats['earned']:,} تومان"
    )
    await update.message.reply_html(text)


# ─── پشتیبانی / تیکت ───
async def support_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = "🎫 <b>پشتیبانی</b>\n\nبرای ثبت درخواست جدید یا پیگیری تیکت‌های قبلی از منوی زیر استفاده کنید."
    await update.message.reply_html(text, reply_markup=support_keyboard())


async def support_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """بازگشت به منوی پشتیبانی"""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🎫 <b>پشتیبانی</b>\n\nاز منوی زیر استفاده کنید:",
        parse_mode=ParseMode.HTML, reply_markup=support_keyboard(),
    )


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
        success, msg, ticket_id = await ticket_service.create_ticket(user_id=user_id, subject=subject, first_message=message)
        if success:
            for admin_id in settings.admin_ids_list:
                try:
                    user_repo = UserRepository(session)
                    user = await user_repo.get_by_telegram_id(user_id)
                    notif = NotificationService(context.bot)
                    await notif.admin_new_ticket(admin_id, ticket_id, user.full_name if user else "کاربر", subject)
                except Exception:
                    pass
    if success:
        await update.message.reply_html(f"✅ تیکت #{ticket_id} ثبت شد!\nبه‌زودی پاسخ می‌دهیم.", reply_markup=support_keyboard())
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
        await query.edit_message_text("🎫 شما هیچ تیکتی ندارید.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="back:support")]]))
        return
    status_icons = {"open": "🔴", "in_progress": "🟡", "answered": "🟢", "closed": "⚫"}
    buttons = []
    for t in tickets:
        icon = status_icons.get(t.status, "❓")
        buttons.append([InlineKeyboardButton(f"{icon} #{t.id} — {t.subject[:30]}", callback_data=f"ticket:detail:{t.id}")])
    buttons.append([InlineKeyboardButton("🔙 بازگشت", callback_data="back:support")])
    await query.edit_message_text("🎫 <b>تیکت‌های شما:</b>", parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))


async def ticket_detail_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """نمایش جزئیات تیکت"""
    query = update.callback_query
    await query.answer()
    ticket_id = int(query.data.split(":")[2])
    async with get_db() as session:
        from repositories.ticket_repository import TicketRepository
        ticket_repo = TicketRepository(session)
        ticket = await ticket_repo.get_by_id(ticket_id)
        messages = ticket.messages if ticket else []
    if not ticket:
        await query.edit_message_text("❌ تیکت یافت نشد.")
        return
    convo = "\n\n".join(f"{'🤖 پشتیبانی' if m.is_admin else '👤 شما'}: {m.message}" for m in messages[-5:])
    status_map = {"open": "🔴 باز", "in_progress": "🟡 در حال بررسی", "answered": "🟢 پاسخ داده‌شده", "closed": "⚫ بسته"}
    text = f"🎫 <b>تیکت #{ticket.id}</b>\n📝 {ticket.subject}\n📌 {status_map.get(ticket.status, ticket.status)}\n\n{convo}"
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=ticket_detail_keyboard(ticket.id, ticket.status))


async def ticket_reply_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """شروع پاسخ به تیکت توسط کاربر"""
    query = update.callback_query
    await query.answer()
    ticket_id = int(query.data.split(":")[2])
    context.user_data["replying_ticket_id"] = ticket_id
    await query.edit_message_text("✉️ پاسخ خود را بنویسید:")
    return TICKET_REPLY_MSG


async def ticket_reply_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    ticket_id = context.user_data.pop("replying_ticket_id", None)
    if not ticket_id:
        return ConversationHandler.END
    user_id = update.effective_user.id
    msg_text = update.message.text
    async with get_db() as session:
        ticket_service = TicketService(session)
        await ticket_service.add_message(ticket_id=ticket_id, user_id=user_id, message=msg_text, is_admin=False)
    await update.message.reply_html(f"✅ پاسخ شما به تیکت #{ticket_id} ارسال شد.", reply_markup=support_keyboard())
    return ConversationHandler.END


async def ticket_close_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """بستن تیکت توسط کاربر"""
    query = update.callback_query
    await query.answer()
    ticket_id = int(query.data.split(":")[2])
    async with get_db() as session:
        ticket_service = TicketService(session)
        await ticket_service.close_ticket(ticket_id)
    await query.edit_message_text(f"✅ تیکت #{ticket_id} بسته شد.")


async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("❌ لغو شد.", reply_markup=support_keyboard())
    return ConversationHandler.END


def register_user_handlers(app) -> None:
    # Profile
    app.add_handler(MessageHandler(filters.Regex("^👤 پروفایل من$"), profile_handler))
    app.add_handler(CallbackQueryHandler(user_orders_handler, pattern="^profile:orders$"))
    app.add_handler(CallbackQueryHandler(order_detail_handler, pattern="^order_detail:"))
    app.add_handler(CallbackQueryHandler(profile_callback, pattern="^back:profile$"))

    # Wallet
    app.add_handler(MessageHandler(filters.Regex("^💰 کیف پول$"), wallet_handler))
    app.add_handler(CallbackQueryHandler(wallet_charge_handler, pattern="^wallet:charge$"))
    app.add_handler(CallbackQueryHandler(wallet_charge_amount_handler, pattern="^charge_amount:"))
    app.add_handler(CallbackQueryHandler(wallet_charge_pay, pattern="^charge_pay:"))
    app.add_handler(CallbackQueryHandler(wallet_history_handler, pattern="^wallet:history$"))
    app.add_handler(CallbackQueryHandler(wallet_callback, pattern="^back:wallet$"))

    # Referral
    app.add_handler(MessageHandler(filters.Regex("^🔗 دعوت از دوستان$"), referral_handler))

    # Support
    app.add_handler(MessageHandler(filters.Regex("^🎫 پشتیبانی$"), support_handler))
    app.add_handler(CallbackQueryHandler(ticket_list_handler, pattern="^ticket:list$"))
    app.add_handler(CallbackQueryHandler(ticket_detail_handler, pattern="^ticket:detail:"))
    app.add_handler(CallbackQueryHandler(ticket_close_handler, pattern="^ticket:close:"))
    app.add_handler(CallbackQueryHandler(support_callback, pattern="^back:support$"))

    # Ticket creation conversation
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(new_ticket_start, pattern="^ticket:new$")],
        states={
            TICKET_SUBJECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ticket_subject_received)],
            TICKET_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ticket_message_received)],
        },
        fallbacks=[MessageHandler(filters.Regex("^❌"), cancel_conversation)],
    ))

    # Ticket reply conversation
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(ticket_reply_start, pattern="^ticket:reply:")],
        states={
            TICKET_REPLY_MSG: [MessageHandler(filters.TEXT & ~filters.COMMAND, ticket_reply_received)],
        },
        fallbacks=[MessageHandler(filters.Regex("^❌"), cancel_conversation)],
    ))
