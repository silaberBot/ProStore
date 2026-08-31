"""
مدل کاربران
User model
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import BigInteger, Boolean, DateTime, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base
from models.base import TimestampMixin


class User(Base, TimestampMixin):
    """جدول کاربران ربات"""
    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_telegram_id", "telegram_id"),
        Index("ix_users_referral_code", "referral_code"),
        Index("ix_users_username", "username"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    phone_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    phone_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    phone_is_iranian: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # سطح کاربری: silver / gold / platinum
    level: Mapped[str] = mapped_column(String(20), default="silver", nullable=False)

    # موجودی کیف پول (ریال)
    wallet_balance: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)

    # سیستم رفرال
    referral_code: Mapped[Optional[str]] = mapped_column(String(20), unique=True, nullable=True)
    referred_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    # وضعیت
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ban_reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # آخرین فعالیت
    last_activity: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # تعداد فعالیت‌ها (برای سیستم رفرال)
    activities_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    orders: Mapped[List["Order"]] = relationship("Order", back_populates="user", lazy="select")
    wallet: Mapped[Optional["Wallet"]] = relationship("Wallet", back_populates="user", uselist=False, lazy="select")
    tickets: Mapped[List["Ticket"]] = relationship("Ticket", back_populates="user", lazy="select")
    payments: Mapped[List["Payment"]] = relationship("Payment", back_populates="user", lazy="select")
    admin_profile: Mapped[Optional["Admin"]] = relationship("Admin", back_populates="user", uselist=False, lazy="select")

    def __repr__(self) -> str:
        return f"<User id={self.id} telegram_id={self.telegram_id} name={self.first_name}>"

    @property
    def full_name(self) -> str:
        if self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name

    @property
    def mention(self) -> str:
        if self.username:
            return f"@{self.username}"
        return self.full_name
