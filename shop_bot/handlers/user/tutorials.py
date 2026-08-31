"""
هندلر بخش آموزش‌ها برای کاربر
Tutorials handler — browse and view software tutorials
"""
from __future__ import annotations

import logging

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode
from telegram.ext import CallbackQueryHandler, ContextTypes, MessageHandler, filters

from core.database import get_db

logger = logging.getLogger(__name__)


async def tutorials_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """منوی اصلی آموزش‌ها"""
    from sqlalchemy import select
    from models.setting import Tutorial

    async with get_db() as session:
        from sqlalchemy.ext.asyncio import AsyncSession
        result = await session.execute(
            select(Tutorial.category).distinct().where(Tutorial.is_active == True)
        )
        categories = [row[0] for row in result.fetchall()]

    if not categories:
        await update.effective_message.reply_text("❌ آموزشی موجود نیست.")
        return

    buttons = [
        [InlineKeyboardButton(f"📂 {cat}", callback_data=f"tut_cat:{cat}")]
        for cat in categories
    ]
    await update.effective_message.reply_html(
        "📚 <b>آموزش‌ها</b>\n\nدسته‌بندی مورد نظر را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def tutorial_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """لیست آموزش‌های یک دسته"""
    query = update.callback_query
    await query.answer()
    category = query.data.split(":", 1)[1]

    from sqlalchemy import select
    from models.setting import Tutorial

    async with get_db() as session:
        result = await session.execute(
            select(Tutorial)
            .where(Tutorial.category == category)
            .where(Tutorial.is_active == True)
            .order_by(Tutorial.order_position.asc())
        )
        tutorials = result.scalars().all()

    if not tutorials:
        await query.edit_message_text("❌ آموزشی در این دسته وجود ندارد.")
        return

    buttons = [
        [InlineKeyboardButton(f"📖 {t.title}", callback_data=f"tut_view:{t.id}")]
        for t in tutorials
    ]
    buttons.append([InlineKeyboardButton("🔙 بازگشت", callback_data="tut_back")])
    await query.edit_message_text(
        f"📂 <b>{category}</b>\n\nآموزش مورد نظر را انتخاب کنید:",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def tutorial_view(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """نمایش یک آموزش"""
    query = update.callback_query
    await query.answer()
    tut_id = int(query.data.split(":")[1])

    from models.setting import Tutorial

    async with get_db() as session:
        tutorial = await session.get(Tutorial, tut_id)
        if not tutorial:
            await query.edit_message_text("❌ آموزش یافت نشد.")
            return

        # افزایش شمارنده بازدید
        tutorial.view_count += 1
        session.add(tutorial)

    back_btn = InlineKeyboardMarkup([[
        InlineKeyboardButton("🔙 بازگشت", callback_data=f"tut_cat:{tutorial.category}")
    ]])

    # ارسال محتوا بر اساس نوع فایل
    try:
        if tutorial.file_id and tutorial.file_type == "photo":
            await context.bot.send_photo(
                chat_id=query.from_user.id,
                photo=tutorial.file_id,
                caption=f"📖 <b>{tutorial.title}</b>\n\n{tutorial.content or ''}",
                parse_mode=ParseMode.HTML,
                reply_markup=back_btn,
            )
            await query.message.delete()
        elif tutorial.file_id and tutorial.file_type == "video":
            await context.bot.send_video(
                chat_id=query.from_user.id,
                video=tutorial.file_id,
                caption=f"📖 <b>{tutorial.title}</b>\n\n{tutorial.content or ''}",
                parse_mode=ParseMode.HTML,
                reply_markup=back_btn,
            )
            await query.message.delete()
        elif tutorial.file_id and tutorial.file_type == "document":
            await context.bot.send_document(
                chat_id=query.from_user.id,
                document=tutorial.file_id,
                caption=f"📖 <b>{tutorial.title}</b>\n\n{tutorial.content or ''}",
                parse_mode=ParseMode.HTML,
                reply_markup=back_btn,
            )
            await query.message.delete()
        else:
            await query.edit_message_text(
                f"📖 <b>{tutorial.title}</b>\n\n{tutorial.content or 'بدون محتوا'}",
                parse_mode=ParseMode.HTML,
                reply_markup=back_btn,
            )
    except Exception as e:
        logger.error(f"Tutorial view error: {e}")
        await query.edit_message_text(
            f"📖 <b>{tutorial.title}</b>\n\n{tutorial.content or 'بدون محتوا'}",
            parse_mode=ParseMode.HTML,
            reply_markup=back_btn,
        )


def register_tutorial_handlers(app) -> None:
    app.add_handler(MessageHandler(filters.Regex("^📚 آموزش‌ها$"), tutorials_menu))
    app.add_handler(CallbackQueryHandler(tutorials_menu, pattern="^tut_back$"))
    app.add_handler(CallbackQueryHandler(tutorial_category, pattern="^tut_cat:"))
    app.add_handler(CallbackQueryHandler(tutorial_view, pattern="^tut_view:"))
