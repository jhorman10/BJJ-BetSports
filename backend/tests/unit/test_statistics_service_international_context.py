import sys
from datetime import datetime
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.domain.constants import LEAGUES_METADATA
from src.domain.entities.entities import League, Match, Team, TrainingDataContextBundle
from src.domain.services.statistics_service import StatisticsService


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
    home_goals: int,
    away_goals: int,
    season: str | None = None,
) -> Match:
    return Match(
        id=match_id,
        home_team=Team(id=f"{match_id}-home", name=home_team_name),
        away_team=Team(id=f"{match_id}-away", name=away_team_name),
        league=_build_league(league_id, season=season),
        match_date=match_date,
        home_goals=home_goals,
        away_goals=away_goals,
        status="FT",
    )


def test_build_contextual_team_statistics_preserves_domestic_legacy_shape() -> None:
    target_match = _build_match(
        "e0-target",
        "Arsenal",
        "Chelsea",
        "E0",
        datetime(2026, 4, 10),
        2,
        1,
        season="2025-2026",
    )
    context_bundle = TrainingDataContextBundle(
        target_matches=[target_match],
        support_matches=[],
        support_matches_by_team={},
        coverage_report={
            "mode": "domestic",
            "requested_league_ids": ("E0",),
            "teams": {},
        },
    )

    stats = StatisticsService.build_contextual_team_statistics(
        "Arsenal", target_match, context_bundle
    )

    assert stats.matches_played == 1
    assert stats.wins == 1
    assert stats.domestic_stats is not None
    assert stats.domestic_stats["matches_played"] == 1
    assert stats.international_stats is None
    assert stats.target_competition_stats is not None
    assert stats.target_competition_stats["matches_played"] == 1
    assert stats.context_resolution_metadata is not None
    assert stats.context_resolution_metadata["mode"] == "domestic"


def test_build_contextual_team_statistics_separates_club_contexts() -> None:
    target_match = _build_match(
        "lib-target",
        "Palmeiras",
        "River Plate",
        "LIB",
        datetime(2026, 4, 10),
        2,
        0,
        season="2026",
    )
    lib_support = _build_match(
        "lib-support",
        "Palmeiras",
        "Nacional",
        "LIB",
        datetime(2026, 2, 14),
        1,
        1,
        season="2026",
    )
    bra1_support = _build_match(
        "bra1-support",
        "Palmeiras",
        "Flamengo",
        "BRA1",
        datetime(2026, 3, 20),
        3,
        1,
        season="2026",
    )
    context_bundle = TrainingDataContextBundle(
        target_matches=[target_match],
        support_matches=[lib_support, bra1_support],
        support_matches_by_team={
            StatisticsService.normalize_team_name("Palmeiras"): [
                bra1_support,
                lib_support,
            ]
        },
        coverage_report={
            "mode": "international",
            "requested_league_ids": ("LIB",),
            "teams": {
                StatisticsService.normalize_team_name("Palmeiras"): {
                    "participant_type": "club",
                    "base_competition_id": "BRA1",
                    "support_competition_ids": ("LIB",),
                    "confidence": 0.92,
                    "evidence": {"resolution": "resolved"},
                }
            },
        },
    )

    stats = StatisticsService.build_contextual_team_statistics(
        "Palmeiras", target_match, context_bundle
    )

    assert stats.matches_played == 3
    assert stats.domestic_stats is not None
    assert stats.domestic_stats["matches_played"] == 1
    assert stats.international_stats is not None
    assert stats.international_stats["matches_played"] == 2
    assert stats.target_competition_stats is not None
    assert stats.target_competition_stats["matches_played"] == 2
    assert stats.context_resolution_metadata is not None
    assert stats.context_resolution_metadata["base_competition_id"] == "BRA1"
    assert stats.context_resolution_metadata["support_match_count"] == 2


def test_build_contextual_team_statistics_keeps_national_team_stats() -> None:
    target_match = _build_match(
        "euro-target",
        "Spain",
        "France",
        "EURO",
        datetime(2026, 6, 10),
        1,
        0,
        season="2026",
    )
    euro_support = _build_match(
        "euro-support",
        "Spain",
        "Italy",
        "EURO",
        datetime(2026, 5, 22),
        2,
        2,
        season="2026",
    )
    wc_support = _build_match(
        "wc-support",
        "Spain",
        "Germany",
        "WC",
        datetime(2025, 11, 18),
        1,
        3,
        season="2025",
    )
    context_bundle = TrainingDataContextBundle(
        target_matches=[target_match],
        support_matches=[euro_support, wc_support],
        support_matches_by_team={
            StatisticsService.normalize_team_name("Spain"): [
                euro_support,
                wc_support,
            ]
        },
        coverage_report={
            "mode": "international",
            "requested_league_ids": ("EURO",),
            "teams": {
                StatisticsService.normalize_team_name("Spain"): {
                    "participant_type": "national_team",
                    "base_competition_id": "EURO",
                    "support_competition_ids": ("WC",),
                    "confidence": 0.9,
                    "evidence": {"excluded_club_competitions": ["SP1"]},
                }
            },
        },
    )

    stats = StatisticsService.build_contextual_team_statistics(
        "Spain", target_match, context_bundle
    )

    assert stats.matches_played == 3
    assert stats.domestic_stats is None
    assert stats.international_stats is not None
    assert stats.international_stats["matches_played"] == 3
    assert stats.target_competition_stats is not None
    assert stats.target_competition_stats["matches_played"] == 2
    assert stats.context_resolution_metadata is not None
    assert stats.context_resolution_metadata["participant_type"] == "national_team"
