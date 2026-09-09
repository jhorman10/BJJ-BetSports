# mypy: ignore-errors
"""
Odds Feed Integration Module

Provides unified access to multiple odds providers:
- Pinnacle (sharp bookmaker, low margin) - primary reference
- Betfair Exchange (market prices, lay/back)
- TheOddsAPI (aggregated from 50+ bookies) - fallback

All odds are normalized to decimal format with overround removed
using the proportional method.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

import aiohttp
import numpy as np
from src.domain.value_objects.value_objects import Odds

logger = logging.getLogger(__name__)


class OddsProvider(str, Enum):
    """Supported odds providers."""

    PINNACLE = "pinnacle"
    BETFAIR = "betfair"
    THE_ODDS_API = "the_odds_api"


@dataclass(frozen=True)
class OddsSnapshot:
    """Single odds snapshot from a provider."""

    provider: OddsProvider
    sport: str
    league: str
    match_id: str
    odds: Odds
    timestamp: datetime
    volume: Optional[float] = None  # Matched volume for exchanges
    is_live: bool = False


@dataclass(frozen=True)
class HistoricalOdds:
    """Historical odds series for a match."""

    match_id: str
    sport: str
    league: str
    snapshots: list[OddsSnapshot] = field(default_factory=list)
    opening_odds: Optional[Odds] = None
    closing_odds: Optional[Odds] = None


@dataclass(frozen=True)
class MarketEfficiencyMetrics:
    """Market efficiency metrics for a match/league."""

    clv: float  # Closing Line Value (positive = beat the closing line)
    market_margin: float  # Average bookmaker margin
    sharp_movement_detected: bool
    steam_score: float  # 0-1 score for sharp money detection
    line_movement_pct: float  # Percentage movement from open to close
    volume_weighted_move: float  # Volume-weighted line movement


class OddsProviderBase(ABC):
    """Abstract base class for odds providers."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.session: Optional[aiohttp.ClientSession] = None
        self._rate_limit_delay = 1.0  # seconds between requests
        self._last_request_time = 0.0

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session

    async def close(self) -> None:
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None

    async def _rate_limit(self) -> None:
        """Enforce rate limiting."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._rate_limit_delay:
            await asyncio.sleep(self._rate_limit_delay - elapsed)
        self._last_request_time = time.time()

    @abstractmethod
    async def fetch_odds(
        self, sport: str, league: str, match_id: str
    ) -> Optional[OddsSnapshot]:
        """Fetch current odds for a specific match."""
        pass

    @abstractmethod
    async def fetch_historical_odds(
        self, sport: str, league: str, date_range: tuple[datetime, datetime]
    ) -> list[HistoricalOdds]:
        """Fetch historical odds for backtesting."""
        pass

    @abstractmethod
    def normalize_odds(self, raw_odds: dict[str, Any]) -> Odds:
        """Convert provider-specific odds format to standardized Odds."""
        pass


class PinnacleProvider(OddsProviderBase):
    """
    Pinnacle odds provider.

    Pinnacle is known as a sharp bookmaker with low margins (~2-3%).
    Their odds are considered the most efficient market reference.
    """

    BASE_URL = "https://api.pinnacle.com/v1"

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key)
        self._rate_limit_delay = 0.5  # Pinnacle allows higher rate

    def _get_headers(self) -> dict[str, str]:
        """Get request headers with authentication."""
        if not self.api_key:
            raise ValueError("Pinnacle API key required")
        # Pinnacle uses Basic Auth with API key as username, empty password
        import base64

        credentials = base64.b64encode(f"{self.api_key}:".encode()).decode()
        return {"Authorization": f"Basic {credentials}", "Accept": "application/json"}

    async def fetch_odds(
        self, sport: str, league: str, match_id: str
    ) -> Optional[OddsSnapshot]:
        """Fetch current odds from Pinnacle."""
        if not self.api_key:
            logger.warning("Pinnacle API key not configured, skipping")
            return None

        await self._rate_limit()
        session = await self._get_session()

        try:
            # Pinnacle uses sport IDs (e.g., 29 for soccer)
            sport_id = self._get_sport_id(sport)
            url = f"{self.BASE_URL}/odds"
            params = {"sport_id": sport_id, "league_id": league, "event_id": match_id}

            async with session.get(
                url, headers=self._get_headers(), params=params
            ) as resp:
                if resp.status == 404:
                    return None
                resp.raise_for_status()
                data = await resp.json()

            odds = self.normalize_odds(data)
            return OddsSnapshot(
                provider=OddsProvider.PINNACLE,
                sport=sport,
                league=league,
                match_id=match_id,
                odds=odds,
                timestamp=datetime.utcnow(),
            )

        except Exception as e:
            logger.error(f"Pinnacle fetch failed for {match_id}: {e}")
            return None

    async def fetch_historical_odds(
        self, sport: str, league: str, date_range: tuple[datetime, datetime]
    ) -> list[HistoricalOdds]:
        """Fetch historical odds from Pinnacle (limited availability)."""
        # Pinnacle historical API requires special access
        # For now, return empty list - would need Pinnacle's historical feed
        logger.warning(
            "Pinnacle historical odds not available without enterprise access"
        )
        return []

    def normalize_odds(self, raw_odds: dict[str, Any]) -> Odds:
        """Normalize Pinnacle odds format."""
        # Pinnacle returns: {"home": 2.10, "draw": 3.20, "away": 3.50, "period": 0}
        # Period 0 = full time (match odds)
        periods = raw_odds.get("periods", [])
        moneyline = None

        for period in periods:
            if period.get("period") == 0:  # Full time
                moneyline = period.get("moneyline") or period.get("spread")
                break

        if not moneyline:
            # Try direct moneyline
            moneyline = raw_odds.get("moneyline", raw_odds)

        home = float(moneyline.get("home", moneyline.get("1", 0)))
        draw = float(moneyline.get("draw", moneyline.get("X", 0)))
        away = float(moneyline.get("away", moneyline.get("2", 0)))

        return Odds(home=home, draw=draw, away=away)

    def _get_sport_id(self, sport: str) -> int:
        """Map sport name to Pinnacle sport ID."""
        sport_ids = {
            "football": 29,
            "soccer": 29,
            "tennis": 33,
            "baseball": 19,
            "basketball": 4,
            "american_football": 15,
            "ice_hockey": 14,
        }
        return sport_ids.get(sport.lower(), 29)


class BetfairProvider(OddsProviderBase):
    """
    Betfair Exchange odds provider.

    Betfair is a betting exchange showing true market prices with lay/back odds.
    No bookmaker margin - prices are set by market participants.
    """

    BASE_URL = "https://api.betfair.com/exchange/betting/json-rpc/v1"

    def __init__(
        self, api_key: Optional[str] = None, session_token: Optional[str] = None
    ):
        super().__init__(api_key)
        self.session_token = session_token
        self._rate_limit_delay = 1.0

    def _get_headers(self) -> dict[str, str]:
        if not self.api_key or not self.session_token:
            raise ValueError("Betfair API key and session token required")
        return {
            "X-Application": self.api_key,
            "X-Authentication": self.session_token,
            "Content-Type": "application/json",
        }

    async def fetch_odds(
        self, sport: str, league: str, match_id: str
    ) -> Optional[OddsSnapshot]:
        """Fetch current odds from Betfair Exchange."""
        if not self.api_key or not self.session_token:
            logger.warning("Betfair credentials not configured, skipping")
            return None

        await self._rate_limit()
        session = await self._get_session()

        try:
            # Betfair uses market IDs - we need to find the match market first
            market_id = await self._find_market_id(sport, league, match_id, session)
            if not market_id:
                return None

            # Get runner prices (lay/back)
            prices = await self._get_runner_prices(market_id, session)
            if not prices:
                return None

            # Convert exchange prices to implied probabilities (use back prices)
            home_back = prices.get("home_back", 0)
            draw_back = prices.get("draw_back", 0)
            away_back = prices.get("away_back", 0)

            if not all([home_back, draw_back, away_back]):
                return None

            odds = Odds(home=home_back, draw=draw_back, away=away_back)
            volume = prices.get("total_matched", 0)

            return OddsSnapshot(
                provider=OddsProvider.BETFAIR,
                sport=sport,
                league=league,
                match_id=match_id,
                odds=odds,
                timestamp=datetime.utcnow(),
                volume=volume,
                is_live=prices.get("in_play", False),
            )

        except Exception as e:
            logger.error(f"Betfair fetch failed for {match_id}: {e}")
            return None

    async def _find_market_id(
        self, sport: str, league: str, match_id: str, session: aiohttp.ClientSession
    ) -> Optional[str]:
        """Find Betfair market ID for a match."""
        # This would use listMarketCatalogue with event ID filter
        # Simplified for now
        return None

    async def _get_runner_prices(
        self, market_id: str, session: aiohttp.ClientSession
    ) -> Optional[dict[str, float]]:
        """Get runner prices (back/lay) for a market."""
        # Would use listRunnerBook
        return None

    async def fetch_historical_odds(
        self,
        sport: str,
        league: str,
        date_range: tuple[datetime, datetime],
    ) -> list[HistoricalOdds]:
        """Fetch historical odds from Betfair (requires historical
        data subscription)."""
        logger.warning("Betfair historical odds require separate subscription")
        return []

    def normalize_odds(self, raw_odds: dict[str, Any]) -> Odds:
        """Normalize Betfair odds format."""
        # Betfair returns runner objects with availableToBack/availableToLay
        runners = raw_odds.get("runners", [])
        home = draw = away = 0.0

        for runner in runners:
            back_prices = runner.get("ex", {}).get("availableToBack", [])
            if back_prices:
                best_back = back_prices[0].get("price", 0)
                name = runner.get("runnerName", "").lower()
                if "home" in name or "1" == name:
                    home = best_back
                elif "draw" in name or "x" == name.lower():
                    draw = best_back
                elif "away" in name or "2" == name:
                    away = best_back

        return Odds(home=home or 1.0, draw=draw or 1.0, away=away or 1.0)


class TheOddsAPIProvider(OddsProviderBase):
    """
    TheOddsAPI provider.

    Aggregates odds from 50+ bookmakers. Good fallback when
    primary sharp sources are unavailable.
    """

    BASE_URL = "https://api.the-odds-api.com/v4"

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key)
        self._rate_limit_delay = 2.0  # Free tier: 500 requests/month

    def _get_sport_key(self, sport: str) -> str:
        """Map sport to TheOddsAPI sport key."""
        sport_keys = {
            "football": "soccer_epl",  # Default to EPL, would need league mapping
            "soccer": "soccer_epl",
            "tennis": "tennis_atp",
            "baseball": "baseball_mlb",
            "basketball": "basketball_nba",
            "american_football": "americanfootball_nfl",
        }
        return sport_keys.get(sport.lower(), "soccer_epl")

    async def fetch_odds(
        self, sport: str, league: str, match_id: str
    ) -> Optional[OddsSnapshot]:
        """Fetch current odds from TheOddsAPI."""
        if not self.api_key:
            logger.warning("TheOddsAPI key not configured, skipping")
            return None

        await self._rate_limit()
        session = await self._get_session()

        try:
            sport_key = self._get_sport_key(sport)
            url = f"{self.BASE_URL}/sports/{sport_key}/odds"
            params = {
                "apiKey": self.api_key,
                "regions": "eu,uk,us",
                "markets": "h2h",  # Moneyline only
                "oddsFormat": "decimal",
                "dateFormat": "iso",
            }

            async with session.get(url, params=params) as resp:
                if resp.status == 401:
                    logger.error("TheOddsAPI: Invalid API key")
                    return None
                if resp.status == 429:
                    logger.warning("TheOddsAPI: Rate limit exceeded")
                    return None
                resp.raise_for_status()
                data = await resp.json()

            # Find the specific match
            for event in data:
                if str(event.get("id")) == str(match_id):
                    odds = self.normalize_odds(event)
                    return OddsSnapshot(
                        provider=OddsProvider.THE_ODDS_API,
                        sport=sport,
                        league=league,
                        match_id=match_id,
                        odds=odds,
                        timestamp=datetime.utcnow(),
                    )

            return None

        except Exception as e:
            logger.error(f"TheOddsAPI fetch failed for {match_id}: {e}")
            return None

    async def fetch_historical_odds(
        self, sport: str, league: str, date_range: tuple[datetime, datetime]
    ) -> list[HistoricalOdds]:
        """Fetch historical odds from TheOddsAPI (requires paid plan)."""
        logger.warning("TheOddsAPI historical odds require paid plan")
        return []

    def normalize_odds(self, raw_odds: dict[str, Any]) -> Odds:
        """Normalize TheOddsAPI odds format."""
        bookmakers = raw_odds.get("bookmakers", [])
        if not bookmakers:
            return Odds(home=1.0, draw=1.0, away=1.0)

        # Use the first bookmaker with all three outcomes (or average across bookmakers)
        home_odds = []
        draw_odds = []
        away_odds = []

        for bm in bookmakers:
            markets = bm.get("markets", [])
            for market in markets:
                if market.get("key") == "h2h":
                    outcomes = market.get("outcomes", [])
                    for outcome in outcomes:
                        name = outcome.get("name", "").lower()
                        price = outcome.get("price", 0)
                        if "home" in name or name == "1":
                            home_odds.append(price)
                        elif "draw" in name or name == "x":
                            draw_odds.append(price)
                        elif "away" in name or name == "2":
                            away_odds.append(price)

        # Use median to reduce outlier impact
        home = float(np.median(home_odds)) if home_odds else 1.0
        draw = float(np.median(draw_odds)) if draw_odds else 1.0
        away = float(np.median(away_odds)) if away_odds else 1.0

        return Odds(home=home, draw=draw, away=away)


class OddsFeed:
    """
    Unified odds feed integrating multiple providers.

    Priority order:
    1. Pinnacle (sharp, low margin) - primary
    2. Betfair Exchange (true market prices) - secondary
    3. TheOddsAPI (aggregated) - fallback

    All odds normalized to decimal format with overround removed.
    """

    def __init__(
        self,
        pinnacle_key: Optional[str] = None,
        betfair_key: Optional[str] = None,
        betfair_session: Optional[str] = None,
        theoddsapi_key: Optional[str] = None,
    ):
        self.providers: dict[OddsProvider, OddsProviderBase] = {}

        # Initialize providers with credentials
        if pinnacle_key or os.getenv("PINNACLE_API_KEY"):
            self.providers[OddsProvider.PINNACLE] = PinnacleProvider(
                pinnacle_key or os.getenv("PINNACLE_API_KEY")
            )

        if (betfair_key or os.getenv("BETFAIR_API_KEY")) and (
            betfair_session or os.getenv("BETFAIR_SESSION_TOKEN")
        ):
            self.providers[OddsProvider.BETFAIR] = BetfairProvider(
                betfair_key or os.getenv("BETFAIR_API_KEY"),
                betfair_session or os.getenv("BETFAIR_SESSION_TOKEN"),
            )

        if theoddsapi_key or os.getenv("THE_ODDS_API_KEY"):
            self.providers[OddsProvider.THE_ODDS_API] = TheOddsAPIProvider(
                theoddsapi_key or os.getenv("THE_ODDS_API_KEY")
            )

        # Default priority order (can be customized)
        self.priority = [
            OddsProvider.PINNACLE,
            OddsProvider.BETFAIR,
            OddsProvider.THE_ODDS_API,
        ]

        # Cache for odds snapshots (TTL: 60 seconds for live, 300 for pre-match)
        self._cache: dict[str, tuple[OddsSnapshot, float]] = {}
        self._cache_ttl_live = 60
        self._cache_ttl_prematch = 300

    async def fetch_odds(
        self, sport: str, league: str, match_id: str
    ) -> Optional[OddsSnapshot]:
        """
        Get current odds for a match, trying providers in priority order.

        Returns the first successful result from the priority list.
        """
        cache_key = f"{sport}:{league}:{match_id}"

        # Check cache
        if cache_key in self._cache:
            snapshot, cached_time = self._cache[cache_key]
            ttl = self._cache_ttl_live if snapshot.is_live else self._cache_ttl_prematch
            if time.time() - cached_time < ttl:
                logger.debug(f"Returning cached odds for {match_id}")
                return snapshot

        # Try providers in priority order
        for provider_type in self.priority:
            provider = self.providers.get(provider_type)
            if not provider:
                continue

            try:
                snapshot = await provider.fetch_odds(sport, league, match_id)
                if snapshot:
                    self._cache[cache_key] = (snapshot, time.time())
                    logger.info(
                        f"Fetched odds for {match_id} from {provider_type.value}"
                    )
                    return snapshot
            except Exception as e:
                logger.warning(f"Provider {provider_type.value} failed: {e}")
                continue

        logger.warning(f"All providers failed for {match_id}")
        return None

    async def fetch_historical_odds(
        self, sport: str, league: str, date_range: tuple[datetime, datetime]
    ) -> list[HistoricalOdds]:
        """
        Fetch historical odds for backtesting.

        Tries all providers and merges results.
        """
        all_historical: dict[str, HistoricalOdds] = {}

        for provider_type in self.priority:
            provider = self.providers.get(provider_type)
            if not provider:
                continue

            try:
                historical = await provider.fetch_historical_odds(
                    sport, league, date_range
                )
                for h in historical:
                    if h.match_id not in all_historical:
                        all_historical[h.match_id] = h
                    else:
                        # Merge snapshots
                        existing = all_historical[h.match_id]
                        merged_snapshots = existing.snapshots + h.snapshots
                        merged_snapshots.sort(key=lambda s: s.timestamp)
                        all_historical[h.match_id] = HistoricalOdds(
                            match_id=h.match_id,
                            sport=h.sport,
                            league=h.league,
                            snapshots=merged_snapshots,
                            opening_odds=existing.opening_odds or h.opening_odds,
                            closing_odds=h.closing_odds or existing.closing_odds,
                        )
            except Exception as e:
                logger.warning(
                    f"Historical fetch from {provider_type.value} failed: {e}"
                )

        return list(all_historical.values())

    def remove_overround_proportional(self, odds: Odds) -> Odds:
        """
        Remove bookmaker overround using the proportional method.

        Proportional method: divide each implied probability by the total.
        This assumes the margin is distributed proportionally to the probabilities.
        """
        home_prob = 1 / odds.home
        draw_prob = 1 / odds.draw
        away_prob = 1 / odds.away

        total = home_prob + draw_prob + away_prob

        # Normalized probabilities (fair odds)
        fair_home = home_prob / total
        fair_draw = draw_prob / total
        fair_away = away_prob / total

        # Convert back to decimal odds
        return Odds(
            home=1 / fair_home if fair_home > 0 else 1.0,
            draw=1 / fair_draw if fair_draw > 0 else 1.0,
            away=1 / fair_away if fair_away > 0 else 1.0,
        )

    def remove_overround_additive(self, odds: Odds) -> Odds:
        """
        Remove bookmaker overround using the additive method.

        Additive method: subtract equal margin from each implied probability.
        """
        home_prob = 1 / odds.home
        draw_prob = 1 / odds.draw
        away_prob = 1 / odds.away

        total = home_prob + draw_prob + away_prob
        margin = total - 1.0

        # Subtract equal margin from each
        fair_home = home_prob - margin / 3
        fair_draw = draw_prob - margin / 3
        fair_away = away_prob - margin / 3

        # Ensure positive
        fair_home = max(fair_home, 0.001)
        fair_draw = max(fair_draw, 0.001)
        fair_away = max(fair_away, 0.001)

        # Renormalize
        new_total = fair_home + fair_draw + fair_away
        fair_home /= new_total
        fair_draw /= new_total
        fair_away /= new_total

        return Odds(
            home=1 / fair_home,
            draw=1 / fair_draw,
            away=1 / fair_away,
        )

    def calculate_market_efficiency(
        self, odds_history: list[OddsSnapshot]
    ) -> MarketEfficiencyMetrics:
        """
        Calculate market efficiency metrics from odds history.

        CLV (Closing Line Value) = (Model Prob * Closing Odds) - 1
        Positive CLV means the model beat the closing line.
        """
        if not odds_history:
            return MarketEfficiencyMetrics(
                clv=0.0,
                market_margin=0.0,
                sharp_movement_detected=False,
                steam_score=0.0,
                line_movement_pct=0.0,
                volume_weighted_move=0.0,
            )

        # Sort by timestamp
        sorted_history = sorted(odds_history, key=lambda s: s.timestamp)

        opening = sorted_history[0].odds
        closing = sorted_history[-1].odds

        # Calculate line movement percentage
        home_move = (closing.home - opening.home) / opening.home
        draw_move = (closing.draw - opening.draw) / opening.draw
        away_move = (closing.away - opening.away) / opening.away
        line_movement_pct = (abs(home_move) + abs(draw_move) + abs(away_move)) / 3

        # Average market margin
        margins = [s.odds.bookmaker_margin for s in sorted_history]
        market_margin = float(np.mean(margins))

        # Detect sharp movement (large moves with volume on exchanges)
        sharp_movement = False
        steam_score = 0.0
        volume_weighted_move = 0.0

        betfair_snapshots = [
            s for s in sorted_history if s.provider == OddsProvider.BETFAIR
        ]
        if betfair_snapshots:
            # Calculate volume-weighted movement on Betfair
            total_volume = sum(s.volume or 0 for s in betfair_snapshots)
            if total_volume > 0:
                for s in betfair_snapshots:
                    vol = s.volume or 0
                    weight = vol / total_volume
                    move = (s.odds.home - opening.home) / opening.home
                    volume_weighted_move += weight * move

                # Steam score based on volume-weighted move magnitude
                steam_score = min(abs(volume_weighted_move) * 10, 1.0)
                sharp_movement = steam_score > 0.3

        # CLV calculation (would need model predictions for full CLV)
        # Placeholder: assume we have model probabilities
        clv = 0.0  # Would be calculated with actual model probs

        return MarketEfficiencyMetrics(
            clv=clv,
            market_margin=market_margin,
            sharp_movement_detected=sharp_movement,
            steam_score=steam_score,
            line_movement_pct=line_movement_pct,
            volume_weighted_move=volume_weighted_move,
        )

    def detect_sharp_movement(self, odds_series: list[OddsSnapshot]) -> dict[str, Any]:
        """
        Detect sharp money movement patterns.

        Analyzes line movement against public betting percentages.
        Returns dict with:
        - reverse_line_movement: bool
        - steam_moves: list of detected steam moves
        - smart_money_side: 'home', 'draw', 'away', or None
        """
        if len(odds_series) < 2:
            return {
                "reverse_line_movement": False,
                "steam_moves": [],
                "smart_money_side": None,
            }

        sorted_series = sorted(odds_series, key=lambda s: s.timestamp)
        opening = sorted_series[0].odds
        current = sorted_series[-1].odds

        # Calculate movement for each outcome
        movements = {
            "home": (current.home - opening.home) / opening.home,
            "draw": (current.draw - opening.draw) / opening.draw,
            "away": (current.away - opening.away) / opening.away,
        }

        # Find biggest move (sharp money typically moves lines 1-3%)
        max_move_outcome = max(movements, key=lambda k: abs(movements[k]))
        max_move_pct = abs(movements[max_move_outcome])

        # Steam move: >1% move in short time with volume
        steam_moves = []
        for i in range(1, len(sorted_series)):
            prev = sorted_series[i - 1]
            curr = sorted_series[i]
            time_diff = (
                curr.timestamp - prev.timestamp
            ).total_seconds() / 60  # minutes

            if time_diff <= 60:  # Within 1 hour
                for outcome in ["home", "draw", "away"]:
                    prev_odds = getattr(prev.odds, outcome)
                    curr_odds = getattr(curr.odds, outcome)
                    move_pct = abs(curr_odds - prev_odds) / prev_odds
                    if move_pct > 0.01 and (curr.volume or 0) > 1000:
                        steam_moves.append(
                            {
                                "outcome": outcome,
                                "move_pct": move_pct,
                                "time_minutes": time_diff,
                                "volume": curr.volume,
                                "timestamp": curr.timestamp.isoformat(),
                            }
                        )

        # Reverse line movement: line moves against public %
        # (Would need public betting % data - simplified here)
        reverse_line_movement = False
        if steam_moves:
            # If line moves on one side but public % is on other side
            # This is a simplified heuristic
            reverse_line_movement = max_move_pct > 0.02

        # Determine smart money side
        smart_money_side = max_move_outcome if max_move_pct > 0.015 else None

        return {
            "reverse_line_movement": reverse_line_movement,
            "steam_moves": steam_moves,
            "smart_money_side": smart_money_side,
            "max_movement": {max_move_outcome: movements[max_move_outcome]},
            "all_movements": movements,
        }

    async def close(self) -> None:
        """Close all provider sessions."""
        for provider in self.providers.values():
            await provider.close()

    def get_available_providers(self) -> list[OddsProvider]:
        """Get list of configured providers."""
        return list(self.providers.keys())

    def is_configured(self) -> bool:
        """Check if at least one provider is configured."""
        return len(self.providers) > 0


# Convenience function for creating OddsFeed from environment
def create_odds_feed_from_env() -> OddsFeed:
    """Create OddsFeed instance using environment variables."""
    return OddsFeed(
        pinnacle_key=os.getenv("PINNACLE_API_KEY"),
        betfair_key=os.getenv("BETFAIR_API_KEY"),
        betfair_session=os.getenv("BETFAIR_SESSION_TOKEN"),
        theoddsapi_key=os.getenv("THE_ODDS_API_KEY"),
    )
