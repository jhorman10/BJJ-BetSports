"""
Risk Manager Service

Responsible for enforcing portfolio-level constraints (Anti-Fragility).
Ensures we don't over-expose the bankroll on a single day or correlated events.
"""

from typing import List, Dict
import logging
from src.domain.entities.suggested_pick import SuggestedPick

logger = logging.getLogger(__name__)

class RiskManager:
    """
    Financial controller that filters picks to respect risk limits.
    """
    
    # Maximum total bankroll exposure per day (e.g., 5%)
    MAX_DAILY_EXPOSURE = 0.05 
    
    # Maximum exposure per league (diversification)
    MAX_LEAGUE_EXPOSURE = 0.03
    
    def apply_portfolio_constraints(
        self, 
        all_picks: List[Dict[str, any]] # List of {match_id, pick, league_id}
    ) -> List[Dict[str, any]]:
        """
        Takes a raw list of potential picks and filters/reduces stakes 
        to fit within the global risk budget.
        
        Input: List of dicts with 'pick': SuggestedPick, 'match': Match
        """
        # 1. Sort by EV (Expected Value) * Priority
        # We want to keep the BEST picks, not just the first ones
        sorted_candidates = sorted(
            all_picks, 
            key=lambda x: x['pick'].expected_value * x['pick'].priority_score, 
            reverse=True
        )
        
        approved_picks = []
        current_daily_exposure = 0.0
        league_exposure = {}
        
        for item in sorted_candidates:
            pick: SuggestedPick = item['pick']
            league_id = item['match'].league.id
            
            # Exposure of this specific bet
            stake_pct = pick.kelly_percentage
            
            # Check constraints
            if current_daily_exposure + stake_pct > self.MAX_DAILY_EXPOSURE:
                # Option A: Reject
                # Option B: Reduce stake to fit remaining budget
                # We choose Option B for the last fit, but reject if too small
                remaining = self.MAX_DAILY_EXPOSURE - current_daily_exposure
                if remaining < 0.005: # Less than 0.5% left? Stop.
                    pick.reasoning += " (Rechazado: Límite Diario de Riesgo alcanzado)."
                    continue
                
                # Cap stake
                stake_pct = remaining
                pick.kelly_percentage = round(stake_pct, 4)
                pick.suggested_stake = round(stake_pct * 100, 2)
                pick.reasoning += " (Stake Reducido: Límite Diario)."
            
            # Check League Limits
            current_league_exp = league_exposure.get(league_id, 0.0)
            if current_league_exp + stake_pct > self.MAX_LEAGUE_EXPOSURE:
                 pick.reasoning += " (Rechazado: Límite de Exposición por Liga)."
                 continue
                 
            # Approve
            approved_picks.append(item)
            current_daily_exposure += stake_pct
            league_exposure[league_id] = current_league_exp + stake_pct
            
            if current_daily_exposure >= self.MAX_DAILY_EXPOSURE:
                break
                
        return approved_picks
