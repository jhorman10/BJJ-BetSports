import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.domain.services.match_aggregator_service import MatchAggregatorService


class _DummyFootballDataOrg:
    is_configured = False

    async def get_upcoming_matches(self, league_id):
        return []


class _DummyTheSportsDB:
    async def get_upcoming_fixtures(self, league_id, next_n):
        return []


class _DummyESPN:
    def __init__(self):
        self.calls: list[tuple[str, int]] = []

    async def get_upcoming_matches(self, league_id, days_ahead):
        self.calls.append((league_id, days_ahead))
        return []


def _build_service(espn: _DummyESPN) -> MatchAggregatorService:
    return MatchAggregatorService(
        football_data_uk=None,
        football_data_org=_DummyFootballDataOrg(),
        openfootball=None,
        thesportsdb=_DummyTheSportsDB(),
        espn=espn,
    )


def test_get_upcoming_matches_expands_window_for_libertadores():
    espn = _DummyESPN()
    service = _build_service(espn)

    asyncio.run(service.get_upcoming_matches("LIB"))

    assert espn.calls == [("LIB", 30)]


def test_get_upcoming_matches_keeps_short_window_for_domestic_leagues():
    espn = _DummyESPN()
    service = _build_service(espn)

    asyncio.run(service.get_upcoming_matches("E0"))

    assert espn.calls == [("E0", 7)]
