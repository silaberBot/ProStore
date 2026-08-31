"""
کلاس پایه مدل‌ها و Mixin های مشترک
Base model class and shared mixins
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base  # noqa: F401 - re-export


class TimestampMixin:
    """Mixin برای اضافه کردن فیلدهای تاریخ ایجاد و بروزرسانی"""
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )


class SoftDeleteMixin:
    """Mixin برای حذف نرم (soft delete)"""
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None
