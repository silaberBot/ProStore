"""
سرویس‌های باقی‌مانده: تیکت، آموزش، گزارش
Ticket, Tutorial, Report services
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from repositories.ticket_repository import TicketRepository, DiscountRepository, SettingRepository
from repositories.user_repository import UserRepository
from repositories.product_repository import ProductRepository
from repositories.order_repository import OrderRepository

logger = logging.getLogger(__name__)


class TicketService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.ticket_repo = TicketRepository(session)

    async def create_ticket(
        self,
        user_id: int,
        subject: str,
        first_message: str,
        order_id: Optional[int] = None,
    ) -> Tuple[bool, str, Optional[int]]:
        ticket = await self.ticket_repo.create(
            user_id=user_id,
            subject=subject,
            order_id=order_id,
            status="open",
            priority="medium",
        )
        await self.ticket_repo.add_message(
            ticket_id=ticket.id,
            sender_id=user_id,
            message=first_message,
            is_admin=False,
        )
        return True, "تیکت ثبت شد", ticket.id

    async def reply_to_ticket(
        self,
        ticket_id: int,
        sender_id: int,
        message: str,
        is_admin: bool = False,
        file_id: Optional[str] = None,
    ) -> Tuple[bool, str]:
        ticket = await self.ticket_repo.get_by_id(ticket_id)
        if not ticket:
            return False, "تیکت یافت نشد"
        if ticket.status == "closed":
            return False, "تیکت بسته است"

        await self.ticket_repo.add_message(
            ticket_id=ticket_id,
            sender_id=sender_id,
            message=message,
            is_admin=is_admin,
            file_id=file_id,
        )

        new_status = "answered" if is_admin else "in_progress"
        await self.ticket_repo.update(ticket, status=new_status, updated_at=datetime.utcnow())
        return True, "پیام ثبت شد"

    async def close_ticket(self, ticket_id: int) -> Tuple[bool, str]:
        ticket = await self.ticket_repo.get_by_id(ticket_id)
        if not ticket:
            return False, "تیکت یافت نشد"
        await self.ticket_repo.update(ticket, status="closed")
        return True, "تیکت بسته شد"

    async def get_user_tickets(self, user_id: int):
        return await self.ticket_repo.get_user_tickets(user_id)

    async def get_open_tickets(self, limit: int = 20):
        return await self.ticket_repo.get_open_tickets(limit)


class DiscountService:
    def __init__(self, session: AsyncSession):
        self.discount_repo = DiscountRepository(session)

    async def validate_code(
        self, code: str, user_id: int, amount: int, product_id: Optional[int] = None
    ) -> Tuple[bool, str, int]:
        """اعتبارسنجی کد تخفیف → (valid, message, discount_amount)"""
        discount = await self.discount_repo.get_by_code(code)
        if not discount or not discount.is_active:
            return False, "کد تخفیف نامعتبر است", 0
        if amount < discount.min_order_amount:
            return False, f"حداقل مبلغ سفارش: {discount.min_order_amount:,} تومان", 0
        if discount.expire_date and discount.expire_date < datetime.utcnow():
            return False, "کد تخفیف منقضی شده است", 0
        if discount.max_uses and discount.used_count >= discount.max_uses:
            return False, "ظرفیت این کد تمام شده است", 0

        if discount.type == "percentage":
            disc_amount = int(amount * discount.value / 100)
        else:
            disc_amount = min(discount.value, amount)

        return True, f"تخفیف {disc_amount:,} تومانی اعمال شد", disc_amount


class ReportService:
    def __init__(self, session: AsyncSession):
        self.order_repo = OrderRepository(session)
        self.user_repo = UserRepository(session)
        self.product_repo = ProductRepository(session)

    async def get_dashboard_stats(self) -> dict:
        """آمار داشبورد ادمین"""
        today_stats = await self.order_repo.get_today_stats()
        total_users = await self.user_repo.get_total_users()
        active_today = await self.user_repo.get_active_users_today()
        waiting_orders = await self.order_repo.get_waiting_orders(limit=3)

        return {
            "today_orders": today_stats["count"],
            "today_revenue": today_stats["total"],
            "total_users": total_users,
            "active_today": active_today,
            "waiting_orders": len(waiting_orders),
            "waiting_list": waiting_orders,
        }


class SettingService:
    def __init__(self, session: AsyncSession):
        self.setting_repo = SettingRepository(session)

    async def get(self, key: str, default: str = "") -> str:
        return await self.setting_repo.get(key, default)

    async def set(self, key: str, value: str) -> bool:
        await self.setting_repo.set(key, value)
        return True

    async def get_all(self) -> dict:
        return await self.setting_repo.get_all_as_dict()

    async def initialize_defaults(self) -> None:
        """مقداردهی پیش‌فرض تنظیمات"""
        defaults = {
            "welcome_message": "🌟 به ربات شاپیار خوش آمدید!\nبهترین اشتراک‌های نرم‌افزاری با قیمت مناسب",
            "shop_description": "🛍 فروشگاه اشتراک‌های نرم‌افزاری",
            "support_username": "@support",
            "channel_username": "",
            "min_wallet_charge": "10000",
            "referral_reward": "5000",
            "low_inventory_alert": "5",
            "order_expiry_hours": "24",
        }
        for key, value in defaults.items():
            existing = await self.setting_repo.get(key)
            if not existing:
                await self.setting_repo.set(key, value)
