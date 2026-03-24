"""
Entry point — starts the Telegram bot and APScheduler.
"""
import logging
import os
print("DEBUG ENV KEYS:", sorted(k for k in os.environ if not k.startswith("_")), flush=True)
from telegram.ext import Application

from config import TELEGRAM_BOT_TOKEN
from bot import build_application
from scheduler import get_scheduler

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def _post_init(app: Application) -> None:
    get_scheduler().start()
    logger.info("APScheduler started.")


async def _post_shutdown(app: Application) -> None:
    get_scheduler().shutdown(wait=False)
    logger.info("APScheduler stopped.")


def main() -> None:
    app = build_application(
        TELEGRAM_BOT_TOKEN,
        post_init=_post_init,
        post_shutdown=_post_shutdown,
    )
    logger.info("Bot polling started.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
