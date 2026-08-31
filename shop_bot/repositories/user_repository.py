"""
ریپازیتوری کاربران
User repository
"""
from __future__ import annotations

import random
import string
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from repositories.base_repository import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession):
        super().__init__(User, session)

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def get_by_referral_code(self, code: str) -> Optional[User]:
        result = await self.session.execute(
            select(User).where(User.referral_code == code)
        )
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> Optional[User]:
        result = await self.session.execute(
            select(User).where(User.username == username.lstrip("@"))
        )
        return result.scalar_one_or_none()

    async def create_user(
        self,
        telegram_id: int,
        first_name: str,
        username: Optional[str] = None,
        last_name: Optional[str] = None,
        referred_by: Optional[int] = None,
    ) -> User:
        referral_code = await self._generate_unique_referral_code()
        return await self.create(
            telegram_id=telegram_id,
            first_name=first_name,
            username=username,
            last_name=last_name,
            referral_code=referral_code,
            referred_by=referred_by,
            last_activity=datetime.utcnow(),
        )

    async def _generate_unique_referral_code(self) -> str:
        while True:
            code = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
            existing = await self.get_by_referral_code(code)
            if not existing:
                return code

    async def update_activity(self, telegram_id: int) -> None:
        user = await self.get_by_telegram_id(telegram_id)
        if user:
            user.last_activity = datetime.utcnow()
            user.activities_count += 1
            self.session.add(user)

    async def search_users(
        self,
        query: str = "",
        level: Optional[str] = None,
        is_banned: Optional[bool] = None,
        limit: int = 10,
        offset: int = 0,
    ) -> List[User]:
        conditions = []
        if query:
            conditions.append(
                or_(
                    User.first_name.ilike(f"%{query}%"),
                    User.username.ilike(f"%{query}%"),
                    User.phone_number.ilike(f"%{query}%"),
                )
            )
        if level:
            conditions.append(User.level == level)
        if is_banned is not None:
            conditions.append(User.is_banned == is_banned)

        stmt = select(User)
        if conditions:
            stmt = stmt.where(and_(*conditions))
        stmt = stmt.order_by(User.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_total_users(self) -> int:
        result = await self.session.execute(select(func.count(User.id)))
        return result.scalar_one()

    async def get_active_users_today(self) -> int:
        from datetime import date
        today = datetime.utcnow().date()
        result = await self.session.execute(
            select(func.count(User.id)).where(
                func.date(User.last_activity) == today
            )
        )
        return result.scalar_one()
