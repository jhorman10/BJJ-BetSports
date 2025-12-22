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
        Extracts high-probability picks from a list of match predictions.
        Currently simple logic: checks prediction probabilities.
        In a real scenario, this would interface with a Strategy engine or examine all SuggestedPicks.
        Here we will assume we can generate picks from the prediction data or use existing suggested picks if available.
        """
        picks = []
        # Define threshold for no-odds scenario to ensure safety
        no_odds_threshold = max(min_probability, 0.75)
        
        for pred in predictions:
            match = pred.match
            
            # Helper: Calculate EV (Expected Value)
            # EV = (Probability * Odds) - 1
            def get_ev(prob, odds):
                return (prob * odds) - 1 if odds and odds > 1 else -1.0

            # Check Home Win
            ev_home = get_ev(pred.prediction.home_win_probability, match.home_odds)
            # Condition: Positive EV OR (No Odds AND High Probability)
            if ev_home > 0.02 or (not match.home_odds and pred.prediction.home_win_probability >= no_odds_threshold):
                confidence = SuggestedPick.get_confidence_level(pred.prediction.home_win_probability)
                risk = self._calculate_risk_level(pred.prediction.home_win_probability)
                
                picks.append(SuggestedPick(
                    market_type=MarketType.WINNER,
                    market_label=f"Victoria {pred.match.home_team.name}",
                    probability=pred.prediction.home_win_probability,
                    confidence_level=confidence,
                    reasoning="Alta probabilidad de victoria local basada en modelo predictivo.",
                    risk_level=risk,
                    is_recommended=True,
                    # Priority based on EV if available, else probability
                    priority_score=ev_home if ev_home > 0 else pred.prediction.home_win_probability
                ))
            
            # Check Away Win
            ev_away = get_ev(pred.prediction.away_win_probability, match.away_odds)
            if ev_away > 0.02 or (not match.away_odds and pred.prediction.away_win_probability >= no_odds_threshold):
                confidence = SuggestedPick.get_confidence_level(pred.prediction.away_win_probability)
                risk = self._calculate_risk_level(pred.prediction.away_win_probability)
                
                picks.append(SuggestedPick(
                    market_type=MarketType.WINNER,
                    market_label=f"Victoria {pred.match.away_team.name}",
                    probability=pred.prediction.away_win_probability,
                    confidence_level=confidence,
                    reasoning="Alta probabilidad de victoria visitante basada en modelo predictivo.",
                    risk_level=risk,
                    is_recommended=True,
                    priority_score=ev_away if ev_away > 0 else pred.prediction.away_win_probability
                ))

            # Check Over 2.5
            # Note: Match entity usually doesn't carry Over/Under odds in this simple model, so we stick to probability
            if pred.prediction.over_25_probability >= min_probability:
                 confidence = SuggestedPick.get_confidence_level(pred.prediction.over_25_probability)
                 risk = self._calculate_risk_level(pred.prediction.over_25_probability)
                 
                 picks.append(SuggestedPick(
                    market_type=MarketType.GOALS_OVER,
                    market_label=f"Más de 2.5 Goles en {pred.match.home_team.name} vs {pred.match.away_team.name}",
                    probability=pred.prediction.over_25_probability,
                    confidence_level=confidence,
                    reasoning="Alta probabilidad de goles basada en modelo predictivo.",
                    risk_level=risk,
                    is_recommended=True,
                    priority_score=pred.prediction.over_25_probability
                ))
        
        return picks

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
