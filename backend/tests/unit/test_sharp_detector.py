"""
Unit tests for SharpMoneyDetector module.
"""

import pytest
from datetime import datetime, timedelta


from src.domain.value_objects.value_objects import Odds
from src.domain.services.sharp_detector import (
    SharpMoneyDetector,
    SharpMoneySignal,
    SteamMove,
)
from src.infrastructure.odds_feed import OddsSnapshot, OddsProvider


class TestSharpMoneyDetector:
    """Tests for SharpMoneyDetector class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.detector = SharpMoneyDetector(
            min_movement_pct=0.01,
            min_volume=1000,
            steam_window_minutes=60,
        )
        self.now = datetime.utcnow()

    def test_calculate_movements(self):
        """Test line movement calculation."""
        opening = Odds(home=2.0, draw=3.2, away=3.5)
        current = Odds(home=1.9, draw=3.3, away=3.7)

        movements = self.detector._calculate_movements(opening, current)

        assert "home" in movements
        assert "draw" in movements
        assert "away" in movements

        # Home shortened from 2.0 to 1.9 = -5%
        assert abs(movements["home"] - (-0.05)) < 0.001
        # Draw lengthened from 3.2 to 3.3 = +3.125%
        assert abs(movements["draw"] - (0.1/3.2)) < 0.001
        # Away lengthened from 3.5 to 3.7 = +5.7%
        assert abs(movements["away"] - (0.2/3.5)) < 0.001

    def test_calculate_steam_score_basic(self):
        """Test steam score calculation with basic inputs."""
        movements = {"home": -0.03, "draw": 0.02, "away": 0.01}
        volume = {"home": 50000, "draw": 10000, "away": 5000}

        score = self.detector.calculate_steam_score(movements, volume, time_window_minutes=30)

        assert 0 <= score <= 1
        # 3% move with high volume should give decent score
        assert score > 0.3

    def test_calculate_steam_score_no_volume(self):
        """Test steam score without volume data."""
        movements = {"home": -0.03, "draw": 0.02, "away": 0.01}

        score = self.detector.calculate_steam_score(movements, None, time_window_minutes=30)

        assert 0 <= score <= 1

    def test_calculate_steam_score_small_movement(self):
        """Test steam score with small movement and low volume."""
        movements = {"home": -0.002, "draw": 0.001, "away": 0.001}
        volume = {"home": 500, "draw": 100, "away": 50}  # Low volume (< min_volume)

        score = self.detector.calculate_steam_score(movements, volume, time_window_minutes=30)

        # Small movement + low volume should give low score
        # movement_score: 0.002 * 20 = 0.04
        # volume_score: 500 / 10000 = 0.05
        # time_score: 1 - 30/120 = 0.75
        # Total: 0.04*0.5 + 0.05*0.3 + 0.75*0.2 = 0.02 + 0.015 + 0.15 = 0.185
        assert score < 0.2

    def test_detect_reverse_line_movement(self):
        """Test reverse line movement detection."""
        # Line moves against public (public 70% on home, but home odds lengthened)
        movements = {"home": 0.02, "draw": -0.01, "away": -0.01}
        public_pcts = {"home": 0.70, "draw": 0.15, "away": 0.15}

        rlm = self.detector._detect_reverse_line_movement(movements, public_pcts)

        assert rlm is True

    def test_no_reverse_line_movement_low_public(self):
        """Test no RLM when public not heavily on one side."""
        movements = {"home": 0.02, "draw": -0.01, "away": -0.01}
        public_pcts = {"home": 0.45, "draw": 0.30, "away": 0.25}

        rlm = self.detector._detect_reverse_line_movement(movements, public_pcts)

        assert rlm is False

    def test_no_reverse_line_movement_line_with_public(self):
        """Test no RLM when line moves with public."""
        movements = {"home": -0.02, "draw": 0.01, "away": 0.01}
        public_pcts = {"home": 0.70, "draw": 0.15, "away": 0.15}

        rlm = self.detector._detect_reverse_line_movement(movements, public_pcts)

        assert rlm is False

    def test_identify_smart_money_side_with_steam(self):
        """Test smart money identification with steam moves."""
        history = self._create_history_with_steam("home")

        # Method expects public_percentages as second arg
        smart_side = self.detector.identify_smart_money_side(history, public_percentages=None)

        # Steam on home (odds shortened) -> smart money on home
        assert smart_side == "home"

    def test_identify_smart_money_side_with_rlm(self):
        """Test smart money identification with RLM."""
        history = self._create_history_rlm("home")  # Public on home, line against home

        public = {"home": 0.75, "draw": 0.15, "away": 0.10}

        smart_side = self.detector.identify_smart_money_side(history, public_percentages=public)

        # RLM -> smart money on opposite side (away or draw)
        assert smart_side in ["away", "draw"]

    def test_identify_smart_money_side_no_signal(self):
        """Test smart money identification with no clear signal."""
        history = self._create_history_no_signal()

        smart_side = self.detector.identify_smart_money_side(history, public_percentages=None)

        assert smart_side is None

    def test_analyze_line_movement_full(self):
        """Test full line movement analysis."""
        opening = Odds(home=2.0, draw=3.2, away=3.5)
        current = Odds(home=1.9, draw=3.3, away=3.7)

        history = [
            OddsSnapshot(
                provider=OddsProvider.PINNACLE,
                sport="football",
                league="E0",
                match_id="123",
                odds=opening,
                timestamp=self.now - timedelta(days=3),
            ),
            OddsSnapshot(
                provider=OddsProvider.PINNACLE,
                sport="football",
                league="E0",
                match_id="123",
                odds=Odds(home=1.95, draw=3.25, away=3.6),
                timestamp=self.now - timedelta(days=1),
            ),
            OddsSnapshot(
                provider=OddsProvider.BETFAIR,
                sport="football",
                league="E0",
                match_id="123",
                odds=current,
                timestamp=self.now,
                volume=50000,
            ),
        ]

        signal = self.detector.analyze_line_movement(
            opening_odds=opening,
            current_odds=current,
            odds_history=history,
        )

        assert isinstance(signal, SharpMoneySignal)
        assert signal.steam_score >= 0
        assert signal.confidence >= 0
        assert "movements_pct" in signal.line_movement_analysis

    def test_analyze_odds_series(self):
        """Test analyzing odds series directly."""
        history = self._create_history_with_steam("home")

        signal = self.detector.analyze_odds_series(history)

        assert isinstance(signal, SharpMoneySignal)
        assert signal.steam_score >= 0
        assert signal.confidence >= 0

    def test_calculate_confidence(self):
        """Test confidence calculation."""
        movements = {"home": -0.03, "draw": 0.01, "away": 0.02}
        steam_moves = [
            SteamMove(
                outcome="home",
                movement_pct=0.03,
                volume=50000,
                time_window_minutes=30,
                timestamp=self.now,
                provider=OddsProvider.PINNACLE,
                confidence=0.8,
            )
        ]

        conf = self.detector._calculate_confidence(
            steam_score=0.6,
            rlm=False,
            smart_side="home",
            steam_moves=steam_moves,
            movements=movements,
        )

        assert 0 <= conf <= 1

    def test_get_movement_direction(self):
        """Test movement direction helper."""
        opening = Odds(home=2.0, draw=3.2, away=3.5)
        current = Odds(home=1.85, draw=3.3, away=3.7)

        directions = self.detector.get_movement_direction(opening, current)

        assert directions["home"] == "shortened"
        assert directions["away"] == "lengthened"
        assert directions["draw"] == "lengthened"

    def test_calculate_closing_line_value(self):
        """Test CLV calculation."""
        model_probs = {"home": 0.55, "draw": 0.25, "away": 0.20}
        closing = Odds(home=2.0, draw=3.5, away=4.0)

        clv = self.detector.calculate_closing_line_value(model_probs, closing)

        assert clv["home"] == 0.55 * 2.0 - 1  # 0.10
        assert clv["draw"] == 0.25 * 3.5 - 1  # -0.125
        assert clv["away"] == 0.20 * 4.0 - 1  # -0.20

    # Helper methods for creating test data
    def _create_history_with_steam(self, side: str) -> list[OddsSnapshot]:
        """Create odds history with steam move on specified side."""
        base_odds = {"home": 2.0, "draw": 3.2, "away": 3.5}
        current_odds = base_odds.copy()
        current_odds[side] *= 0.92  # 8% shortening

        return [
            OddsSnapshot(
                provider=OddsProvider.PINNACLE,
                sport="football",
                league="E0",
                match_id="123",
                odds=Odds(**base_odds),
                timestamp=self.now - timedelta(hours=2),
            ),
            OddsSnapshot(
                provider=OddsProvider.BETFAIR,
                sport="football",
                league="E0",
                match_id="123",
                odds=Odds(**current_odds),
                timestamp=self.now,
                volume=50000,
            ),
        ]

    def _create_history_rlm(self, public_side: str) -> list[OddsSnapshot]:
        """Create odds history with RLM (line moves against public)."""
        base_odds = {"home": 2.0, "draw": 3.2, "away": 3.5}
        # Line moves AGAINST public side (odds lengthen for public side)
        current_odds = base_odds.copy()
        current_odds[public_side] *= 1.05  # 5% lengthening

        return [
            OddsSnapshot(
                provider=OddsProvider.PINNACLE,
                sport="football",
                league="E0",
                match_id="123",
                odds=Odds(**base_odds),
                timestamp=self.now - timedelta(hours=2),
            ),
            OddsSnapshot(
                provider=OddsProvider.BETFAIR,
                sport="football",
                league="E0",
                match_id="123",
                odds=Odds(**current_odds),
                timestamp=self.now,
                volume=30000,
            ),
        ]

    def _create_history_no_signal(self) -> list[OddsSnapshot]:
        """Create odds history with no clear signal."""
        base_odds = {"home": 2.0, "draw": 3.2, "away": 3.5}
        current_odds = {"home": 2.01, "draw": 3.21, "away": 3.51}  # Tiny moves

        return [
            OddsSnapshot(
                provider=OddsProvider.PINNACLE,
                sport="football",
                league="E0",
                match_id="123",
                odds=Odds(**base_odds),
                timestamp=self.now - timedelta(hours=2),
            ),
            OddsSnapshot(
                provider=OddsProvider.PINNACLE,
                sport="football",
                league="E0",
                match_id="123",
                odds=Odds(**current_odds),
                timestamp=self.now,
                volume=1000,
            ),
        ]


class TestSharpMoneySignal:
    """Tests for SharpMoneySignal dataclass."""

    def test_signal_creation(self):
        """Test creating a sharp money signal."""
        signal = SharpMoneySignal(
            smart_money_side="home",
            steam_score=0.75,
            reverse_line_movement=True,
            confidence=0.8,
        )

        assert signal.smart_money_side == "home"
        assert signal.steam_score == 0.75
        assert signal.reverse_line_movement is True
        assert signal.confidence == 0.8


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
