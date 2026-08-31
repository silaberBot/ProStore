"""
ریپازیتوری‌های باقی‌مانده: تیکت، رفرال، تخفیف، تنظیمات
Ticket, Referral, Discount, Setting repositories
"""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.ticket import Ticket, TicketMessage
from models.referral import Referral, Discount
from models.setting import Setting
from repositories.base_repository import BaseRepository


class TicketRepository(BaseRepository[Ticket]):
    def __init__(self, session: AsyncSession):
        super().__init__(Ticket, session)

    async def get_user_tickets(self, user_id: int) -> List[Ticket]:
        result = await self.session.execute(
            select(Ticket)
            .where(Ticket.user_id == user_id)
            .order_by(Ticket.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_open_tickets(self, limit: int = 20) -> List[Ticket]:
        result = await self.session.execute(
            select(Ticket)
            .where(Ticket.status.in_(["open", "in_progress"]))
            .order_by(Ticket.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def add_message(
        self,
        ticket_id: int,
        sender_id: int,
        message: str,
        is_admin: bool = False,
        file_id: Optional[str] = None,
    ) -> TicketMessage:
        msg = TicketMessage(
            ticket_id=ticket_id,
            sender_id=sender_id,
            message=message,
            is_admin=is_admin,
            file_id=file_id,
        )
        self.session.add(msg)
        await self.session.flush()
        return msg

    async def get_open_count(self) -> int:
        result = await self.session.execute(
            select(func.count(Ticket.id)).where(Ticket.status == "open")
        )
        return result.scalar_one()


class ReferralRepository(BaseRepository[Referral]):
    def __init__(self, session: AsyncSession):
        super().__init__(Referral, session)

    async def get_by_referred_id(self, referred_id: int) -> Optional[Referral]:
        result = await self.session.execute(
            select(Referral).where(Referral.referred_id == referred_id)
        )
        return result.scalar_one_or_none()

    async def get_referrer_list(self, referrer_id: int) -> List[Referral]:
        result = await self.session.execute(
            select(Referral)
            .where(Referral.referrer_id == referrer_id)
            .order_by(Referral.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_pending_referrals(self) -> List[Referral]:
        result = await self.session.execute(
            select(Referral).where(Referral.status == "pending")
        )
        return list(result.scalars().all())


class DiscountRepository(BaseRepository[Discount]):
    def __init__(self, session: AsyncSession):
        super().__init__(Discount, session)

    async def get_by_code(self, code: str) -> Optional[Discount]:
        result = await self.session.execute(
            select(Discount).where(Discount.code == code.upper())
        )
        return result.scalar_one_or_none()

    async def get_active_discounts(self) -> List[Discount]:
        from datetime import datetime
        result = await self.session.execute(
            select(Discount).where(
                and_(
                    Discount.is_active == True,
                    Discount.expire_date.is_(None)
                    | (Discount.expire_date > datetime.utcnow()),
                )
            )
        )
        return list(result.scalars().all())

    async def increment_used_count(self, discount: Discount) -> None:
        discount.used_count += 1
        if discount.max_uses and discount.used_count >= discount.max_uses:
            discount.is_active = False
        self.session.add(discount)


class SettingRepository(BaseRepository[Setting]):
    def __init__(self, session: AsyncSession):
        super().__init__(Setting, session)

    async def get(self, key: str, default: str = "") -> str:
        result = await self.session.execute(
            select(Setting).where(Setting.key == key)
        )
        setting = result.scalar_one_or_none()
        return setting.value if setting else default

    async def set(self, key: str, value: str, description: Optional[str] = None) -> Setting:
        result = await self.session.execute(
            select(Setting).where(Setting.key == key)
        )
        setting = result.scalar_one_or_none()
        if setting:
            setting.value = value
            if description:
                setting.description = description
            self.session.add(setting)
        else:
            setting = await self.create(key=key, value=value, description=description or "")
        await self.session.flush()
        return setting

    async def get_all_as_dict(self) -> dict:
        result = await self.session.execute(select(Setting))
        return {s.key: s.value for s in result.scalars().all()}
