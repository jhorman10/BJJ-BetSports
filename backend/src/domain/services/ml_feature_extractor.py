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
    def extract_features(
        pick: SuggestedPick,
        match: 'Match' = None, 
        home_stats: 'TeamStatistics' = None, 
        away_stats: 'TeamStatistics' = None
    ) -> List[float]:
        """
        Extract a standardized feature vector from a suggested pick + match context.
        """
        # 1. Market type hash for categorization
        market_type_str = pick.market_type.value if hasattr(pick.market_type, "value") else str(pick.market_type)
        mt_hash = zlib.adler32(market_type_str.encode('utf-8')) % 1000
        
        # 2. Basic Pick Features
        features = [
            float(pick.probability),
            float(pick.expected_value),
            float(pick.risk_level),
            float(mt_hash)
        ]
        
        # 3. Enhanced Match Stats (if available)
        if home_stats and away_stats:
            # Shot Dominance (Home vs Away)
            h_shots = getattr(home_stats, 'total_shots', 0) / max(1, home_stats.matches_played)
            a_shots = getattr(away_stats, 'total_shots', 0) / max(1, away_stats.matches_played)
            features.append(h_shots)
            features.append(a_shots)
            features.append(h_shots - a_shots) # Shot diff
            
            # Efficiency (Shots on Target)
            h_sot = getattr(home_stats, 'total_shots_on_target', 0) / max(1, home_stats.matches_played)
            a_sot = getattr(away_stats, 'total_shots_on_target', 0) / max(1, away_stats.matches_played)
            features.append(h_sot)
            features.append(a_sot)
            
            # Aggression (Fouls)
            h_fouls = getattr(home_stats, 'total_fouls', 0) / max(1, home_stats.matches_played)
            a_fouls = getattr(away_stats, 'total_fouls', 0) / max(1, away_stats.matches_played)
            features.append(h_fouls - a_fouls)
            
            # Form (Last 5 matches points estimate)
            h_form_pts = sum(3 if c == 'W' else 1 if c == 'D' else 0 for c in home_stats.recent_form[-5:]) if home_stats.recent_form else 0
            a_form_pts = sum(3 if c == 'W' else 1 if c == 'D' else 0 for c in away_stats.recent_form[-5:]) if away_stats.recent_form else 0
            features.append(float(h_form_pts))
            features.append(float(a_form_pts))
        else:
            # Padding if no stats provided (8 zeros)
            features.extend([0.0] * 8)
            
        return features
