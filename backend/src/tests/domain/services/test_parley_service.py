import pytest
from datetime import datetime
from src.domain.services.parley_service import ParleyService, ParleyConfig
from src.domain.entities.entities import MatchPrediction, Prediction, Team, Match, League
from src.domain.entities.suggested_pick import SuggestedPick

# Mock Data
def create_mock_prediction(home_prob, away_prob, over_prob, home="Home", away="Away"):
    return MatchPrediction(
        match=Match(
            id="1", 
            home_team=Team(id="h", name=home), 
            away_team=Team(id="a", name=away), 
            match_date=datetime.now(),
            league=League(id="1", name="Test League", country="Test Country"),
            status="SCHEDULED"
        ),
        prediction=Prediction(
            match_id="1",
            home_win_probability=home_prob,
            draw_probability=0.1,
            away_win_probability=away_prob,
            over_25_probability=over_prob,
            under_25_probability=1-over_prob,
            predicted_home_goals=1.5,
            predicted_away_goals=1.0,
            confidence=0.8,
            data_sources=["mock"]
        )
    )


@pytest.fixture
def parley_service():
    return ParleyService()

def test_filter_eligible_picks(parley_service):
    """Test filtering picks based on probability threshold."""
    preds = [
        create_mock_prediction(0.7, 0.2, 0.4, "StrongHome", "WeakAway"),
        create_mock_prediction(0.3, 0.6, 0.3, "WeakHome", "StrongAway"),
        create_mock_prediction(0.45, 0.45, 0.8, "GoalHome", "GoalAway"),
    ]
    
    # Min prob 0.6
    picks = parley_service._filter_eligible_picks(preds, 0.6)
    
    assert len(picks) == 3
    assert any(p.market_label == "Victoria StrongHome" for p in picks)
    assert any(p.market_label == "Victoria StrongAway" for p in picks)
    assert any(p.market_type == "goals_over" for p in picks)

def test_generate_parleys_min_picks(parley_service):
    """Test that parleys respect min_picks configuration."""
    # Create 5 high prob predictions
    preds = [
        create_mock_prediction(0.8, 0.1, 0.1, f"Home{i}", f"Away{i}") 
        for i in range(5)
    ]
    
    config = ParleyConfig(min_probability=0.7, min_picks=3, max_picks=3, count=5)
    
    parleys = parley_service.generate_parleys(preds, config)
    
    assert len(parleys) > 0
    for parley in parleys:
        assert len(parley.picks) == 3
        # Check totals calculation
        assert parley.total_probability > 0
        assert parley.total_odds > 1

def test_generate_parleys_insufficient_picks(parley_service):
    """Test handling when not enough picks are available."""
    preds = [create_mock_prediction(0.8, 0.1, 0.1)] # Only 1 valid pick
    
    config = ParleyConfig(min_probability=0.7, min_picks=3, max_picks=3)
    
    parleys = parley_service.generate_parleys(preds, config)
    
    assert len(parleys) == 0
