"""
Telegram bot handlers.
"""
from __future__ import annotations

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from config import TELEGRAM_CHAT_ID
from scheduler import cancel_schedule, get_schedule_info, schedule_report

logger = logging.getLogger(__name__)

# ConversationHandler states
AWAITING_SCHEDULE_CONFIRM = 1


# ── Keyboards ──────────────────────────────────────────────────────────────

def _main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📊 Відправити зараз", callback_data="send_now"),
            InlineKeyboardButton("🕐 Автоматично", callback_data="auto"),
        ]
    ])


def _schedule_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Підтвердити", callback_data="schedule_confirm")],
        [InlineKeyboardButton("❌ Скасувати розклад", callback_data="schedule_cancel")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back")],
    ])


# ── Helpers ────────────────────────────────────────────────────────────────

async def _generate_and_send(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fetch data, build report, send it."""
    from google_ads_client import fetch_last_two_months
    
    from ai_summary import generate_summary
    from report import build_report

    msg = update.effective_message
    status = await msg.reply_text("⏳ Збираю дані з Google Ads…")

    try:
        current, previous = fetch_last_two_months()
        await status.edit_text("🤖 Генерую AI summary…")
        summary = generate_summary(current, previous)
        
        text = build_report(current, previous, summary)
        await status.delete()
        await context.bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=text,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
        )
    except Exception as exc:
        logger.exception("Failed to generate report")
        await status.edit_text(f"⚠️ Помилка: {exc}")


# ── Command handlers ───────────────────────────────────────────────────────

async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    user = update.effective_user
    await update.message.reply_text(
        f"Chat ID: `{chat.id}`\nUser ID: `{user.id}`\nChat type: {chat.type}",
        parse_mode=ParseMode.MARKDOWN,
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    info = get_schedule_info()
    schedule_text = (
        f"\n\n🕐 Активний розклад: {info['day']}-го числа о "
        f"{info['hour'].zfill(2)}:{info['minute'].zfill(2)}"
        f"\nНаступний запуск: {info['next_run'].strftime('%d.%m.%Y %H:%M')}"
        if info else ""
    )
    await update.message.reply_text(
        f"👋 Привіт! Це бот для Google Ads звітів.\n"
        f"Оберіть дію:{schedule_text}",
        reply_markup=_main_keyboard(),
        parse_mode=ParseMode.MARKDOWN,
    )


# ── Callback query handlers ────────────────────────────────────────────────

async def cb_send_now(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.answer()
    await _generate_and_send(update, context)


async def cb_auto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    info = get_schedule_info()
    if info:
        status_line = (
            f"✅ Зараз активний розклад: *{info['day']}-го числа* о "
            f"*{info['hour'].zfill(2)}:{info['minute'].zfill(2)}*\n"
            f"Наступний запуск: {info['next_run'].strftime('%d.%m.%Y %H:%M')}\n\n"
        )
    else:
        status_line = "Розклад не активний.\n\n"

    await query.edit_message_text(
        f"{status_line}"
        "📅 Стандартний розклад: *1-го числа о 09:00*\n\n"
        "Підтвердити стандартний розклад або скасувати поточний?",
        reply_markup=_schedule_keyboard(),
        parse_mode=ParseMode.MARKDOWN,
    )
    return AWAITING_SCHEDULE_CONFIRM


async def cb_schedule_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    schedule_report(bot=context.bot)
    info = get_schedule_info()

    await query.edit_message_text(
        f"✅ Розклад встановлено: *1-го числа о 09:00*\n"
        f"Наступний запуск: {info['next_run'].strftime('%d.%m.%Y %H:%M')}",
        reply_markup=_main_keyboard(),
        parse_mode=ParseMode.MARKDOWN,
    )
    return ConversationHandler.END


async def cb_schedule_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    removed = cancel_schedule()
    text = "🗑 Розклад скасовано." if removed else "ℹ️ Активного розкладу не було."
    await query.edit_message_text(text, reply_markup=_main_keyboard())
    return ConversationHandler.END


async def cb_back(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Оберіть дію:", reply_markup=_main_keyboard())
    return ConversationHandler.END


# ── Application builder ────────────────────────────────────────────────────

def build_application(token: str, post_init=None, post_shutdown=None) -> Application:
    builder = Application.builder().token(token)
    if post_init:
        builder = builder.post_init(post_init)
    if post_shutdown:
        builder = builder.post_shutdown(post_shutdown)
    app = builder.build()

    auto_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(cb_auto, pattern="^auto$")],
        states={
            AWAITING_SCHEDULE_CONFIRM: [
                CallbackQueryHandler(cb_schedule_confirm, pattern="^schedule_confirm$"),
                CallbackQueryHandler(cb_schedule_cancel, pattern="^schedule_cancel$"),
                CallbackQueryHandler(cb_back, pattern="^back$"),
            ]
        },
        fallbacks=[CallbackQueryHandler(cb_back, pattern="^back$")],
        per_chat=True,
    )

    app.add_handler(CommandHandler("id", get_id))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(cb_send_now, pattern="^send_now$"))
    app.add_handler(auto_conv)

    return app
