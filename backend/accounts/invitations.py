from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import holidays


COLOMBIA_TIME_ZONE = ZoneInfo("America/Bogota")
COLOMBIA_HOLIDAYS = holidays.country_holidays("CO")


def add_colombia_business_days(start_at: datetime, business_days: int) -> datetime:
    if start_at.utcoffset() is None:
        raise ValueError("start_at must be timezone-aware.")
    if business_days < 0:
        raise ValueError("business_days must be non-negative.")

    local_start = start_at.astimezone(COLOMBIA_TIME_ZONE)
    expiry_date = local_start.date()
    days_added = 0

    while days_added < business_days:
        expiry_date += timedelta(days=1)
        if expiry_date.weekday() < 5 and expiry_date not in COLOMBIA_HOLIDAYS:
            days_added += 1

    return local_start.replace(
        year=expiry_date.year,
        month=expiry_date.month,
        day=expiry_date.day,
    )
