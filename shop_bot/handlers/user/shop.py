"""
هندلر فروشگاه (اصلاح‌شده — هندلرهای بازگشت اضافه شد)
"""
from __future__ import annotations
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode
from telegram.ext import CallbackQueryHandler, ContextTypes, MessageHandler, filters
from core.database import get_db
from repositories.product_repository import ProductRepository
from repositories.order_repository import WalletRepository
from services.order_service import OrderService
from services.notification_service import NotificationService
from utils.keyboards import (
    categories_keyboard, products_keyboard, product_detail_keyboard,
    payment_methods_keyboard, back_keyboard,
)

logger = logging.getLogger(__name__)


async def shop_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    msg = update.effective_message
    async with get_db() as session:
        product_repo = ProductRepository(session)
        categories = await product_repo.get_categories()
    if not categories:
        text = "❌ در حال حاضر محصولی موجود نیست."
        if query:
            await query.answer()
            await query.edit_message_text(text)
        else:
            await msg.reply_text(text)
        return
    text = "🛍 <b>فروشگاه شاپیار</b>\n\nدسته‌بندی مورد نظر را انتخاب کنید:"
    kb = categories_keyboard(categories)
    if query:
        await query.answer()
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        await msg.reply_html(text, reply_markup=kb)


async def show_category_products(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    category = query.data.split(":", 1)[1]
    context.user_data["current_category"] = category
    async with get_db() as session:
        product_repo = ProductRepository(session)
        products = await product_repo.get_by_category(category)
    if not products:
        await query.edit_message_text(
            f"❌ محصولی در دسته‌بندی «{category}» موجود نیست.",
            reply_markup=back_keyboard("back:categories"),
        )
        return
    text = f"📂 <b>{category}</b>\n\nمحصول مورد نظر را انتخاب کنید:"
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=products_keyboard(products, category))


async def show_product_detail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    product_id = int(query.data.split(":")[1])
    async with get_db() as session:
        product_repo = ProductRepository(session)
        product = await product_repo.get_by_id(product_id)
    if not product:
        await query.edit_message_text("❌ محصول یافت نشد.")
        return
    status_text = "✅ موجود" if product.is_available else "❌ ناموجود"
    stock_text = f"\n📊 موجودی: {product.available_count} عدد" if product.has_inventory else ""
    text = (
        f"📦 <b>{product.name}</b>\n\n"
        f"💰 قیمت: <b>{product.price:,} تومان</b>\n"
        f"📁 دسته‌بندی: {product.category}\n"
        f"🔹 وضعیت: {status_text}{stock_text}\n"
    )
    if product.description:
        text += f"\n📝 توضیحات:\n{product.description}"
    kb = product_detail_keyboard(product_id, product.is_available)
    if product.image_file_id:
        try:
            await query.message.delete()
            await context.bot.send_photo(
                chat_id=query.from_user.id, photo=product.image_file_id,
                caption=text, parse_mode=ParseMode.HTML, reply_markup=kb,
            )
            return
        except Exception:
            pass
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


async def back_to_products(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """بازگشت از جزئیات محصول به لیست محصولات دسته"""
    query = update.callback_query
    await query.answer()
    category = context.user_data.get("current_category", "")
    if not category:
        await shop_menu(update, context)
        return
    async with get_db() as session:
        product_repo = ProductRepository(session)
        products = await product_repo.get_by_category(category)
    if not products:
        await shop_menu(update, context)
        return
    text = f"📂 <b>{category}</b>\n\nمحصول مورد نظر را انتخاب کنید:"
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=products_keyboard(products, category))


async def unavailable_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer("❌ این محصول در حال حاضر ناموجود است.", show_alert=True)


async def start_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    product_id = int(query.data.split(":")[1])
    user_id = query.from_user.id
    async with get_db() as session:
        order_service = OrderService(session)
        wallet_repo = WalletRepository(session)
        success, msg, order = await order_service.create_order(user_id=user_id, product_id=product_id)
        if not success or not order:
            await query.edit_message_text(f"❌ خطا: {msg}")
            return
        wallet = await wallet_repo.get_or_create(user_id)
        context.user_data["current_order_id"] = order.id
    text = (
        f"🛒 <b>خرید محصول</b>\n\n"
        f"📋 شماره سفارش: <code>{order.order_number}</code>\n"
        f"💰 مبلغ: <b>{order.final_amount:,} تومان</b>\n\n"
        f"روش پرداخت را انتخاب کنید:"
    )
    kb = payment_methods_keyboard(order.id, wallet.balance, order.final_amount)
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


async def process_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    parts = query.data.split(":")
    method = parts[1]
    order_id = int(parts[2])
    user_id = query.from_user.id
    async with get_db() as session:
        order_service = OrderService(session)
        notif = NotificationService(context.bot)
        if method == "wallet":
            success, msg = await order_service.pay_with_wallet(order_id, user_id)
            if success:
                order = await order_service.order_repo.get_by_id(order_id)
                delivered, d_msg, account = await order_service.deliver_account(order_id)
                if delivered and account:
                    await query.edit_message_text(
                        f"✅ پرداخت موفق!\n\n🎉 <b>اکانت شما:</b>\n<code>{account['account_text']}</code>",
                        parse_mode=ParseMode.HTML,
                    )
                else:
                    await query.edit_message_text("✅ پرداخت موفق!\n⏳ اکانت شما به‌زودی ارسال می‌شود.")
                    await notif.manual_delivery_pending(user_id, order.order_number)
            else:
                await query.edit_message_text(f"❌ {msg}")
        elif method == "zarinpal":
            from services.payment_service import PaymentService
            pay_service = PaymentService(session)
            order = await order_service.order_repo.get_by_id(order_id)
            ok, url, authority = await pay_service.zarinpal_request(
                user_id=user_id, amount=order.final_amount,
                description=f"سفارش {order.order_number}", order_id=order_id,
            )
            if ok:
                kb = InlineKeyboardMarkup([[InlineKeyboardButton("💳 پرداخت از طریق درگاه", url=url)]])
                await query.edit_message_text(
                    f"🏦 برای پرداخت روی دکمه زیر کلیک کنید:\n\n💰 مبلغ: <b>{order.final_amount:,} تومان</b>",
                    parse_mode=ParseMode.HTML, reply_markup=kb,
                )
            else:
                await query.edit_message_text(f"❌ {url}")
        else:
            await query.edit_message_text(f"⚙️ درگاه «{method}» در حال پیاده‌سازی است.\nلطفاً روش دیگری انتخاب کنید.")


async def cancel_order_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    order_id = int(query.data.split(":")[1])
    async with get_db() as session:
        order_service = OrderService(session)
        success, msg = await order_service.cancel_order(order_id)
        await query.edit_message_text(f"{'✅' if success else '❌'} {msg}")


def register_shop_handlers(app) -> None:
    app.add_handler(MessageHandler(filters.Regex("^🛍 فروشگاه$"), shop_menu))
    app.add_handler(CallbackQueryHandler(shop_menu, pattern="^back:categories$"))
    app.add_handler(CallbackQueryHandler(shop_menu, pattern="^back:main$"))
    app.add_handler(CallbackQueryHandler(back_to_products, pattern="^back:products$"))
    app.add_handler(CallbackQueryHandler(unavailable_handler, pattern="^unavailable$"))
    app.add_handler(CallbackQueryHandler(show_category_products, pattern="^cat:"))
    app.add_handler(CallbackQueryHandler(show_product_detail, pattern="^product:"))
    app.add_handler(CallbackQueryHandler(start_purchase, pattern="^buy:"))
    app.add_handler(CallbackQueryHandler(process_payment, pattern="^pay:"))
    app.add_handler(CallbackQueryHandler(cancel_order_callback, pattern="^cancel_order:"))
