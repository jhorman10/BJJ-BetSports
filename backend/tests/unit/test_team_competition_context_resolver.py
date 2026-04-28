import sys
from datetime import datetime
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.domain.constants import LEAGUES_METADATA
from src.domain.entities.entities import League, Match, Team
from src.domain.services.statistics_service import StatisticsService
from src.domain.services.team_competition_context_resolver import (
    TeamCompetitionContextResolver,
)


def _build_league(league_id: str, season: str | None = None) -> League:
    meta = LEAGUES_METADATA.get(league_id, {"name": league_id, "country": "Test"})
    return League(
        id=league_id,
        name=meta["name"],
        country=meta["country"],
        season=season,
    )


def _build_match(
    match_id: str,
    home_team_name: str,
    away_team_name: str,
    league_id: str,
    match_date: datetime,
    season: str | None = None,
) -> Match:
    return Match(
        id=match_id,
        home_team=Team(id=f"{match_id}-home", name=home_team_name),
        away_team=Team(id=f"{match_id}-away", name=away_team_name),
        league=_build_league(league_id, season=season),
        match_date=match_date,
        status="FT",
    )


def test_resolve_club_context_prefers_recent_competition_window():
    resolver = TeamCompetitionContextResolver()
    target_match = _build_match(
        "target",
        "Palmeiras FC",
        "River Plate",
        "LIB",
        datetime(2026, 4, 10),
        season="2026",
    )
    candidate_matches = [
        _build_match(
            "bra1-1",
            "Palmeiras",
            "Flamengo",
            "BRA1",
            datetime(2026, 3, 20),
            season="2026",
        ),
        _build_match(
            "bra1-2",
            "Santos",
            "Palmeiras",
            "BRA1",
            datetime(2026, 3, 5),
            season="2026",
        ),
        _build_match(
            "bra2-1",
            "Palmeiras",
            "Cruzeiro",
            "BRA2",
            datetime(2024, 3, 20),
            season="2024",
        ),
        _build_match(
            "bra2-2",
            "Palmeiras",
            "Sport Recife",
            "BRA2",
            datetime(2024, 3, 1),
            season="2024",
        ),
        _build_match(
            "bra2-3",
            "Palmeiras",
            "Vitoria",
            "BRA2",
            datetime(2024, 2, 10),
            season="2024",
        ),
        _build_match(
            "lib-1",
            "Palmeiras",
            "River Plate",
            "LIB",
            datetime(2026, 2, 12),
            season="2026",
        ),
    ]

    context = resolver.resolve("Palmeiras FC", target_match, candidate_matches)

    assert context.participant_type == "club"
    assert context.base_competition_id == "BRA1"
    assert "LIB" in context.support_competition_ids
    assert context.confidence > 0.7
    assert context.evidence["dominant_match_count"] == 2


def test_resolve_club_context_degrades_without_domestic_history():
    resolver = TeamCompetitionContextResolver()
    target_match = _build_match(
        "target",
        "River Plate",
        "Boca Juniors",
        "LIB",
        datetime(2026, 4, 10),
        season="2026",
    )
    candidate_matches = [
        _build_match(
            "lib-1",
            "River Plate",
            "Palmeiras",
            "LIB",
            datetime(2026, 2, 15),
            season="2026",
        ),
        _build_match(
            "sud-1",
            "Barcelona SC",
            "River Plate",
            "SUD",
            datetime(2025, 9, 18),
            season="2025",
        ),
    ]

    context = resolver.resolve("River Plate", target_match, candidate_matches)

    assert context.participant_type == "club"
    assert context.base_competition_id is None
    assert set(context.support_competition_ids) == {"LIB", "SUD"}
    assert context.confidence == 0.35
    assert context.evidence["resolution"] == "no_domestic_context"


def test_resolve_national_team_context_filters_club_leagues():
    resolver = TeamCompetitionContextResolver()
    target_match = _build_match(
        "target",
        "Spain",
        "France",
        "EURO",
        datetime(2026, 6, 10),
        season="2026",
    )
    candidate_matches = [
        _build_match(
            "wc-1",
            "Spain",
            "Germany",
            "WC",
            datetime(2025, 11, 18),
            season="2025",
        ),
        _build_match(
            "euro-1",
            "Spain",
            "Italy",
            "EURO",
            datetime(2026, 5, 20),
            season="2026",
        ),
        _build_match(
            "club-noise",
            "Spain",
            "Barcelona",
            "SP1",
            datetime(2026, 3, 1),
            season="2025-2026",
        ),
    ]

    context = resolver.resolve("Spain", target_match, candidate_matches)

    assert context.participant_type == "national_team"
    assert context.base_competition_id == "EURO"
    assert context.support_competition_ids == ("WC",)
    assert context.confidence == 0.9
    assert "SP1" in context.evidence["excluded_club_competitions"]


def test_resolve_club_context_reuses_statistics_normalization():
    resolver = TeamCompetitionContextResolver()
    target_match = _build_match(
        "target",
        "Manchester City FC",
        "Inter",
        "UCL",
        datetime(2026, 4, 9),
        season="2025-2026",
    )
    candidate_matches = [
        _build_match(
            "e0-1",
            "Man City",
            "Arsenal",
            "E0",
            datetime(2026, 3, 15),
            season="2025-2026",
        ),
        _build_match(
            "e0-2",
            "Tottenham",
            "Manchester City",
            "E0",
            datetime(2026, 2, 28),
            season="2025-2026",
        ),
        _build_match(
            "ucl-1",
            "Manchester City",
            "Inter",
            "UCL",
            datetime(2026, 3, 8),
            season="2025-2026",
        ),
    ]

    context = resolver.resolve("Manchester City FC", target_match, candidate_matches)

    assert context.participant_type == "club"
    assert context.base_competition_id == "E0"
    assert context.evidence["normalized_team_name"] == StatisticsService.normalize_team_name(
        "Manchester City FC"
    )
    assert "UCL" in context.support_competition_ids
