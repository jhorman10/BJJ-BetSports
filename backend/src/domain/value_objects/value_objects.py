"""
Domain Value Objects Module

Value objects are immutable objects that are defined by their attributes rather than identity.
They encapsulate validation logic and provide type safety.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Probability:
    """
    Represents a probability value (0.0 to 1.0).
    
    This value object ensures probability values are always valid.
    """
    value: float
    
    def __post_init__(self):
        if not 0.0 <= self.value <= 1.0:
            raise ValueError(f"Probability must be between 0 and 1, got {self.value}")
    
    def as_percentage(self) -> float:
        """Convert to percentage (0-100)."""
        return self.value * 100
    
    def __str__(self) -> str:
        return f"{self.as_percentage():.1f}%"


@dataclass(frozen=True)
class Odds:
    """
    Represents betting odds for a match.
    
    Stores decimal odds for home win, draw, and away win.
    """
    home: float
    draw: float
    away: float
    
    def __post_init__(self):
        if self.home < 1.0 or self.draw < 1.0 or self.away < 1.0:
            raise ValueError("Odds must be >= 1.0")
    
    def to_probabilities(self) -> tuple[float, float, float]:
        """
        Convert odds to implied probabilities.
        
        Returns:
            Tuple of (home_prob, draw_prob, away_prob) normalized to sum to 1.
        """
        # Implied probability = 1 / odds
        home_prob = 1 / self.home
        draw_prob = 1 / self.draw
        away_prob = 1 / self.away
        
        # Normalize to account for bookmaker margin
        total = home_prob + draw_prob + away_prob
        return (
            home_prob / total,
            draw_prob / total,
            away_prob / total,
        )
    
    @property
    def bookmaker_margin(self) -> float:
        """
        Calculate the bookmaker's margin (overround).
        
        A fair market would have a margin of 0%.
        Typically, margins are 2-10% for most bookmakers.
        """
        home_prob = 1 / self.home
        draw_prob = 1 / self.draw
        away_prob = 1 / self.away
        return (home_prob + draw_prob + away_prob - 1) * 100


@dataclass(frozen=True)
class Score:
    """
    Represents a match score.
    
    Immutable value object for home and away goals.
    """
    home: int
    away: int
    
    def __post_init__(self):
        if self.home < 0 or self.away < 0:
            raise ValueError("Goals cannot be negative")
    
    @property
    def total(self) -> int:
        """Total goals in the match."""
        return self.home + self.away
    
    @property
    def is_over_25(self) -> bool:
        """Check if total goals is over 2.5."""
        return self.total > 2
    
    @property
    def winner(self) -> Optional[str]:
        """
        Get the winner of the match.
        
        Returns:
            'home', 'away', or None for draw
        """
        if self.home > self.away:
            return "home"
        elif self.away > self.home:
            return "away"
        return None
    
    def __str__(self) -> str:
        return f"{self.home}-{self.away}"


@dataclass(frozen=True)
class TeamStrength:
    """
    Represents a team's attacking and defensive strength.
    
    Used for Poisson-based goal predictions.
    Values are relative to league average (1.0 = average).
    """
    attack_strength: float  # > 1 means stronger than average
    defense_strength: float  # < 1 means better defense than average
    
    def __post_init__(self):
        if self.attack_strength < 0 or self.defense_strength < 0:
            raise ValueError("Strength values cannot be negative")


@dataclass(frozen=True)
class PredictionConfidence:
    """
    Represents the confidence level of a prediction.
    
    Includes overall confidence and contributing factors.
    """
    overall: float  # 0.0 to 1.0
    data_quality: float  # Based on amount and recency of data
    model_certainty: float  # How certain the model is
    
    def __post_init__(self):
        for val in [self.overall, self.data_quality, self.model_certainty]:
            if not 0.0 <= val <= 1.0:
                raise ValueError("Confidence values must be between 0 and 1")
    
    @property
    def confidence_level(self) -> str:
        """
        Get human-readable confidence level.
        
        Returns:
            'High', 'Medium', or 'Low'
        """
        if self.overall >= 0.7:
            return "High"
        elif self.overall >= 0.4:
            return "Medium"
        return "Low"


@dataclass(frozen=True)
class LeagueAverages:
    """Average statistics for a league used in predictions."""
    avg_home_goals: float
    avg_away_goals: float
    avg_total_goals: float
