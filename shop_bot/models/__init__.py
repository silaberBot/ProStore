"""
ثبت تمام مدل‌های دیتابیس
Register all models so SQLAlchemy metadata is complete
"""
from models.base import Base, TimestampMixin
from models.user import User
from models.product import Product
from models.order import Order, OrderItem
from models.inventory import Inventory
from models.payment import Payment, Wallet
from models.ticket import Ticket, TicketMessage
from models.referral import Referral, Discount
from models.setting import Setting, Admin, Tutorial

__all__ = [
    "Base",
    "TimestampMixin",
    "User",
    "Product",
    "Order",
    "OrderItem",
    "Inventory",
    "Payment",
    "Wallet",
    "Ticket",
    "TicketMessage",
    "Referral",
    "Discount",
    "Setting",
    "Admin",
    "Tutorial",
]
