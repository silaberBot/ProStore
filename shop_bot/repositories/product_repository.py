"""
ریپازیتوری محصولات
Product repository
"""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models.product import Product
from repositories.base_repository import BaseRepository


class ProductRepository(BaseRepository[Product]):
    def __init__(self, session: AsyncSession):
        super().__init__(Product, session)

    async def get_active_products(self, category: Optional[str] = None) -> List[Product]:
        stmt = select(Product).where(Product.is_active == True)
        if category:
            stmt = stmt.where(Product.category == category)
        stmt = stmt.order_by(Product.position.asc(), Product.id.asc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_category(self, category: str) -> List[Product]:
        result = await self.session.execute(
            select(Product)
            .where(and_(Product.category == category, Product.is_active == True))
            .order_by(Product.position.asc())
        )
        return list(result.scalars().all())

    async def get_categories(self) -> List[str]:
        result = await self.session.execute(
            select(Product.category).distinct().where(Product.is_active == True)
        )
        return [row[0] for row in result.fetchall()]

    async def search(self, query: str) -> List[Product]:
        result = await self.session.execute(
            select(Product).where(Product.name.ilike(f"%{query}%"))
        )
        return list(result.scalars().all())

    async def decrement_available_count(self, product_id: int) -> None:
        product = await self.get_by_id(product_id)
        if product and product.available_count > 0:
            product.available_count -= 1
            if product.available_count == 0 and product.out_of_stock_action == "disable_product":
                product.is_active = False
            product.sold_count += 1
            self.session.add(product)

    async def increment_available_count(self, product_id: int, count: int = 1) -> None:
        product = await self.get_by_id(product_id)
        if product:
            product.available_count += count
            if not product.is_active and product.available_count > 0:
                product.is_active = True
            self.session.add(product)
