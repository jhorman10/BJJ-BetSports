"""
Centralized constants for the BJJ-BetSports backend.
"""

from src.domain.constants import ORDERED_INTERNATIONAL_TOURNAMENTS

# Default leagues used for training and predictions (§15.B compliant)
DEFAULT_LEAGUES = [
    # Top Tier
    "E0",
    "SP1",
    "D1",
    "I1",
    "F1",
    "N1",
    "B1",
    "P1",
    # Second/Third Tier
    "E1",
    "E2",
    "E3",
    "E_FA",
    "SP2",
    "SP_C",
    "D2",
    "I2",
    "F2",
    "N2",
    "B2",
    "P2",
    # International & South America
    *ORDERED_INTERNATIONAL_TOURNAMENTS,
    "COL1",
    "ARG1",
    "BRA1",
]

# ML Model Configuration
ML_MODEL_FILENAME = "ml_picks_classifier.joblib"

# Training Configuration (Auditoría v4)
DAYS_BACK_DEFAULT = 550  # Safe for GitHub Actions (2 vCPU, 7GB RAM)
DAYS_BACK_FULL = 3650  # 10 years - requires dedicated server or local

# Probability Thresholds (§3 No Hardcoding)
PROBABILITY_THRESHOLDS = {
    "high": 0.65,
    "medium": 0.50,
    "low": 0.35,
    "draw_adjusted": 0.35,
    "volatile_base": 0.50,
    "standard_base": 0.45,
}

# ML Confidence Thresholds
ML_CONFIDENCE_THRESHOLDS = {
    "top_pick": 0.80,
    "favorable": 0.65,
    "skeptical": 0.50,
}

# Recommendation Threshold
RECOMMENDATION_THRESHOLD = 0.65

# Color Codes for Frontend (Fuente Única de Verdad)
COLOR_CODES = {
    "high": "#10b981",  # Green (≥65%)
    "medium": "#f59e0b",  # Amber (35-64%)
    "low": "#ef4444",  # Red (<35%)
}

# Market Priority Weights - Externalized from picks_service.py (Auditoría v4)
# Higher value = more prioritized in recommendations
MARKET_PRIORITY = {
    "corners_over": 1.3,
    "corners_under": 1.2,
    "cards_over": 1.25,
    "cards_under": 1.15,
    "va_handicap": 1.2,
    "goals_over": 0.8,
    "goals_under": 0.9,
    "team_goals_over": 0.7,
    "team_goals_under": 0.85,
    "result_1x2": 1.0,
    "btts_yes": 0.9,
    "btts_no": 0.85,
    "double_chance_1x": 1.1,
    "double_chance_x2": 1.1,
    "double_chance_12": 1.05,
    "goals_over_0_5": 0.95,
    "goals_over_1_5": 0.9,
    "goals_over_2_5": 0.85,
    "goals_over_3_5": 0.8,
    "goals_under_0_5": 0.95,
    "goals_under_1_5": 0.8,
    "goals_under_2_5": 0.85,
    "goals_under_3_5": 0.9,
    "home_corners_over": 1.15,
    "home_corners_under": 1.1,
    "away_corners_over": 1.15,
    "away_corners_under": 1.1,
    "home_cards_over": 1.15,
    "home_cards_under": 1.1,
    "away_cards_over": 1.15,
    "away_cards_under": 1.1,
}
