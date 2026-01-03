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
        
        Feature groups:
        [0-3]: Basic pick features (probability, EV, risk, market hash)
        [4-12]: Shot/form features
        [13-20]: Advanced ESPN stats (possession, passes, tackles, interceptions)
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
            mp_h = max(1, home_stats.matches_played)
            mp_a = max(1, away_stats.matches_played)
            
            # Shot Dominance (Home vs Away)
            h_shots = getattr(home_stats, 'total_shots', 0) / mp_h
            a_shots = getattr(away_stats, 'total_shots', 0) / mp_a
            features.append(h_shots)
            features.append(a_shots)
            features.append(h_shots - a_shots) # Shot diff
            
            # Efficiency (Shots on Target)
            h_sot = getattr(home_stats, 'total_shots_on_target', 0) / mp_h
            a_sot = getattr(away_stats, 'total_shots_on_target', 0) / mp_a
            features.append(h_sot)
            features.append(a_sot)
            
            # Aggression (Fouls)
            h_fouls = getattr(home_stats, 'total_fouls', 0) / mp_h
            a_fouls = getattr(away_stats, 'total_fouls', 0) / mp_a
            features.append(h_fouls - a_fouls)
            
            # Form (Last 5 matches points estimate)
            h_form_pts = sum(3 if c == 'W' else 1 if c == 'D' else 0 for c in home_stats.recent_form[-5:]) if home_stats.recent_form else 0
            a_form_pts = sum(3 if c == 'W' else 1 if c == 'D' else 0 for c in away_stats.recent_form[-5:]) if away_stats.recent_form else 0
            features.append(float(h_form_pts))
            features.append(float(a_form_pts))
            
            # ============================================================
            # ADVANCED ESPN STATS FEATURES (New)
            # ============================================================
            
            # Possession (0-1 normalized from percentage)
            h_poss = getattr(home_stats, 'avg_possession', 0.5)
            a_poss = getattr(away_stats, 'avg_possession', 0.5)
            # Convert percentage strings like "55.5%" to float if needed
            if isinstance(h_poss, str): h_poss = float(h_poss.replace('%', '')) / 100
            if isinstance(a_poss, str): a_poss = float(a_poss.replace('%', '')) / 100
            features.append(float(h_poss))
            features.append(float(a_poss))
            
            # Pass Accuracy (0-1)
            h_pass_acc = getattr(home_stats, 'avg_pass_accuracy', 0.75)
            a_pass_acc = getattr(away_stats, 'avg_pass_accuracy', 0.75)
            if isinstance(h_pass_acc, str): h_pass_acc = float(h_pass_acc.replace('%', '')) / 100
            if isinstance(a_pass_acc, str): a_pass_acc = float(a_pass_acc.replace('%', '')) / 100
            features.append(float(h_pass_acc))
            features.append(float(a_pass_acc))
            
            # Tackles per game
            h_tackles = getattr(home_stats, 'total_tackles', 0) / mp_h
            a_tackles = getattr(away_stats, 'total_tackles', 0) / mp_a
            features.append(h_tackles)
            features.append(a_tackles)
            
            # Interceptions per game
            h_interceptions = getattr(home_stats, 'total_interceptions', 0) / mp_h
            a_interceptions = getattr(away_stats, 'total_interceptions', 0) / mp_a
            features.append(h_interceptions)
            features.append(a_interceptions)
            
        else:
            # Padding if no stats provided (16 zeros: 8 original + 8 new ESPN)
            features.extend([0.0] * 16)
            
        return features

