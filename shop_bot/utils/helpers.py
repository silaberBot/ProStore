"""
توابع کمکی
Helper utilities
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Optional


def format_price(amount: int) -> str:
    """فرمت قیمت با جداکننده هزارگان"""
    return f"{amount:,} تومان"


def validate_iranian_phone(phone: str) -> bool:
    """اعتبارسنجی شماره موبایل ایرانی"""
    phone = phone.replace(" ", "").replace("-", "")
    if phone.startswith("+98"):
        phone = "0" + phone[3:]
    if phone.startswith("98") and len(phone) == 12:
        phone = "0" + phone[2:]
    pattern = r"^09[0-9]{9}$"
    return bool(re.match(pattern, phone))


def normalize_phone(phone: str) -> str:
    """نرمال‌سازی شماره موبایل"""
    phone = phone.replace(" ", "").replace("-", "")
    if phone.startswith("+98"):
        phone = "0" + phone[3:]
    elif phone.startswith("98") and len(phone) == 12:
        phone = "0" + phone[2:]
    return phone


def format_datetime(dt: Optional[datetime], fmt: str = "%Y/%m/%d %H:%M") -> str:
    """فرمت تاریخ و زمان"""
    if not dt:
        return "—"
    try:
        import jdatetime
        jdt = jdatetime.datetime.fromgregorian(datetime=dt)
        return jdt.strftime(fmt)
    except ImportError:
        return dt.strftime(fmt)


def truncate_text(text: str, max_length: int = 50) -> str:
    """کوتاه کردن متن طولانی"""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def escape_html(text: str) -> str:
    """Escape HTML characters"""
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
    )


def parse_callback_data(data: str) -> tuple[str, ...]:
    """تجزیه callback data به اجزا"""
    return tuple(data.split(":"))


def generate_stars_invoice_payload(order_id: int) -> str:
    return f"stars_order_{order_id}"


def build_account_message(username: str, password: str, extra_info: Optional[str] = None) -> str:
    """ساخت پیام اطلاعات اکانت"""
    msg = f"👤 <b>نام کاربری:</b> <code>{username}</code>\n"
    msg += f"🔑 <b>رمز عبور:</b> <code>{password}</code>"
    if extra_info:
        msg += f"\n📝 <b>اطلاعات بیشتر:</b>\n{extra_info}"
    return msg
