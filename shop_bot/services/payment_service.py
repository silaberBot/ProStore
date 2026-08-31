"""
سرویس پرداخت — پشتیبانی از 10+ درگاه
Payment service with multiple gateway support
"""
from __future__ import annotations

import logging
from typing import Optional, Tuple

import aiohttp
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from repositories.order_repository import PaymentRepository, WalletRepository

logger = logging.getLogger(__name__)

GATEWAY_NAMES = {
    "zarinpal":   "زرین‌پال",
    "idpay":      "آیدی‌پی",
    "wallet":     "کیف پول",
    "stars":      "Telegram Stars",
    "nowpayments":"رمزارز (NOWPayments)",
    "wallet_addr": "واریز مستقیم",
}


class PaymentService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.payment_repo = PaymentRepository(session)
        self.wallet_repo = WalletRepository(session)

    # ─────────────────────────────────────────
    # ۱. زرین‌پال
    # ─────────────────────────────────────────
    async def zarinpal_request(
        self, user_id: int, amount: int, description: str, order_id: Optional[int] = None
    ) -> Tuple[bool, str, Optional[str]]:
        """درخواست پرداخت زرین‌پال → (success, msg, authority)"""
        if not settings.ZARINPAL_MERCHANT_ID:
            return False, "درگاه زرین‌پال تنظیم نشده", None

        callback = f"{settings.BASE_URL}/payment/zarinpal/verify"
        payload = {
            "merchant_id": settings.ZARINPAL_MERCHANT_ID,
            "amount": amount * 10,  # ریال
            "description": description,
            "callback_url": callback,
        }
        try:
            async with aiohttp.ClientSession() as http:
                async with http.post(
                    "https://api.zarinpal.com/pg/v4/payment/request.json",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    data = await resp.json()
            if data.get("data", {}).get("code") == 100:
                authority = data["data"]["authority"]
                payment = await self.payment_repo.create(
                    user_id=user_id,
                    order_id=order_id,
                    amount=amount,
                    type="purchase",
                    method="zarinpal",
                    status="pending",
                    authority=authority,
                )
                url = f"https://www.zarinpal.com/pg/StartPay/{authority}"
                return True, url, authority
        except Exception as e:
            logger.error(f"Zarinpal request error: {e}")
        return False, "خطا در اتصال به درگاه", None

    async def zarinpal_verify(self, authority: str, amount: int) -> Tuple[bool, str]:
        """تأیید پرداخت زرین‌پال"""
        payload = {
            "merchant_id": settings.ZARINPAL_MERCHANT_ID,
            "amount": amount * 10,
            "authority": authority,
        }
        try:
            async with aiohttp.ClientSession() as http:
                async with http.post(
                    "https://api.zarinpal.com/pg/v4/payment/verify.json",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    data = await resp.json()
            code = data.get("data", {}).get("code")
            if code in (100, 101):
                ref_id = str(data["data"].get("ref_id", ""))
                payment = await self.payment_repo.get_by_authority(authority)
                if payment:
                    await self.payment_repo.update(
                        payment, status="success", reference_id=ref_id
                    )
                return True, ref_id
        except Exception as e:
            logger.error(f"Zarinpal verify error: {e}")
        return False, "پرداخت ناموفق"

    # ─────────────────────────────────────────
    # ۲. IDPay
    # ─────────────────────────────────────────
    async def idpay_request(
        self, user_id: int, amount: int, description: str, order_id: Optional[int] = None
    ) -> Tuple[bool, str, Optional[str]]:
        if not settings.IDPAY_API_KEY:
            return False, "درگاه آیدی‌پی تنظیم نشده", None

        callback = f"{settings.BASE_URL}/payment/idpay/verify"
        payload = {
            "order_id": str(order_id or "wallet"),
            "amount": amount * 10,
            "desc": description,
            "callback": callback,
        }
        headers = {"X-API-KEY": settings.IDPAY_API_KEY, "X-SANDBOX": "0"}
        try:
            async with aiohttp.ClientSession() as http:
                async with http.post(
                    "https://api.idpay.ir/v1.1/payment",
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    data = await resp.json()
            if data.get("id"):
                payment = await self.payment_repo.create(
                    user_id=user_id,
                    order_id=order_id,
                    amount=amount,
                    type="purchase",
                    method="idpay",
                    status="pending",
                    authority=data["id"],
                )
                return True, data.get("link", ""), data["id"]
        except Exception as e:
            logger.error(f"IDPay request error: {e}")
        return False, "خطا در اتصال به درگاه", None

    # ─────────────────────────────────────────
    # ۳. شارژ کیف پول (stub — درگاه‌های دیگر)
    # ─────────────────────────────────────────
    async def create_wallet_deposit(
        self, user_id: int, amount: int, method: str
    ) -> Tuple[bool, str]:
        """ایجاد رکورد شارژ کیف پول (بعد از تأیید درگاه، موجودی شارژ می‌شه)"""
        payment = await self.payment_repo.create(
            user_id=user_id,
            amount=amount,
            type="deposit",
            method=method,
            status="pending",
        )
        return True, f"درخواست شارژ {amount:,} تومانی ایجاد شد"

    async def confirm_deposit(self, payment_id: int, ref_id: str = "") -> Tuple[bool, str]:
        """تأیید و شارژ کیف پول توسط ادمین یا درگاه"""
        payment = await self.payment_repo.get_by_id(payment_id)
        if not payment:
            return False, "تراکنش یافت نشد"
        if payment.status == "success":
            return False, "این تراکنش قبلاً تأیید شده"

        await self.payment_repo.update(payment, status="success", reference_id=ref_id)
        await self.wallet_repo.add_balance(payment.user_id, payment.amount)

        # بروزرسانی موجودی user نیز
        from repositories.user_repository import UserRepository
        user_repo = UserRepository(self.session)
        user = await user_repo.get_by_telegram_id(payment.user_id)
        if user:
            user.wallet_balance += payment.amount
            self.session.add(user)

        return True, "کیف پول شارژ شد"

    # ─────────────────────────────────────────
    # ۴. NOWPayments (Crypto)
    # ─────────────────────────────────────────
    async def nowpayments_create(
        self, user_id: int, amount_usd: float, order_id: Optional[int] = None
    ) -> Tuple[bool, str, Optional[str]]:
        if not settings.NOWPAYMENTS_API_KEY:
            return False, "درگاه رمزارز تنظیم نشده", None

        callback = f"{settings.BASE_URL}/payment/nowpayments/ipn"
        payload = {
            "price_amount": amount_usd,
            "price_currency": "usd",
            "pay_currency": "usdttrc20",
            "order_id": str(order_id or "wallet"),
            "order_description": "Shapiyar Bot",
            "ipn_callback_url": callback,
        }
        headers = {"x-api-key": settings.NOWPAYMENTS_API_KEY}
        try:
            async with aiohttp.ClientSession() as http:
                async with http.post(
                    "https://api.nowpayments.io/v1/payment",
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    data = await resp.json()
            if data.get("payment_id"):
                await self.payment_repo.create(
                    user_id=user_id,
                    order_id=order_id,
                    amount=int(amount_usd),
                    type="deposit",
                    method="nowpayments",
                    status="pending",
                    authority=str(data["payment_id"]),
                )
                pay_address = data.get("pay_address", "")
                pay_amount = data.get("pay_amount", 0)
                return True, f"آدرس پرداخت: {pay_address}\nمقدار: {pay_amount} USDT", str(data["payment_id"])
        except Exception as e:
            logger.error(f"NOWPayments error: {e}")
        return False, "خطا در اتصال به درگاه رمزارز", None
