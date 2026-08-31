"""
Middleware — ثبت خودکار کاربر و بروزرسانی فعالیت
"""
from __future__ import annotations

import logging
from typing import Any, Callable

from telegram import Update
from telegram.ext import BaseHandler, ContextTypes

from config.settings import settings
from core.database import get_db
from repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


class UserRegistrationMiddleware:
    """
    Middleware برای ثبت خودکار کاربر جدید
    و بروزرسانی آخرین فعالیت
    """

    async def __call__(
        self,
        handler: Callable,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> Any:
        tg_user = update.effective_user
        if tg_user and tg_user.id and not tg_user.is_bot:
            try:
                async with get_db() as session:
                    user_repo = UserRepository(session)
                    user = await user_repo.get_by_telegram_id(tg_user.id)

                    if user:
                        # بروزرسانی اطلاعات اگر تغییر کرده
                        updates = {}
                        if user.first_name != tg_user.first_name:
                            updates["first_name"] = tg_user.first_name
                        if user.username != tg_user.username:
                            updates["username"] = tg_user.username
                        if updates:
                            await user_repo.update(user, **updates)

                        # بروزرسانی فعالیت (هر 5 دقیقه یکبار)
                        from datetime import datetime, timedelta
                        if (
                            not user.last_activity
                            or datetime.utcnow() - user.last_activity > timedelta(minutes=5)
                        ):
                            await user_repo.update_activity(tg_user.id)

                        context.user_data["registered"] = True
                        context.user_data["is_admin"] = tg_user.id in settings.admin_ids_list

            except Exception as e:
                logger.warning(f"Middleware error for user {tg_user.id}: {e}")

        return await handler(update, context)
