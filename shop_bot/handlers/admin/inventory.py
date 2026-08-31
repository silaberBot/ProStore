"""
هندلر مدیریت انبار اکانت‌ها در پنل ادمین
Admin inventory management — bulk upload and management
"""
from __future__ import annotations

import logging

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, Document
from telegram.constants import ParseMode
from telegram.ext import (
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from core.database import get_db
from repositories.inventory_repository import InventoryRepository
from repositories.product_repository import ProductRepository
from utils.decorators import admin_only

logger = logging.getLogger(__name__)

WAITING_ACCOUNTS_TEXT, WAITING_ACCOUNTS_FILE = range(2)


# ─────────────────────────────────────────────
# نمایش انبار یک محصول
# ─────────────────────────────────────────────
@admin_only
async def admin_inventory_view(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    product_id = int(query.data.split(":")[3])
    context.user_data["inventory_product_id"] = product_id

    async with get_db() as session:
        prod_repo = ProductRepository(session)
        inv_repo = InventoryRepository(session)
        product = await prod_repo.get_by_id(product_id)
        available = await inv_repo.get_product_accounts(product_id, "available")
        sold = await inv_repo.get_product_accounts(product_id, "sold")
        broken = await inv_repo.get_product_accounts(product_id, "broken")

    if not product:
        await query.edit_message_text("❌ محصول یافت نشد.")
        return

    text = (
        f"📦 <b>انبار: {product.name}</b>\n\n"
        f"✅ موجود: <b>{len(available)}</b>\n"
        f"💳 فروخته‌شده: <b>{len(sold)}</b>\n"
        f"❌ خراب: <b>{len(broken)}</b>\n"
        f"📊 جمع کل: {len(available) + len(sold) + len(broken)}"
    )
    buttons = [
        [InlineKeyboardButton("➕ افزودن اکانت (متن)", callback_data=f"inv:add_text:{product_id}")],
        [InlineKeyboardButton("📄 افزودن اکانت (فایل TXT)", callback_data=f"inv:add_file:{product_id}")],
        [InlineKeyboardButton("📋 مشاهده اکانت‌های موجود", callback_data=f"inv:list:{product_id}")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data=f"admin:product:detail:{product_id}")],
    ]
    await query.edit_message_text(
        text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons)
    )


# ─────────────────────────────────────────────
# لیست اکانت‌های موجود
# ─────────────────────────────────────────────
@admin_only
async def admin_inventory_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    product_id = int(query.data.split(":")[2])

    async with get_db() as session:
        inv_repo = InventoryRepository(session)
        accounts = await inv_repo.get_product_accounts(product_id, "available")

    if not accounts:
        await query.edit_message_text(
            "❌ انباری موجود نیست.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 بازگشت", callback_data=f"admin:product:inventory:{product_id}")
            ]]),
        )
        return

    lines = []
    for i, acc in enumerate(accounts[:20], 1):
        exp = f" | انقضا: {acc.expire_date}" if acc.expire_date else ""
        lines.append(f"{i}. {acc.username}:{acc.password}{exp}")

    text = f"📋 <b>اکانت‌های موجود (نمایش ۲۰ تا):</b>\n\n<code>{''.join(chr(10).join(lines))}</code>"
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 بازگشت", callback_data=f"admin:product:inventory:{product_id}")
        ]]),
    )


# ─────────────────────────────────────────────
# افزودن اکانت به‌صورت متن مستقیم
# ─────────────────────────────────────────────
@admin_only
async def add_inventory_text_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    product_id = int(query.data.split(":")[2])
    context.user_data["inventory_product_id"] = product_id

    await query.edit_message_text(
        "📝 <b>افزودن اکانت (متن)</b>\n\n"
        "هر خط یک اکانت را به این فرمت وارد کنید:\n"
        "<code>username:password</code>\n"
        "یا با اطلاعات اضافه:\n"
        "<code>username:password:extra_info</code>\n\n"
        "مثال:\n"
        "<code>user1@gmail.com:pass123\n"
        "user2@gmail.com:pass456:اشتراک تا پایان ماه</code>",
        parse_mode=ParseMode.HTML,
    )
    return WAITING_ACCOUNTS_TEXT


async def add_inventory_text_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    product_id = context.user_data.get("inventory_product_id")
    if not product_id:
        await update.message.reply_text("❌ خطا. دوباره امتحان کنید.")
        return ConversationHandler.END

    lines = update.message.text.strip().split("\n")
    accounts = _parse_account_lines(lines)

    if not accounts:
        await update.message.reply_html(
            "❌ هیچ اکانت معتبری یافت نشد.\n"
            "فرمت: <code>username:password</code>"
        )
        return WAITING_ACCOUNTS_TEXT

    added = await _save_accounts(product_id, accounts)
    await update.message.reply_text(
        f"✅ <b>{added}</b> اکانت با موفقیت افزوده شد.",
        parse_mode=ParseMode.HTML,
    )
    return ConversationHandler.END


# ─────────────────────────────────────────────
# افزودن اکانت از فایل TXT
# ─────────────────────────────────────────────
@admin_only
async def add_inventory_file_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    product_id = int(query.data.split(":")[2])
    context.user_data["inventory_product_id"] = product_id

    await query.edit_message_text(
        "📄 <b>افزودن اکانت (فایل)</b>\n\n"
        "یک فایل <b>.txt</b> بفرستید که هر خط آن یک اکانت باشد:\n"
        "<code>username:password</code>",
        parse_mode=ParseMode.HTML,
    )
    return WAITING_ACCOUNTS_FILE


async def add_inventory_file_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    product_id = context.user_data.get("inventory_product_id")
    if not product_id:
        return ConversationHandler.END

    document: Document = update.message.document
    if not document or not document.file_name.endswith(".txt"):
        await update.message.reply_text("❌ فقط فایل .txt قابل قبول است.")
        return WAITING_ACCOUNTS_FILE

    if document.file_size > 500_000:  # 500KB max
        await update.message.reply_text("❌ حجم فایل نباید بیش از ۵۰۰ کیلوبایت باشد.")
        return ConversationHandler.END

    try:
        file = await context.bot.get_file(document.file_id)
        content = bytes()
        import io
        buf = io.BytesIO()
        await file.download_to_memory(buf)
        buf.seek(0)
        raw = buf.read().decode("utf-8", errors="ignore")
    except Exception as e:
        logger.error(f"File download error: {e}")
        await update.message.reply_text("❌ خطا در دریافت فایل.")
        return ConversationHandler.END

    lines = raw.strip().split("\n")
    accounts = _parse_account_lines(lines)

    if not accounts:
        await update.message.reply_text("❌ هیچ اکانت معتبری در فایل یافت نشد.")
        return ConversationHandler.END

    await update.message.reply_text(f"⏳ در حال پردازش {len(accounts)} اکانت...")
    added = await _save_accounts(product_id, accounts)
    await update.message.reply_html(f"✅ <b>{added}</b> اکانت با موفقیت افزوده شد.")
    return ConversationHandler.END


# ─────────────────────────────────────────────
# توابع کمکی
# ─────────────────────────────────────────────
def _parse_account_lines(lines: list) -> list[dict]:
    """تجزیه خطوط متنی به دیکشنری اکانت"""
    accounts = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(":", 2)
        if len(parts) < 2:
            continue
        acc = {
            "username": parts[0].strip(),
            "password": parts[1].strip(),
        }
        if len(parts) == 3:
            acc["extra_info"] = parts[2].strip()
        if acc["username"] and acc["password"]:
            accounts.append(acc)
    return accounts


async def _save_accounts(product_id: int, accounts: list) -> int:
    """ذخیره اکانت‌ها در دیتابیس و بروزرسانی موجودی محصول"""
    async with get_db() as session:
        inv_repo = InventoryRepository(session)
        prod_repo = ProductRepository(session)
        added = await inv_repo.add_bulk(product_id, accounts)
        product = await prod_repo.get_by_id(product_id)
        if product:
            await prod_repo.update(
                product,
                available_count=product.available_count + added,
                is_active=True,
            )
    return added


async def cancel_inventory(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop("inventory_product_id", None)
    await update.effective_message.reply_text("❌ لغو شد.")
    return ConversationHandler.END


def build_inventory_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(add_inventory_text_start, pattern="^inv:add_text:"),
            CallbackQueryHandler(add_inventory_file_start, pattern="^inv:add_file:"),
        ],
        states={
            WAITING_ACCOUNTS_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_inventory_text_receive)
            ],
            WAITING_ACCOUNTS_FILE: [
                MessageHandler(filters.Document.MimeType("text/plain"), add_inventory_file_receive),
                MessageHandler(filters.Document.FileExtension("txt"), add_inventory_file_receive),
            ],
        },
        fallbacks=[MessageHandler(filters.COMMAND, cancel_inventory)],
    )


def register_inventory_admin_handlers(app) -> None:
    app.add_handler(build_inventory_conversation())
    app.add_handler(CallbackQueryHandler(admin_inventory_view, pattern="^admin:product:inventory:"))
    app.add_handler(CallbackQueryHandler(admin_inventory_list, pattern="^inv:list:"))
