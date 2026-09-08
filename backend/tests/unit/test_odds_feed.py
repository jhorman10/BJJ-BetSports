"""
Unit tests for OddsFeed module.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np

from src.domain.value_objects.value_objects import Odds
from src.infrastructure.odds_feed import (
    OddsFeed,
    OddsSnapshot,
    OddsProvider,
    MarketEfficiencyMetrics,
    PinnacleProvider,
    BetfairProvider,
    TheOddsAPIProvider,
    create_odds_feed_from_env,
)


class TestOddsValueObject:
    """Tests for the Odds value object."""

    def test_odds_to_probabilities(self):
        """Test odds to probabilities conversion with overround removal."""
        odds = Odds(home=2.0, draw=3.5, away=4.0)
        probs = odds.to_probabilities()

        # Sum should be 1.0 (overround removed)
        assert abs(sum(probs) - 1.0) < 0.001

        # Probabilities should be positive
        assert all(p > 0 for p in probs)

    def test_bookmaker_margin(self):
        """Test bookmaker margin calculation."""
        # Fair odds: 2.0, 2.0, 2.0 -> margin = 0%
        fair_odds = Odds(home=2.0, draw=2.0, away=2.0)
        assert fair_odds.bookmaker_margin == 50.0  # 1/2 + 1/2 + 1/2 - 1 = 0.5

        # Typical odds with margin
        typical_odds = Odds(home=2.1, draw=3.4, away=3.6)
        margin = typical_odds.bookmaker_margin
        assert 0 < margin < 15  # Reasonable margin range


class TestOddsSnapshot:
    """Tests for OddsSnapshot dataclass."""

    def test_odds_snapshot_creation(self):
        """Test creating an odds snapshot."""
        odds = Odds(home=2.0, draw=3.2, away=3.5)
        snapshot = OddsSnapshot(
            provider=OddsProvider.PINNACLE,
            sport="football",
            league="E0",
            match_id="12345",
            odds=odds,
            timestamp=datetime.utcnow(),
            volume=10000.0,
            is_live=False,
        )

        assert snapshot.provider == OddsProvider.PINNACLE
        assert snapshot.sport == "football"
        assert snapshot.league == "E0"
        assert snapshot.match_id == "12345"
        assert snapshot.odds == odds
        assert snapshot.volume == 10000.0
        assert snapshot.is_live is False


class TestOddsFeed:
    """Tests for OddsFeed class."""

    def test_odds_feed_creation_empty(self):
        """Test creating OddsFeed without any providers."""
        feed = OddsFeed()
        assert len(feed.providers) == 0
        assert not feed.is_configured()

    def test_odds_feed_with_pinnacle(self):
        """Test creating OddsFeed with Pinnacle provider."""
        feed = OddsFeed(pinnacle_key="test_key")
        assert OddsProvider.PINNACLE in feed.providers
        assert feed.is_configured()

    def test_remove_overround_proportional(self):
        """Test proportional overround removal."""
        feed = OddsFeed()
        odds = Odds(home=1.9, draw=3.5, away=4.0)  # Has overround

        fair_odds = feed.remove_overround_proportional(odds)

        # Fair odds should be higher (lower implied probability)
        assert fair_odds.home > odds.home
        assert fair_odds.draw > odds.draw
        assert fair_odds.away > odds.away

        # Fair odds should have no margin
        fair_probs = fair_odds.to_probabilities()
        assert abs(sum(fair_probs) - 1.0) < 0.001

    def test_remove_overround_additive(self):
        """Test additive overround removal."""
        feed = OddsFeed()
        odds = Odds(home=1.9, draw=3.5, away=4.0)

        fair_odds = feed.remove_overround_additive(odds)

        # Fair odds should be higher
        assert fair_odds.home > odds.home
        assert fair_odds.draw > odds.draw
        assert fair_odds.away > odds.away

        # Should have no margin
        fair_probs = fair_odds.to_probabilities()
        assert abs(sum(fair_probs) - 1.0) < 0.001

    def test_calculate_market_efficiency_empty(self):
        """Test market efficiency with empty history."""
        feed = OddsFeed()
        metrics = feed.calculate_market_efficiency([])

        assert metrics.clv == 0.0
        assert metrics.market_margin == 0.0
        assert not metrics.sharp_movement_detected
        assert metrics.steam_score == 0.0

    def test_calculate_market_efficiency_with_history(self):
        """Test market efficiency with odds history."""
        feed = OddsFeed()
        now = datetime.utcnow()

        history = [
            OddsSnapshot(
                provider=OddsProvider.PINNACLE,
                sport="football",
                league="E0",
                match_id="123",
                odds=Odds(home=2.0, draw=3.2, away=3.5),
                timestamp=now - timedelta(days=7),
            ),
            OddsSnapshot(
                provider=OddsProvider.PINNACLE,
                sport="football",
                league="E0",
                match_id="123",
                odds=Odds(home=1.9, draw=3.3, away=3.8),
                timestamp=now,
            ),
        ]

        metrics = feed.calculate_market_efficiency(history)

        assert metrics.line_movement_pct > 0
        assert metrics.market_margin > 0

    def test_detect_sharp_movement(self):
        """Test sharp movement detection."""
        feed = OddsFeed()
        now = datetime.utcnow()

        history = [
            OddsSnapshot(
                provider=OddsProvider.PINNACLE,
                sport="football",
                league="E0",
                match_id="123",
                odds=Odds(home=2.0, draw=3.2, away=3.5),
                timestamp=now - timedelta(hours=2),
            ),
            OddsSnapshot(
                provider=OddsProvider.BETFAIR,
                sport="football",
                league="E0",
                match_id="123",
                odds=Odds(home=1.85, draw=3.3, away=3.7),  # Home odds shortened
                timestamp=now,
                volume=50000,
            ),
        ]

        result = feed.detect_sharp_movement(history)

        assert "smart_money_side" in result
        assert "steam_moves" in result
        assert "reverse_line_movement" in result
        # Home odds shortened significantly -> smart money on home
        assert result["smart_money_side"] == "home"

    def test_get_available_providers(self):
        """Test getting available providers."""
        feed = OddsFeed(pinnacle_key="test")
        providers = feed.get_available_providers()
        assert OddsProvider.PINNACLE in providers

    def test_close(self):
        """Test closing the feed."""
        import asyncio
        feed = OddsFeed(pinnacle_key="test")
        asyncio.run(feed.close())
        # Should not raise


class TestPinnacleProvider:
    """Tests for PinnacleProvider."""

    def test_normalize_odds(self):
        """Test Pinnacle odds normalization."""
        provider = PinnacleProvider(api_key="test")

        # Test with periods format
        raw_odds = {
            "periods": [
                {"period": 0, "moneyline": {"home": 2.1, "draw": 3.3, "away": 3.6}},
            ]
        }
        odds = provider.normalize_odds(raw_odds)

        assert odds.home == 2.1
        assert odds.draw == 3.3
        assert odds.away == 3.6


class TestTheOddsAPIProvider:
    """Tests for TheOddsAPIProvider."""

    def test_normalize_odds(self):
        """Test TheOddsAPI odds normalization."""
        provider = TheOddsAPIProvider(api_key="test")

        raw_odds = {
            "bookmakers": [
                {
                    "markets": [
                        {
                            "key": "h2h",
                            "outcomes": [
                                {"name": "Home Team", "price": 2.1},
                                {"name": "Draw", "price": 3.3},
                                {"name": "Away Team", "price": 3.6},
                            ],
                        }
                    ]
                }
            ]
        }
        odds = provider.normalize_odds(raw_odds)

        assert odds.home == 2.1
        assert odds.draw == 3.3
        assert odds.away == 3.6


class TestCreateOddsFeedFromEnv:
    """Tests for create_odds_feed_from_env function."""

    @patch.dict("os.environ", {}, clear=True)
    def test_create_without_env(self):
        """Test creating feed without environment variables."""
        feed = create_odds_feed_from_env()
        assert not feed.is_configured()

    @patch.dict("os.environ", {"PINNACLE_API_KEY": "test"}, clear=True)
    def test_create_with_pinnacle_env(self):
        """Test creating feed with Pinnacle env."""
        feed = create_odds_feed_from_env()
        assert feed.is_configured()
        assert OddsProvider.PINNACLE in feed.providers


if __name__ == "__main__":
    pytest.main([__file__, "-v"])