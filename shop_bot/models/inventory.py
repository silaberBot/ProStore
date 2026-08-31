"""
مدل انبار اکانت‌ها
Inventory model for account storage
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class Inventory(Base):
    """جدول انبار اکانت‌ها"""
    __tablename__ = "inventory"
    __table_args__ = (
        Index("ix_inventory_product_id", "product_id"),
        Index("ix_inventory_status", "status"),
        Index("ix_inventory_expire_date", "expire_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id"), nullable=False)

    # اطلاعات اکانت
    username: Mapped[str] = mapped_column(String(200), nullable=False)
    password: Mapped[str] = mapped_column(String(200), nullable=False)
    extra_info: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # اطلاعات اضافه (JSON یا متن)

    # تاریخ انقضا (NULL = بدون انقضا)
    expire_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # ظرفیت (برای اکانت‌های چندنفره)
    capacity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # وضعیت: available / sold / broken / reserved
    status: Mapped[str] = mapped_column(String(20), default="available", nullable=False)

    # اگر reserved، برای چه کاربری
    reserved_for: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    added_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    sold_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    product: Mapped["Product"] = relationship("Product", back_populates="inventory_items", lazy="select")

    def __repr__(self) -> str:
        return f"<Inventory id={self.id} product={self.product_id} status={self.status}>"

    @property
    def is_available(self) -> bool:
        return self.status == "available" and self.capacity > 0
