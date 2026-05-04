import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest

sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.application.services.training_data_service import TrainingDataService
from src.domain.constants import LEAGUES_METADATA
from src.domain.entities.entities import League, Match, Team, TrainingDataContextBundle
from src.domain.services.match_enrichment_service import MatchEnrichmentService
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


async def _load_bundle(
    leagues: list[str],
    target_matches: list[Match],
    support_candidates: list[Match] | None = None,
) -> TrainingDataContextBundle:
    service = TrainingDataService(
        data_sources=Mock(),
        enrichment_service=MatchEnrichmentService(),
    )
    if support_candidates is None:
        service.fetch_comprehensive_training_data = AsyncMock(
            return_value=target_matches
        )
    else:
        service.fetch_comprehensive_training_data = AsyncMock(
            side_effect=[target_matches, support_candidates]
        )
    bundle = await service.fetch_contextual_training_data(leagues, days_back=365)
    return bundle


@pytest.mark.asyncio
async def test_lib_context_uses_domestic_support_for_both_clubs() -> None:
    target_match = _build_match(
        "lib-target",
        "Palmeiras FC",
        "River Plate",
        "LIB",
        datetime(2026, 4, 10),
        2,
        1,
        season="2026",
    )
    support_candidates = [
        target_match,
        _build_match(
            "palmeiras-bra1",
            "Palmeiras",
            "Flamengo",
            "BRA1",
            datetime(2026, 3, 20),
            3,
            1,
            season="2026",
        ),
        _build_match(
            "palmeiras-lib",
            "Palmeiras",
            "Nacional",
            "LIB",
            datetime(2026, 2, 14),
            1,
            1,
            season="2026",
        ),
        _build_match(
            "river-arg1",
            "River Plate",
            "Boca Juniors",
            "ARG1",
            datetime(2026, 3, 19),
            2,
            0,
            season="2026",
        ),
    ]

    bundle = await _load_bundle(["LIB"], [target_match], support_candidates)
    palmeiras_key = StatisticsService.normalize_team_name("Palmeiras FC")
    river_key = StatisticsService.normalize_team_name("River Plate")
    palmeiras_stats = StatisticsService.build_contextual_team_statistics(
        "Palmeiras FC", target_match, bundle
    )

    assert (
        bundle.coverage_report["teams"][palmeiras_key]["base_competition_id"] == "BRA1"
    )
    assert bundle.coverage_report["teams"][river_key]["base_competition_id"] == "ARG1"
    assert palmeiras_stats.domestic_stats is not None
    assert palmeiras_stats.domestic_stats["matches_played"] == 1
    assert palmeiras_stats.international_stats is not None
    assert palmeiras_stats.international_stats["matches_played"] == 2
    assert palmeiras_stats.target_competition_stats is not None
    assert palmeiras_stats.target_competition_stats["matches_played"] == 2


@pytest.mark.asyncio
async def test_sud_context_degrades_when_domestic_support_is_missing() -> None:
    target_match = _build_match(
        "sud-target",
        "Independiente del Valle",
        "Defensa y Justicia",
        "SUD",
        datetime(2026, 5, 12),
        1,
        0,
        season="2026",
    )
    support_candidates = [
        target_match,
        _build_match(
            "idv-ecu1",
            "Independiente del Valle",
            "LDU Quito",
            "ECU1",
            datetime(2026, 4, 2),
            2,
            0,
            season="2026",
        ),
    ]

    bundle = await _load_bundle(["SUD"], [target_match], support_candidates)
    defensa_key = StatisticsService.normalize_team_name("Defensa y Justicia")
    defensa_stats = StatisticsService.build_contextual_team_statistics(
        "Defensa y Justicia", target_match, bundle
    )

    assert bundle.coverage_report["teams"][defensa_key]["base_competition_id"] is None
    assert bundle.coverage_report["teams"][defensa_key]["support_match_count"] == 0
    assert (
        bundle.coverage_report["teams"][defensa_key]["evidence"]["resolution"]
        == "no_domestic_context"
    )
    assert defensa_stats.domestic_stats is None
    assert defensa_stats.international_stats is not None
    assert defensa_stats.international_stats["matches_played"] == 1
    assert defensa_stats.context_resolution_metadata is not None
    assert defensa_stats.context_resolution_metadata["support_match_count"] == 0


@pytest.mark.asyncio
async def test_ucl_context_blends_domestic_and_international_club_history() -> None:
    target_match = _build_match(
        "ucl-target",
        "Real Madrid",
        "Inter",
        "UCL",
        datetime(2026, 4, 9),
        2,
        2,
        season="2025-2026",
    )
    support_candidates = [
        target_match,
        _build_match(
            "real-sp1",
            "Real Madrid",
            "Valencia",
            "SP1",
            datetime(2026, 3, 30),
            3,
            0,
            season="2025-2026",
        ),
        _build_match(
            "real-ucl",
            "Real Madrid",
            "Bayern Munich",
            "UCL",
            datetime(2026, 2, 18),
            1,
            0,
            season="2025-2026",
        ),
        _build_match(
            "inter-i1",
            "Inter",
            "Juventus",
            "I1",
            datetime(2026, 3, 29),
            2,
            1,
            season="2025-2026",
        ),
    ]

    bundle = await _load_bundle(["UCL"], [target_match], support_candidates)
    real_stats = StatisticsService.build_contextual_team_statistics(
        "Real Madrid", target_match, bundle
    )

    assert real_stats.domestic_stats is not None
    assert real_stats.domestic_stats["matches_played"] == 1
    assert real_stats.international_stats is not None
    assert real_stats.international_stats["matches_played"] == 2
    assert real_stats.target_competition_stats is not None
    assert real_stats.target_competition_stats["matches_played"] == 2
    assert real_stats.context_resolution_metadata is not None
    assert real_stats.context_resolution_metadata["base_competition_id"] == "SP1"


@pytest.mark.asyncio
async def test_euro_context_uses_national_baseline_without_club_contamination() -> None:
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
    support_candidates = [
        target_match,
        _build_match(
            "spain-euro",
            "Spain",
            "Italy",
            "EURO",
            datetime(2026, 5, 22),
            2,
            2,
            season="2026",
        ),
        _build_match(
            "spain-wc",
            "Spain",
            "Germany",
            "WC",
            datetime(2025, 11, 18),
            1,
            3,
            season="2025",
        ),
        _build_match(
            "france-wc",
            "France",
            "Portugal",
            "WC",
            datetime(2025, 11, 17),
            2,
            1,
            season="2025",
        ),
        _build_match(
            "club-noise",
            "Spain",
            "Barcelona",
            "SP1",
            datetime(2026, 3, 1),
            0,
            1,
            season="2025-2026",
        ),
    ]

    bundle = await _load_bundle(["EURO"], [target_match], support_candidates)
    spain_key = StatisticsService.normalize_team_name("Spain")
    spain_stats = StatisticsService.build_contextual_team_statistics(
        "Spain", target_match, bundle
    )

    assert {match.league.id for match in bundle.support_matches_by_team[spain_key]} == {
        "EURO",
        "WC",
    }
    assert spain_stats.domestic_stats is None
    assert spain_stats.international_stats is not None
    assert spain_stats.international_stats["matches_played"] == 3
    assert spain_stats.target_competition_stats is not None
    assert spain_stats.target_competition_stats["matches_played"] == 2
    assert spain_stats.context_resolution_metadata is not None
    assert (
        spain_stats.context_resolution_metadata["participant_type"] == "national_team"
    )
    assert spain_stats.context_resolution_metadata["support_competition_ids"] == ("WC",)
    assert (
        "SP1"
        in spain_stats.context_resolution_metadata["evidence"][
            "excluded_club_competitions"
        ]
    )


@pytest.mark.asyncio
async def test_e0_context_preserves_domestic_regression_path() -> None:
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

    bundle = await _load_bundle(["E0"], [target_match])
    arsenal_stats = StatisticsService.build_contextual_team_statistics(
        "Arsenal", target_match, bundle
    )

    assert bundle.coverage_report["mode"] == "domestic"
    assert bundle.support_matches == []
    assert arsenal_stats.domestic_stats is not None
    assert arsenal_stats.domestic_stats["matches_played"] == 1
    assert arsenal_stats.international_stats is None
    assert arsenal_stats.target_competition_stats is not None
    assert arsenal_stats.target_competition_stats["matches_played"] == 1
