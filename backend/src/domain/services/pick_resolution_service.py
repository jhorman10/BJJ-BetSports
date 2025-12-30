"""
Pick Resolution Service

Centralizes the logic for determining the result (WIN/LOSS/VOID) 
and payout of a suggested pick based on the actual match outcome.
"""

import logging
import re
from typing import Tuple

from src.domain.entities.entities import Match
from src.domain.entities.suggested_pick import SuggestedPick

logger = logging.getLogger(__name__)

class PickResolutionService:
    """
    Service for validating pick outcomes and calculating payouts.
    """

    def resolve_pick(self, pick: SuggestedPick, match: Match) -> Tuple[str, float]:
        """
        Determine if a pick won and calculate its payout.
        
        Returns:
            Tuple of (result_str, payout_amount)
            result_str can be "WIN", "LOSS", or "VOID"
        """
        # 1. If the pick already has a result assigned by an external source, trust it
        if hasattr(pick, 'result') and pick.result:
            payout = self._calculate_payout_for_result(pick.result, pick)
            return pick.result, payout

        # 2. Logic-based validation
        market_type_str = pick.market_type.value if hasattr(pick.market_type, "value") else str(pick.market_type)
        was_correct = False
        
        try:
            threshold = 0.0
            # Extract threshold from label if needed (e.g., "Over 2.5")
            if "Más de" in pick.market_label or "Menos de" in pick.market_label or "Over" in pick.market_label or "Under" in pick.market_label:
                found = re.findall(r"[-+]?\d*\.\d+|\d+", pick.market_label)
                if found: threshold = float(found[0])

            if market_type_str in ["winner", "draw", "result_1x2"]:
                actual = "X"
                if match.home_goals > match.away_goals: actual = "1"
                elif match.away_goals > match.home_goals: actual = "2"
                
                predicted = "X"
                if "(1)" in pick.market_label: predicted = "1"
                elif "(2)" in pick.market_label: predicted = "2"
                was_correct = (actual == predicted)
                
            elif "over" in market_type_str:
                total = 0
                if "corners" in market_type_str: total = (match.home_corners or 0) + (match.away_corners or 0)
                elif "cards" in market_type_str: total = (match.home_yellow_cards or 0) + (match.away_yellow_cards or 0)
                elif "goals" in market_type_str: total = (match.home_goals or 0) + (match.away_goals or 0)
                else: total = (match.home_goals or 0) + (match.away_goals or 0) # Default to goals
                was_correct = total > threshold
                
            elif "under" in market_type_str:
                total = 0
                if "corners" in market_type_str: total = (match.home_corners or 0) + (match.away_corners or 0)
                elif "cards" in market_type_str: total = (match.home_yellow_cards or 0) + (match.away_yellow_cards or 0)
                elif "goals" in market_type_str: total = (match.home_goals or 0) + (match.away_goals or 0)
                else: total = (match.home_goals or 0) + (match.away_goals or 0)
                was_correct = total < threshold
                
            elif "btts_yes" in market_type_str:
                was_correct = (match.home_goals > 0 and match.away_goals > 0)
            elif "btts_no" in market_type_str:
                was_correct = not (match.home_goals > 0 and match.away_goals > 0)
            
            result = "WIN" if was_correct else "LOSS"
            return result, self._calculate_payout_for_result(result, pick)

        except Exception as e:
            logger.warning(f"Error resolving pick {pick.market_label}: {e}")
            return "UNKNOWN", 0.0

    def _calculate_payout_for_result(self, result: str, pick: SuggestedPick) -> float:
        """Helper to calculate payout based on result string."""
        if result == "WIN":
            # Payout is the odds (e.g., 1.95 means $1 staked returns $1.95 total)
            # Find odds in the pick (usually pick.probability is used as a proxy for odds in some backtests,
            # but we should look for actual odds if available)
            # For backtesting, we often pass odds in a specific field or name
            return getattr(pick, 'odds', 1.0)
        elif result == "VOID":
            return 1.0 # Stake returned
        return 0.0 # Loss
