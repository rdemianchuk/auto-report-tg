import os
from dotenv import load_dotenv

load_dotenv()

# Telegram
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]

# Google Ads — hardcoded test account
GOOGLE_ADS_CUSTOMER_ID = os.environ.get("GOOGLE_ADS_CUSTOMER_ID", "123-456-7890")

# Anthropic / Claude
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
CLAUDE_MODEL = "claude-sonnet-4-6"

# Override report month for demo (leave empty to use last completed calendar month)
# Format: YYYY-MM  e.g. "2025-07"
REPORT_MONTH_OVERRIDE = os.environ.get("REPORT_MONTH_OVERRIDE", "").strip()

# Scheduler defaults
DEFAULT_SCHEDULE_DAY = 1    # 1st of each month
DEFAULT_SCHEDULE_HOUR = 9   # 09:00
DEFAULT_SCHEDULE_MINUTE = 0
