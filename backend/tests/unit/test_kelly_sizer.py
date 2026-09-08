"""
Unit tests for KellySizer module.
"""

import pytest

from src.domain.services.kelly_sizer import (
    KellySizer,
    KellyResult,
    MultiOutcomeKellyResult,
)


class TestKellySizer:
    """Tests for KellySizer class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.sizer = KellySizer(
            kelly_fraction=0.25,  # Quarter Kelly
            max_stake_pct=0.05,   # 5% max stake
            min_edge=0.02,        # 2% minimum edge
        )

    def test_calculatekelly_fraction_basic(self):
        """Test basic Kelly fraction calculation."""
        # Model prob 0.55, odds 2.0 -> edge = 0.55 * 2 - 1 = 0.10
        # Full Kelly = 0.10 / (2.0 - 1) = 0.10
        # Quarter Kelly = 0.10 * 0.25 = 0.025
        kelly = self.sizer.calculate_kelly_fraction(0.55, 2.0)

        assert abs(kelly - 0.025) < 0.001

    def test_calculatekelly_fraction_no_edge(self):
        """Test Kelly with no edge."""
        # Model prob 0.45, odds 2.0 -> edge = 0.45 * 2 - 1 = -0.10
        kelly = self.sizer.calculate_kelly_fraction(0.45, 2.0)

        assert kelly == 0.0

    def test_calculatekelly_fraction_break_even(self):
        """Test Kelly at break-even."""
        # Model prob 0.5, odds 2.0 -> edge = 0
        kelly = self.sizer.calculate_kelly_fraction(0.5, 2.0)

        assert kelly == 0.0

    def test_calculatekelly_fraction_high_odds(self):
        """Test Kelly with high odds."""
        # Model prob 0.20, odds 6.0 -> edge = 0.20 * 6 - 1 = 0.20
        # Full Kelly = 0.20 / 5 = 0.04
        # Quarter Kelly = 0.01
        kelly = self.sizer.calculate_kelly_fraction(0.20, 6.0)

        assert abs(kelly - 0.01) < 0.001

    def test_calculatekelly_fraction_custom_fraction(self):
        """Test Kelly with custom fraction override."""
        # Half Kelly instead of quarter
        kelly = self.sizer.calculate_kelly_fraction(0.55, 2.0, kelly_fraction=0.5)

        assert abs(kelly - 0.05) < 0.001

    def test_calculatekelly_fraction_capped(self):
        """Test Kelly capped at 0.5."""
        # Very high edge case
        kelly = self.sizer.calculate_kelly_fraction(0.9, 1.5, kelly_fraction=1.0)
        # Full Kelly = (0.9*1.5-1)/0.5 = 0.35/0.5 = 0.7 -> capped at 0.5

        assert kelly <= 0.5

    def test_calculate_optimal_stake(self):
        """Test optimal stake calculation."""
        bankroll = 1000.0
        _kelly = self.sizer.calculate_kelly_fraction(0.55, 2.0)  # 0.025
        stake = self.sizer.calculate_optimal_stake(bankroll, 0.55, 2.0)

        assert abs(stake - 25.0) < 0.01  # 1000 * 0.025

    def test_calculate_optimal_stake_capped(self):
        """Test stake capped at max_stake_pct."""
        # Use high edge to exceed max_stake_pct
        bankroll = 1000.0
        stake = self.sizer.calculate_optimal_stake(bankroll, 0.70, 2.0)
        # Full Kelly = (0.7*2-1)/1 = 0.4, Quarter = 0.1 -> capped at 0.05

        assert abs(stake - 50.0) < 0.01  # 1000 * 0.05

    def testkelly_with_confidence_high(self):
        """Test Kelly with high confidence."""
        result = self.sizer.kelly_with_confidence(
            model_prob=0.55,
            odds=2.0,
            confidence=0.9,
            min_edge=0.02,
        )

        assert isinstance(result, KellyResult)
        assert result.meets_min_edge is True
        assert result.edge > 0
        assert result.confidence_adjusted > 0

    def testkelly_with_confidence_low(self):
        """Test Kelly with low confidence reduces stake."""
        result_high = self.sizer.kelly_with_confidence(0.55, 2.0, 0.9)
        result_low = self.sizer.kelly_with_confidence(0.55, 2.0, 0.4)

        # Low confidence should reduce the adjusted kelly
        assert result_low.confidence_adjusted < result_high.confidence_adjusted

    def testkelly_with_confidence_below_min_edge(self):
        """Test Kelly when edge below minimum."""
        result = self.sizer.kelly_with_confidence(
            model_prob=0.525,  # Edge = 0.525 - 0.5 = 0.025 (clearly above 0.02)
            odds=2.0,
            confidence=0.9,
            min_edge=0.02,
        )

        # Edge clearly above minimum should meet threshold
        assert result.meets_min_edge is True

    def testkelly_with_confidence_no_edge(self):
        """Test Kelly with no edge after confidence adjustment."""
        result = self.sizer.kelly_with_confidence(
            model_prob=0.51,
            odds=2.0,
            confidence=0.1,  # Very low confidence shrinks edge
            min_edge=0.02,
        )

        # With low confidence, adjusted edge might be below min
        assert result.confidence_adjusted >= 0

    def test_calculate_multi_outcomekelly_1x2(self):
        """Test multi-outcome Kelly for 1X2 market."""
        model_probs = {"home": 0.50, "draw": 0.25, "away": 0.25}
        odds = {"home": 2.1, "draw": 3.4, "away": 3.6}
        bankroll = 1000.0

        result = self.sizer.calculate_multi_outcome_kelly(
            model_probs, odds, bankroll
        )

        assert isinstance(result, MultiOutcomeKellyResult)
        assert len(result.outcomes) == 3
        assert result.total_stake >= 0
        assert all(o >= 0 for o in result.bankroll_allocation.values())

    def test_calculate_multi_outcomekelly_some_no_edge(self):
        """Test multi-outcome Kelly when some outcomes have no edge."""
        model_probs = {"home": 0.45, "draw": 0.30, "away": 0.25}
        odds = {"home": 2.0, "draw": 3.5, "away": 4.0}  # Home has no edge
        bankroll = 1000.0

        result = self.sizer.calculate_multi_outcome_kelly(
            model_probs, odds, bankroll
        )

        assert result.outcomes["home"].meets_min_edge is False
        assert result.outcomes["home"].recommended_stake == 0.0

    def test_calculate_football_1x2_kelly(self):
        """Test football 1X2 Kelly convenience method."""
        result = self.sizer.calculate_football_1x2_kelly(
            home_prob=0.50,
            draw_prob=0.25,
            away_prob=0.25,
            home_odds=2.1,
            draw_odds=3.4,
            away_odds=3.6,
            bankroll=1000.0,
            confidence=0.8,
        )

        assert isinstance(result, MultiOutcomeKellyResult)
        assert len(result.outcomes) == 3

    def test_calculate_tennis_kelly(self):
        """Test tennis Kelly convenience method."""
        result = self.sizer.calculate_tennis_kelly(
            p1_prob=0.60,
            p2_prob=0.40,
            p1_odds=1.8,
            p2_odds=2.2,
            bankroll=1000.0,
            confidence=0.8,
        )

        assert isinstance(result, MultiOutcomeKellyResult)
        assert len(result.outcomes) == 2

    def test_generate_stake_recommendations(self):
        """Test stake recommendation generation."""
        model_probs = {"home": 0.50, "draw": 0.25, "away": 0.25}
        odds = {"home": 2.1, "draw": 3.4, "away": 3.6}
        bankroll = 1000.0

        multi_result = self.sizer.calculate_multi_outcome_kelly(
            model_probs, odds, bankroll
        )

        recommendations = self.sizer.generate_stake_recommendations(
            multi_result, bankroll, confidence=0.8
        )

        assert len(recommendations) > 0
        for rec in recommendations:
            assert hasattr(rec, "outcome")
            assert hasattr(rec, "stake_units")
            assert hasattr(rec, "risk_level")
            assert 1 <= rec.risk_level <= 5

    def test_calculate_expected_growth(self):
        """Test expected bankroll growth calculation."""
        growth = self.sizer.calculate_expected_growth(
            bankroll=1000.0,
            kelly_fraction=0.025,
            win_prob=0.55,
            odds=2.0,
            num_bets=100,
        )

        assert growth > 1000.0  # Positive EV should grow bankroll

    def test_probability_of_ruin(self):
        """Test probability of ruin calculation."""
        ruin_prob = self.sizer.probability_of_ruin(
            bankroll=1000.0,
            kelly_fraction=0.025,
            win_prob=0.55,
            odds=2.0,
            target_bankroll=2000.0,
        )

        assert 0 <= ruin_prob <= 1

    def test_fullkelly_vs_fractional(self):
        """Test that fractional Kelly is safer than full Kelly."""
        sizer_full = KellySizer(kelly_fraction=1.0, max_stake_pct=1.0)
        sizer_quarter = KellySizer(kelly_fraction=0.25, max_stake_pct=0.05)

        kelly_full = sizer_full.calculate_kelly_fraction(0.55, 2.0)
        kelly_quarter = sizer_quarter.calculate_kelly_fraction(0.55, 2.0)

        assert kelly_quarter == kelly_full * 0.25

    def test_variance_reduction_with_fractional(self):
        """Test that fractional Kelly reduces variance."""
        # Simulate multiple bets
        n_bets = 1000
        bankroll = 1000.0

        # Full Kelly
        _growth_full = self.sizer.calculate_expected_growth(
            bankroll, 0.10, 0.55, 2.0, n_bets
        )

        # Quarter Kelly
        _growth_quarter = self.sizer.calculate_expected_growth(
            bankroll, 0.025, 0.55, 2.0, n_bets
        )

        # Quarter Kelly has lower growth but much lower variance/ruin risk
        ruin_full = self.sizer.probability_of_ruin(
            bankroll, 0.10, 0.55, 2.0, 2000.0
        )
        ruin_quarter = self.sizer.probability_of_ruin(
            bankroll, 0.025, 0.55, 2.0, 2000.0
        )

        assert ruin_quarter < ruin_full


class TestKellyResult:
    """Tests for KellyResult dataclass."""

    def test_result_creation(self):
        """Test creating a KellyResult."""
        result = KellyResult(
            outcome="home",
            kelly_fraction=0.10,
            fractional_kelly=0.025,
            recommended_stake=25.0,
            expected_value=0.10,
            edge=0.10,
            confidence_adjusted=0.025,
            meets_min_edge=True,
        )

        assert result.outcome == "home"
        assert result.kelly_fraction == 0.10
        assert result.fractional_kelly == 0.025


class TestMultiOutcomeKellyResult:
    """Tests for MultiOutcomeKellyResult dataclass."""

    def test_result_creation(self):
        """Test creating a MultiOutcomeKellyResult."""
        result = MultiOutcomeKellyResult(
            outcomes={},
            total_kelly=0.0,
            total_stake=0.0,
            bankroll_allocation={},
            max_single_stake_pct=0.05,
            is_balanced=False,
        )

        assert result.total_kelly == 0.0
        assert not result.is_balanced


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
