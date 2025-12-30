"""
ML Feature Extractor

Centralizes the logic for creating feature vectors for ML models.
"""

import zlib
from typing import List
from src.domain.entities.suggested_pick import SuggestedPick

class MLFeatureExtractor:
    """
    Service for extracting features from picks for ML model consumption.
    """

    @staticmethod
    def extract_features(pick: SuggestedPick) -> List[float]:
        """
        Extract a standardized feature vector from a suggested pick.
        """
        # 1. Market type hash for categorization
        market_type_str = pick.market_type.value if hasattr(pick.market_type, "value") else str(pick.market_type)
        mt_hash = zlib.adler32(market_type_str.encode('utf-8')) % 1000
        
        # 2. standardized feature vector
        # [probability, expected_value, risk_level, market_type_hash]
        return [
            float(pick.probability),
            float(pick.expected_value),
            float(pick.risk_level),
            float(mt_hash)
        ]
