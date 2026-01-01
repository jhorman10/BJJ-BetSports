"""
Domain Entities Module

This module contains the core domain entities for the football betting prediction system.
These entities represent the core business concepts and are independent of any infrastructure.
"""

from dataclasses import dataclass, field
from datetime import datetime
from src.utils.time_utils import get_current_time
from typing import Optional, TYPE_CHECKING
from enum import Enum

if TYPE_CHECKING:
    from .suggested_pick import SuggestedPick


class MatchOutcome(Enum):
    """Possible outcomes of a football match."""
    HOME_WIN = "home_win"
    DRAW = "draw"
    AWAY_WIN = "away_win"


@dataclass(frozen=True)
class Team:
    """
    Represents a football team.
    
    Attributes:
        id: Unique identifier for the team
        name: Full name of the team
        short_name: Abbreviated name (e.g., "MAN UTD")
        country: Country where the team is based
    """
    id: str
    name: str
    short_name: Optional[str] = None
    country: Optional[str] = None
    logo_url: Optional[str] = None
    
    def __post_init__(self):
        if not self.name:
            raise ValueError("Team name cannot be empty")


@dataclass(frozen=True)
class League:
    """
    Represents a football league or competition.
    
    Attributes:
        id: Unique identifier for the league
        name: Full name of the league (e.g., "Premier League")
        country: Country where the league is played
        season: Current season (e.g., "2024-2025")
    """
    id: str
    name: str
    country: str
    season: Optional[str] = None
    
    def __post_init__(self):
        if not self.name or not self.country:
            raise ValueError("League name and country are required")


@dataclass
class Match:
    """
    Represents a football match between two teams.
    
    Attributes:
        id: Unique identifier for the match
        home_team: The home team
        away_team: The away team
        league: The league/competition
        match_date: Date and time of the match
        home_goals: Goals scored by home team (None if not played)
        away_goals: Goals scored by away team (None if not played)
        home_odds: Betting odds for home win
        draw_odds: Betting odds for draw
        away_odds: Betting odds for away win
    """
    id: str
    home_team: Team
    away_team: Team
    league: League
    match_date: datetime
    home_goals: Optional[int] = None
    away_goals: Optional[int] = None
    status: str = "NS"  # NS=Not Started, LIVE, FT=Full Time, etc.
    home_corners: Optional[int] = None
    away_corners: Optional[int] = None
    home_yellow_cards: Optional[int] = None
    away_yellow_cards: Optional[int] = None
    home_red_cards: Optional[int] = None
    away_red_cards: Optional[int] = None
    home_odds: Optional[float] = None
    draw_odds: Optional[float] = None
    away_odds: Optional[float] = None
    minute: Optional[str] = None
    # Extended Stats
    home_shots_on_target: Optional[int] = None
    away_shots_on_target: Optional[int] = None
    home_total_shots: Optional[int] = None
    away_total_shots: Optional[int] = None
    home_possession: Optional[str] = None # "50%"
    away_possession: Optional[str] = None
    home_fouls: Optional[int] = None
    away_fouls: Optional[int] = None
    home_offsides: Optional[int] = None
    away_offsides: Optional[int] = None
    home_spi: Optional[float] = None
    away_spi: Optional[float] = None
    events: list["MatchEvent"] = field(default_factory=list)
    data_fetched_at: Optional[datetime] = None

    def __post_init__(self):
        """Ensure data consistency logic."""
        # 1. Shots on target must be at least goals scored
        if self.home_goals is not None and self.home_goals > 0:
            current_shots_on = self.home_shots_on_target or 0
            self.home_shots_on_target = max(current_shots_on, self.home_goals)
            
            # 2. Total shots must be at least shots on target
            current_total = self.home_total_shots or 0
            self.home_total_shots = max(current_total, self.home_shots_on_target)
            
        if self.away_goals is not None and self.away_goals > 0:
            current_shots_on = self.away_shots_on_target or 0
            self.away_shots_on_target = max(current_shots_on, self.away_goals)
            
            # 2. Total shots must be at least shots on target
            current_total = self.away_total_shots or 0
            self.away_total_shots = max(current_total, self.away_shots_on_target)
            
        # 3. Corners must be at least 0 if goals are present (logical, but ensure it's not None if goals exist and it's a live match)
        # Actually, let's keep it simple for now and only focus on Shots.

    @property
    def is_played(self) -> bool:
        """Check if the match has been played."""
        return self.home_goals is not None and self.away_goals is not None
    
    @property
    def outcome(self) -> Optional[MatchOutcome]:
        """Get the match outcome if played."""
        if not self.is_played:
            return None
        if self.home_goals > self.away_goals:
            return MatchOutcome.HOME_WIN
        elif self.home_goals < self.away_goals:
            return MatchOutcome.AWAY_WIN
        return MatchOutcome.DRAW
    
    @property
    def total_goals(self) -> Optional[int]:
        """Get total goals scored in the match."""
        if not self.is_played:
            return None
        return self.home_goals + self.away_goals

@dataclass
class MatchEvent:
    """
    Represents a significant event in a match (goal, card, substitution, etc).
    """
    time: str
    team_id: str
    player_name: str
    type: str  # "Goal", "Card", "subst"
    detail: str  # "Normal Goal", "Yellow Card", etc.


@dataclass
class Prediction:
    """
    Represents a prediction for a football match.
    
    Attributes:
        match_id: ID of the match being predicted
        home_win_probability: Probability of home team winning (0-1)
        draw_probability: Probability of a draw (0-1)
        away_win_probability: Probability of away team winning (0-1)
        over_25_probability: Probability of over 2.5 goals (0-1)
        under_25_probability: Probability of under 2.5 goals (0-1)
        predicted_home_goals: Expected goals for home team
        predicted_away_goals: Expected goals for away team
        confidence: Overall confidence in the prediction (0-1)
        data_sources: List of data sources used for this prediction
        created_at: Timestamp when prediction was created
    """
    match_id: str
    home_win_probability: float
    draw_probability: float
    away_win_probability: float
    over_25_probability: float
    under_25_probability: float
    predicted_home_goals: float
    predicted_away_goals: float
    
    # New Projected Stats
    predicted_home_corners: float = 0.0
    predicted_away_corners: float = 0.0
    predicted_home_yellow_cards: float = 0.0
    predicted_away_yellow_cards: float = 0.0
    predicted_home_red_cards: float = 0.0
    predicted_away_red_cards: float = 0.0
    
    # New Standard Probabilities
    over_95_corners_probability: float = 0.0
    under_95_corners_probability: float = 0.0
    over_45_cards_probability: float = 0.0
    under_45_cards_probability: float = 0.0
    # Dynamic Handicap
    handicap_line: float = 0.0
    handicap_home_probability: float = 0.0
    handicap_away_probability: float = 0.0
    
    # Value Bet Fields
    expected_value: float = 0.0
    is_value_bet: bool = False
    
    confidence: float = 0.0
    data_sources: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=get_current_time)
    data_updated_at: Optional[datetime] = None
    fundamental_analysis: Optional[dict] = field(default=None)
    suggested_picks: list["SuggestedPick"] = field(default_factory=list)
    highlights_url: Optional[str] = None
    real_time_odds: Optional[dict[str, float]] = None
    
    def __post_init__(self):
        """Validate probability values."""
        probs = [
            self.home_win_probability,
            self.draw_probability,
            self.away_win_probability,
        ]
        for prob in probs:
            if not 0 <= prob <= 1:
                raise ValueError(f"Probability must be between 0 and 1, got {prob}")
        
        # Probabilities should sum to approximately 1
        # Exception: Allow sum of 0 if all are 0 (indicates no prediction possible due to lack of data)
        total = sum(probs)
        if total == 0:
            return

        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Match outcome probabilities must sum to 1, got {total}")
    
    @property
    def recommended_bet(self) -> str:
        """Get the recommended bet based on highest probability."""
        probs = {
            "Home Win (1)": self.home_win_probability,
            "Draw (X)": self.draw_probability,
            "Away Win (2)": self.away_win_probability,
        }
        return max(probs, key=probs.get)
    
    @property
    def over_under_recommendation(self) -> str:
        """Get over/under 2.5 recommendation."""
        if self.over_25_probability > self.under_25_probability:
            return "Over 2.5"
        return "Under 2.5"


@dataclass
class TeamStatistics:
    """
    Historical statistics for a team.
    
    Attributes:
        team_id: ID of the team
        matches_played: Total matches played
        wins: Total wins
        draws: Total draws
        losses: Total losses
        goals_scored: Total goals scored
        goals_conceded: Total goals conceded
        home_wins: Wins at home
        away_wins: Wins away
        recent_form: Last 5 match results (W/D/L)
    """
    team_id: str
    matches_played: int
    wins: int
    draws: int
    losses: int
    goals_scored: int
    goals_conceded: int
    home_wins: int = 0
    away_wins: int = 0
    
    # Granular venue stats
    home_matches_played: int = 0
    home_goals_scored: int = 0
    home_goals_conceded: int = 0
    
    away_matches_played: int = 0
    away_goals_scored: int = 0
    away_goals_conceded: int = 0
    
    total_corners: int = 0
    total_yellow_cards: int = 0
    total_red_cards: int = 0
    matches_with_corners: int = 0
    matches_with_cards: int = 0
    recent_form: str = ""  # e.g., "WWDLW"
    data_updated_at: Optional[datetime] = None
    
    @property
    def win_rate(self) -> float:
        """Calculate win rate."""
        if self.matches_played == 0:
            return 0.0
        return self.wins / self.matches_played
    
    @property
    def goals_per_match(self) -> float:
        """Calculate average goals scored per match."""
        if self.matches_played == 0:
            return 0.0
        return self.goals_scored / self.matches_played
    
    @property
    def goals_conceded_per_match(self) -> float:
        """Calculate average goals conceded per match."""
        if self.matches_played == 0:
            return 0.0
        return self.goals_conceded / self.matches_played
    
    @property
    def home_goals_per_match(self) -> float:
        """Average goals scored when playing at home."""
        if self.home_matches_played == 0:
            return 0.0
        return self.home_goals_scored / self.home_matches_played

    @property
    def home_goals_conceded_per_match(self) -> float:
        """Average goals conceded when playing at home."""
        if self.home_matches_played == 0:
            return 0.0
        return self.home_goals_conceded / self.home_matches_played

    @property
    def away_goals_per_match(self) -> float:
        """Average goals scored when playing away."""
        if self.away_matches_played == 0:
            return 0.0
        return self.away_goals_scored / self.away_matches_played

    @property
    def away_goals_conceded_per_match(self) -> float:
        """Average goals conceded when playing away."""
        if self.away_matches_played == 0:
            return 0.0
        return self.away_goals_conceded / self.away_matches_played
    
    @property
    def goal_difference(self) -> int:
        """Calculate goal difference."""
        return self.goals_scored - self.goals_conceded
    
    @property
    def avg_corners_per_match(self) -> float:
        denom = self.matches_with_corners or self.matches_played
        if denom == 0: return 0.0
        return round(self.total_corners / denom, 2)
        
    @property
    def avg_yellow_cards_per_match(self) -> float:
        denom = self.matches_with_cards or self.matches_played
        if denom == 0: return 0.0
        return round(self.total_yellow_cards / denom, 2)
        
    @property
    def avg_red_cards_per_match(self) -> float:
        denom = self.matches_with_cards or self.matches_played
        if denom == 0: return 0.0
        return round(self.total_red_cards / denom, 2)


@dataclass
class MatchPrediction:
    """
    Combined entity containing both Match and Prediction data.
    Useful for services that need context from both.
    """
    match: Match
    prediction: Prediction


@dataclass
class TeamH2HStatistics:
    """
    Head-to-head statistics between two teams.
    
    Attributes:
        team_a_id: ID of team A
        team_b_id: ID of team B
        matches_played: Total matches played between them
        team_a_wins: Wins for team A
        draws: Draws
        team_b_wins: Wins for team B
        team_a_goals: Goals scored by team A
        team_b_goals: Goals scored by team B
        recent_matches: List of recent match results (dates/scores)
    """
    team_a_id: str
    team_b_id: str
    matches_played: int
    team_a_wins: int
    draws: int
    team_b_wins: int
    team_a_goals: int
    team_b_goals: int
    recent_matches: list[dict] = field(default_factory=list)
