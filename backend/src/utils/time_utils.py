from datetime import datetime
from pytz import timezone

# Colombia timezone constant
COLOMBIA_TZ = timezone('America/Bogota')

def get_current_time() -> datetime:
    """Get current time in Colombia timezone."""
    return datetime.now(COLOMBIA_TZ)

def get_today_str() -> str:
    """Get today's date string in Colombia timezone (YYYY-MM-DD)."""
    return get_current_time().strftime("%Y-%m-%d")
