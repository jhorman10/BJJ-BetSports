"""
Bankroll Service Module

Handles stake sizing and bankroll management using methods like
Fractional Kelly Criterion to optimize long-term growth while minimizing ruin risk.
"""

import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

@dataclass
class SuggestedStake:
    """Represents a recommended stake."""
    units: float          # 1 unit = 1% of bankroll usually, or user defined
    percentage: float     # Percentage of total bankroll (e.g. 0.02 for 2%)
    amount: float         # Raw currency amount (optional/calculated later)
    risk_factor: float    # 0.0 to 1.0 (how aggressive this stake is)
    reasoning: str

class BankrollService:
    """
    Service for calculating optimal stake sizes.
    """
    
    # Conservative default for automated systems
    DEFAULT_KELLY_FRACTION = 0.25 
    
    # Safety limits
    MAX_STAKE_PERCENTAGE = 0.05  # Never bet more than 5% on a single outcome
    MIN_CONFIDENCE_THRESHOLD = 0.50 # Below this, stake is 0
    
    def __init__(self, kelly_fraction: float = DEFAULT_KELLY_FRACTION):
        self.kelly_fraction = kelly_fraction
        
    def calculate_stake(
        self, 
        probability: float, 
        odds: float, 
        confidence: float = 1.0, 
        bankroll_total: float = 1000.0
    ) -> SuggestedStake:
        """
        Calculate optimal stake using Fractional Kelly Criterion.
        
        Formula: f* = (bp - q) / b
        where:
          b = decimal odds - 1
          p = probability of winning
          q = probability of losing (1-p)
        """
        # 1. Validation
        if probability < self.MIN_CONFIDENCE_THRESHOLD:
             return SuggestedStake(0.0, 0.0, 0.0, 0.0, "Probabilidad debajo del umbral mínimo.")
             
        if odds <= 1.0:
            return SuggestedStake(0.0, 0.0, 0.0, 0.0, "Cuota inválida.")
            
        # 2. Kelly Calculation
        b = odds - 1
        q = 1.0 - probability
        f_star = (b * probability - q) / b
        
        if f_star <= 0:
            return SuggestedStake(0.0, 0.0, 0.0, 0.0, "EV Negativo según Kelly.")
            
        # 3. Apply Fraction (Safety Adjustment)
        # We also scale by internal 'confidence' score if provided (0.8, 0.9 etc)
        adjusted_stake_pct = f_star * self.kelly_fraction * confidence
        
        # 4. Apply Hard Limits
        final_percentage = min(adjusted_stake_pct, self.MAX_STAKE_PERCENTAGE)
        final_percentage = max(0.0, final_percentage) # No negative stakes
        
        # 5. Unit Conversion (Standard convention: 1 Unit = 1% of Bank)
        units = round(final_percentage * 100, 2)
        amount = round(bankroll_total * final_percentage, 2)
        
        reasoning = f"Kelly Full: {f_star:.1%}. Fracción ({self.kelly_fraction}): {adjusted_stake_pct:.1%}."
        
        if final_percentage == self.MAX_STAKE_PERCENTAGE:
            reasoning += " (Limitado por Max Stake)."
            
        return SuggestedStake(
            units=units,
            percentage=round(final_percentage, 4),
            amount=amount,
            risk_factor=round(f_star, 2),
            reasoning=reasoning
        )
