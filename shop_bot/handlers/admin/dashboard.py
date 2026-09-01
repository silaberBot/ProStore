"""
هندلرهای پنل ادمین (اصلاح‌شده)
Admin panel handlers — dashboard, orders, products, users, tickets
"""
from __future__ import annotations

import logging

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode
from telegram.ext import (
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from config.settings import settings
from core.database import get_db
from repositories.product_repository import ProductRepository
from repositories.user_repository import UserRepository
from repositories.order_repository import OrderRepository, WalletRepository
from repositories.ticket_repository import TicketRepository
from services.order_service import OrderService
from services.ticket_service import TicketService, ReportService, SettingService
from services.notification_service import NotificationService
from utils.decorators import admin_only
from utils.keyboards import (
    admin_main_menu,
    admin_order_actions,
    admin_user_actions,
    admin_ticket_actions,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# داشبورد
# ─────────────────────────────────────────────
@admin_only
async def admin_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    async with get_db() as session:
        report = ReportService(session)
        stats = await report.get_dashboard_stats()

        ticket_repo = TicketRepository(session)
        open_tickets = await ticket_repo.get_open_count()

    text = (
        f"📊 <b>داشبورد مدیریت</b>\n\n"
        f"📦 سفارشات امروز: <b>{stats['today_orders']}</b>\n"
        f"💰 درآمد امروز: <b>{stats['today_revenue']:,} تومان</b>\n"
        f"👥 کل کاربران: <b>{stats['total_users']}</b>\n"
        f"🟢 کاربران فعال امروز: <b>{stats['active_today']}</b>\n"
        f"⏳ سفارشات در انتظار: <b>{stats['waiting_orders']}</b>\n"
        f"🎫 تیکت‌های باز: <b>{open_tickets}</b>"
    )
    await update.effective_message.reply_html(text, reply_markup=admin_main_menu())


# ─────────────────────────────────────────────
# مدیریت سفارشات
# ─────────────────────────────────────────────
@admin_only
async def admin_orders_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    async with get_db() as session:
        order_repo = OrderRepository(session)
        orders = await order_repo.get_pending_orders()

    if not orders:
        await update.effective_message.reply_text("✅ هیچ سفارش در انتظاری وجود ندارد.")
        return

    buttons = []
    for o in orders:
        buttons.append([
            InlineKeyboardButton(
                f"#{o.order_number} | {o.final_amount:,} تومان",
                callback_data=f"admin:order:detail:{o.id}",
            )
        ])
    await update.effective_message.reply_html(
        f"📦 <b>سفارشات در انتظار ({len(orders)})</b>:",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


@admin_only
async def admin_order_detail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    order_id = int(query.data.split(":")[3])

    async with get_db() as session:
        order_repo = OrderRepository(session)
        order = await order_repo.get_by_id(order_id)
        user_repo = UserRepository(session)
        user = await user_repo.get_by_telegram_id(order.user_id) if order else None

    if not order:
        await query.edit_message_text("❌ سفارش یافت نشد.")
        return

    text = (
        f"📦 <b>جزئیات سفارش #{order.order_number}</b>\n\n"
        f"👤 کاربر: {user.full_name if user else order.user_id}\n"
        f"💰 مبلغ: <b>{order.final_amount:,} تومان</b>\n"
        f"💳 روش پرداخت: {order.payment_method or '—'}\n"
        f"📌 وضعیت: {order.status}\n"
        f"📅 تاریخ: {order.created_at.strftime('%Y/%m/%d %H:%M')}"
    )
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=admin_order_actions(order.id, order.status),
    )


@admin_only
async def admin_deliver_order(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    order_id = int(query.data.split(":")[3])

    async with get_db() as session:
        order_service = OrderService(session)
        order = await order_service.order_repo.get_by_id(order_id)
        success, msg, account = await order_service.deliver_account(order_id)

        notif = NotificationService(context.bot)
        if success and account:
            await notif.account_delivered(
                order.user_id,
                order.order_number,
                account["account_text"],
                "محصول",
            )

    result = "✅ اکانت ارسال شد" if success else f"❌ {msg}"
    await query.edit_message_text(result)


@admin_only
async def admin_cancel_order(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    order_id = int(query.data.split(":")[3])

    async with get_db() as session:
        order_service = OrderService(session)
        success, msg = await order_service.cancel_order(order_id)

    await query.edit_message_text(f"{'✅' if success else '❌'} {msg}")


# ─────────────────────────────────────────────
# مدیریت محصولات — همیشه دکمه افزودن نمایش داده میشه
# ─────────────────────────────────────────────
@admin_only
async def admin_products_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    async with get_db() as session:
        product_repo = ProductRepository(session)
        products = await product_repo.get_all(limit=50)

    buttons = []
    if products:
        for p in products:
            status = "✅" if p.is_active else "❌"
            buttons.append([
                InlineKeyboardButton(
                    f"{status} {p.name} | {p.price:,} تومان",
                    callback_data=f"admin:product:detail:{p.id}",
                )
            ])
        text = f"🏪 <b>محصولات ({len(products)} عدد)</b>:"
    else:
        text = "🏪 <b>محصولات</b>\n\nهیچ محصولی وجود ندارد. برای شروع، اولین محصول خود را اضافه کنید:"

    # همیشه دکمه افزودن نمایش داده بشه
    buttons.append([InlineKeyboardButton("➕ افزودن محصول جدید", callback_data="admin:product:add")])
    await update.effective_message.reply_html(text, reply_markup=InlineKeyboardMarkup(buttons))


# ─────────────────────────────────────────────
# مدیریت کاربران
# ─────────────────────────────────────────────
@admin_only
async def admin_users_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(
        "🔍 شناسه تلگرام، نام کاربری یا شماره موبایل را وارد کنید:"
    )
    context.user_data["admin_waiting_for"] = "user_search"


@admin_only
async def admin_user_detail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    target_user_id = int(query.data.split(":")[3])

    async with get_db() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_telegram_id(target_user_id)
        wallet_repo = WalletRepository(session)
        wallet = await wallet_repo.get_by_user_id(target_user_id)

    if not user:
        await query.edit_message_text("❌ کاربر یافت نشد.")
        return

    wallet_text = f"💰 کیف پول: {wallet.balance:,} تومان\n" if wallet else ""
    text = (
        f"👤 <b>{user.full_name}</b>\n\n"
        f"🆔 ID: <code>{user.telegram_id}</code>\n"
        f"👤 Username: @{user.username or '—'}\n"
        f"📱 موبایل: {user.phone_number or '—'}\n"
        f"⭐ سطح: {user.level}\n"
        f"{wallet_text}"
        f"🚫 مسدود: {'بله' if user.is_banned else 'خیر'}\n"
        f"📅 عضویت: {user.created_at.strftime('%Y/%m/%d')}"
    )
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=admin_user_actions(user.telegram_id, user.is_banned),
    )


@admin_only
async def admin_ban_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    target_user_id = int(query.data.split(":")[3])

    async with get_db() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_telegram_id(target_user_id)
        if user:
            new_ban = not user.is_banned
            await user_repo.update(user, is_banned=new_ban)
            action = "مسدود" if new_ban else "رفع مسدودی"
            await query.edit_message_text(f"✅ کاربر {user.full_name} {action} شد.")


# ─────────────────────────────────────────────
# مدیریت تیکت‌ها
# ─────────────────────────────────────────────
@admin_only
async def admin_tickets_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    async with get_db() as session:
        ticket_service = TicketService(session)
        tickets = await ticket_service.get_open_tickets(limit=10)

    if not tickets:
        await update.effective_message.reply_text("✅ هیچ تیکت بازی وجود ندارد.")
        return

    buttons = [[
        InlineKeyboardButton(
            f"#{t.id} — {t.subject[:30]}",
            callback_data=f"admin:ticket:detail:{t.id}",
        )
    ] for t in tickets]
    await update.effective_message.reply_html(
        f"🎫 <b>تیکت‌های باز ({len(tickets)}):</b>",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


@admin_only
async def admin_ticket_detail_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    ticket_id = int(query.data.split(":")[3])

    async with get_db() as session:
        ticket_repo = TicketRepository(session)
        ticket = await ticket_repo.get_by_id(ticket_id)
        messages = ticket.messages if ticket else []

    if not ticket:
        await query.edit_message_text("❌ تیکت یافت نشد.")
        return

    convo = "\n\n".join(
        f"{'🤖 ادمین' if m.is_admin else '👤 کاربر'}: {m.message}"
        for m in messages[-5:]
    )
    text = (
        f"🎫 <b>تیکت #{ticket.id}</b>\n"
        f"📝 {ticket.subject}\n"
        f"📌 وضعیت: {ticket.status}\n\n"
        f"<b>آخرین پیام‌ها:</b>\n{convo}"
    )
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=admin_ticket_actions(ticket.id),
    )


# ─────────────────────────────────────────────
# تنظیمات — ارسال به هندلر settings.py
# ─────────────────────────────────────────────
@admin_only
async def admin_settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from handlers.admin.settings import EDITABLE_SETTINGS
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


# ─────────────────────────────────────────────
# تخفیف‌ها — اتصال دکمه کیبورد به هندلر discounts.py
# ─────────────────────────────────────────────
@admin_only
async def admin_discounts_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from handlers.admin.discounts import admin_discounts_list as disc_list
    await disc_list(update, context)


# ─────────────────────────────────────────────
# پرداخت‌ها
# ─────────────────────────────────────────────
@admin_only
async def admin_payments_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    async with get_db() as session:
        from repositories.order_repository import PaymentRepository
        pay_repo = PaymentRepository(session)
        payments = await pay_repo.get_recent(limit=10)

    if not payments:
        await update.effective_message.reply_text("💳 هیچ پرداختی ثبت نشده است.")
        return

    lines = []
    for p in payments:
        status = {"success": "✅", "pending": "⏳", "failed": "❌"}.get(p.status, "❓")
        lines.append(f"{status} {p.amount:,} ت | {p.gateway} | {p.created_at.strftime('%m/%d %H:%M')}")

    await update.effective_message.reply_html(
        "💳 <b>آخرین پرداخت‌ها:</b>\n\n" + "\n".join(lines)
    )


# ─────────────────────────────────────────────
# پیام همگانی
# ─────────────────────────────────────────────
@admin_only
async def admin_broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(
        "📢 متن پیام همگانی را بنویسید (از HTML استفاده کنید):"
    )
    context.user_data["admin_waiting_for"] = "broadcast"


# ─────────────────────────────────────────────
# هندلر جنریک برای ورودی‌های متنی ادمین
# (جستجوی کاربر + ارسال broadcast)
# ─────────────────────────────────────────────
async def admin_text_input_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    waiting_for = context.user_data.get("admin_waiting_for")
    if not waiting_for:
        return

    if waiting_for == "user_search":
        context.user_data.pop("admin_waiting_for", None)
        query_text = update.message.text.strip()
        async with get_db() as session:
            user_repo = UserRepository(session)
            users = await user_repo.search_users(query=query_text, limit=5)

        if not users:
            await update.message.reply_text("❌ کاربری یافت نشد.")
            return

        buttons = []
        for u in users:
            ban_icon = "🚫" if u.is_banned else "✅"
            buttons.append([
                InlineKeyboardButton(
                    f"{ban_icon} {u.full_name} (@{u.username or '—'})",
                    callback_data=f"admin:user:detail:{u.telegram_id}",
                )
            ])
        await update.message.reply_html(
            f"👥 <b>نتایج جستجو ({len(users)} کاربر):</b>",
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    elif waiting_for == "broadcast":
        context.user_data.pop("admin_waiting_for", None)
        text = update.message.text
        await update.message.reply_text("⏳ در حال ارسال...")

        async with get_db() as session:
            user_repo = UserRepository(session)
            users = await user_repo.get_all(limit=10000)
            user_ids = [u.telegram_id for u in users if not u.is_banned]

        notif = NotificationService(context.bot)
        success, failed = await notif.broadcast(user_ids, text)
        await update.message.reply_text(
            f"✅ ارسال تمام شد\n"
            f"📤 موفق: {success}\n"
            f"❌ ناموفق: {failed}"
        )


# ─────────────────────────────────────────────
# بکاپ
# ─────────────────────────────────────────────
@admin_only
async def admin_backup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    import shutil
    import os
    from datetime import datetime

    src_db = os.path.join(os.getcwd(), "shop_bot.db")
    if not os.path.exists(src_db):
        await update.effective_message.reply_text("❌ فایل دیتابیس یافت نشد.")
        return

    backup_dir = os.path.join(os.getcwd(), "backups")
    os.makedirs(backup_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(backup_dir, f"backup_{timestamp}.db")
    shutil.copy2(src_db, backup_path)

    await context.bot.send_document(
        chat_id=update.effective_user.id,
        document=open(backup_path, "rb"),
        filename=f"backup_{timestamp}.db",
        caption=f"✅ بکاپ دیتابیس — {timestamp}",
    )


def register_admin_handlers(app) -> None:
    # Dashboard
    app.add_handler(MessageHandler(
        filters.Regex("^📊 داشبورد$") & filters.ChatType.PRIVATE,
        admin_dashboard,
    ))

    # Orders
    app.add_handler(MessageHandler(filters.Regex("^📦 سفارشات$"), admin_orders_list))
    app.add_handler(CallbackQueryHandler(admin_order_detail, pattern="^admin:order:detail:"))
    app.add_handler(CallbackQueryHandler(admin_deliver_order, pattern="^admin:order:deliver:"))
    app.add_handler(CallbackQueryHandler(admin_cancel_order, pattern="^admin:order:cancel:"))

    # Products
    app.add_handler(MessageHandler(filters.Regex("^🏪 محصولات$"), admin_products_list))
    app.add_handler(CallbackQueryHandler(admin_products_list, pattern="^admin:products_list$"))

    # Users
    app.add_handler(MessageHandler(filters.Regex("^👥 کاربران$"), admin_users_search))
    app.add_handler(CallbackQueryHandler(admin_user_detail, pattern="^admin:user:detail:"))
    app.add_handler(CallbackQueryHandler(admin_ban_toggle, pattern="^admin:user:ban_toggle:"))

    # Tickets
    app.add_handler(MessageHandler(filters.Regex("^🎫 تیکت‌ها$"), admin_tickets_list))
    app.add_handler(CallbackQueryHandler(admin_ticket_detail_callback, pattern="^admin:ticket:detail:"))

    # Settings
    app.add_handler(MessageHandler(filters.Regex("^⚙️ تنظیمات$"), admin_settings_menu))

    # Discounts
    app.add_handler(MessageHandler(filters.Regex("^🎟 تخفیف‌ها$"), admin_discounts_menu))

    # Payments
    app.add_handler(MessageHandler(filters.Regex("^💳 پرداخت‌ها$"), admin_payments_list))

    # Broadcast
    app.add_handler(MessageHandler(filters.Regex("^📢 پیام همگانی$"), admin_broadcast_start))

    # Backup
    app.add_handler(MessageHandler(filters.Regex("^📁 بکاپ$"), admin_backup))
