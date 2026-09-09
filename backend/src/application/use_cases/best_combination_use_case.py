"""
Best Combination Use Case Module

Fetches candidate pools from the four sport prediction services and assembles
the single 4-leg best combination (one pick per sport) via the
``CombinationOptimizer``.

Fetchers are injected as a dict of ``sport -> async callable`` returning raw
pick dicts; tests inject mocks and the production wiring uses the default
per-sport fetchers below.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any, Awaitable, Callable, Optional

from src.api.dtos.best_combination_dtos import (
    BestCombinationAggregate,
    BestCombinationLeg,
    BestCombinationRequest,
    BestCombinationResponse,
    BestCombinationStake,
)
from src.domain.services.combination_optimizer import (
    CombinationLeg,
    CombinationOptimizer,
    CombinationResult,
)
from src.utils.time_utils import get_current_time

logger = logging.getLogger(__name__)

#: Fetcher contract: async, returns raw pick dicts in the unified vocabulary.
PoolFetcher = Callable[[], Awaitable[list[dict[str, Any]]]]

# Soccer pool harvesting knobs (bounded latency on cold cache).
_SOCCER_LEAGUE_LIMIT = 8
_SOCCER_MATCH_LIMIT = 6
_SOCCER_POOL_TARGET = 24


def _stable_id(*parts: str) -> str:
    """Deterministic short id from fixture parts (stable across requests)."""
    digest = hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:10]
    return f"bc_{digest}"


def _to_soccer_pick(pick: Any, match: Any) -> dict[str, Any]:
    """Map a soccer SuggestedPick + MatchDTO into a unified raw pick dict."""
    confidence = pick.confidence_level
    if hasattr(confidence, "value"):
        confidence = confidence.value
    return {
        "sport": "soccer",
        "match_id": match.id,
        "match_label": f"{match.home_team.name} vs {match.away_team.name}",
        "league": match.league.id,
        "pick_label": pick.market_label,
        "market_label": pick.market_label,
        "probability": pick.probability,
        "odds": 0.0,  # soccer DTOs do not expose decimal odds -> fair fallback
        "confidence_level": confidence,
        "is_recommended": pick.is_recommended,
        "priority_score": pick.priority_score,
        "is_ml_confirmed": pick.is_ml_confirmed,
        "is_ia_confirmed": pick.is_ia_confirmed,
    }


async def _fetch_soccer_pool() -> list[dict[str, Any]]:
    """Harvest soccer candidates from league predictions (cached when warm)."""
    from src.application.use_cases.use_cases import GetPredictionsUseCase
    from src.domain.constants import LEAGUES_METADATA
    from src.dependencies import (
        get_data_sources,
        get_match_aggregator_service,
        get_prediction_service,
        get_statistics_service,
    )

    use_case = GetPredictionsUseCase(
        data_sources=get_data_sources(),
        prediction_service=get_prediction_service(),
        statistics_service=get_statistics_service(),
        match_aggregator=get_match_aggregator_service(),
    )
    pool: list[dict[str, Any]] = []
    for league_id in list(LEAGUES_METADATA.keys())[:_SOCCER_LEAGUE_LIMIT]:
        try:
            response = await use_case.execute(
                league_id=league_id, limit=_SOCCER_MATCH_LIMIT
            )
        except Exception:
            logger.warning(
                "best-combination soccer fetch failed for league %s",
                league_id,
                exc_info=True,
            )
            continue
        for dto in response.predictions:
            if not dto.prediction.suggested_picks:
                continue
            for pick in dto.prediction.suggested_picks:
                pool.append(_to_soccer_pick(pick, dto.match))
                if len(pool) >= _SOCCER_POOL_TARGET:
                    return pool
    return pool


async def _fetch_tennis_pool() -> list[dict[str, Any]]:
    """Build tennis candidates from upcoming fixtures + markets."""
    from datetime import date

    from src.api.routers.tennis_router import get_all_fixtures, get_prediction_service
    from src.domain.entities.tennis_match import TennisMatch

    fixtures = get_all_fixtures() or []
    predictor = get_prediction_service()
    pool: list[dict[str, Any]] = []
    for fixture in fixtures:
        try:
            p1, p2 = fixture["player1"], fixture["player2"]
            raw_date = fixture["match_date"]
            match_date = (
                date.fromisoformat(raw_date) if isinstance(raw_date, str) else raw_date
            )
            match = TennisMatch(
                match_id=_stable_id(
                    p1["name"], p2["name"], str(raw_date), fixture["tournament"]
                ),
                tournament_name=fixture["tournament"],
                surface=fixture["surface"],
                tourney_level=fixture["tourney_level"],
                round_name=fixture["round"],
                match_date=match_date,
                best_of=fixture.get("best_of", 3),
                p1_name=p1["name"],
                p1_rank=p1.get("rank"),
                p1_rank_points=p1.get("rank_points"),
                p1_age=p1.get("age"),
                p1_hand=p1.get("hand", "R"),
                p1_height=p1.get("height"),
                p1_seed=p1.get("seed"),
                p2_name=p2["name"],
                p2_rank=p2.get("rank"),
                p2_rank_points=p2.get("rank_points"),
                p2_age=p2.get("age"),
                p2_hand=p2.get("hand", "R"),
                p2_height=p2.get("height"),
                p2_seed=p2.get("seed"),
            )
            prediction = predictor.predict(match)
            if not prediction:
                continue
            markets = predictor.generate_tennis_markets(
                match, prediction.p1_win_prob, prediction.p2_win_prob
            )
            label = f"{p1['name']} vs {p2['name']}"
            for market in markets:
                market["match_label"] = label
                market["league"] = fixture["tournament"]
                pool.append(market)
        except Exception:
            logger.warning(
                "best-combination tennis fetch failed for a fixture",
                exc_info=True,
            )
            continue
    return pool


async def _fetch_baseball_pool() -> list[dict[str, Any]]:
    """Build baseball candidates from upcoming games + markets."""
    from datetime import date

    from src.api.routers.baseball_router import get_all_games, get_prediction_service
    from src.domain.entities.baseball_game import BaseballGame

    games = get_all_games() or []
    predictor = get_prediction_service()
    pool: list[dict[str, Any]] = []
    for gd in games:
        try:
            game = BaseballGame(
                game_id=gd.get("game_id")
                or _stable_id(gd["home_team"], gd["away_team"], gd["date"]),
                date=(
                    date.fromisoformat(gd["date"])
                    if isinstance(gd["date"], str)
                    else gd["date"]
                ),
                home_team=gd["home_team"],
                away_team=gd["away_team"],
                venue=gd.get("venue"),
                day_night=gd.get("day_night", "day"),
                home_pitcher_name=gd.get("home_pitcher_name"),
                away_pitcher_name=gd.get("away_pitcher_name"),
                series_id=gd.get("series_id"),
            )
            prediction = predictor.predict(game)
            if not prediction:
                continue
            markets = predictor.generate_baseball_markets(
                game, prediction.home_win_prob, prediction.away_win_prob
            )
            label = f"{gd['home_team']} vs {gd['away_team']}"
            for market in markets:
                market["match_label"] = label
                market["league"] = gd.get("league") or "MLB"
                pool.append(market)
        except Exception:
            logger.warning(
                "best-combination baseball fetch failed for a game",
                exc_info=True,
            )
            continue
    return pool


async def _fetch_basketball_pool() -> list[dict[str, Any]]:
    """Build basketball candidates from upcoming games + markets."""
    from datetime import date

    from src.api.routers.basketball_router import get_all_games, get_prediction_service
    from src.domain.entities.basketball_game import BasketballGame

    games = get_all_games() or []
    predictor = get_prediction_service()
    pool: list[dict[str, Any]] = []
    for gd in games:
        try:
            game = BasketballGame(
                game_id=gd.get("game_id")
                or _stable_id(gd["home_team"], gd["away_team"], gd["date"]),
                game_date=(
                    date.fromisoformat(gd["date"])
                    if isinstance(gd["date"], str)
                    else gd["date"]
                ),
                home_team=gd["home_team"],
                away_team=gd["away_team"],
                venue=gd.get("venue"),
            )
            prediction = predictor.predict(game)
            if not prediction:
                continue
            markets = predictor.generate_basketball_markets(
                game, prediction.home_win_prob, prediction.away_win_prob
            )
            label = f"{gd['home_team']} vs {gd['away_team']}"
            for market in markets:
                market["match_label"] = label
                market["league"] = gd.get("league") or "NBA"
                pool.append(market)
        except Exception:
            logger.warning(
                "best-combination basketball fetch failed for a game",
                exc_info=True,
            )
            continue
    return pool


def default_pool_fetchers() -> dict[str, PoolFetcher]:
    """Production fetchers for the four combination sports."""
    return {
        "soccer": _fetch_soccer_pool,
        "tennis": _fetch_tennis_pool,
        "baseball": _fetch_baseball_pool,
        "basketball": _fetch_basketball_pool,
    }


class BestCombinationUseCase:
    """Application use case: fetch pools, assemble, size the combination."""

    def __init__(
        self,
        optimizer: Optional[CombinationOptimizer] = None,
        fetch_pools: Optional[dict[str, PoolFetcher]] = None,
    ) -> None:
        self.optimizer = optimizer or CombinationOptimizer()
        self._fetch = fetch_pools or default_pool_fetchers()

    async def execute(self, request: BestCombinationRequest) -> BestCombinationResponse:
        """Assemble the best combination for the validated request.

        Raises:
            CombinationError: propagated from the optimizer (router maps to 409).
        """
        per_sport_raw: dict[str, list[dict[str, Any]]] = {}
        for sport, fetcher in self._fetch.items():
            try:
                per_sport_raw[sport] = await fetcher()
            except Exception:
                logger.warning(
                    "best-combination fetcher failed for %s; pool treated as empty",
                    sport,
                    exc_info=True,
                )
                per_sport_raw[sport] = []

        pools = self.optimizer.aggregate_pools(per_sport_raw)
        result = self.optimizer.build_combination(
            pools,
            min_probability=request.min_probability,
            exclude_leagues=request.exclude_leagues,
        )
        return self._to_response(result)

    @staticmethod
    def _to_leg_dto(leg: CombinationLeg) -> BestCombinationLeg:
        return BestCombinationLeg(
            sport=leg.sport,
            match_id=leg.match_id,
            match_label=leg.match_label,
            pick_label=leg.pick_label,
            league=leg.league,
            probability=leg.probability,
            odds=leg.odds,
            odds_source=leg.odds_source,
            confidence_level=leg.confidence_level,
            is_recommended=leg.is_recommended,
            priority_score=leg.priority_score,
            confidence_warning=leg.confidence_warning,
            odds_warning=leg.odds_warning,
        )

    def _to_response(self, result: CombinationResult) -> BestCombinationResponse:
        return BestCombinationResponse(
            legs=[self._to_leg_dto(leg) for leg in result.legs],
            aggregate=BestCombinationAggregate(
                total_probability=result.totals.total_probability,
                total_odds=result.totals.total_odds,
                expected_value=result.totals.expected_value,
                mixed_odds=result.totals.mixed_odds,
            ),
            stake=BestCombinationStake(
                suggested_stake_pct=result.stake.suggested_stake_pct,
                risk_level=result.stake.risk_level,
                kelly_fraction=result.stake.kelly_fraction,
            ),
            generated_at=get_current_time().isoformat(),
            independence_disclaimer=result.independence_disclaimer,
            warnings=list(result.warnings),
        )
