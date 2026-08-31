"""
سرویس رفرال
Referral service — manages invite links and reward logic
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from repositories.user_repository import UserRepository
from repositories.ticket_repository import ReferralRepository
from repositories.order_repository import WalletRepository

logger = logging.getLogger(__name__)


class ReferralService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)
        self.referral_repo = ReferralRepository(session)
        self.wallet_repo = WalletRepository(session)

    async def register_referral(
        self, referred_telegram_id: int, referral_code: str
    ) -> Tuple[bool, str]:
        """ثبت رفرال جدید هنگام /start با کد"""
        # بررسی اینکه کاربر قبلاً رفرال داشته یا نه
        existing = await self.referral_repo.get_by_referred_id(referred_telegram_id)
        if existing:
            return False, "این کاربر قبلاً از طریق رفرال ثبت شده"

        referrer = await self.user_repo.get_by_referral_code(referral_code)
        if not referrer:
            return False, "کد دعوت نامعتبر است"

        if referrer.telegram_id == referred_telegram_id:
            return False, "نمی‌توانید از لینک خودتان استفاده کنید"

        referral = await self.referral_repo.create(
            referrer_id=referrer.telegram_id,
            referred_id=referred_telegram_id,
            status="pending",
        )

        logger.info(
            f"Referral registered: referrer={referrer.telegram_id}, referred={referred_telegram_id}"
        )
        return True, f"رفرال برای {referrer.full_name} ثبت شد"

    async def check_and_reward_referrals(self) -> int:
        """
        بررسی تمام رفرال‌های pending و پاداش‌دهی
        این متد توسط cron job هر چند ساعت یکبار اجرا می‌شود
        """
        pending = await self.referral_repo.get_pending_referrals()
        rewarded = 0

        for referral in pending:
            referred = await self.user_repo.get_by_telegram_id(referral.referred_id)
            if not referred:
                continue

            # بررسی تأخیر زمانی
            delay_days = (
                settings.REFERRAL_DELAY_WITH_PHONE
                if referred.phone_verified and referred.phone_is_iranian
                else settings.REFERRAL_DELAY_WITHOUT_PHONE
            )
            min_date = referral.created_at + timedelta(days=delay_days)
            if datetime.utcnow() < min_date:
                continue

            # بررسی شرایط
            conditions_met = (
                referral.channel_joined
                and referred.activities_count >= settings.REFERRAL_MIN_ACTIVITIES
            )

            if conditions_met:
                reward = 5000  # پاداش پیش‌فرض (از settings خوانده می‌شود)

                await self.referral_repo.update(
                    referral,
                    status="success",
                    reward_amount=reward,
                    reward_type="cash",
                    rewarded_at=datetime.utcnow(),
                )

                # شارژ کیف پول معرف
                await self.wallet_repo.add_balance(referral.referrer_id, reward)
                rewarded += 1
                logger.info(
                    f"Referral {referral.id} rewarded: referrer={referral.referrer_id} +{reward}"
                )

        return rewarded

    async def get_referral_stats(self, user_id: int) -> dict:
        """آمار رفرال کاربر"""
        referrals = await self.referral_repo.get_referrer_list(user_id)
        total = len(referrals)
        success = len([r for r in referrals if r.status == "success"])
        pending = len([r for r in referrals if r.status == "pending"])
        earned = sum(r.reward_amount for r in referrals if r.status == "success")
        user = await self.user_repo.get_by_telegram_id(user_id)
        return {
            "total": total,
            "success": success,
            "pending": pending,
            "earned": earned,
            "referral_code": user.referral_code if user else "",
            "referral_link": f"https://t.me/{settings.BOT_USERNAME}?start={user.referral_code}" if user else "",
        }
