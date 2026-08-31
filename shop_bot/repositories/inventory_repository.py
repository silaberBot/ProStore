"""
ریپازیتوری انبار اکانت‌ها
Inventory repository with locking support
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import select, and_, asc, nulls_last
from sqlalchemy.ext.asyncio import AsyncSession

from models.inventory import Inventory
from repositories.base_repository import BaseRepository


class InventoryRepository(BaseRepository[Inventory]):
    def __init__(self, session: AsyncSession):
        super().__init__(Inventory, session)

    async def get_available_count(self, product_id: int) -> int:
        """تعداد اکانت‌های موجود برای یک محصول"""
        from sqlalchemy import func
        result = await self.session.execute(
            select(func.sum(Inventory.capacity)).where(
                and_(
                    Inventory.product_id == product_id,
                    Inventory.status == "available",
                    Inventory.capacity > 0,
                )
            )
        )
        return result.scalar_one() or 0

    async def select_account_with_lock(self, product_id: int) -> Optional[Inventory]:
        """
        انتخاب اکانت با قفل (SELECT FOR UPDATE)
        اولویت: تاریخ انقضای نزدیک‌تر → FIFO
        """
        result = await self.session.execute(
            select(Inventory)
            .where(
                and_(
                    Inventory.product_id == product_id,
                    Inventory.status == "available",
                    Inventory.capacity > 0,
                )
            )
            .order_by(
                nulls_last(asc(Inventory.expire_date)),
                asc(Inventory.added_at),
            )
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        return result.scalar_one_or_none()

    async def mark_as_sold(self, inventory: Inventory) -> Inventory:
        """کاهش ظرفیت و تغییر وضعیت در صورت نیاز"""
        inventory.capacity -= 1
        if inventory.capacity <= 0:
            inventory.status = "sold"
            inventory.sold_at = datetime.utcnow()
        self.session.add(inventory)
        await self.session.flush()
        return inventory

    async def get_product_accounts(self, product_id: int, status: Optional[str] = None) -> List[Inventory]:
        stmt = select(Inventory).where(Inventory.product_id == product_id)
        if status:
            stmt = stmt.where(Inventory.status == status)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def add_bulk(self, product_id: int, accounts: List[dict]) -> int:
        """افزودن دسته‌ای اکانت‌ها"""
        count = 0
        for acc in accounts:
            await self.create(product_id=product_id, **acc)
            count += 1
        return count
