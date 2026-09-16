"""
Unit tests for the best-combination use case (Phase 3.2).

Exercises the injected per-sport fetchers: happy path, coverage errors,
neg-EV rejection, filter passthrough, and fetcher failure semantics.
"""

from __future__ import annotations

import pytest
from src.api.dtos.best_combination_dtos import BestCombinationRequest
from src.application.use_cases.best_combination_use_case import BestCombinationUseCase
from src.domain.services.combination_optimizer import CombinationError


def raw_pick(sport: str = "soccer", match_id: str = "m1", **overrides) -> dict:
    default_league = {
        "soccer": "E0",
        "tennis": "WTA",
        "baseball": "MLB",
        "basketball": "NBA",
    }.get(sport, "L0")
    base = {
        "sport": sport,
        "match_id": match_id,
        "match_label": f"{sport} label {match_id}",
        "pick_label": "ML_H",
        "probability": 0.60,
        "odds": 2.05,
        "confidence_level": "high",
        "is_recommended": True,
        "priority_score": 60.0,
        "is_ml_confirmed": True,
        "is_ia_confirmed": False,
        "league": default_league,
    }
    base.update(overrides)
    return base


def fetcher(picks: list[dict]):
    async def _fetch() -> list[dict]:
        return picks

    return _fetch


def broken_fetcher():
    async def _fetch() -> list[dict]:
        raise RuntimeError("network down")

    return _fetch


def use_case(**pools_source) -> BestCombinationUseCase:
    fetch_pools = {sport: fetcher(picks or []) for sport, picks in pools_source.items()}
    return BestCombinationUseCase(fetch_pools=fetch_pools)


FOUR_POOLS = {
    "soccer": [raw_pick("soccer", "s1")],
    "tennis": [raw_pick("tennis", "t1")],
    "baseball": [raw_pick("baseball", "b1")],
    "basketball": [raw_pick("basketball", "bb1")],
}


class TestExecuteHappyPath:
    async def test_returns_four_legs(self) -> None:
        uc = use_case(**FOUR_POOLS)
        response = await uc.execute(BestCombinationRequest())
        assert len(response.legs) == 4
        assert {leg.sport for leg in response.legs} == {
            "soccer",
            "tennis",
            "baseball",
            "basketball",
        }
        assert response.aggregate.total_probability > 0
        assert response.aggregate.expected_value > 0
        assert response.independence_disclaimer
        assert response.generated_at
        assert response.stake.suggested_stake_pct > 0

    async def test_legs_carry_unified_fields(self) -> None:
        uc = use_case(**FOUR_POOLS)
        response = await uc.execute(BestCombinationRequest())
        leg = response.legs[0]
        assert leg.match_id
        assert leg.match_label
        assert leg.pick_label
        assert leg.odds_source in ("market", "fair")

    async def test_min_probability_passthrough(self) -> None:
        pools = {
            **FOUR_POOLS,
            "soccer": [
                raw_pick("soccer", "s1", probability=0.80, priority_score=90.0),
                raw_pick("soccer", "s2", probability=0.70, priority_score=95.0),
            ],
        }
        uc = use_case(**pools)
        response = await uc.execute(BestCombinationRequest(min_probability=0.75))
        soccer_leg = [leg for leg in response.legs if leg.sport == "soccer"][0]
        assert soccer_leg.match_id == "s1"

    async def test_exclude_leagues_passthrough(self) -> None:
        pools = {
            **FOUR_POOLS,
            "soccer": [
                raw_pick("soccer", "s1", league="E0"),
                raw_pick("soccer", "s2", league="E1", priority_score=10.0),
            ],
        }
        uc = use_case(**pools)
        response = await uc.execute(BestCombinationRequest(exclude_leagues=["E0"]))
        soccer_leg = [leg for leg in response.legs if leg.sport == "soccer"][0]
        assert soccer_leg.league == "E1"


class TestErrorPaths:
    async def test_insufficient_pool(self) -> None:
        uc = use_case(
            soccer=[raw_pick("soccer", "s1")],
            basketball=[raw_pick("basketball", "bb1")],
        )
        with pytest.raises(CombinationError) as exc:
            await uc.execute(BestCombinationRequest())
        assert exc.value.code == "insufficient_pool"
        assert set(exc.value.missing_sports or []) == {"tennis", "baseball"}

    async def test_no_picks_available(self) -> None:
        uc = use_case()
        with pytest.raises(CombinationError) as exc:
            await uc.execute(BestCombinationRequest())
        assert exc.value.code == "no_picks_available"

    async def test_no_positive_ev(self) -> None:
        pools = {
            "soccer": [raw_pick("soccer", "s1", probability=0.50, odds=0.0)],
            "tennis": [raw_pick("tennis", "t1", probability=0.50, odds=0.0)],
            "baseball": [raw_pick("baseball", "b1", probability=0.50, odds=0.0)],
            "basketball": [raw_pick("basketball", "bb1", probability=0.50, odds=0.0)],
        }
        uc = use_case(**pools)
        with pytest.raises(CombinationError) as exc:
            await uc.execute(BestCombinationRequest())
        assert exc.value.code == "no_positive_ev"


class TestFetcherFailure:
    async def test_broken_fetcher_treated_as_empty_pool(self) -> None:
        uc = BestCombinationUseCase(
            fetch_pools={
                "soccer": fetcher([raw_pick("soccer", "s1")]),
                "tennis": broken_fetcher(),
                "baseball": fetcher([raw_pick("baseball", "b1")]),
                "basketball": fetcher([raw_pick("basketball", "bb1")]),
            }
        )
        with pytest.raises(CombinationError) as exc:
            await uc.execute(BestCombinationRequest())
        assert exc.value.code == "insufficient_pool"
        assert "tennis" in (exc.value.missing_sports or [])
