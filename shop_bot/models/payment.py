"""
مدل تراکنش‌های مالی (پرداخت‌ها)
Payment/Transaction model
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class Payment(Base):
    """جدول تراکنش‌های مالی"""
    __tablename__ = "payments"
    __table_args__ = (
        Index("ix_payments_user_id", "user_id"),
        Index("ix_payments_type", "type"),
        Index("ix_payments_method", "method"),
        Index("ix_payments_status", "status"),
        Index("ix_payments_reference_id", "reference_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id"), nullable=False)
    order_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("orders.id"), nullable=True)

    # مبلغ تراکنش (مثبت = دریافت، منفی = پرداخت)
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)

    # نوع تراکنش: deposit / withdraw / purchase / refund / referral / bonus
    type: Mapped[str] = mapped_column(String(20), nullable=False)

    # روش پرداخت
    method: Mapped[str] = mapped_column(String(50), nullable=False)

    # وضعیت: pending / success / failed / expired
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)

    # اطلاعات درگاه
    reference_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    authority: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    gateway_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON

    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="payments", lazy="select")
    order: Mapped[Optional["Order"]] = relationship("Order", back_populates="payments", lazy="select")

    def __repr__(self) -> str:
        return f"<Payment id={self.id} type={self.type} amount={self.amount} status={self.status}>"


class Wallet(Base):
    """جدول کیف پول کاربران"""
    __tablename__ = "wallets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id"), unique=True, nullable=False)

    balance: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    total_deposited: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    total_spent: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    total_withdrawn: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    total_referral_earned: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="wallet", lazy="select")

    def __repr__(self) -> str:
        return f"<Wallet user={self.user_id} balance={self.balance}>"
