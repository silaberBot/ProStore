"""
سرویس مدیریت سفارشات
Order service — handles the full order lifecycle
"""
from __future__ import annotations

import logging
from typing import Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from models.order import Order, OrderItem
from models.inventory import Inventory
from repositories.order_repository import OrderRepository, WalletRepository
from repositories.product_repository import ProductRepository
from repositories.inventory_repository import InventoryRepository
from repositories.ticket_repository import DiscountRepository

logger = logging.getLogger(__name__)


class OrderService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.order_repo = OrderRepository(session)
        self.product_repo = ProductRepository(session)
        self.inventory_repo = InventoryRepository(session)
        self.wallet_repo = WalletRepository(session)
        self.discount_repo = DiscountRepository(session)

    async def create_order(
        self,
        user_id: int,
        product_id: int,
        discount_code: Optional[str] = None,
    ) -> Tuple[bool, str, Optional[Order]]:
        """ایجاد سفارش جدید"""
        product = await self.product_repo.get_by_id(product_id)
        if not product:
            return False, "محصول یافت نشد", None
        if not product.is_available:
            return False, "محصول در دسترس نیست", None

        total = product.price
        discount_amount = 0
        discount = None

        if discount_code:
            discount = await self.discount_repo.get_by_code(discount_code)
            if discount and discount.is_active:
                from config.settings import settings
                if discount.type == "percentage":
                    discount_amount = int(total * discount.value / 100)
                    max_disc = int(total * settings.MAX_DISCOUNT_PERCENT / 100)
                    discount_amount = min(discount_amount, max_disc)
                else:
                    discount_amount = min(discount.value, total)

        final = total - discount_amount
        order_number = await self.order_repo.generate_order_number()

        order = await self.order_repo.create(
            user_id=user_id,
            order_number=order_number,
            total_amount=total,
            discount_amount=discount_amount,
            final_amount=final,
            discount_code=discount_code if discount_amount > 0 else None,
            status="pending",
        )
        return True, "سفارش ایجاد شد", order

    async def pay_with_wallet(self, order_id: int, user_id: int) -> Tuple[bool, str]:
        """پرداخت سفارش با کیف پول"""
        order = await self.order_repo.get_by_id(order_id)
        if not order or order.user_id != user_id:
            return False, "سفارش یافت نشد"
        if order.payment_status == "success":
            return False, "این سفارش قبلاً پرداخت شده"

        success, wallet = await self.wallet_repo.deduct_balance(user_id, order.final_amount)
        if not success:
            return False, "موجودی کیف پول کافی نیست"

        await self.order_repo.update(
            order,
            payment_status="success",
            payment_method="wallet",
            status="waiting",
        )
        logger.info(f"Order #{order.order_number} paid via wallet by user {user_id}")
        return True, "پرداخت موفق"

    async def deliver_account(self, order_id: int) -> Tuple[bool, str, Optional[dict]]:
        """ارسال خودکار اکانت با قفل"""
        order = await self.order_repo.get_by_id(order_id)
        if not order:
            return False, "سفارش یافت نشد", None

        # دریافت محصول
        for item in order.items:
            product = await self.product_repo.get_by_id(item.product_id)
            if not product or not product.has_inventory:
                continue

            # قفل و انتخاب اکانت
            inventory = await self.inventory_repo.select_account_with_lock(item.product_id)
            if not inventory:
                logger.warning(f"No inventory for product {item.product_id}")
                return False, "اکانتی موجود نیست", None

            await self.inventory_repo.mark_as_sold(inventory)
            await self.product_repo.decrement_available_count(item.product_id)

            # ذخیره اکانت ارسال‌شده
            from datetime import datetime
            account_text = f"👤 نام کاربری: {inventory.username}\n🔑 رمز عبور: {inventory.password}"
            if inventory.extra_info:
                account_text += f"\n📝 اطلاعات بیشتر: {inventory.extra_info}"

            await self.order_repo.update(
                order,
                status="completed",
                delivery_status="sent",
            )

            # ثبت اکانت روی order item
            item.inventory_id = inventory.id
            item.delivered_at = datetime.utcnow()
            item.delivered_account = account_text
            self.session.add(item)

            return True, "ارسال شد", {
                "username": inventory.username,
                "password": inventory.password,
                "extra_info": inventory.extra_info,
                "account_text": account_text,
            }

        return False, "محصول انبار ندارد", None

    async def cancel_order(self, order_id: int) -> Tuple[bool, str]:
        order = await self.order_repo.get_by_id(order_id)
        if not order:
            return False, "سفارش یافت نشد"
        if order.status == "completed":
            return False, "سفارش تکمیل شده قابل لغو نیست"

        await self.order_repo.update(order, status="cancelled", payment_status="refunded")

        # استرداد به کیف پول اگر با کیف پول پرداخت شده
        if order.payment_method == "wallet" and order.payment_status == "success":
            await self.wallet_repo.add_balance(order.user_id, order.final_amount)

        return True, "سفارش لغو شد"

    async def get_user_orders(self, user_id: int) -> list:
        return await self.order_repo.get_user_orders(user_id)
