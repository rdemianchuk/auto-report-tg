"""
Google Ads API client.
Fetches spend, leads (conversions), CTR, cost-per-lead for a given date range.
"""
from __future__ import annotations

import calendar
import os
from dataclasses import dataclass
from datetime import date

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

from config import GOOGLE_ADS_CUSTOMER_ID


@dataclass
class AdsMetrics:
    month_label: str
    spend: float        # in account currency
    leads: int
    ctr: float          # fraction, e.g. 0.034 = 3.4%
    cost_per_lead: float
    currency: str       # e.g. "PLN", "USD"


def _month_range(year: int, month: int) -> tuple[str, str]:
    first = date(year, month, 1)
    last = date(year, month, calendar.monthrange(year, month)[1])
    return first.strftime("%Y-%m-%d"), last.strftime("%Y-%m-%d")


def _month_label(year: int, month: int) -> str:
    ua_months = [
        "", "Січень", "Лютий", "Березень", "Квітень", "Травень", "Червень",
        "Липень", "Серпень", "Вересень", "Жовтень", "Листопад", "Грудень",
    ]
    return f"{ua_months[month]} {year}"


def _previous_month(year: int, month: int) -> tuple[int, int]:
    if month == 1:
        return year - 1, 12
    return year, month - 1


def _metrics_query(start: str, end: str) -> str:
    return f"""
        SELECT
            metrics.cost_micros,
            metrics.conversions,
            metrics.clicks,
            metrics.impressions
        FROM campaign
        WHERE segments.date BETWEEN '{start}' AND '{end}'
          AND campaign.status != 'REMOVED'
    """


def _currency_query() -> str:
    return "SELECT customer.currency_code FROM customer LIMIT 1"


def _aggregate(rows) -> dict:
    total_cost_micros = 0
    total_conversions = 0.0
    total_clicks = 0
    total_impressions = 0

    for row in rows:
        m = row.metrics
        total_cost_micros += m.cost_micros
        total_conversions += m.conversions
        total_clicks += m.clicks
        total_impressions += m.impressions

    spend = total_cost_micros / 1_000_000
    leads = int(round(total_conversions))
    ctr = total_clicks / total_impressions if total_impressions else 0.0
    cost_per_lead = spend / leads if leads else 0.0

    return {
        "spend": spend,
        "leads": leads,
        "ctr": ctr,
        "cost_per_lead": cost_per_lead,
    }


def _build_client() -> GoogleAdsClient:
    return GoogleAdsClient.load_from_dict({
        "developer_token": os.environ["GOOGLE_ADS_DEVELOPER_TOKEN"],
        "client_id": os.environ["GOOGLE_ADS_CLIENT_ID"],
        "client_secret": os.environ["GOOGLE_ADS_CLIENT_SECRET"],
        "refresh_token": os.environ["GOOGLE_ADS_REFRESH_TOKEN"],
        "use_proto_plus": True,
    })


def _fetch_currency(service, customer_id: str) -> str:
    try:
        response = service.search(customer_id=customer_id, query=_currency_query())
        for row in response:
            return row.customer.currency_code
    except Exception:
        pass
    return ""


def fetch_metrics(year: int, month: int) -> AdsMetrics:
    client = _build_client()
    service = client.get_service("GoogleAdsService")
    customer_id = GOOGLE_ADS_CUSTOMER_ID.replace("-", "")
    start, end = _month_range(year, month)

    try:
        response = service.search_stream(
            customer_id=customer_id, query=_metrics_query(start, end)
        )
        rows = [row for batch in response for row in batch.results]
    except GoogleAdsException as exc:
        raise RuntimeError(f"Google Ads API error: {exc.failure}") from exc

    currency = _fetch_currency(service, customer_id)
    data = _aggregate(rows)

    return AdsMetrics(
        month_label=_month_label(year, month),
        spend=data["spend"],
        leads=data["leads"],
        ctr=data["ctr"],
        cost_per_lead=data["cost_per_lead"],
        currency=currency,
    )


def fetch_last_two_months() -> tuple[AdsMetrics, AdsMetrics]:
    """Return (current_month, previous_month) metrics.

    If REPORT_MONTH_OVERRIDE is set (e.g. "2025-07"), uses that as 'current'.
    Otherwise falls back to the last completed calendar month.
    """
    from config import REPORT_MONTH_OVERRIDE

    if REPORT_MONTH_OVERRIDE:
        cur_year, cur_month = (int(p) for p in REPORT_MONTH_OVERRIDE.split("-"))
    else:
        today = date.today()
        if today.month == 1:
            cur_year, cur_month = today.year - 1, 12
        else:
            cur_year, cur_month = today.year, today.month - 1

    prev_year, prev_month = _previous_month(cur_year, cur_month)

    current = fetch_metrics(cur_year, cur_month)
    previous = fetch_metrics(prev_year, prev_month)
    return current, previous
