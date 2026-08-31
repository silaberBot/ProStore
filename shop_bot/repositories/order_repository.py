"""
ریپازیتوری سفارشات، پرداخت و کیف پول
Order, Payment and Wallet repositories
"""
from __future__ import annotations

import random
import string
from datetime import datetime, date
from typing import List, Optional

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.order import Order, OrderItem
from models.payment import Payment, Wallet
from repositories.base_repository import BaseRepository


class OrderRepository(BaseRepository[Order]):
    def __init__(self, session: AsyncSession):
        super().__init__(Order, session)

    async def get_by_order_number(self, order_number: str) -> Optional[Order]:
        result = await self.session.execute(
            select(Order).where(Order.order_number == order_number)
        )
        return result.scalar_one_or_none()

    async def get_user_orders(self, user_id: int, limit: int = 10) -> List[Order]:
        result = await self.session.execute(
            select(Order)
            .where(Order.user_id == user_id)
            .order_by(Order.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_pending_orders(self) -> List[Order]:
        result = await self.session.execute(
            select(Order)
            .where(Order.status == "waiting")
            .order_by(Order.created_at.asc())
        )
        return list(result.scalars().all())

    async def get_expiring_orders(self, days_ahead: int = 2) -> List[Order]:
        """سفارشاتی که اشتراک‌شان به زودی منقضی می‌شود"""
        target_date = date.today()
        from sqlalchemy import cast, Date
        result = await self.session.execute(
            select(Order).where(
                and_(
                    Order.status == "completed",
                )
            )
        )
        return list(result.scalars().all())

    async def generate_order_number(self) -> str:
        while True:
            suffix = "".join(random.choices(string.digits, k=6))
            number = f"ORD{suffix}"
            existing = await self.get_by_order_number(number)
            if not existing:
                return number

    async def get_today_stats(self) -> dict:
        today = datetime.utcnow().date()
        result = await self.session.execute(
            select(
                func.count(Order.id).label("count"),
                func.coalesce(func.sum(Order.final_amount), 0).label("total"),
            ).where(
                and_(
                    func.date(Order.created_at) == today,
                    Order.payment_status == "success",
                )
            )
        )
        row = result.one()
        return {"count": row.count, "total": row.total}

    async def get_waiting_orders(self, limit: int = 3) -> List[Order]:
        result = await self.session.execute(
            select(Order)
            .where(Order.status == "waiting")
            .order_by(Order.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())


class PaymentRepository(BaseRepository[Payment]):
    def __init__(self, session: AsyncSession):
        super().__init__(Payment, session)

    async def get_by_authority(self, authority: str) -> Optional[Payment]:
        result = await self.session.execute(
            select(Payment).where(Payment.authority == authority)
        )
        return result.scalar_one_or_none()

    async def get_user_payments(self, user_id: int, limit: int = 10) -> List[Payment]:
        result = await self.session.execute(
            select(Payment)
            .where(Payment.user_id == user_id)
            .order_by(Payment.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())


class WalletRepository(BaseRepository[Wallet]):
    def __init__(self, session: AsyncSession):
        super().__init__(Wallet, session)

    async def get_by_user_id(self, user_id: int) -> Optional[Wallet]:
        result = await self.session.execute(
            select(Wallet).where(Wallet.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_or_create(self, user_id: int) -> Wallet:
        wallet = await self.get_by_user_id(user_id)
        if not wallet:
            wallet = await self.create(user_id=user_id)
        return wallet

    async def add_balance(self, user_id: int, amount: int) -> Wallet:
        wallet = await self.get_or_create(user_id)
        wallet.balance += amount
        wallet.total_deposited += amount
        wallet.updated_at = datetime.utcnow()
        self.session.add(wallet)
        return wallet

    async def deduct_balance(self, user_id: int, amount: int) -> tuple[bool, Wallet]:
        wallet = await self.get_or_create(user_id)
        if wallet.balance < amount:
            return False, wallet
        wallet.balance -= amount
        wallet.total_spent += amount
        wallet.updated_at = datetime.utcnow()
        self.session.add(wallet)
        return True, wallet
