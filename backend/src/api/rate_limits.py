"""Shared rate limiter for all API endpoints.

Single Limiter instance so that storage/state is shared app-wide
and the exception handler registered in main.py catches violations
from every router consistently.
"""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

# Single shared limiter — main.py registers this on app.state.limiter
limiter = Limiter(key_func=get_remote_address)

# Predefined limit strings (tunable per endpoint category)
LIMIT_PREDICTIONS_READ = "60/minute"
LIMIT_PREDICTIONS_MATCH = "120/minute"  # cheap per-match lookup
LIMIT_MATCHES_LIVE = "60/minute"
LIMIT_MATCHES_QUERY = "30/minute"
LIMIT_SPORTS_PREDICT = "30/minute"  # expensive ML compute
LIMIT_SPORTS_READ = "60/minute"
LIMIT_PICKS_GENERATE = "20/minute"  # 90s timeout, heavy AI synthesis
LIMIT_PICKS_OTHER = "60/minute"
LIMIT_BEST_COMBINATION = "10/minute"  # combinatorial optimization
