"""
تنظیمات اصلی پروژه ربات شاپیار
Main configuration settings using Pydantic Settings
"""
from __future__ import annotations

import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import field_validator


class Settings(BaseSettings):
    """تمام تنظیمات پروژه از فایل .env خوانده می‌شود"""

    # ===========================
    # Telegram Bot
    # ===========================
    TELEGRAM_BOT_TOKEN: str = ""
    BOT_NAME: str = "شاپیار"
    BOT_USERNAME: str = "ShapiyarBot"

    # Admin IDs (list of telegram user IDs)
    ADMIN_IDS: str = ""

    @property
    def admin_ids_list(self) -> List[int]:
        """تبدیل رشته ADMIN_IDS به لیست عدد"""
        if not self.ADMIN_IDS:
            return []
        return [int(uid.strip()) for uid in self.ADMIN_IDS.split(",") if uid.strip()]

    # ===========================
    # Database
    # ===========================
    DATABASE_URL: str = "sqlite+aiosqlite:///./shop_bot.db"

    # ===========================
    # Redis
    # ===========================
    REDIS_URL: str = "redis://localhost:6379/0"
    USE_REDIS: bool = False  # اگر Redis نصب نیست False بذار

    # ===========================
    # Webhook
    # ===========================
    WEBHOOK_URL: Optional[str] = None
    WEBHOOK_PORT: int = 8443
    WEBHOOK_SECRET: Optional[str] = None

    # ===========================
    # Logging
    # ===========================
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # ===========================
    # Payment Gateways
    # ===========================
    ZARINPAL_MERCHANT_ID: str = ""
    IDPAY_API_KEY: str = ""
    SIZPAY_MERCHANT_ID: str = ""
    NOWPAYMENTS_API_KEY: str = ""
    YEKPAY_MERCHANT_ID: str = ""

    # Wallet addresses
    TETHER_WALLET_ADDRESS: str = ""
    TRON_WALLET_ADDRESS: str = ""
    TON_WALLET_ADDRESS: str = ""

    # Stars accounts
    STARS_ACCOUNTS: str = ""

    @property
    def stars_accounts_list(self) -> List[str]:
        if not self.STARS_ACCOUNTS:
            return []
        return [acc.strip() for acc in self.STARS_ACCOUNTS.split(",") if acc.strip()]

    BASE_URL: str = "https://your-domain.com"

    # ===========================
    # Business Settings
    # ===========================
    MIN_WALLET_CHARGE: int = 10000        # حداقل شارژ کیف پول (ریال)
    MAX_DISCOUNT_PERCENT: int = 50         # حداکثر درصد تخفیف
    REMINDER_DAYS_BEFORE: int = 2          # روز قبل از انقضا برای یادآوری

    # ===========================
    # Referral Settings
    # ===========================
    REFERRAL_MAX_PER_MONTH: int = 20       # حداکثر دعوت موفق در ماه
    REFERRAL_DELAY_WITH_PHONE: int = 3     # روز تأخیر با تأیید شماره
    REFERRAL_DELAY_WITHOUT_PHONE: int = 7  # روز تأخیر بدون تأیید شماره
    REFERRAL_MIN_CHANNEL_DAYS: int = 7     # حداقل روز عضویت در کانال
    REFERRAL_MIN_ACTIVITIES: int = 3       # حداقل فعالیت در ربات

    # ===========================
    # Channel Settings
    # ===========================
    CHANNEL_ID: str = ""
    CHANNEL_USERNAME: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# نمونه singleton از تنظیمات
settings = Settings()
