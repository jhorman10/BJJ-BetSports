"""
Unit tests for the best-combination optimizer (Phase 3.1/3.3).

Covers pool aggregation, quality filtering, best-available fallback, odds
resolution (market vs fair), totals math, neg-EV rejection, coverage errors,
and Kelly/RiskManager stake caps.
"""

from __future__ import annotations

import pytest
from src.domain.services.combination_optimizer import (
    CombinationError,
    CombinationOptimizer,
)
from src.domain.services.kelly_sizer import KellySizer
from src.domain.services.risk_management.risk_manager import RiskManager


def raw_pick(sport: str = "soccer", match_id: str = "m1", **overrides) -> dict:
    """Build a raw pick dict in the unified vocabulary."""
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


def normalized(**sport_raw: list[dict]) -> dict[str, list]:
    """Aggregate per-sport raw lists into normalized pools."""
    return {
        sport: OPT.aggregate_pools({sport: picks})[sport]
        for sport, picks in sport_raw.items()
    }


def four_sport_pools(**overrides) -> dict[str, list[dict]]:
    """One quality pick per sport with market odds (positive edge)."""
    pools = {
        "soccer": [
            raw_pick("soccer", "m-s1", probability=0.65, odds=1.90, league="E0"),
            raw_pick("soccer", "m-s2", probability=0.20, odds=5.00, league="E1"),
        ],
        "tennis": [
            raw_pick("tennis", "m-t1", probability=0.70, odds=2.10, league="WTA")
        ],
        "baseball": [
            raw_pick("baseball", "m-b1", probability=0.62, odds=1.85, league="MLB")
        ],
        "basketball": [
            raw_pick("basketball", "m-bb1", probability=0.72, odds=2.25, league="NBA")
        ],
    }
    pools.update(overrides)
    return pools


OPT = CombinationOptimizer()


class TestAggregatePools:
    def test_drops_picks_missing_match_id(self) -> None:
        pools = OPT.aggregate_pools(
            {
                "soccer": [
                    raw_pick("soccer", match_id=None),  # type: ignore[arg-type]
                    raw_pick("soccer", match_id="m1"),
                ]
            }
        )
        assert len(pools["soccer"]) == 1
        assert pools["soccer"][0].match_id == "m1"

    def test_drops_invalid_probability(self) -> None:
        pools = OPT.aggregate_pools(
            {
                "soccer": [
                    raw_pick("soccer", probability=0.0),
                    raw_pick("soccer", probability=1.1),
                    raw_pick("soccer", probability=-0.5),
                    raw_pick("soccer", probability=0.75, match_id="ok"),
                ]
            }
        )
        assert len(pools["soccer"]) == 1
        assert pools["soccer"][0].probability == 0.75

    def test_drops_pick_without_label(self) -> None:
        pools = OPT.aggregate_pools(
            {"tennis": [raw_pick("tennis", pick_label=None, market_label=None)]}
        )
        assert pools["tennis"] == []

    def test_sport_is_forced_from_key(self) -> None:
        pools = OPT.aggregate_pools({"basketball": [raw_pick("soccer", match_id="m1")]})
        assert pools["basketball"][0].sport == "basketball"

    def test_accepts_market_label_as_pick_label_alias(self) -> None:
        pools = OPT.aggregate_pools(
            {"tennis": [raw_pick("tennis", pick_label=None, market_label="ML_H")]}
        )
        assert pools["tennis"][0].pick_label == "ML_H"


class TestQualityFilter:
    def test_soccer_requires_ml_or_ia_confirmed(self) -> None:
        soccer = [
            raw_pick("soccer", "m1", is_ml_confirmed=False, is_ia_confirmed=False),
            raw_pick("soccer", "m2", is_ml_confirmed=True, is_ia_confirmed=False),
            raw_pick("soccer", "m3", is_ml_confirmed=False, is_ia_confirmed=True),
            raw_pick("soccer", "m4", is_ml_confirmed=True, is_ia_confirmed=True),
        ]
        result = OPT.build_combination(
            normalized(
                soccer=soccer,
                tennis=[raw_pick("tennis", "t1")],
                baseball=[raw_pick("baseball", "b1")],
                basketball=[raw_pick("basketball", "bb1")],
            )
        )
        soccer_leg = [leg for leg in result.legs if leg.sport == "soccer"][0]
        assert soccer_leg.match_id == "m2"  # highest priority among quality picks

    def test_other_sports_require_high_and_recommended(self) -> None:
        tennis = [
            raw_pick("tennis", "t1", confidence_level="high", is_recommended=False),
            raw_pick("tennis", "t2", confidence_level="medium", is_recommended=True),
            raw_pick(
                "tennis",
                "t3",
                confidence_level="high",
                is_recommended=True,
                priority_score=99.0,
            ),
        ]
        result = OPT.build_combination(
            normalized(
                soccer=[raw_pick("soccer", "s1")],
                tennis=tennis,
                baseball=[raw_pick("baseball", "b1")],
                basketball=[raw_pick("basketball", "bb1")],
            )
        )
        tennis_leg = [leg for leg in result.legs if leg.sport == "tennis"][0]
        assert tennis_leg.match_id == "t3"


class TestBuildCombination:
    def test_happy_path_four_legs_and_totals(self) -> None:
        pools = OPT.aggregate_pools(four_sport_pools())
        result = OPT.build_combination(pools)
        assert len(result.legs) == 4
        assert {leg.sport for leg in result.legs} == {
            "soccer",
            "tennis",
            "baseball",
            "basketball",
        }
        # product of probabilities: 0.65*0.70*0.62*0.72 = 0.203112 -> 0.2031
        assert result.totals.total_probability == pytest.approx(0.2031, abs=1e-3)
        # all market odds -> product: 1.90*2.10*1.85*2.25 = 16.603875 -> 16.6
        assert result.totals.total_odds == pytest.approx(16.60, abs=1e-2)
        assert result.totals.mixed_odds is False
        assert result.totals.expected_value == pytest.approx(
            result.totals.total_probability * result.totals.total_odds - 1,
            abs=1e-3,
        )
        assert result.stake.suggested_stake_pct > 0
        assert 1 <= result.stake.risk_level <= 5

    def test_picks_best_by_priority_then_probability(self) -> None:
        pool = [
            raw_pick("soccer", "low-prio", priority_score=10.0, probability=0.9),
            raw_pick("soccer", "high-prio", priority_score=80.0, probability=0.3),
        ]
        pools = OPT.aggregate_pools(
            {
                "soccer": pool,
                "tennis": [raw_pick("tennis", "t1")],
                "baseball": [raw_pick("baseball", "b1")],
                "basketball": [raw_pick("basketball", "bb1")],
            }
        )
        result = OPT.build_combination(pools)
        soccer_leg = [leg for leg in result.legs if leg.sport == "soccer"][0]
        assert soccer_leg.match_id == "high-prio"

    def test_priority_tie_breaks_by_probability(self) -> None:
        pool = [
            raw_pick("soccer", "p60", priority_score=50.0, probability=0.60),
            raw_pick("soccer", "p80", priority_score=50.0, probability=0.80),
        ]
        pools = OPT.aggregate_pools(
            {
                "soccer": pool,
                "tennis": [raw_pick("tennis", "t1")],
                "baseball": [raw_pick("baseball", "b1")],
                "basketball": [raw_pick("basketball", "bb1")],
            }
        )
        result = OPT.build_combination(pools)
        soccer_leg = [leg for leg in result.legs if leg.sport == "soccer"][0]
        assert soccer_leg.match_id == "p80"

    def test_fallback_when_quality_pool_empty(self) -> None:
        pools = OPT.aggregate_pools(
            {
                "soccer": [raw_pick("soccer", "s1")],
                "tennis": [
                    # fails quality gate (high+recommended)
                    raw_pick(
                        "tennis",
                        "t1",
                        confidence_level="low",
                        is_recommended=False,
                    )
                ],
                "baseball": [raw_pick("baseball", "b1")],
                "basketball": [raw_pick("basketball", "bb1")],
            }
        )
        result = OPT.build_combination(pools)
        tennis_leg = [leg for leg in result.legs if leg.sport == "tennis"][0]
        assert tennis_leg.match_id == "t1"
        assert tennis_leg.confidence_warning is True
        assert any("tennis" in w and "alta confianza" in w for w in result.warnings)

    def test_fallback_leg_forces_is_recommended_false(self) -> None:
        """W-2: a fallback pick that IS recommended in the raw data must still
        be presented as not recommended on the assembled leg."""
        pools = OPT.aggregate_pools(
            {
                "soccer": [raw_pick("soccer", "s1")],
                "tennis": [
                    # is_recommended=True but fails the quality gate
                    raw_pick(
                        "tennis",
                        "t1",
                        confidence_level="medium",
                        is_recommended=True,
                        priority_score=99.0,
                    )
                ],
                "baseball": [raw_pick("baseball", "b1")],
                "basketball": [raw_pick("basketball", "bb1")],
            }
        )
        result = OPT.build_combination(pools)
        tennis_leg = [leg for leg in result.legs if leg.sport == "tennis"][0]
        assert tennis_leg.confidence_warning is True
        assert tennis_leg.is_recommended is False

    def test_high_confidence_leg_keeps_recommended_flag(self) -> None:
        """W-2 guard: a quality-pool leg preserves its is_recommended flag."""
        pools = OPT.aggregate_pools(
            {
                "soccer": [raw_pick("soccer", "s1")],
                "tennis": [
                    raw_pick(
                        "tennis", "t1", confidence_level="high", is_recommended=True
                    )
                ],
                "baseball": [raw_pick("baseball", "b1")],
                "basketball": [raw_pick("basketball", "bb1")],
            }
        )
        result = OPT.build_combination(pools)
        tennis_leg = [leg for leg in result.legs if leg.sport == "tennis"][0]
        assert tennis_leg.confidence_warning is False
        assert tennis_leg.is_recommended is True

    def test_fair_odds_fallback_when_odds_missing(self) -> None:
        pools = OPT.aggregate_pools(
            {
                "soccer": [raw_pick("soccer", "s1", odds=0.0)],
                "tennis": [raw_pick("tennis", "t1", odds=2.10)],
                "baseball": [raw_pick("baseball", "b1", odds=1.85)],
                "basketball": [raw_pick("basketball", "bb1", odds=2.25)],
            }
        )
        result = OPT.build_combination(pools)
        soccer_leg = [leg for leg in result.legs if leg.sport == "soccer"][0]
        assert soccer_leg.odds_source == "fair"
        assert soccer_leg.odds == pytest.approx(round(1 / 0.60, 2), abs=1e-2)
        assert soccer_leg.odds_warning is True
        # not ALL legs have market odds -> fair total = 1/total_p
        assert result.totals.mixed_odds is True
        assert result.totals.total_odds == pytest.approx(
            round(1 / result.totals.total_probability, 2), abs=1e-2
        )

    def test_no_positive_ev_when_edge_not_positive(self) -> None:
        pools = OPT.aggregate_pools(
            {
                "soccer": [raw_pick("soccer", "s1", probability=0.50, odds=0.0)],
                "tennis": [raw_pick("tennis", "t1", probability=0.50, odds=0.0)],
                "baseball": [raw_pick("baseball", "b1", probability=0.50, odds=0.0)],
                "basketball": [
                    raw_pick("basketball", "bb1", probability=0.50, odds=0.0)
                ],
            }
        )
        with pytest.raises(CombinationError) as exc:
            OPT.build_combination(pools)
        assert exc.value.code == "no_positive_ev"

    def test_insufficient_pool_reports_missing_sports(self) -> None:
        pools = OPT.aggregate_pools(
            {
                "soccer": [raw_pick("soccer", "s1")],
                "basketball": [raw_pick("basketball", "bb1")],
            }
        )
        with pytest.raises(CombinationError) as exc:
            OPT.build_combination(pools)
        assert exc.value.code == "insufficient_pool"
        assert set(exc.value.missing_sports or []) == {"tennis", "baseball"}

    def test_no_picks_available_when_all_empty(self) -> None:
        with pytest.raises(CombinationError) as exc:
            OPT.build_combination(OPT.aggregate_pools({}))
        assert exc.value.code == "no_picks_available"
        assert set(exc.value.missing_sports or []) == {
            "soccer",
            "tennis",
            "baseball",
            "basketball",
        }

    def test_exclude_leagues_is_hard_constraint(self) -> None:
        pools = OPT.aggregate_pools(four_sport_pools())
        result = OPT.build_combination(pools, exclude_leagues=["E0"])
        soccer_leg = [leg for leg in result.legs if leg.sport == "soccer"][0]
        assert soccer_leg.league == "E1"  # E0 excluded -> only E1 left

    def test_exclude_leagues_wiping_sport_raises_insufficient(self) -> None:
        only_E0 = {
            "soccer": [raw_pick("soccer", "s1", league="E0")],
            "tennis": [raw_pick("tennis", "t1")],
            "baseball": [raw_pick("baseball", "b1")],
            "basketball": [raw_pick("basketball", "bb1")],
        }
        pools = OPT.aggregate_pools(only_E0)
        with pytest.raises(CombinationError) as exc:
            OPT.build_combination(pools, exclude_leagues=["E0"])
        assert exc.value.code == "insufficient_pool"
        assert "soccer" in (exc.value.missing_sports or [])

    def test_min_probability_filters_quality_pool(self) -> None:
        pools = OPT.aggregate_pools(
            {
                "soccer": [
                    raw_pick("soccer", "low", probability=0.55, priority_score=90.0),
                    raw_pick("soccer", "high", probability=0.85, priority_score=50.0),
                ],
                "tennis": [raw_pick("tennis", "t1", probability=0.90)],
                "baseball": [raw_pick("baseball", "b1", probability=0.90)],
                "basketball": [raw_pick("basketball", "bb1", probability=0.90)],
            }
        )
        result = OPT.build_combination(pools, min_probability=0.60)
        soccer_leg = [leg for leg in result.legs if leg.sport == "soccer"][0]
        assert soccer_leg.match_id == "high"

    def test_fallback_ignores_min_probability_but_warns(self) -> None:
        """W-3: fallback pool is NOT threshold-filtered (coverage policy keeps
        the 4-leg scope); the fallback leg may sit below the requested
        min_probability and must carry confidence_warning."""
        pools = OPT.aggregate_pools(
            {
                "soccer": [raw_pick("soccer", "s1", probability=0.90)],
                "tennis": [
                    # quality pick, but under the requested threshold
                    raw_pick(
                        "tennis",
                        "t1",
                        probability=0.40,
                        confidence_level="high",
                        is_recommended=True,
                    )
                ],
                "baseball": [raw_pick("baseball", "b1", probability=0.90)],
                "basketball": [raw_pick("basketball", "bb1", probability=0.90)],
            }
        )
        result = OPT.build_combination(pools, min_probability=0.60)
        tennis_leg = [leg for leg in result.legs if leg.sport == "tennis"][0]
        assert tennis_leg.match_id == "t1"
        assert tennis_leg.probability < 0.60
        assert tennis_leg.confidence_warning is True
        assert len(result.legs) == 4  # coverage policy keeps the scope

    def test_best_available_selected_for_sport_without_picks(self) -> None:
        pools = OPT.aggregate_pools(four_sport_pools())
        del pools["tennis"]
        # coverage check happens BEFORE selection -> insufficient_pool
        with pytest.raises(CombinationError) as exc:
            OPT.build_combination(pools)
        assert exc.value.code == "insufficient_pool"


class TestStakeSizing:
    def test_stake_capped_at_risk_manager_max(self) -> None:
        # Strong edge would demand a huge Kelly stake; cap must hold.
        stake = OPT.size_stake(
            total_probability=0.95,
            total_odds=10.0,
        )
        assert stake.suggested_stake_pct <= RiskManager.MAX_SINGLE_STAKE
        assert stake.suggested_stake_pct <= RiskManager.MAX_DAILY_EXPOSURE
        assert stake.risk_level == 4

    def test_stake_capped_by_league_exposure_when_league_present(self) -> None:
        """W-4: with leg league info available, the per-league cap (0.03)
        trims a stake that would otherwise fit under single/daily caps."""

        class KellyAboveLeagueCap(KellySizer):
            def calculate_kelly_fraction(self, model_prob, odds, kelly_fraction=None):
                del model_prob, odds, kelly_fraction
                return 0.04  # > 0.03 league cap, < 0.05 single/daily caps

        stake = OPT.size_stake(
            total_probability=0.80,
            total_odds=2.0,
            kelly_sizer=KellyAboveLeagueCap(),  # type: ignore[arg-type]
            leagues=["E0", "WTA", "MLB", "NBA"],
        )
        assert stake.suggested_stake_pct == pytest.approx(
            RiskManager.MAX_LEAGUE_EXPOSURE, abs=1e-4
        )
        assert stake.suggested_stake_pct <= RiskManager.MAX_SINGLE_STAKE

    def test_stake_without_league_uses_single_and_daily_caps(self) -> None:
        """W-4 guard: no league info -> league cap NOT applied; single/daily
        caps still hold."""

        class KellyInBand(KellySizer):
            def calculate_kelly_fraction(self, model_prob, odds, kelly_fraction=None):
                del model_prob, odds, kelly_fraction
                return 0.04

        stake = OPT.size_stake(
            total_probability=0.80,
            total_odds=2.0,
            kelly_sizer=KellyInBand(),  # type: ignore[arg-type]
            leagues=[None, None, None, None],
        )
        assert stake.suggested_stake_pct == pytest.approx(0.04, abs=1e-4)

    def test_build_combination_applies_league_cap_end_to_end(self) -> None:
        """W-4 end-to-end: a 4-leg combo with leagues is capped at 0.03 even
        when Kelly alone would exceed it."""
        pools = OPT.aggregate_pools(four_sport_pools())
        result = OPT.build_combination(pools)
        assert result.stake.suggested_stake_pct <= RiskManager.MAX_LEAGUE_EXPOSURE

    def test_low_edge_yields_low_risk_level(self) -> None:
        stake = OPT.size_stake(
            total_probability=0.51,
            total_odds=1.99,  # tiny positive edge
        )
        assert stake.suggested_stake_pct < 0.005
        assert stake.risk_level == 1
        assert stake.kelly_fraction >= 0

    def test_injected_kelly_sizer_overrides_default(self) -> None:
        class FixedKelly(KellySizer):
            def calculate_kelly_fraction(self, model_prob, odds, kelly_fraction=None):
                del model_prob, odds, kelly_fraction
                return 0.03

        stake = OPT.size_stake(
            total_probability=0.7,
            total_odds=2.0,
            kelly_sizer=FixedKelly(),  # type: ignore[arg-type]
        )
        assert stake.suggested_stake_pct == pytest.approx(0.03, abs=1e-4)
        assert stake.risk_level == 3
