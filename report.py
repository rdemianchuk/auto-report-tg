"""
Builds the final report text from metrics + AI summary.
"""
from google_ads_client import AdsMetrics
from config import GOOGLE_ADS_CUSTOMER_ID


def _trend(current: float, previous: float) -> str:
    """Return a trend arrow based on direction."""
    if previous == 0:
        return ""
    if current > previous:
        return " ▲"
    if current < previous:
        return " ▼"
    return " ▬"


def _cost_trend(current: float, previous: float) -> str:
    """For cost metrics: up is bad (▲ red-ish), down is good (▼ green-ish)."""
    return _trend(current, previous)


def _pct(current: float, previous: float) -> str:
    if previous == 0:
        return ""
    delta = (current - previous) / previous * 100
    sign = "+" if delta >= 0 else ""
    return f" ({sign}{delta:.1f}%)"


def build_report(current: AdsMetrics, previous: AdsMetrics, summary: str) -> str:
    customer_url = (
        f"https://ads.google.com/aw/overview"
        f"?ocid={GOOGLE_ADS_CUSTOMER_ID.replace('-', '')}"
    )
    cur = current.currency or ""
    cur_label = f" {cur}" if cur else ""

    lines = [
        f"📊 *Звіт Google Ads — {current.month_label}*",
        "",
        f"💰 Витрати: *{current.spend:,.2f}{cur_label}*{_pct(current.spend, previous.spend)}{_cost_trend(current.spend, previous.spend)}",
        f"👥 Ліди: *{current.leads}*{_pct(current.leads, previous.leads)}{_trend(current.leads, previous.leads)}",
        f"📈 CTR: *{current.ctr * 100:.2f}%*{_pct(current.ctr, previous.ctr)}{_trend(current.ctr, previous.ctr)}",
        f"💵 Ціна за лід: *{current.cost_per_lead:.2f}{cur_label}*{_pct(current.cost_per_lead, previous.cost_per_lead)}{_cost_trend(current.cost_per_lead, previous.cost_per_lead)}",
        "",
        "🤖 *AI Summary:*",
        summary,
        "",
        f"🔗 [Google Ads]({customer_url})",
        "",
        f"_Порівняння з {previous.month_label}_",
    ]
    return "\n".join(lines)
