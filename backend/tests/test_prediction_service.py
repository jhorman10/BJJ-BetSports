"""
Unit Tests for Prediction Service

Tests the core prediction algorithm and calculations.
"""

import pytest
import math

from src.domain.services.prediction_service import (
    PredictionService,
    LeagueAverages,
)
from src.domain.entities.entities import (
    Team,
    League,
    Match,
    TeamStatistics,
)
from src.domain.value_objects.value_objects import TeamStrength
from datetime import datetime


class TestPredictionService:
    """Tests for PredictionService."""
    
    @pytest.fixture
    def service(self):
        """Create prediction service instance."""
        return PredictionService()
    
    @pytest.fixture
    def league_averages(self):
        """Create sample league averages."""
        return LeagueAverages(
            avg_home_goals=1.5,
            avg_away_goals=1.1,
            avg_total_goals=2.6,
        )
    
    @pytest.fixture
    def sample_match(self):
        """Create sample match for testing."""
        home = Team(id="home_id", name="Home FC")
        away = Team(id="away_id", name="Away FC")
        league = League(id="E0", name="Premier League", country="England")
        
        return Match(
            id="match_1",
            home_team=home,
            away_team=away,
            league=league,
            match_date=datetime(2024, 1, 15, 15, 0),
            home_odds=2.0,
            draw_odds=3.5,
            away_odds=3.2,
        )
    
    def test_poisson_probability(self, service):
        """Test Poisson probability calculation."""
        # P(X=2) when λ=2 should be about 0.27
        prob = service.poisson_probability(2.0, 2)
        assert 0.26 < prob < 0.28
        
        # P(X=0) when λ=1 should be about 0.37
        prob = service.poisson_probability(1.0, 0)
        assert 0.36 < prob < 0.38
    
    def test_poisson_probability_edge_cases(self, service):
        """Test Poisson probability edge cases."""
        # λ=0 should give P(X=0)=1 and P(X>0)=0
        assert service.poisson_probability(0.0, 0) == 1.0
        assert service.poisson_probability(0.0, 1) == 0.0
    
    def test_calculate_team_strength(self, service, league_averages):
        """Test team strength calculation."""
        stats = TeamStatistics(
            team_id="test_team",
            matches_played=10,
            wins=5,
            draws=3,
            losses=2,
            goals_scored=15,
            goals_conceded=8,
        )
        
        strength = service.calculate_team_strength(stats, league_averages, is_home=True)
        
        assert strength.attack_strength > 0
        assert strength.defense_strength > 0
    
    def test_calculate_team_strength_no_matches(self, service, league_averages):
        """Test team strength with no match history."""
        stats = TeamStatistics(
            team_id="new_team",
            matches_played=0,
            wins=0,
            draws=0,
            losses=0,
            goals_scored=0,
            goals_conceded=0,
        )
        
        strength = service.calculate_team_strength(stats, league_averages)
        
        # Should return average strength
        assert strength.attack_strength == 1.0
        assert strength.defense_strength == 1.0
    
    def test_calculate_expected_goals(self, service, league_averages):
        """Test expected goals calculation."""
        home_strength = TeamStrength(attack_strength=1.2, defense_strength=0.8)
        away_strength = TeamStrength(attack_strength=1.0, defense_strength=1.0)
        
        home_exp, away_exp = service.calculate_expected_goals(
            home_strength, away_strength, league_averages
        )
        
        # Home team should be expected to score more
        assert home_exp > 0
        assert away_exp > 0
    
    def test_calculate_outcome_probabilities(self, service):
        """Test outcome probability calculation."""
        home_win, draw, away_win = service.calculate_outcome_probabilities(
            home_expected=1.5,
            away_expected=1.0,
        )
        
        # Probabilities should sum to 1
        assert abs(home_win + draw + away_win - 1.0) < 0.01
        
        # Home win should be more likely given higher expected goals
        assert home_win > away_win
    
    def test_calculate_outcome_probabilities_equal_teams(self, service):
        """Test outcome probabilities for equal teams."""
        home_win, draw, away_win = service.calculate_outcome_probabilities(
            home_expected=1.2,
            away_expected=1.2,
        )
        
        # Should be roughly equal for home and away
        assert abs(home_win - away_win) < 0.05
    
    def test_calculate_over_under_probability(self, service):
        """Test over/under 2.5 probability calculation."""
        over, under = service.calculate_over_under_probability(
            home_expected=2.0,
            away_expected=1.5,
        )
        
        # Should sum to 1
        assert abs(over + under - 1.0) < 0.01
        
        # With 3.5 expected total goals, over 2.5 should be likely
        assert over > under
    
    def test_calculate_over_under_low_scoring(self, service):
        """Test over/under for low-scoring match."""
        over, under = service.calculate_over_under_probability(
            home_expected=0.8,
            away_expected=0.6,
        )
        
        # With 1.4 expected total goals, under 2.5 should be more likely
        assert under > over
    
    def test_adjust_with_odds(self, service):
        """Test odds adjustment."""
        from src.domain.value_objects.value_objects import Odds
        
        calculated = (0.4, 0.3, 0.3)
        odds = Odds(home=2.0, draw=3.5, away=3.5)
        
        adjusted = service.adjust_with_odds(calculated, odds, weight=0.5)
        
        # Adjusted should still sum to 1
        assert abs(sum(adjusted) - 1.0) < 0.01
    
    def test_generate_prediction(self, service, sample_match, league_averages):
        """Test complete prediction generation."""
        home_stats = TeamStatistics(
            team_id="home_id",
            matches_played=10,
            wins=6,
            draws=2,
            losses=2,
            goals_scored=18,
            goals_conceded=10,
        )
        
        away_stats = TeamStatistics(
            team_id="away_id",
            matches_played=10,
            wins=4,
            draws=3,
            losses=3,
            goals_scored=12,
            goals_conceded=12,
        )
        
        prediction = service.generate_prediction(
            match=sample_match,
            home_stats=home_stats,
            away_stats=away_stats,
            league_averages=league_averages,
            data_sources=["Football-Data.co.uk"],
        )
        
        # Verify prediction properties
        assert prediction.match_id == sample_match.id
        assert 0 <= prediction.home_win_probability <= 1
        assert 0 <= prediction.draw_probability <= 1
        assert 0 <= prediction.away_win_probability <= 1
        assert prediction.predicted_home_goals >= 0
        assert prediction.predicted_away_goals >= 0
        assert 0 <= prediction.confidence <= 1
        assert "Football-Data.co.uk" in prediction.data_sources
    
    def test_generate_prediction_no_stats(self, service, sample_match):
        """Test prediction generation without team stats."""
        prediction = service.generate_prediction(
            match=sample_match,
            home_stats=None,
            away_stats=None,
        )
        
        # Should still generate valid prediction with defaults
        assert prediction is not None
        assert 0 <= prediction.home_win_probability <= 1
    
    def test_confidence_calculation(self, service):
        """Test confidence calculation based on data availability and certainty."""
        # High confidence with lots of data, certain prediction, and recent form
        high_stats = TeamStatistics(
            team_id="team",
            matches_played=30,  # More matches
            wins=15,
            draws=10,
            losses=5,
            goals_scored=45,
            goals_conceded=30,
            recent_form="WWWWW"  # Consistent form
        )
        
        # Low entropy probabilities (very certain)
        certain_probs = (0.8, 0.1, 0.1)
        
        from src.domain.value_objects.value_objects import Odds
        odds = Odds(home=1.2, draw=6.0, away=12.0)
        
        confidence = service.calculate_confidence(
            high_stats, high_stats, has_odds=True,
            calculated_probs=certain_probs,
            odds=odds
        )
        # Should be high now
        assert confidence >= 0.6
        
        # Lower confidence with no stats and high entropy
        low_confidence = service.calculate_confidence(
            None, None, has_odds=False,
            calculated_probs=(0.33, 0.34, 0.33)
        )
        assert low_confidence < confidence
