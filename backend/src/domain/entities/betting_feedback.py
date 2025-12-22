"""
Betting Feedback Entity Module

Contains entities for tracking bet outcomes to enable continuous learning.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class BettingFeedback:
    """
    Represents feedback on a betting prediction outcome.
    
    Used for continuous learning to track which predictions
    were correct and adjust model weights accordingly.
    
    Attributes:
        bet_id: Unique identifier for this bet record
        match_id: ID of the match that was bet on
        market_type: Type of market (corners_over, cards_over, etc.)
        prediction: The prediction made (e.g., "over_6.5")
        actual_outcome: What actually happened (e.g., "over" or "under")
        was_correct: Whether the prediction was correct
        odds: Betting odds at time of prediction
        stake: Amount staked (optional)
        profit_loss: Net profit/loss (optional)
        timestamp: When the bet was placed
        settled_at: When the bet was settled (optional)
    """
    bet_id: str
    match_id: str
    market_type: str
    prediction: str
    actual_outcome: str
    was_correct: bool
    odds: float
    stake: Optional[float] = None
    profit_loss: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    settled_at: Optional[datetime] = None
    
    def calculate_profit_loss(self) -> Optional[float]:
        """Calculate profit/loss if stake is provided."""
        if self.stake is None:
            return None
        if self.was_correct:
            return self.stake * (self.odds - 1)
        return -self.stake


@dataclass
class MarketPerformance:
    """
    Aggregated performance metrics for a specific market type.
    
    Used to track historical success rates and adjust model confidence.
    
    Attributes:
        market_type: Type of market
        total_predictions: Total number of predictions made
        correct_predictions: Number of correct predictions
        success_rate: Percentage of correct predictions (0-1)
        avg_odds: Average odds for predictions
        total_profit_loss: Net profit/loss
        confidence_adjustment: Adjustment factor for future predictions
        last_updated: When metrics were last updated
    """
    market_type: str
    total_predictions: int = 0
    correct_predictions: int = 0
    success_rate: float = 0.0
    avg_odds: float = 1.0
    total_profit_loss: float = 0.0
    confidence_adjustment: float = 1.0  # Multiplier for confidence
    last_updated: datetime = field(default_factory=datetime.utcnow)
    
    def update_with_feedback(self, feedback: BettingFeedback) -> None:
        """Update metrics with new feedback."""
        self.total_predictions += 1
        if feedback.was_correct:
            self.correct_predictions += 1
        
        self.success_rate = self.correct_predictions / self.total_predictions
        
        # Update average odds
        self.avg_odds = (
            (self.avg_odds * (self.total_predictions - 1) + feedback.odds) 
            / self.total_predictions
        )
        
        # Update profit/loss if available
        pl = feedback.calculate_profit_loss()
        if pl is not None:
            self.total_profit_loss += pl
        
        # Adjust confidence based on recent performance
        self._recalculate_confidence_adjustment()
        self.last_updated = datetime.utcnow()
    
    def _recalculate_confidence_adjustment(self) -> None:
        """
        Recalculate confidence adjustment based on performance.
        
        - Success rate > 70%: Boost confidence (up to 1.2x)
        - Success rate 50-70%: Neutral
        - Success rate < 50%: Penalize confidence (down to 0.7x)
        """
        if self.total_predictions < 5:
            # Not enough data, keep neutral
            self.confidence_adjustment = 1.0
            return
        
        if self.success_rate > 0.70:
            # Boost confidence proportionally
            self.confidence_adjustment = 1.0 + (self.success_rate - 0.70) * 0.67
        elif self.success_rate < 0.50:
            # Penalize confidence proportionally
            self.confidence_adjustment = 0.7 + (self.success_rate * 0.6)
        else:
            # Neutral zone
            self.confidence_adjustment = 1.0
        
        # Clamp to reasonable range
        self.confidence_adjustment = max(0.5, min(1.3, self.confidence_adjustment))


@dataclass
class LearningWeights:
    """
    Container for all learning weights and market performances.
    
    Persisted to disk to maintain learning across restarts.
    """
    market_performances: dict[str, MarketPerformance] = field(default_factory=dict)
    global_adjustments: dict[str, float] = field(default_factory=dict)
    version: str = "1.0"
    last_saved: datetime = field(default_factory=datetime.utcnow)
    
    def get_market_adjustment(self, market_type: str) -> float:
        """Get confidence adjustment for a specific market type."""
        if market_type in self.market_performances:
            return self.market_performances[market_type].confidence_adjustment
        return 1.0
    
    def update_with_feedback(self, feedback: BettingFeedback) -> None:
        """Update learning weights with new feedback."""
        market_type = feedback.market_type
        
        if market_type not in self.market_performances:
            self.market_performances[market_type] = MarketPerformance(
                market_type=market_type
            )
        
        self.market_performances[market_type].update_with_feedback(feedback)
        self.last_saved = datetime.utcnow()
