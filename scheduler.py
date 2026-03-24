"""
APScheduler wrapper — manages the monthly report job.
"""
from __future__ import annotations

import logging
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram import Bot

from config import (
    DEFAULT_SCHEDULE_DAY,
    DEFAULT_SCHEDULE_HOUR,
    DEFAULT_SCHEDULE_MINUTE,
)

logger = logging.getLogger(__name__)

JOB_ID = "monthly_report"

_scheduler: Optional[AsyncIOScheduler] = None


def get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler()
    return _scheduler


async def _send_report(bot: Bot, chat_id: int) -> None:
    """Scheduled job: generate and send the report."""
    # Import here to avoid circular imports
    from google_ads_client import fetch_last_two_months
    from ai_summary import generate_summary
    from report import build_report

    try:
        current, previous = fetch_last_two_months()
        summary = generate_summary(current, previous)
        text = build_report(current, previous, summary)
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="Markdown",
            disable_web_page_preview=True,
        )
        logger.info("Scheduled report sent successfully.")
    except Exception:
        logger.exception("Failed to send scheduled report.")
        await bot.send_message(
            chat_id=chat_id,
            text="⚠️ Не вдалося сформувати звіт. Перевірте логи.",
        )


def schedule_report(
    bot: Bot,
    chat_id: int,
    day: int = DEFAULT_SCHEDULE_DAY,
    hour: int = DEFAULT_SCHEDULE_HOUR,
    minute: int = DEFAULT_SCHEDULE_MINUTE,
) -> None:
    """Add (or replace) the monthly report job."""
    scheduler = get_scheduler()

    if scheduler.get_job(JOB_ID):
        scheduler.remove_job(JOB_ID)

    scheduler.add_job(
        _send_report,
        trigger=CronTrigger(day=day, hour=hour, minute=minute),
        id=JOB_ID,
        kwargs={"bot": bot, "chat_id": chat_id},
        replace_existing=True,
        name="Monthly Google Ads report",
    )
    logger.info("Report scheduled: day=%d, %02d:%02d", day, hour, minute)


def cancel_schedule() -> bool:
    """Remove the scheduled job. Returns True if it existed."""
    scheduler = get_scheduler()
    if scheduler.get_job(JOB_ID):
        scheduler.remove_job(JOB_ID)
        return True
    return False


def get_schedule_info() -> Optional[dict]:
    """Return info about the current schedule, or None if not set."""
    scheduler = get_scheduler()
    job = scheduler.get_job(JOB_ID)
    if not job:
        return None
    trigger: CronTrigger = job.trigger
    fields = {f.name: f for f in trigger.fields}
    return {
        "day": str(fields["day"]),
        "hour": str(fields["hour"]),
        "minute": str(fields["minute"]),
        "next_run": job.next_run_time,
    }
