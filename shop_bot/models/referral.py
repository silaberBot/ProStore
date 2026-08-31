"""
مدل سیستم رفرال
Referral system model
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class Referral(Base):
    """جدول دعوت‌های رفرال"""
    __tablename__ = "referrals"
    __table_args__ = (
        Index("ix_referrals_referrer_id", "referrer_id"),
        Index("ix_referrals_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    referrer_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id"), nullable=False)
    referred_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id"), unique=True, nullable=False)

    # وضعیت: pending / success / rejected
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)

    # پاداش
    reward_amount: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    reward_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # discount / points / cash

    # شرایط
    channel_joined: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    channel_join_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    activities_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    has_purchased: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    min_days_satisfied: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    rewarded_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<Referral referrer={self.referrer_id} referred={self.referred_id} status={self.status}>"


class Discount(Base):
    """جدول کدهای تخفیف"""
    __tablename__ = "discounts"
    __table_args__ = (
        Index("ix_discounts_code", "code"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    # نوع: percentage / fixed
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    value: Mapped[int] = mapped_column(Integer, nullable=False)

    min_order_amount: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    max_uses: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_uses_per_user: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    used_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    expire_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # JSON: لیست product_id یا level یا null (همه)
    applicable_products: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    applicable_levels: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    created_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<Discount code={self.code} type={self.type} value={self.value}>"
