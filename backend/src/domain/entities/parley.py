from dataclasses import dataclass, field
from typing import List
from uuid import uuid4
from .suggested_pick import SuggestedPick

@dataclass
class Parley:
    """
    Represents a combination of bets (parley/accumulator).
    """
    picks: List[SuggestedPick]
    parley_id: str = field(default_factory=lambda: str(uuid4()))
    total_odds: float = 0.0
    total_probability: float = 0.0

    def __post_init__(self):
        self._calculate_totals()

    def _calculate_totals(self):
        """Calculate total odds and probability based on picks."""
        if not self.picks:
            return

        # Simple accumulator logic: multiply probabilities
        # For odds, we assume fair odds = 1/probability if not provided,
        # but in a real scenario we'd use actual bookmaker odds.
        # Since SuggestedPick has probability but not explicit 'odds' field yet (as per current schema),
        # we will estimate fair decimal odds as 1 / probability.
        
        prob = 1.0
        odds = 1.0

        for pick in self.picks:
            prob *= pick.probability
            # Avoid division by zero
            pick_odds = 1 / pick.probability if pick.probability > 0 else 1.0
            odds *= pick_odds

        self.total_probability = prob
        self.total_odds = round(odds, 2)
