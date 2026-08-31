"""
مدل محصولات
Product model
"""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy import Boolean, Index, Integer, String, Text, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base
from models.base import TimestampMixin


class Product(Base, TimestampMixin):
    """جدول محصولات"""
    __tablename__ = "products"
    __table_args__ = (
        Index("ix_products_name", "name"),
        Index("ix_products_category", "category"),
        Index("ix_products_is_active", "is_active"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    price: Mapped[int] = mapped_column(BigInteger, nullable=False)
    image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    image_file_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # دسته‌بندی: editing / ai / vpn / other
    category: Mapped[str] = mapped_column(String(50), nullable=False, default="other")

    # وضعیت
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # انبار
    has_inventory: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    delivery_type: Mapped[str] = mapped_column(String(20), default="manual", nullable=False)  # manual / auto
    auto_delivery: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # ظرفیت (برای محصولات چندنفره مثل کپ‌کات)
    capacity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    available_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sold_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # ترتیب نمایش
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # رفتار هنگام اتمام انبار: disable_product / keep_active
    out_of_stock_action: Mapped[str] = mapped_column(String(30), default="disable_product", nullable=False)

    # Relationships
    inventory_items: Mapped[List["Inventory"]] = relationship("Inventory", back_populates="product", lazy="select")
    order_items: Mapped[List["OrderItem"]] = relationship("OrderItem", back_populates="product", lazy="select")
    tutorials: Mapped[List["Tutorial"]] = relationship("Tutorial", back_populates="product", lazy="select")

    def __repr__(self) -> str:
        return f"<Product id={self.id} name={self.name} price={self.price}>"

    @property
    def is_available(self) -> bool:
        """آیا محصول موجود است؟"""
        if not self.is_active:
            return False
        if self.has_inventory:
            return self.available_count > 0
        return True

    @property
    def formatted_price(self) -> str:
        return f"{self.price:,} تومان"
