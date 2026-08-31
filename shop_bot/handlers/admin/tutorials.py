"""
هندلر مدیریت آموزش‌ها در پنل ادمین
Admin tutorial management — add/edit/delete tutorials
"""
from __future__ import annotations

import logging

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode
from telegram.ext import (
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from core.database import get_db
from utils.decorators import admin_only

logger = logging.getLogger(__name__)

TUT_TITLE, TUT_CATEGORY, TUT_CONTENT, TUT_FILE, TUT_CONFIRM = range(5)


@admin_only
async def admin_tutorials_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from sqlalchemy import select
    from models.setting import Tutorial

    async with get_db() as session:
        result = await session.execute(
            select(Tutorial).order_by(Tutorial.category, Tutorial.order_position)
        )
        tutorials = result.scalars().all()

    if not tutorials:
        buttons = [[InlineKeyboardButton("➕ افزودن آموزش", callback_data="tut_admin:new")]]
        await update.effective_message.reply_html(
            "📚 <b>آموزش‌ها</b>\n\nهیچ آموزشی وجود ندارد.",
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        return

    buttons = [
        [InlineKeyboardButton(
            f"{'✅' if t.is_active else '❌'} {t.title[:30]}",
            callback_data=f"tut_admin:detail:{t.id}",
        )]
        for t in tutorials
    ]
    buttons.append([InlineKeyboardButton("➕ افزودن آموزش", callback_data="tut_admin:new")])
    await update.effective_message.reply_html(
        f"📚 <b>آموزش‌ها ({len(tutorials)} عدد)</b>",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


@admin_only
async def admin_tutorial_detail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    tut_id = int(query.data.split(":")[2])

    from models.setting import Tutorial
    async with get_db() as session:
        tut = await session.get(Tutorial, tut_id)

    if not tut:
        await query.edit_message_text("❌ آموزش یافت نشد.")
        return

    text = (
        f"📖 <b>{tut.title}</b>\n\n"
        f"📂 دسته: {tut.category}\n"
        f"📊 بازدید: {tut.view_count}\n"
        f"🔸 وضعیت: {'✅ فعال' if tut.is_active else '❌ غیرفعال'}\n"
        f"📎 نوع فایل: {tut.file_type or 'فقط متن'}"
    )
    buttons = [
        [
            InlineKeyboardButton(
                "❌ غیرفعال" if tut.is_active else "✅ فعال",
                callback_data=f"tut_admin:toggle:{tut_id}",
            ),
            InlineKeyboardButton("🗑 حذف", callback_data=f"tut_admin:delete:{tut_id}"),
        ],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="tut_admin:list")],
    ]
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))


@admin_only
async def admin_tutorial_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    tut_id = int(query.data.split(":")[2])

    from models.setting import Tutorial
    async with get_db() as session:
        tut = await session.get(Tutorial, tut_id)
        if tut:
            tut.is_active = not tut.is_active
            session.add(tut)

    query.data = f"tut_admin:detail:{tut_id}"
    await admin_tutorial_detail(update, context)


@admin_only
async def admin_tutorial_delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    tut_id = int(query.data.split(":")[2])

    from models.setting import Tutorial
    async with get_db() as session:
        tut = await session.get(Tutorial, tut_id)
        if tut:
            await session.delete(tut)

    await query.edit_message_text("✅ آموزش حذف شد.")


# ─────────────────────────────────────────────
# افزودن آموزش — Conversation
# ─────────────────────────────────────────────
@admin_only
async def new_tutorial_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data["new_tutorial"] = {}
    await query.edit_message_text(
        "📚 <b>افزودن آموزش جدید</b>\n\n📝 عنوان آموزش را وارد کنید:",
        parse_mode=ParseMode.HTML,
    )
    return TUT_TITLE


async def tutorial_title_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["new_tutorial"]["title"] = update.message.text.strip()
    await update.message.reply_text("📂 دسته‌بندی را وارد کنید (مثلاً: CapCut | Photoshop):")
    return TUT_CATEGORY


async def tutorial_category_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["new_tutorial"]["category"] = update.message.text.strip()
    await update.message.reply_text(
        "📝 متن آموزش را وارد کنید (یا /skip):"
    )
    return TUT_CONTENT


async def tutorial_content_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    if text != "/skip":
        context.user_data["new_tutorial"]["content"] = text.strip()
    await update.message.reply_text(
        "📎 فایل آموزشی ارسال کنید (عکس/ویدیو/سند) یا /skip برای بدون فایل:"
    )
    return TUT_FILE


async def tutorial_file_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.photo:
        context.user_data["new_tutorial"]["file_id"] = update.message.photo[-1].file_id
        context.user_data["new_tutorial"]["file_type"] = "photo"
    elif update.message.video:
        context.user_data["new_tutorial"]["file_id"] = update.message.video.file_id
        context.user_data["new_tutorial"]["file_type"] = "video"
    elif update.message.document:
        context.user_data["new_tutorial"]["file_id"] = update.message.document.file_id
        context.user_data["new_tutorial"]["file_type"] = "document"
    elif update.message.text == "/skip":
        pass

    t = context.user_data["new_tutorial"]
    text = (
        f"✅ <b>تأیید آموزش</b>\n\n"
        f"📝 عنوان: {t.get('title')}\n"
        f"📂 دسته: {t.get('category')}\n"
        f"📎 فایل: {'دارد' if t.get('file_id') else 'ندارد'}"
    )
    await update.message.reply_html(
        text,
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ ثبت", callback_data="tut_confirm:yes"),
                InlineKeyboardButton("❌ لغو", callback_data="tut_confirm:no"),
            ]
        ]),
    )
    return TUT_CONFIRM


async def tutorial_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "tut_confirm:no":
        await query.edit_message_text("❌ لغو شد.")
        context.user_data.pop("new_tutorial", None)
        return ConversationHandler.END

    t = context.user_data.pop("new_tutorial", {})

    from models.setting import Tutorial
    async with get_db() as session:
        tut = Tutorial(
            title=t.get("title", "بدون عنوان"),
            category=t.get("category", "عمومی"),
            content=t.get("content"),
            file_id=t.get("file_id"),
            file_type=t.get("file_type"),
            is_active=True,
        )
        session.add(tut)
        await session.flush()

    await query.edit_message_text(f"✅ آموزش «{t.get('title')}» ثبت شد!")
    return ConversationHandler.END


async def cancel_tutorial(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop("new_tutorial", None)
    await update.effective_message.reply_text("❌ لغو شد.")
    return ConversationHandler.END


def build_tutorial_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(new_tutorial_start, pattern="^tut_admin:new$")],
        states={
            TUT_TITLE:    [MessageHandler(filters.TEXT & ~filters.COMMAND, tutorial_title_received)],
            TUT_CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, tutorial_category_received)],
            TUT_CONTENT:  [MessageHandler(filters.TEXT, tutorial_content_received)],
            TUT_FILE: [
                MessageHandler(filters.PHOTO | filters.VIDEO | filters.Document.ALL, tutorial_file_received),
                MessageHandler(filters.Regex("^/skip$"), tutorial_file_received),
            ],
            TUT_CONFIRM: [CallbackQueryHandler(tutorial_confirm, pattern="^tut_confirm:")],
        },
        fallbacks=[MessageHandler(filters.COMMAND, cancel_tutorial)],
    )


def register_tutorial_admin_handlers(app) -> None:
    app.add_handler(build_tutorial_conversation())
    app.add_handler(CallbackQueryHandler(admin_tutorials_list, pattern="^tut_admin:list$"))
    app.add_handler(CallbackQueryHandler(admin_tutorial_detail, pattern="^tut_admin:detail:"))
    app.add_handler(CallbackQueryHandler(admin_tutorial_toggle, pattern="^tut_admin:toggle:"))
    app.add_handler(CallbackQueryHandler(admin_tutorial_delete, pattern="^tut_admin:delete:"))
