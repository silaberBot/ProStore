"""
هندلر مدیریت محصولات در پنل ادمین
Admin product management — add/edit products with ConversationHandler
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
from repositories.product_repository import ProductRepository
from utils.decorators import admin_only

logger = logging.getLogger(__name__)

# States برای ConversationHandler
(
    PROD_NAME, PROD_PRICE, PROD_CATEGORY,
    PROD_DESC, PROD_IMAGE, PROD_HAS_INVENTORY,
    PROD_CAPACITY, PROD_CONFIRM,
    EDIT_CHOOSE_FIELD, EDIT_VALUE,
) = range(10)

CATEGORIES = ["تدوین ویدیو", "هوش مصنوعی", "VPN و فیلترشکن", "طراحی گرافیک", "دیگر"]


def products_list_buttons(products: list) -> InlineKeyboardMarkup:
    buttons = []
    for p in products:
        icon = "✅" if p.is_active else "❌"
        stock = f" ({p.available_count}🗄)" if p.has_inventory else ""
        buttons.append([
            InlineKeyboardButton(
                f"{icon} {p.name}{stock} | {p.price:,} ت",
                callback_data=f"admin:product:detail:{p.id}",
            )
        ])
    buttons.append([InlineKeyboardButton("➕ افزودن محصول جدید", callback_data="admin:product:add")])
    return InlineKeyboardMarkup(buttons)


# ─────────────────────────────────────────────
# لیست محصولات
# ─────────────────────────────────────────────
@admin_only
async def admin_products_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    async with get_db() as session:
        repo = ProductRepository(session)
        products = await repo.get_all(limit=50)

    text = f"🏪 <b>محصولات ({len(products)} عدد)</b>"
    if not products:
        text += "\n\nهیچ محصولی وجود ندارد."
    await update.effective_message.reply_html(text, reply_markup=products_list_buttons(products))


# ─────────────────────────────────────────────
# جزئیات محصول
# ─────────────────────────────────────────────
@admin_only
async def admin_product_detail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    product_id = int(query.data.split(":")[3])

    async with get_db() as session:
        repo = ProductRepository(session)
        p = await repo.get_by_id(product_id)

    if not p:
        await query.edit_message_text("❌ محصول یافت نشد.")
        return

    text = (
        f"📦 <b>{p.name}</b>\n\n"
        f"💰 قیمت: {p.price:,} تومان\n"
        f"📂 دسته: {p.category}\n"
        f"🔹 وضعیت: {'✅ فعال' if p.is_active else '❌ غیرفعال'}\n"
        f"📊 موجودی: {p.available_count} | فروش: {p.sold_count}\n"
        f"🏭 نوع ارسال: {p.delivery_type}\n"
    )
    if p.description:
        text += f"\n📝 {p.description}"

    buttons = [
        [
            InlineKeyboardButton("✏️ ویرایش", callback_data=f"admin:product:edit:{p.id}"),
            InlineKeyboardButton(
                "❌ غیرفعال" if p.is_active else "✅ فعال",
                callback_data=f"admin:product:toggle:{p.id}",
            ),
        ],
        [
            InlineKeyboardButton("📦 مدیریت انبار", callback_data=f"admin:product:inventory:{p.id}"),
            InlineKeyboardButton("🗑 حذف", callback_data=f"admin:product:delete:{p.id}"),
        ],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="admin:products_list")],
    ]
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))


# ─────────────────────────────────────────────
# تغییر وضعیت فعال/غیرفعال
# ─────────────────────────────────────────────
@admin_only
async def toggle_product_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    product_id = int(query.data.split(":")[3])

    async with get_db() as session:
        repo = ProductRepository(session)
        p = await repo.get_by_id(product_id)
        if p:
            await repo.update(p, is_active=not p.is_active)
            status = "فعال" if not p.is_active else "غیرفعال"
            await query.answer(f"✅ محصول {status} شد", show_alert=True)

    # بازنمایی جزئیات
    context.args = []
    update.callback_query.data = f"admin:product:detail:{product_id}"
    await admin_product_detail(update, context)


# ─────────────────────────────────────────────
# حذف محصول
# ─────────────────────────────────────────────
@admin_only
async def delete_product(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    product_id = int(query.data.split(":")[3])
    context.user_data["delete_product_id"] = product_id

    await query.edit_message_text(
        "⚠️ آیا از حذف این محصول مطمئن هستید؟\nاین عمل قابل بازگشت نیست.",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ بله، حذف شود", callback_data=f"admin:product:confirm_delete:{product_id}"),
                InlineKeyboardButton("❌ خیر", callback_data=f"admin:product:detail:{product_id}"),
            ]
        ]),
    )


@admin_only
async def confirm_delete_product(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    product_id = int(query.data.split(":")[3])

    async with get_db() as session:
        repo = ProductRepository(session)
        p = await repo.get_by_id(product_id)
        if p:
            await repo.delete(p)

    await query.edit_message_text("✅ محصول حذف شد.")


# ─────────────────────────────────────────────
# افزودن محصول جدید — Conversation
# ─────────────────────────────────────────────
@admin_only
async def add_product_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data["new_product"] = {}
    await query.edit_message_text(
        "➕ <b>افزودن محصول جدید</b>\n\n📝 نام محصول را وارد کنید:",
        parse_mode=ParseMode.HTML,
    )
    return PROD_NAME


async def product_name_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["new_product"]["name"] = update.message.text.strip()
    await update.message.reply_text("💰 قیمت محصول را به تومان وارد کنید (فقط عدد):")
    return PROD_PRICE


async def product_price_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        price = int(update.message.text.replace(",", "").strip())
        if price <= 0:
            raise ValueError
        context.user_data["new_product"]["price"] = price
    except ValueError:
        await update.message.reply_text("❌ لطفاً یک عدد صحیح معتبر وارد کنید:")
        return PROD_PRICE

    cat_buttons = [
        [InlineKeyboardButton(cat, callback_data=f"set_cat:{cat}")]
        for cat in CATEGORIES
    ]
    await update.message.reply_text(
        "📂 دسته‌بندی محصول را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(cat_buttons),
    )
    return PROD_CATEGORY


async def product_category_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    cat = query.data.split(":", 1)[1]
    context.user_data["new_product"]["category"] = cat
    await query.edit_message_text(
        "📝 توضیحات محصول را بنویسید (یا /skip برای رد شدن):"
    )
    return PROD_DESC


async def product_desc_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    if text != "/skip":
        context.user_data["new_product"]["description"] = text.strip()
    await update.message.reply_text(
        "🖼 عکس محصول را ارسال کنید (یا /skip برای رد شدن):"
    )
    return PROD_IMAGE


async def product_image_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        context.user_data["new_product"]["image_file_id"] = file_id
    elif update.message.text == "/skip":
        pass

    await update.message.reply_text(
        "📦 آیا این محصول انبار اکانت دارد؟ (ارسال خودکار اکانت)",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ بله (با انبار)", callback_data="has_inv:yes"),
                InlineKeyboardButton("❌ خیر (دستی)", callback_data="has_inv:no"),
            ]
        ]),
    )
    return PROD_HAS_INVENTORY


async def product_inventory_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    has_inv = query.data.split(":")[1] == "yes"
    context.user_data["new_product"]["has_inventory"] = has_inv
    context.user_data["new_product"]["auto_delivery"] = has_inv
    context.user_data["new_product"]["delivery_type"] = "auto" if has_inv else "manual"

    if has_inv:
        await query.edit_message_text("👥 ظرفیت هر اکانت (تعداد نفر — معمولاً ۱):")
        return PROD_CAPACITY
    else:
        return await product_show_confirm(query, context)


async def product_capacity_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        capacity = int(update.message.text.strip())
        if capacity <= 0:
            raise ValueError
        context.user_data["new_product"]["capacity"] = capacity
    except ValueError:
        await update.message.reply_text("❌ عدد معتبر وارد کنید:")
        return PROD_CAPACITY
    return await product_show_confirm_msg(update.message, context)


async def product_show_confirm(query, context) -> int:
    p = context.user_data["new_product"]
    text = (
        f"✅ <b>تأیید اطلاعات محصول</b>\n\n"
        f"📛 نام: {p.get('name')}\n"
        f"💰 قیمت: {p.get('price', 0):,} تومان\n"
        f"📂 دسته: {p.get('category')}\n"
        f"📦 انبار: {'✅ دارد' if p.get('has_inventory') else '❌ ندارد'}\n"
    )
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ ثبت محصول", callback_data="prod_confirm:yes"),
                InlineKeyboardButton("❌ لغو", callback_data="prod_confirm:no"),
            ]
        ]),
    )
    return PROD_CONFIRM


async def product_show_confirm_msg(message, context) -> int:
    p = context.user_data["new_product"]
    text = (
        f"✅ <b>تأیید اطلاعات محصول</b>\n\n"
        f"📛 نام: {p.get('name')}\n"
        f"💰 قیمت: {p.get('price', 0):,} تومان\n"
        f"📂 دسته: {p.get('category')}\n"
        f"📦 ظرفیت: {p.get('capacity', 1)} نفر\n"
    )
    await message.reply_html(
        text,
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ ثبت محصول", callback_data="prod_confirm:yes"),
                InlineKeyboardButton("❌ لغو", callback_data="prod_confirm:no"),
            ]
        ]),
    )
    return PROD_CONFIRM


async def product_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "prod_confirm:no":
        await query.edit_message_text("❌ ثبت محصول لغو شد.")
        context.user_data.pop("new_product", None)
        return ConversationHandler.END

    p = context.user_data.pop("new_product", {})
    async with get_db() as session:
        repo = ProductRepository(session)
        product = await repo.create(
            name=p.get("name", "بدون نام"),
            price=p.get("price", 0),
            category=p.get("category", "دیگر"),
            description=p.get("description"),
            image_file_id=p.get("image_file_id"),
            has_inventory=p.get("has_inventory", False),
            auto_delivery=p.get("auto_delivery", False),
            delivery_type=p.get("delivery_type", "manual"),
            capacity=p.get("capacity", 1),
            is_active=True,
        )

    await query.edit_message_text(
        f"✅ محصول <b>{product.name}</b> با موفقیت ثبت شد!\n"
        f"🆔 شناسه: {product.id}",
        parse_mode=ParseMode.HTML,
    )
    return ConversationHandler.END


async def cancel_product_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop("new_product", None)
    await update.effective_message.reply_text("❌ عملیات لغو شد.")
    return ConversationHandler.END


def build_product_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(add_product_start, pattern="^admin:product:add$")],
        states={
            PROD_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, product_name_received)],
            PROD_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, product_price_received)],
            PROD_CATEGORY: [CallbackQueryHandler(product_category_received, pattern="^set_cat:")],
            PROD_DESC: [MessageHandler(filters.TEXT, product_desc_received)],
            PROD_IMAGE: [
                MessageHandler(filters.PHOTO, product_image_received),
                MessageHandler(filters.Regex("^/skip$"), product_image_received),
            ],
            PROD_HAS_INVENTORY: [CallbackQueryHandler(product_inventory_type, pattern="^has_inv:")],
            PROD_CAPACITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, product_capacity_received)],
            PROD_CONFIRM: [CallbackQueryHandler(product_confirm, pattern="^prod_confirm:")],
        },
        fallbacks=[
            MessageHandler(filters.COMMAND, cancel_product_add),
            CallbackQueryHandler(cancel_product_add, pattern="^admin:products_list$"),
        ],
    )


def register_product_admin_handlers(app) -> None:
    from handlers.user.start import register_start_handlers
    app.add_handler(build_product_conversation())
    app.add_handler(CallbackQueryHandler(admin_product_detail, pattern="^admin:product:detail:"))
    app.add_handler(CallbackQueryHandler(toggle_product_status, pattern="^admin:product:toggle:"))
    app.add_handler(CallbackQueryHandler(delete_product, pattern="^admin:product:delete:"))
    app.add_handler(CallbackQueryHandler(confirm_delete_product, pattern="^admin:product:confirm_delete:"))
