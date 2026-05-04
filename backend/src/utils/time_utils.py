from datetime import datetime
from typing import Optional

from pytz import timezone, utc

# Colombia timezone constant
COLOMBIA_TZ = timezone("America/Bogota")


def get_current_time() -> datetime:
    """Get current time in Colombia timezone."""
    return datetime.now(COLOMBIA_TZ)


def get_today_str() -> str:
    """Get today's date string in Colombia timezone (YYYY-MM-DD)."""
    return get_current_time().strftime("%Y-%m-%d")


def to_colombia_time(dt: datetime) -> datetime:
    """Convert any datetime to Colombia timezone."""
    if dt.tzinfo is None:
        # Treat naive datetimes as UTC before converting.
        dt = utc.localize(dt)

    return dt.astimezone(COLOMBIA_TZ)


def is_future_time(dt: Optional[datetime]) -> bool:
    """Return True when a datetime is still in the future in Colombia TZ.

    Mongo reads may yield naive datetimes even when the application stored aware
    values, so normalize before comparing against the current app clock.
    """
    if dt is None:
        return False

    return to_colombia_time(dt) > get_current_time()
