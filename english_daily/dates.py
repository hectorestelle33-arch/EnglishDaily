from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


try:
    APP_TIMEZONE = ZoneInfo("Asia/Shanghai")
except ZoneInfoNotFoundError:
    APP_TIMEZONE = timezone(timedelta(hours=8), name="Asia/Shanghai")


def app_today() -> date:
    return datetime.now(APP_TIMEZONE).date()


def app_today_iso() -> str:
    return app_today().isoformat()


def parse_app_date(value: str) -> date | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = parsedate_to_datetime(value)
        except (TypeError, ValueError, IndexError, OverflowError):
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=APP_TIMEZONE)
    return parsed.astimezone(APP_TIMEZONE).date()


def recent_allowed_dates(base_date: date | None = None, days: int = 3) -> set[date]:
    base = base_date or app_today()
    return {base - timedelta(days=offset) for offset in range(days)}
