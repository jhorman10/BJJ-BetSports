from typing import List, Optional
from itertools import combinations
import random
from dataclasses import dataclass

from src.domain.entities.parley import Parley
from src.domain.entities.suggested_pick import SuggestedPick, MarketType, ConfidenceLevel
from src.domain.entities.entities import MatchPrediction

@dataclass
class ParleyConfig:
    min_probability: float = 0.50  # Lowered to allow Value Bets (e.g. Odds 2.10 with 55% prob)
    min_picks: int = 3
    max_picks: int = 5
    count: int = 3

class ParleyService:
    """
    Domain service for generating parleys/accumulators from predictions.
    """

    def generate_parleys(
        self, 
        predictions: List[MatchPrediction], 
        config: ParleyConfig
    ) -> List[Parley]:
        """
        Generates a list of suggested parleys based on predictions and configuration.
        """
        # 1. Filter eligible picks from predictions
        eligible_picks = self._filter_eligible_picks(predictions, config.min_probability)
        
        if len(eligible_picks) < config.min_picks:
            return []

        # 2. Generate combinations
        parleys = self._combine_picks(eligible_picks, config)
        
        # 3. Sort/Rank parleys (e.g. by total probability or odds)
        # We want to maximize return (odds) while respecting the min probability threshold (which is already done in filtering).
        # Let's sort by total odds descending (higher return).
        parleys.sort(key=lambda p: p.total_odds, reverse=True)

        return parleys[:config.count]

    def _filter_eligible_picks(
        self, 
        predictions: List[MatchPrediction], 
        min_probability: float
    ) -> List[SuggestedPick]:
        """
        Extracts valid picks. Now strictly uses pre-calculated AI picks 
        marked as 'ML Confianza Alta'.
        """
        eligible_picks = []
        
        for pred in predictions:
            if not pred.prediction.suggested_picks:
                continue
                
            # Filter for Top ML picks
            # User Requirement: "Select Top ML, highest probability and ML confidence"
            # Logic: Look for "ML Confianza Alta" tag in reasoning.
            
            # 1. Try to find Top ML picks (Priority)
            top_ml_picks = [
                p for p in pred.prediction.suggested_picks 
                if (
                    "ML Confianza Alta" in (p.reasoning or "") and
                    p.probability >= min_probability
                )
            ]
            
            if top_ml_picks:
                # Best Scenario: We have an ML validated pick
                top_ml_picks.sort(key=lambda x: x.priority_score, reverse=True)
                eligible_picks.append(top_ml_picks[0])
            else:
                # 2. Fallback: Select highest probability pick (Safety net)
                # User Requirement: "If no top ML picks, select the pick with highest probability"
                other_picks = [
                    p for p in pred.prediction.suggested_picks 
                    if p.probability >= min_probability
                ]
                
                if other_picks:
                    other_picks.sort(key=lambda x: x.probability, reverse=True)
                    eligible_picks.append(other_picks[0])
        
        return eligible_picks

    def _calculate_risk_level(self, probability: float) -> int:
        """Calculate risk level (1-5) from probability."""
        if probability > 0.80:
            return 1
        elif probability > 0.70:
            return 2
        elif probability > 0.60:
            return 3
        elif probability > 0.50:
            return 4
        return 5

    def _combine_picks(
        self, 
        picks: List[SuggestedPick], 
        config: ParleyConfig
    ) -> List[Parley]:
        """
        Generates combinations of picks.
        Uses a heuristic aproach to avoid factorial explosion if there are many picks.
        """
        generated_parleys = []
        
        # Heuristic: Shuffle picks to get random variety if we have too many
        pool = picks[:]
        random.shuffle(pool)
        
        # Limit pool size for combinations to avoid performance issues
        # C(20, 5) is 15504, manageable. C(50, 5) is 2M, too big.
        # Let's limit the pool to top 20 by priority/prob
        pool.sort(key=lambda p: p.priority_score, reverse=True)
        pool = pool[:25] 

        # Try to generate combinations of sizes min_picks to max_picks
        for r in range(config.min_picks, config.max_picks + 1):
            # Generate a subset of combinations
            # To ensure we get *some* results if the pool is small, we just try all.
            # If the pool is large, we might want to sample, but keeping pool small (25) handles this.
            
            combs = list(combinations(pool, r))
            random.shuffle(combs) # Shuffle to give variety
            
            for combo in combs[:10]: # Take a few from each size
                # Validate combo: e.g. not having conflicting bets for same match (simplified here as we don't have match_id on SuggestedPick easily accessible without refactor, 
                # strictly speaking SuggestedPick should link back to Match. Assuming diverse enough pool for now).
                
                # Note: In a robust system we MUST Ensure unique matches in a parley. 
                # Current SuggestedPick entity doesn't strictly enforce match_id reference.
                # Use caution. We will skip this check for the MVP as per current entities 
                # or rely on market labels distinctness.
                
                generated_parleys.append(Parley(picks=list(combo)))
                
        return generated_parleys
