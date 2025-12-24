import pytest
from datetime import datetime
from src.domain.services.picks_service import PicksService
from src.domain.entities.entities import Match, Team, League, TeamStatistics
from src.domain.value_objects.value_objects import LeagueAverages

@pytest.fixture
def picks_service():
    """Fixture for PicksService."""
    return PicksService()

@pytest.fixture
def sample_match():
    """Sample match for testing."""
    return Match(
        id="match1",
        home_team=Team(id="team1", name="FC Dynamic"),
        away_team=Team(id="team2", name="SC Static"),
        match_date=datetime.now(),
        league=League(id="league1", name="Test League", country="Testland"),
        status="SCHEDULED",
        home_odds=2.0,
        draw_odds=3.0,
        away_odds=4.0,
    )

def test_generate_dynamic_goals_picks(picks_service, sample_match):
    """
    Test that goal picks are generated with dynamic thresholds based on
    predicted goals, not a fixed 2.5 line.
    """
    # High-scoring context: expecting lines like 3.5, 4.5
    home_stats = TeamStatistics(team_id="team1", matches_played=10, wins=0, draws=0, losses=0, goals_scored=25, goals_conceded=0)
    away_stats = TeamStatistics(team_id="team2", matches_played=10, wins=0, draws=0, losses=0, goals_scored=18, goals_conceded=0)
    
    picks = picks_service.generate_suggested_picks(
        match=sample_match,
        home_stats=home_stats,
        away_stats=away_stats,
        predicted_home_goals=2.5,
        predicted_away_goals=1.8, # Total expected: 4.3
    )

    assert picks is not None
    suggested_picks = picks.suggested_picks
    
    # Check for dynamic goal lines like 3.5 or 4.5
    has_dynamic_over = any("Más de 3.5 goles" in p.market_label for p in suggested_picks)
    has_dynamic_under = any("Menos de 4.5 goles" in p.market_label for p in suggested_picks)
    
    assert has_dynamic_over or has_dynamic_under, "Should generate dynamic goal lines like 3.5 or 4.5"
    
    # Ensure no hardcoded 2.5 unless it's the calculated dynamic line
    total_expected = 4.3
    main_line = 3.5 # Calculated based on new logic
    
    has_hardcoded_over = any("Más de 2.5 goles" in p.market_label and main_line != 2.5 for p in suggested_picks)
    
    assert not has_hardcoded_over, "Should not use hardcoded 'Más de 2.5 goles' if dynamic line is different"


def test_generate_dynamic_corners_picks(picks_service, sample_match):
    """
    Test that corner picks use dynamic thresholds based on team averages.
    """
    # High-corner context
    home_stats = TeamStatistics(team_id="team1", matches_played=10, wins=0, draws=0, losses=0, goals_scored=0, goals_conceded=0, total_corners=72)
    away_stats = TeamStatistics(team_id="team2", matches_played=10, wins=0, draws=0, losses=0, goals_scored=0, goals_conceded=0, total_corners=41) # Total avg: 11.3
    
    picks = picks_service.generate_suggested_picks(
        match=sample_match,
        home_stats=home_stats,
        away_stats=away_stats,
    )
    
    assert picks is not None
    suggested_picks = picks.suggested_picks
    
    # Expected dynamic lines: 10.5, 11.5
    has_dynamic_over = any("Más de 10.5 córners" in p.market_label for p in suggested_picks)
    has_dynamic_under = any("Menos de 11.5 córners" in p.market_label for p in suggested_picks)
    
    assert has_dynamic_over or has_dynamic_under, "Should generate dynamic corner lines around 10.5/11.5"
    
    # Ensure reasoning includes the specific averages
    for pick in suggested_picks:
        if "córners" in pick.market_label:
            assert "Promedio de córners: 11.30" in pick.reasoning or "Línea de" in pick.reasoning


def test_generate_dynamic_cards_picks(picks_service, sample_match):
    """
    Test that card picks use dynamic thresholds.
    """
    # High-card context
    home_stats = TeamStatistics(team_id="team1", matches_played=10, wins=0, draws=0, losses=0, goals_scored=0, goals_conceded=0, total_yellow_cards=28)
    away_stats = TeamStatistics(team_id="team2", matches_played=10, wins=0, draws=0, losses=0, goals_scored=0, goals_conceded=0, total_yellow_cards=21) # Total avg: 4.9
    
    picks = picks_service.generate_suggested_picks(
        match=sample_match,
        home_stats=home_stats,
        away_stats=away_stats,
    )
    
    assert picks is not None
    suggested_picks = picks.suggested_picks

    # Expected dynamic lines: 4.5, 5.5
    has_dynamic_over = any("Más de 4.5 tarjetas" in p.market_label for p in suggested_picks)
    has_dynamic_under = any("Menos de 5.5 tarjetas" in p.market_label for p in suggested_picks)
    
    assert has_dynamic_over or has_dynamic_under, "Should generate dynamic card lines around 4.5/5.5"
    
    # Ensure reasoning includes the specific averages
    for pick in suggested_picks:
        if "tarjetas" in pick.market_label:
            assert "Promedio de tarjetas: 4.90" in pick.reasoning or "Línea de" in pick.reasoning


def test_generate_dynamic_handicap_picks(picks_service, sample_match):
    """
    Test that handicap picks are dynamic and can be negative for favorites.
    """
    # Clear favorite context
    home_stats = TeamStatistics(team_id="team1", matches_played=10, wins=0, draws=0, losses=0, goals_scored=0, goals_conceded=0)
    away_stats = TeamStatistics(team_id="team2", matches_played=10, wins=0, draws=0, losses=0, goals_scored=0, goals_conceded=0)
    
    picks = picks_service.generate_suggested_picks(
        match=sample_match,
        home_stats=home_stats,
        away_stats=away_stats,
        predicted_home_goals=2.8, # Expected goal diff of 1.5
        predicted_away_goals=1.3,
        home_win_prob=0.75,
        away_win_prob=0.15,
    )

    assert picks is not None
    suggested_picks = picks.suggested_picks
    
    # Check for a negative handicap on the favorite (FC Dynamic)
    # With goal_diff=1.5, base handicap is 1.5, lines to test are ~ -1.25, -1.5, -1.75
    has_negative_handicap = any(
        "Hándicap Asiático -" in p.market_label and "FC Dynamic" in p.market_label for p in suggested_picks
    )
    
    # Check for a positive handicap on the underdog (SC Static)
    # With goal_diff=-1.5, base is -1.5, lines to test are ~ +1.25, +1.5, +1.75
    has_positive_handicap = any(
        "Hándicap Asiático +" in p.market_label and "SC Static" in p.market_label for p in suggested_picks
    )

    assert has_negative_handicap, "Should generate a negative handicap for the favorite."
    assert has_positive_handicap, "Should generate a positive handicap for the underdog."


def test_picks_are_sorted_by_probability(picks_service, sample_match):
    """
    Test that the final list of suggested picks is sorted by probability
    in descending order.
    """
    # Setup a context that will generate a variety of picks
    home_stats = TeamStatistics(
        team_id="team1", 
        matches_played=10, 
        wins=0, draws=0, losses=0,
        goals_scored=25, 
        goals_conceded=0,
        total_corners=72,
        total_yellow_cards=28
    )
    away_stats = TeamStatistics(
        team_id="team2", 
        matches_played=10, 
        wins=0, draws=0, losses=0,
        goals_scored=18,
        goals_conceded=0,
        total_corners=41,
        total_yellow_cards=21
    )
    
    picks_result = picks_service.generate_suggested_picks(
        match=sample_match,
        home_stats=home_stats,
        away_stats=away_stats,
        predicted_home_goals=2.8,
        predicted_away_goals=1.3,
        home_win_prob=0.75, # High prob winner pick
        away_win_prob=0.15,
        draw_prob=0.10,
    )

    assert picks_result is not None
    suggested_picks = picks_result.suggested_picks
    
    # Ensure we have more than one pick to test sorting
    assert len(suggested_picks) > 1
    
    # Check if the list is sorted by probability descending
    probabilities = [p.probability for p in suggested_picks]
    assert probabilities == sorted(probabilities, reverse=True), "Picks are not sorted by probability descending."
