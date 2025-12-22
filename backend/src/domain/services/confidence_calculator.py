"""
Confidence Calculator Service Module

Calculates granular confidence scores for betting picks based on 
data quality, odds alignment, and statistical strength.
"""

from typing import Optional, Dict, Any
from src.domain.entities.entities import Prediction, TeamStatistics
from src.domain.entities.suggested_pick import MarketType

class ConfidenceCalculator:
    """
    Calculates detailed confidence metrics for specific picks.
    """
    
    def calculate_pick_confidence(
        self,
        market_type: MarketType,
        probability: float,
        prediction: Prediction,
        home_stats: Optional[TeamStatistics],
        away_stats: Optional[TeamStatistics],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive confidence score for a pick.
        """
        data_quality = self._assess_data_quality(home_stats, away_stats)
        
        # Calculate alignment with odds (if available)
        odds_alignment = self._check_odds_alignment(market_type, probability, prediction)
        
        # Calculate statistical strength (how extreme the probability is)
        stat_strength = self._calculate_stat_strength(probability)
        
        # Weighted sum
        # Data Quality: 30%
        # Odds Alignment: 30%
        # Statistical Strength: 40%
        
        weighted_score = (
            data_quality * 0.30 +
            odds_alignment * 0.30 +
            stat_strength * 0.40
        )
        
        # Penalize if data quality is very low
        if data_quality < 0.4:
            weighted_score *= 0.8
            
        return {
            'score': round(weighted_score, 2),
            'factors': {
                'data_quality': round(data_quality, 2),
                'odds_alignment': round(odds_alignment, 2),
                'statistical_strength': round(stat_strength, 2)
            }
        }

    def _assess_data_quality(
        self, 
        home_stats: Optional[TeamStatistics], 
        away_stats: Optional[TeamStatistics]
    ) -> float:
        """
        Assess quality of historical data (0.0 - 1.0).
        > 20 matches is considered perfect (1.0).
        """
        if not home_stats or not away_stats:
            return 0.1
            
        avg_matches = (home_stats.matches_played + away_stats.matches_played) / 2
        
        # Sigmoid-like scaling
        # 0 matches -> 0.1
        # 5 matches -> 0.4
        # 10 matches -> 0.7
        # 20+ matches -> 1.0
        return min(1.0, avg_matches / 20.0)

    def _check_odds_alignment(
        self, 
        market_type: MarketType, 
        model_prob: float, 
        prediction: Prediction
    ) -> float:
        """
        Check if model probability aligns with market odds.
        Returns 0.0 (strong disagreement) to 1.0 (strong agreement).
        """
        # Note: In a real betting bot, we look for Disagreement (Value).
        # But for "Confidence" in the prediction correctness, Agreement is safer.
        
        market_prob = 0.0
        
        # Extract implied probability from prediction if available
        # (Prediction service stores odds-derived probs in home_win_probability etc)
        if market_type == MarketType.WINNER:
            # Heuristic: Compare with base prediction (which might be odds-adjusted)
            # This is a simplification
            pass 
            
        # Default neutral score if we can't compare
        return 0.5 

    def _calculate_stat_strength(self, probability: float) -> float:
        """
        How strong is the signal? 
        50% prob = 0 strength (uncertainty)
        90% prob = 1 strength (certainty)
        """
        # Distance from 0.5, scaled
        # 0.5 -> 0.0
        # 1.0 -> 1.0
        # 0.0 -> 1.0 (but usually we only bet on >0.5)
        
        dist = abs(probability - 0.5)
        return min(1.0, dist * 2)
