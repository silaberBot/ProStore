"""
مدل سفارشات و آیتم‌های سفارش
Order and OrderItem models
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base
from models.base import TimestampMixin


class Order(Base, TimestampMixin):
    """جدول سفارشات"""
    __tablename__ = "orders"
    __table_args__ = (
        Index("ix_orders_user_id", "user_id"),
        Index("ix_orders_status", "status"),
        Index("ix_orders_payment_status", "payment_status"),
        Index("ix_orders_delivery_status", "delivery_status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id"), nullable=False)
    order_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)

    # مبالغ
    total_amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    discount_amount: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    final_amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    discount_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # وضعیت سفارش: pending / waiting / completed / cancelled / error / refunded
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)

    # روش پرداخت
    payment_method: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    # وضعیت پرداخت: pending / success / failed / refunded
    payment_status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    # وضعیت ارسال: pending / sent / failed
    delivery_status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="orders", lazy="select")
    items: Mapped[List["OrderItem"]] = relationship("OrderItem", back_populates="order", lazy="select")
    payments: Mapped[List["Payment"]] = relationship("Payment", back_populates="order", lazy="select")

    def __repr__(self) -> str:
        return f"<Order #{self.order_number} user={self.user_id} status={self.status}>"


class OrderItem(Base):
    """جدول آیتم‌های سفارش"""
    __tablename__ = "order_items"
    __table_args__ = (
        Index("ix_order_items_order_id", "order_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id"), nullable=False)
    inventory_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("inventory.id"), nullable=True)

    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    unit_price: Mapped[int] = mapped_column(BigInteger, nullable=False)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # اکانت ارسال‌شده (برای نگهداری نسخه ارسال‌شده)
    delivered_account: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="items", lazy="select")
    product: Mapped["Product"] = relationship("Product", back_populates="order_items", lazy="select")
    inventory: Mapped[Optional["Inventory"]] = relationship("Inventory", lazy="select")

    def __repr__(self) -> str:
        return f"<OrderItem order={self.order_id} product={self.product_id}>"
