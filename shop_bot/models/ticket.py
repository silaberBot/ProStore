"""
مدل تیکت‌های پشتیبانی
Support ticket models
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base
from models.base import TimestampMixin


class Ticket(Base, TimestampMixin):
    """جدول تیکت‌های پشتیبانی"""
    __tablename__ = "tickets"
    __table_args__ = (
        Index("ix_tickets_user_id", "user_id"),
        Index("ix_tickets_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id"), nullable=False)
    order_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("orders.id"), nullable=True)

    subject: Mapped[str] = mapped_column(String(200), nullable=False)

    # وضعیت: open / in_progress / answered / closed
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False)

    # اولویت: low / medium / high / critical
    priority: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="tickets", lazy="select")
    messages: Mapped[List["TicketMessage"]] = relationship("TicketMessage", back_populates="ticket", lazy="select")

    def __repr__(self) -> str:
        return f"<Ticket #{self.id} user={self.user_id} status={self.status}>"


class TicketMessage(Base):
    """جدول پیام‌های تیکت"""
    __tablename__ = "ticket_messages"
    __table_args__ = (
        Index("ix_ticket_messages_ticket_id", "ticket_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(Integer, ForeignKey("tickets.id"), nullable=False)
    sender_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    file_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)

    # Relationships
    ticket: Mapped["Ticket"] = relationship("Ticket", back_populates="messages", lazy="select")

    def __repr__(self) -> str:
        return f"<TicketMessage ticket={self.ticket_id} sender={self.sender_id}>"
