"""
Generates a 1–2 sentence Ukrainian summary comparing two months of Google Ads data
using the Claude API.
"""
import anthropic

from config import ANTHROPIC_API_KEY, CLAUDE_MODEL
from google_ads_client import AdsMetrics


def _pct_change(current: float, previous: float) -> str:
    if previous == 0:
        return "н/д"
    delta = (current - previous) / previous * 100
    sign = "+" if delta >= 0 else ""
    return f"{sign}{delta:.1f}%"


def generate_summary(current: AdsMetrics, previous: AdsMetrics) -> str:
    prompt = f"""Ти аналітик Google Ads. Порівняй два місяці і напиши 1–2 речення українською мовою.
Будь конкретним: вкажи найважливіші зміни в цифрах (% або абсолютні значення).

{previous.month_label}:
  Витрати: ${previous.spend:,.2f}
  Ліди: {previous.leads}
  CTR: {previous.ctr * 100:.2f}%
  Ціна за лід: ${previous.cost_per_lead:.2f}

{current.month_label}:
  Витрати: ${current.spend:,.2f}
  Ліди: {current.leads}
  CTR: {current.ctr * 100:.2f}%
  Ціна за лід: ${current.cost_per_lead:.2f}

Зміни:
  Витрати: {_pct_change(current.spend, previous.spend)}
  Ліди: {_pct_change(current.leads, previous.leads)}
  CTR: {_pct_change(current.ctr, previous.ctr)}
  Ціна за лід: {_pct_change(current.cost_per_lead, previous.cost_per_lead)}

Напиши стисло і по суті, без вступних фраз."""

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()
