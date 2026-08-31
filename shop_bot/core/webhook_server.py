"""
Webhook Callback Server برای بازگشت درگاه‌های پرداخت
Payment gateway callback server using aiohttp
"""
from __future__ import annotations

import logging
from typing import Optional

from aiohttp import web

logger = logging.getLogger(__name__)

_bot = None
_app: Optional[web.Application] = None


def set_bot(bot) -> None:
    global _bot
    _bot = bot


# ─────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────
async def zarinpal_verify_handler(request: web.Request) -> web.Response:
    """بازگشت کاربر از درگاه زرین‌پال"""
    try:
        authority = request.query.get("Authority", "")
        status = request.query.get("Status", "")

        if not authority:
            return web.Response(text="Bad Request", status=400)

        from core.database import get_db
        from repositories.order_repository import PaymentRepository

        async with get_db() as session:
            pay_repo = PaymentRepository(session)
            payment = await pay_repo.get_by_authority(authority)

            if not payment:
                logger.warning(f"Zarinpal callback: payment not found for authority {authority}")
                return web.Response(text="Payment not found", status=404)

            if status != "OK":
                await pay_repo.update(payment, status="failed")
                if _bot:
                    from services.notification_service import NotificationService
                    notif = NotificationService(_bot)
                    await notif.payment_failed(payment.user_id, str(payment.order_id or ""))
                return web.Response(
                    text="<html><body><h2>❌ پرداخت ناموفق</h2><p>به ربات بازگردید.</p></body></html>",
                    content_type="text/html",
                )

            # تأیید پرداخت
            from services.payment_service import PaymentService
            pay_service = PaymentService(session)
            success, ref_id = await pay_service.zarinpal_verify(authority, payment.amount)

            if success and payment.order_id:
                # تحویل اکانت
                from services.order_service import OrderService
                from services.notification_service import NotificationService
                notif = NotificationService(_bot)
                order_service = OrderService(session)
                order = await order_service.order_repo.get_by_id(payment.order_id)

                if order:
                    await order_service.order_repo.update(
                        order, payment_status="success", payment_method="zarinpal", status="waiting"
                    )
                    ok, msg, account = await order_service.deliver_account(payment.order_id)
                    if ok and account and _bot:
                        await notif.account_delivered(
                            payment.user_id,
                            order.order_number,
                            account["account_text"],
                            "محصول",
                        )
                    else:
                        await notif.manual_delivery_pending(payment.user_id, order.order_number)

                return web.Response(
                    text="<html><body><h2>✅ پرداخت موفق!</h2><p>اکانت به ربات ارسال شد.</p></body></html>",
                    content_type="text/html",
                )

    except Exception as e:
        logger.error(f"Zarinpal callback error: {e}")

    return web.Response(text="Error", status=500)


async def idpay_verify_handler(request: web.Request) -> web.Response:
    """Callback آیدی‌پی"""
    try:
        data = await request.post()
        status = data.get("status", "")
        order_id = data.get("order_id", "")
        payment_id = data.get("id", "")

        if status not in ("10", "200"):
            return web.Response(text="FAILED", status=200)

        from core.database import get_db
        from repositories.order_repository import PaymentRepository

        async with get_db() as session:
            pay_repo = PaymentRepository(session)
            payment = await pay_repo.get_by_authority(payment_id)
            if payment:
                await pay_repo.update(payment, status="success", reference_id=payment_id)
                if payment.order_id:
                    from services.order_service import OrderService
                    order_service = OrderService(session)
                    order = await order_service.order_repo.get_by_id(payment.order_id)
                    if order:
                        await order_service.order_repo.update(
                            order, payment_status="success", payment_method="idpay", status="waiting"
                        )

        return web.Response(text="OK", status=200)
    except Exception as e:
        logger.error(f"IDPay callback error: {e}")
        return web.Response(text="Error", status=500)


async def nowpayments_ipn_handler(request: web.Request) -> web.Response:
    """IPN از NOWPayments (رمزارز)"""
    try:
        data = await request.json()
        payment_status = data.get("payment_status", "")
        payment_id = str(data.get("payment_id", ""))

        if payment_status in ("finished", "confirmed"):
            from core.database import get_db
            from repositories.order_repository import PaymentRepository

            async with get_db() as session:
                pay_repo = PaymentRepository(session)
                payment = await pay_repo.get_by_authority(payment_id)
                if payment and payment.status != "success":
                    await pay_repo.update(payment, status="success", reference_id=payment_id)
                    # شارژ کیف پول
                    from services.payment_service import PaymentService
                    pay_service = PaymentService(session)
                    await pay_service.confirm_deposit(payment.id, ref_id=payment_id)

                    if _bot:
                        from services.notification_service import NotificationService
                        notif = NotificationService(_bot)
                        await notif.wallet_charged(payment.user_id, payment.amount, 0)

        return web.Response(text="OK", status=200)
    except Exception as e:
        logger.error(f"NOWPayments IPN error: {e}")
        return web.Response(text="Error", status=500)


async def health_check(request: web.Request) -> web.Response:
    """Health check endpoint"""
    return web.json_response({"status": "ok", "bot": "shapiyar"})


# ─────────────────────────────────────────────
# App factory
# ─────────────────────────────────────────────
def create_webhook_app() -> web.Application:
    global _app
    app = web.Application()
    app.router.add_get("/health", health_check)
    app.router.add_get("/payment/zarinpal/verify", zarinpal_verify_handler)
    app.router.add_post("/payment/idpay/verify", idpay_verify_handler)
    app.router.add_post("/payment/nowpayments/ipn", nowpayments_ipn_handler)
    _app = app
    return app


async def start_webhook_server(host: str = "0.0.0.0", port: int = 8080) -> None:
    """راه‌اندازی سرور webhook به صورت async"""
    app = create_webhook_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    logger.info(f"✅ Webhook server started on {host}:{port}")
