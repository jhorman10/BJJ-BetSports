"""
Unit Tests for Domain Entities

Tests the core domain entities and their validation logic.
"""

import pytest
from datetime import datetime

from src.domain.entities.entities import (
    Team,
    League,
    Match,
    Prediction,
    TeamStatistics,
    MatchOutcome,
)


class TestTeam:
    """Tests for Team entity."""
    
    def test_create_team_valid(self):
        """Test creating a valid team."""
        team = Team(id="test_id", name="Test FC", country="England")
        assert team.id == "test_id"
        assert team.name == "Test FC"
        assert team.country == "England"
    
    def test_create_team_without_optional_fields(self):
        """Test creating team without optional fields."""
        team = Team(id="test_id", name="Test FC")
        assert team.short_name is None
        assert team.country is None
    
    def test_team_is_frozen(self):
        """Test that Team is immutable."""
        team = Team(id="test_id", name="Test FC")
        with pytest.raises(AttributeError):
            team.name = "New Name"
    
    def test_team_empty_name_raises_error(self):
        """Test that empty name raises ValueError."""
        with pytest.raises(ValueError, match="Team name cannot be empty"):
            Team(id="test_id", name="")


class TestLeague:
    """Tests for League entity."""
    
    def test_create_league_valid(self):
        """Test creating a valid league."""
        league = League(
            id="E0",
            name="Premier League",
            country="England",
            season="2024-2025",
        )
        assert league.id == "E0"
        assert league.name == "Premier League"
        assert league.country == "England"
        assert league.season == "2024-2025"
    
    def test_league_requires_name_and_country(self):
        """Test that league requires name and country."""
        with pytest.raises(ValueError, match="League name and country are required"):
            League(id="E0", name="", country="England")


class TestMatch:
    """Tests for Match entity."""
    
    @pytest.fixture
    def sample_match(self):
        """Create a sample match for testing."""
        home = Team(id="home_id", name="Home FC")
        away = Team(id="away_id", name="Away FC")
        league = League(id="E0", name="Premier League", country="England")
        
        return Match(
            id="match_1",
            home_team=home,
            away_team=away,
            league=league,
            match_date=datetime(2024, 1, 15, 15, 0),
        )
    
    def test_match_not_played(self, sample_match):
        """Test unplayed match properties."""
        assert sample_match.is_played is False
        assert sample_match.outcome is None
        assert sample_match.total_goals is None
    
    def test_match_played_home_win(self, sample_match):
        """Test played match with home win."""
        sample_match.home_goals = 2
        sample_match.away_goals = 1
        
        assert sample_match.is_played is True
        assert sample_match.outcome == MatchOutcome.HOME_WIN
        assert sample_match.total_goals == 3
    
    def test_match_played_draw(self, sample_match):
        """Test played match with draw."""
        sample_match.home_goals = 1
        sample_match.away_goals = 1
        
        assert sample_match.outcome == MatchOutcome.DRAW
    
    def test_match_played_away_win(self, sample_match):
        """Test played match with away win."""
        sample_match.home_goals = 0
        sample_match.away_goals = 2
        
        assert sample_match.outcome == MatchOutcome.AWAY_WIN


class TestPrediction:
    """Tests for Prediction entity."""
    
    def test_create_valid_prediction(self):
        """Test creating a valid prediction."""
        prediction = Prediction(
            match_id="match_1",
            home_win_probability=0.45,
            draw_probability=0.30,
            away_win_probability=0.25,
            over_25_probability=0.55,
            under_25_probability=0.45,
            predicted_home_goals=1.5,
            predicted_away_goals=1.2,
            confidence=0.75,
            data_sources=["Football-Data.co.uk"],
        )
        assert prediction.match_id == "match_1"
        assert prediction.home_win_probability == 0.45
    
    def test_prediction_probabilities_must_sum_to_one(self):
        """Test that match outcome probabilities must sum to 1."""
        with pytest.raises(ValueError, match="probabilities must sum to 1"):
            Prediction(
                match_id="match_1",
                home_win_probability=0.5,
                draw_probability=0.5,
                away_win_probability=0.5,  # Sum = 1.5
                over_25_probability=0.55,
                under_25_probability=0.45,
                predicted_home_goals=1.5,
                predicted_away_goals=1.2,
                confidence=0.75,
            )
    
    def test_prediction_probability_range(self):
        """Test that probabilities must be between 0 and 1."""
        with pytest.raises(ValueError, match="Probability must be between 0 and 1"):
            Prediction(
                match_id="match_1",
                home_win_probability=1.5,  # Invalid
                draw_probability=0.30,
                away_win_probability=0.25,
                over_25_probability=0.55,
                under_25_probability=0.45,
                predicted_home_goals=1.5,
                predicted_away_goals=1.2,
                confidence=0.75,
            )
    
    def test_recommended_bet(self):
        """Test recommended bet calculation."""
        prediction = Prediction(
            match_id="match_1",
            home_win_probability=0.50,
            draw_probability=0.30,
            away_win_probability=0.20,
            over_25_probability=0.55,
            under_25_probability=0.45,
            predicted_home_goals=1.5,
            predicted_away_goals=1.2,
            confidence=0.75,
        )
        assert prediction.recommended_bet == "Home Win (1)"
    
    def test_over_under_recommendation(self):
        """Test over/under recommendation."""
        prediction = Prediction(
            match_id="match_1",
            home_win_probability=0.45,
            draw_probability=0.30,
            away_win_probability=0.25,
            over_25_probability=0.60,
            under_25_probability=0.40,
            predicted_home_goals=1.5,
            predicted_away_goals=1.2,
            confidence=0.75,
        )
        assert prediction.over_under_recommendation == "Over 2.5"


class TestTeamStatistics:
    """Tests for TeamStatistics entity."""
    
    def test_team_statistics_calculations(self):
        """Test calculated properties."""
        stats = TeamStatistics(
            team_id="test_team",
            matches_played=10,
            wins=5,
            draws=3,
            losses=2,
            goals_scored=15,
            goals_conceded=10,
            home_wins=3,
            away_wins=2,
            recent_form="WWDLW",
        )
        
        assert stats.win_rate == 0.5
        assert stats.goals_per_match == 1.5
        assert stats.goals_conceded_per_match == 1.0
        assert stats.goal_difference == 5
    
    def test_team_statistics_zero_matches(self):
        """Test calculations with zero matches."""
        stats = TeamStatistics(
            team_id="test_team",
            matches_played=0,
            wins=0,
            draws=0,
            losses=0,
            goals_scored=0,
            goals_conceded=0,
        )
        
        assert stats.win_rate == 0.0
        assert stats.goals_per_match == 0.0
