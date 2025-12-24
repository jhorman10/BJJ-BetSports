"""
Suggested Pick Entity Module

Contains entities for AI-suggested betting picks with probability-based
confidence levels and risk assessments.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum


class MarketType(str, Enum):
    """Types of betting markets supported."""
    CORNERS_OVER = "corners_over"
    CORNERS_UNDER = "corners_under"
    CARDS_OVER = "cards_over"
    CARDS_UNDER = "cards_under"
    RED_CARDS = "red_cards"
    VA_HANDICAP = "va_handicap"
    WINNER = "winner"
    GOALS_OVER = "goals_over"
    GOALS_UNDER = "goals_under"
    TEAM_GOALS_OVER = "team_goals_over"
    TEAM_GOALS_UNDER = "team_goals_under"
    RESULT_1X2 = "result_1x2"
    DOUBLE_CHANCE_1X = "double_chance_1x"
    DOUBLE_CHANCE_X2 = "double_chance_x2"
    DOUBLE_CHANCE_12 = "double_chance_12"
    BTTS_YES = "btts_yes"
    BTTS_NO = "btts_no"
    GOALS_OVER_0_5 = "goals_over_0_5"
    GOALS_OVER_1_5 = "goals_over_1_5"
    GOALS_OVER_2_5 = "goals_over_2_5"
    GOALS_OVER_3_5 = "goals_over_3_5"
    GOALS_UNDER_0_5 = "goals_under_0_5"
    GOALS_UNDER_1_5 = "goals_under_1_5"
    GOALS_UNDER_2_5 = "goals_under_2_5"
    GOALS_UNDER_3_5 = "goals_under_3_5"
    
    # Team Props
    HOME_CORNERS_OVER = "home_corners_over"
    HOME_CORNERS_UNDER = "home_corners_under"
    AWAY_CORNERS_OVER = "away_corners_over"
    AWAY_CORNERS_UNDER = "away_corners_under"
    
    HOME_CARDS_OVER = "home_cards_over"
    HOME_CARDS_UNDER = "home_cards_under"
    AWAY_CARDS_OVER = "away_cards_over"
    AWAY_CARDS_UNDER = "away_cards_under"


class ConfidenceLevel(str, Enum):
    """Confidence level for a suggested pick."""
    HIGH = "high"      # > 80% probability
    MEDIUM = "medium"  # 60-80% probability
    LOW = "low"        # <= 60% probability


@dataclass
class SuggestedPick:
    """
    Represents an AI-suggested betting pick for a match.
    
    Attributes:
        market_type: Type of betting market
        market_label: Human-readable label for the pick (e.g., "Más de 6.5 córners")
        probability: Calculated probability (0.0 - 1.0)
        confidence_level: HIGH/MEDIUM/LOW based on probability thresholds
        reasoning: Explanation for why this pick is suggested
        risk_level: Risk score from 1 (low risk) to 5 (high risk)
        is_recommended: Whether this pick is actively recommended
        priority_score: Score for sorting picks (higher = better)
    """
    market_type: MarketType
    market_label: str
    probability: float
    confidence_level: ConfidenceLevel
    reasoning: str
    risk_level: int  # 1-5 scale
    is_recommended: bool = True
    priority_score: float = 0.0
    expected_value: float = 0.0
    
    def __post_init__(self):
        """Validate probability and risk level."""
        if not 0 <= self.probability <= 1:
            raise ValueError(f"Probability must be 0-1, got {self.probability}")
        if not 1 <= self.risk_level <= 5:
            raise ValueError(f"Risk level must be 1-5, got {self.risk_level}")
    
    @staticmethod
    def get_confidence_level(probability: float) -> ConfidenceLevel:
        """Get confidence level from probability value."""
        if probability > 0.80:
            return ConfidenceLevel.HIGH
        elif probability > 0.60:
            return ConfidenceLevel.MEDIUM
        return ConfidenceLevel.LOW


@dataclass
class MatchSuggestedPicks:
    """
    Container for all suggested picks for a match.
    
    Attributes:
        match_id: ID of the match
        suggested_picks: List of suggested picks sorted by priority
        combination_warning: Warning message if too many picks are selected
        generated_at: Timestamp when picks were generated
    """
    match_id: str
    suggested_picks: list[SuggestedPick] = field(default_factory=list)
    combination_warning: Optional[str] = None
    generated_at: datetime = field(default_factory=datetime.utcnow)
    
    def add_pick(self, pick: SuggestedPick) -> None:
        """Add a pick and re-sort by priority."""
        self.suggested_picks.append(pick)
        self.suggested_picks.sort(key=lambda p: p.priority_score, reverse=True)
    
    def get_recommended_picks(self, max_picks: int = 3) -> list[SuggestedPick]:
        """Get top recommended picks (default max 3 to avoid combination risk)."""
        recommended = [p for p in self.suggested_picks if p.is_recommended]
        return recommended[:max_picks]
    
    def has_duplicate_markets(self) -> bool:
        """Check if there are duplicate market types that shouldn't be combined."""
        # Goals markets that shouldn't be combined
        goals_markets = [MarketType.GOALS_OVER, MarketType.GOALS_UNDER, 
                        MarketType.TEAM_GOALS_OVER, MarketType.TEAM_GOALS_UNDER]
        
        goals_picks = [p for p in self.suggested_picks 
                      if p.market_type in goals_markets and p.is_recommended]
        
        return len(goals_picks) > 1
    
    def has_market(self, market_type: MarketType) -> bool:
        """Check if a pick of a specific market type already exists."""
        return any(p.market_type == market_type for p in self.suggested_picks)
