"""
سرویس نوتیفیکیشن — 25+ نوع پیام
Notification service for all bot messages
"""
from __future__ import annotations

import logging
from typing import Optional

from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import TelegramError

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, bot: Bot):
        self.bot = bot

    async def _send(self, chat_id: int, text: str, **kwargs) -> bool:
        try:
            await self.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=ParseMode.HTML,
                **kwargs,
            )
            return True
        except TelegramError as e:
            logger.warning(f"Failed to send notification to {chat_id}: {e}")
            return False

    # ─────────────────────────────────────────
    # کاربر — خرید
    # ─────────────────────────────────────────
    async def order_created(self, user_id: int, order_number: str, amount: int) -> bool:
        text = (
            f"🛍 <b>سفارش جدید ثبت شد</b>\n\n"
            f"📋 شماره سفارش: <code>{order_number}</code>\n"
            f"💰 مبلغ: <b>{amount:,} تومان</b>\n\n"
            f"لطفاً پرداخت را انجام دهید."
        )
        return await self._send(user_id, text)

    async def payment_success(self, user_id: int, order_number: str, amount: int) -> bool:
        text = (
            f"✅ <b>پرداخت موفق</b>\n\n"
            f"📋 سفارش: <code>{order_number}</code>\n"
            f"💳 مبلغ: <b>{amount:,} تومان</b>\n\n"
            f"سفارش شما در حال پردازش است..."
        )
        return await self._send(user_id, text)

    async def payment_failed(self, user_id: int, order_number: str) -> bool:
        text = (
            f"❌ <b>پرداخت ناموفق</b>\n\n"
            f"📋 سفارش: <code>{order_number}</code>\n\n"
            f"در صورت کسر وجه، مبلغ ظرف ۷۲ ساعت به حساب شما بازمی‌گردد."
        )
        return await self._send(user_id, text)

    async def account_delivered(
        self,
        user_id: int,
        order_number: str,
        account_text: str,
        product_name: str,
    ) -> bool:
        text = (
            f"🎉 <b>اکانت شما آماده است!</b>\n\n"
            f"📦 محصول: <b>{product_name}</b>\n"
            f"📋 سفارش: <code>{order_number}</code>\n\n"
            f"<b>اطلاعات اکانت:</b>\n"
            f"<code>{account_text}</code>\n\n"
            f"⚠️ این اطلاعات را در جای امنی ذخیره کنید."
        )
        return await self._send(user_id, text)

    async def manual_delivery_pending(self, user_id: int, order_number: str) -> bool:
        text = (
            f"⏳ <b>سفارش شما در صف ارسال است</b>\n\n"
            f"📋 سفارش: <code>{order_number}</code>\n\n"
            f"اکانت شما به‌زودی توسط تیم پشتیبانی ارسال می‌شود.\n"
            f"حداکثر زمان: ۲۴ ساعت"
        )
        return await self._send(user_id, text)

    # ─────────────────────────────────────────
    # کاربر — کیف پول
    # ─────────────────────────────────────────
    async def wallet_charged(self, user_id: int, amount: int, balance: int) -> bool:
        text = (
            f"💰 <b>کیف پول شارژ شد</b>\n\n"
            f"➕ مبلغ شارژ: <b>{amount:,} تومان</b>\n"
            f"💵 موجودی فعلی: <b>{balance:,} تومان</b>"
        )
        return await self._send(user_id, text)

    async def wallet_low_balance(self, user_id: int, needed: int, balance: int) -> bool:
        diff = needed - balance
        text = (
            f"⚠️ <b>موجودی ناکافی</b>\n\n"
            f"💵 موجودی: <b>{balance:,} تومان</b>\n"
            f"💳 مبلغ مورد نیاز: <b>{needed:,} تومان</b>\n"
            f"➖ کمبود: <b>{diff:,} تومان</b>"
        )
        return await self._send(user_id, text)

    # ─────────────────────────────────────────
    # کاربر — رفرال
    # ─────────────────────────────────────────
    async def referral_success(self, referrer_id: int, reward_amount: int, referred_name: str) -> bool:
        text = (
            f"🎁 <b>دعوت موفق!</b>\n\n"
            f"👤 کاربر <b>{referred_name}</b> با لینک شما وارد شد\n"
            f"🎉 پاداش: <b>{reward_amount:,} تومان</b> به کیف پول شما افزوده شد!"
        )
        return await self._send(referrer_id, text)

    async def referral_pending(self, referrer_id: int, referred_name: str) -> bool:
        text = (
            f"👤 <b>دعوت جدید!</b>\n\n"
            f"کاربر <b>{referred_name}</b> با لینک شما وارد ربات شد.\n"
            f"پس از تأیید شرایط، پاداش دریافت خواهید کرد."
        )
        return await self._send(referrer_id, text)

    # ─────────────────────────────────────────
    # کاربر — اشتراک
    # ─────────────────────────────────────────
    async def subscription_expiring(self, user_id: int, product_name: str, days: int) -> bool:
        text = (
            f"⏰ <b>یادآوری انقضای اشتراک</b>\n\n"
            f"📦 محصول: <b>{product_name}</b>\n"
            f"⚠️ اشتراک شما <b>{days} روز دیگر</b> منقضی می‌شود.\n\n"
            f"برای تمدید از منوی خرید اقدام کنید."
        )
        return await self._send(user_id, text)

    # ─────────────────────────────────────────
    # کاربر — تیکت
    # ─────────────────────────────────────────
    async def ticket_created(self, user_id: int, ticket_id: int, subject: str) -> bool:
        text = (
            f"🎫 <b>تیکت ثبت شد</b>\n\n"
            f"🔢 شماره تیکت: <code>#{ticket_id}</code>\n"
            f"📝 موضوع: {subject}\n\n"
            f"تیم پشتیبانی به‌زودی پاسخ خواهد داد."
        )
        return await self._send(user_id, text)

    async def ticket_replied(self, user_id: int, ticket_id: int, reply: str) -> bool:
        text = (
            f"💬 <b>پاسخ تیکت #{ticket_id}</b>\n\n"
            f"{reply}"
        )
        return await self._send(user_id, text)

    async def ticket_closed(self, user_id: int, ticket_id: int) -> bool:
        text = f"✅ تیکت <code>#{ticket_id}</code> بسته شد."
        return await self._send(user_id, text)

    # ─────────────────────────────────────────
    # ادمین — اعلان‌ها
    # ─────────────────────────────────────────
    async def admin_new_order(self, admin_id: int, order_number: str, user_name: str, amount: int) -> bool:
        text = (
            f"🛒 <b>سفارش جدید!</b>\n\n"
            f"📋 شماره: <code>{order_number}</code>\n"
            f"👤 کاربر: {user_name}\n"
            f"💰 مبلغ: <b>{amount:,} تومان</b>"
        )
        return await self._send(admin_id, text)

    async def admin_new_ticket(self, admin_id: int, ticket_id: int, user_name: str, subject: str) -> bool:
        text = (
            f"🎫 <b>تیکت جدید!</b>\n\n"
            f"🔢 شماره: <code>#{ticket_id}</code>\n"
            f"👤 کاربر: {user_name}\n"
            f"📝 موضوع: {subject}"
        )
        return await self._send(admin_id, text)

    async def admin_low_inventory(self, admin_id: int, product_name: str, count: int) -> bool:
        text = (
            f"⚠️ <b>هشدار کمبود انبار!</b>\n\n"
            f"📦 محصول: <b>{product_name}</b>\n"
            f"📊 موجودی: <b>{count}</b> اکانت"
        )
        return await self._send(admin_id, text)

    async def admin_payment_received(self, admin_id: int, user_name: str, amount: int, method: str) -> bool:
        text = (
            f"💳 <b>پرداخت جدید!</b>\n\n"
            f"👤 کاربر: {user_name}\n"
            f"💰 مبلغ: <b>{amount:,} تومان</b>\n"
            f"🏦 درگاه: {method}"
        )
        return await self._send(admin_id, text)

    # ─────────────────────────────────────────
    # Broadcast
    # ─────────────────────────────────────────
    async def broadcast(self, user_ids: list, text: str) -> tuple[int, int]:
        """ارسال پیام همگانی"""
        success, failed = 0, 0
        for uid in user_ids:
            ok = await self._send(uid, text)
            if ok:
                success += 1
            else:
                failed += 1
        return success, failed
