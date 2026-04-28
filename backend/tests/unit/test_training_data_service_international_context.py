import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest

sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.domain.constants import LEAGUES_METADATA
from src.domain.entities.entities import League, Match, Team
from src.domain.services.match_enrichment_service import MatchEnrichmentService
from src.domain.services.statistics_service import StatisticsService
from src.application.services.training_data_service import TrainingDataService


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


def _build_service() -> TrainingDataService:
    return TrainingDataService(
        data_sources=Mock(),
        enrichment_service=MatchEnrichmentService(),
    )


@pytest.mark.asyncio
async def test_fetch_contextual_training_data_keeps_domestic_bundle_compatible():
    service = _build_service()
    domestic_matches = [
        _build_match(
            "e0-target",
            "Arsenal",
            "Chelsea",
            "E0",
            datetime(2026, 4, 10),
            season="2025-2026",
        )
    ]
    service.fetch_comprehensive_training_data = AsyncMock(return_value=domestic_matches)

    bundle = await service.fetch_contextual_training_data(["E0"], days_back=90)

    assert bundle.target_matches == domestic_matches
    assert bundle.support_matches == []
    assert bundle.support_matches_by_team == {}
    assert bundle.coverage_report == {
        "mode": "domestic",
        "requested_league_ids": ("E0",),
        "target_match_count": 1,
        "support_match_count": 0,
        "team_count": 0,
        "teams": {},
    }
    assert service.fetch_comprehensive_training_data.await_count == 1


@pytest.mark.asyncio
async def test_fetch_contextual_training_data_separates_target_and_support_for_club_tournaments():
    service = _build_service()
    target_matches = [
        _build_match(
            "lib-target",
            "Palmeiras FC",
            "River Plate",
            "LIB",
            datetime(2026, 4, 10),
            season="2026",
        )
    ]
    support_candidates = [
        target_matches[0],
        _build_match(
            "bra1-support",
            "Palmeiras",
            "Flamengo",
            "BRA1",
            datetime(2026, 3, 20),
            season="2026",
        ),
        _build_match(
            "lib-support",
            "Palmeiras",
            "Nacional",
            "LIB",
            datetime(2026, 2, 14),
            season="2026",
        ),
        _build_match(
            "arg1-support",
            "River Plate",
            "Boca Juniors",
            "ARG1",
            datetime(2026, 3, 19),
            season="2026",
        ),
        _build_match(
            "noise",
            "Real Madrid",
            "Barcelona",
            "SP1",
            datetime(2026, 3, 15),
            season="2025-2026",
        ),
    ]
    service.fetch_comprehensive_training_data = AsyncMock(
        side_effect=[target_matches, support_candidates]
    )

    bundle = await service.fetch_contextual_training_data(["LIB"], days_back=180)

    palmeiras_key = StatisticsService.normalize_team_name("Palmeiras FC")
    river_key = StatisticsService.normalize_team_name("River Plate")

    assert [match.id for match in bundle.target_matches] == ["lib-target"]
    assert {match.id for match in bundle.support_matches} == {
        "arg1-support",
        "bra1-support",
        "lib-support",
    }
    assert {match.id for match in bundle.support_matches_by_team[palmeiras_key]} == {
        "bra1-support",
        "lib-support",
    }
    assert {match.id for match in bundle.support_matches_by_team[river_key]} == {
        "arg1-support",
    }
    assert bundle.coverage_report["mode"] == "international"
    assert bundle.coverage_report["requested_league_ids"] == ("LIB",)
    assert bundle.coverage_report["target_match_count"] == 1
    assert bundle.coverage_report["support_match_count"] == 3
    assert bundle.coverage_report["team_count"] == 2
    assert bundle.coverage_report["teams"][palmeiras_key]["base_competition_id"] == "BRA1"
    assert bundle.coverage_report["teams"][river_key]["base_competition_id"] == "ARG1"
    assert "LIB" in bundle.coverage_report["teams"][palmeiras_key]["support_competition_ids"]
    assert service.fetch_comprehensive_training_data.await_count == 2


@pytest.mark.asyncio
async def test_fetch_contextual_training_data_uses_national_team_support_without_club_noise():
    service = _build_service()
    target_matches = [
        _build_match(
            "euro-target",
            "Spain",
            "France",
            "EURO",
            datetime(2026, 6, 10),
            season="2026",
        )
    ]
    support_candidates = [
        target_matches[0],
        _build_match(
            "spain-euro-support",
            "Spain",
            "Italy",
            "EURO",
            datetime(2026, 5, 22),
            season="2026",
        ),
        _build_match(
            "spain-wc-support",
            "Spain",
            "Germany",
            "WC",
            datetime(2025, 11, 18),
            season="2025",
        ),
        _build_match(
            "france-wc-support",
            "France",
            "Portugal",
            "WC",
            datetime(2025, 11, 17),
            season="2025",
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
    service.fetch_comprehensive_training_data = AsyncMock(
        side_effect=[target_matches, support_candidates]
    )

    bundle = await service.fetch_contextual_training_data(["EURO"], days_back=365)

    spain_key = StatisticsService.normalize_team_name("Spain")
    france_key = StatisticsService.normalize_team_name("France")

    assert {match.id for match in bundle.support_matches} == {
        "france-wc-support",
        "spain-euro-support",
        "spain-wc-support",
    }
    assert {
        match.league.id for match in bundle.support_matches_by_team[spain_key]
    } == {"EURO", "WC"}
    assert {
        match.league.id for match in bundle.support_matches_by_team[france_key]
    } == {"WC"}
    assert set(bundle.coverage_report["teams"][spain_key]) == {
        "participant_type",
        "base_competition_id",
        "support_competition_ids",
        "target_match_count",
        "support_match_count",
        "confidence",
        "evidence",
    }
    assert "SP1" in bundle.coverage_report["teams"][spain_key]["evidence"]["excluded_club_competitions"]
