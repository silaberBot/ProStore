"""
کیبوردهای ربات
All keyboards (Reply and Inline) for the bot
"""
from __future__ import annotations

from typing import List, Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton

# ─────────────────────────────────────────────
# منوی اصلی کاربر (Reply Keyboard)
# ─────────────────────────────────────────────
def main_menu_keyboard() -> ReplyKeyboardMarkup:
    buttons = [
        ["🛍 فروشگاه", "👤 پروفایل من"],
        ["💰 کیف پول", "🔗 دعوت از دوستان"],
        ["🎫 پشتیبانی", "📚 آموزش‌ها"],
    ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True, one_time_keyboard=False)


def admin_main_menu() -> ReplyKeyboardMarkup:
    buttons = [
        ["📊 داشبورد", "📦 سفارشات"],
        ["🏪 محصولات", "👥 کاربران"],
        ["💳 پرداخت‌ها", "🎟 تخفیف‌ها"],
        ["🎫 تیکت‌ها", "⚙️ تنظیمات"],
        ["📢 پیام همگانی", "📁 بکاپ"],
    ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)


# ─────────────────────────────────────────────
# فروشگاه
# ─────────────────────────────────────────────
def categories_keyboard(categories: List[str]) -> InlineKeyboardMarkup:
    buttons = [[InlineKeyboardButton(cat, callback_data=f"cat:{cat}")] for cat in categories]
    buttons.append([InlineKeyboardButton("🔙 بازگشت", callback_data="back:main")])
    return InlineKeyboardMarkup(buttons)


def products_keyboard(products: list, category: str) -> InlineKeyboardMarkup:
    buttons = []
    for p in products:
        status = "✅" if p.is_available else "❌"
        buttons.append([
            InlineKeyboardButton(
                f"{status} {p.name} | {p.price:,} تومان",
                callback_data=f"product:{p.id}"
            )
        ])
    buttons.append([InlineKeyboardButton("🔙 دسته‌بندی‌ها", callback_data="back:categories")])
    return InlineKeyboardMarkup(buttons)


def product_detail_keyboard(product_id: int, is_available: bool) -> InlineKeyboardMarkup:
    buttons = []
    if is_available:
        buttons.append([InlineKeyboardButton("🛒 خرید", callback_data=f"buy:{product_id}")])
    else:
        buttons.append([InlineKeyboardButton("❌ ناموجود", callback_data="unavailable")])
    buttons.append([InlineKeyboardButton("🔙 بازگشت", callback_data=f"back:products")])
    return InlineKeyboardMarkup(buttons)


def payment_methods_keyboard(order_id: int, wallet_balance: int, amount: int) -> InlineKeyboardMarkup:
    buttons = []
    if wallet_balance >= amount:
        buttons.append([InlineKeyboardButton(f"💵 کیف پول ({wallet_balance:,} تومان)", callback_data=f"pay:wallet:{order_id}")])
    buttons.append([InlineKeyboardButton("🏦 زرین‌پال", callback_data=f"pay:zarinpal:{order_id}")])
    buttons.append([InlineKeyboardButton("💳 آیدی‌پی", callback_data=f"pay:idpay:{order_id}")])
    buttons.append([InlineKeyboardButton("💎 Telegram Stars", callback_data=f"pay:stars:{order_id}")])
    buttons.append([InlineKeyboardButton("🪙 رمزارز (USDT)", callback_data=f"pay:crypto:{order_id}")])
    buttons.append([InlineKeyboardButton("❌ لغو", callback_data=f"cancel_order:{order_id}")])
    return InlineKeyboardMarkup(buttons)


# ─────────────────────────────────────────────
# پروفایل
# ─────────────────────────────────────────────
def profile_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("📦 سفارشات من", callback_data="profile:orders")],
        [InlineKeyboardButton("📱 تأیید شماره موبایل", callback_data="profile:verify_phone")],
    ]
    return InlineKeyboardMarkup(buttons)


def orders_list_keyboard(orders: list) -> InlineKeyboardMarkup:
    buttons = []
    for o in orders:
        status_icon = {"completed": "✅", "pending": "⏳", "cancelled": "❌", "waiting": "🔄"}.get(o.status, "❓")
        buttons.append([
            InlineKeyboardButton(
                f"{status_icon} #{o.order_number} — {o.final_amount:,} تومان",
                callback_data=f"order_detail:{o.id}"
            )
        ])
    buttons.append([InlineKeyboardButton("🔙 بازگشت", callback_data="back:profile")])
    return InlineKeyboardMarkup(buttons)


# ─────────────────────────────────────────────
# کیف پول
# ─────────────────────────────────────────────
def wallet_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("➕ شارژ کیف پول", callback_data="wallet:charge")],
        [InlineKeyboardButton("📋 تاریخچه تراکنش‌ها", callback_data="wallet:history")],
    ]
    return InlineKeyboardMarkup(buttons)


def wallet_charge_amounts_keyboard() -> InlineKeyboardMarkup:
    amounts = [10000, 20000, 50000, 100000, 200000, 500000]
    buttons = []
    for i in range(0, len(amounts), 2):
        row = []
        for amt in amounts[i:i+2]:
            row.append(InlineKeyboardButton(f"{amt:,} تومان", callback_data=f"charge_amount:{amt}"))
        buttons.append(row)
    buttons.append([InlineKeyboardButton("✏️ مبلغ دلخواه", callback_data="charge_amount:custom")])
    buttons.append([InlineKeyboardButton("🔙 بازگشت", callback_data="back:wallet")])
    return InlineKeyboardMarkup(buttons)


# ─────────────────────────────────────────────
# پشتیبانی / تیکت
# ─────────────────────────────────────────────
def support_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("➕ تیکت جدید", callback_data="ticket:new")],
        [InlineKeyboardButton("📋 تیکت‌های من", callback_data="ticket:list")],
    ]
    return InlineKeyboardMarkup(buttons)


def ticket_detail_keyboard(ticket_id: int, status: str) -> InlineKeyboardMarkup:
    buttons = []
    if status != "closed":
        buttons.append([InlineKeyboardButton("✉️ پاسخ دادن", callback_data=f"ticket:reply:{ticket_id}")])
        buttons.append([InlineKeyboardButton("✅ بستن تیکت", callback_data=f"ticket:close:{ticket_id}")])
    buttons.append([InlineKeyboardButton("🔙 بازگشت", callback_data="ticket:list")])
    return InlineKeyboardMarkup(buttons)


# ─────────────────────────────────────────────
# ادمین
# ─────────────────────────────────────────────
def admin_order_actions(order_id: int, status: str) -> InlineKeyboardMarkup:
    buttons = []
    if status == "waiting":
        buttons.append([
            InlineKeyboardButton("✅ تأیید و ارسال", callback_data=f"admin:order:deliver:{order_id}"),
            InlineKeyboardButton("❌ لغو", callback_data=f"admin:order:cancel:{order_id}"),
        ])
    buttons.append([InlineKeyboardButton("🔙 بازگشت", callback_data="admin:orders")])
    return InlineKeyboardMarkup(buttons)


def admin_ticket_actions(ticket_id: int) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("✉️ پاسخ دادن", callback_data=f"admin:ticket:reply:{ticket_id}")],
        [InlineKeyboardButton("✅ بستن", callback_data=f"admin:ticket:close:{ticket_id}")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="admin:tickets")],
    ]
    return InlineKeyboardMarkup(buttons)


def admin_user_actions(user_id: int, is_banned: bool) -> InlineKeyboardMarkup:
    ban_text = "✅ رفع مسدودی" if is_banned else "🚫 مسدود کردن"
    buttons = [
        [InlineKeyboardButton(ban_text, callback_data=f"admin:user:ban_toggle:{user_id}")],
        [InlineKeyboardButton("💰 شارژ کیف پول", callback_data=f"admin:user:charge:{user_id}")],
        [InlineKeyboardButton("📦 سفارشات", callback_data=f"admin:user:orders:{user_id}")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="admin:users")],
    ]
    return InlineKeyboardMarkup(buttons)


def admin_product_actions(product_id: int) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("✏️ ویرایش", callback_data=f"admin:product:edit:{product_id}")],
        [InlineKeyboardButton("📦 مدیریت انبار", callback_data=f"admin:product:inventory:{product_id}")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="admin:products")],
    ]
    return InlineKeyboardMarkup(buttons)


def confirm_keyboard(yes_data: str, no_data: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ بله", callback_data=yes_data),
            InlineKeyboardButton("❌ خیر", callback_data=no_data),
        ]
    ])


def back_keyboard(callback: str = "back:main") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data=callback)]])
