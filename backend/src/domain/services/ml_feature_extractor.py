"""
ML Feature Extractor

Centralizes the logic for creating feature vectors for ML models.
"""

import statistics
import zlib
from typing import TYPE_CHECKING, List, Optional, Sequence

from src.domain.entities.suggested_pick import SuggestedPick

if TYPE_CHECKING:
    from src.domain.entities.entities import Match, TeamStatistics


class MLFeatureExtractor:
    """
    Service for extracting features from picks for ML model consumption.
    """

    FEATURE_VECTOR_LENGTH = 45

    @staticmethod
    def _calculate_variance_features(
        recent_list: Sequence[float], season_avg: float
    ) -> list[float]:
        if not recent_list or len(recent_list) < 2:
            return [0.0, 0.0, 0.0]  # Trend, Volatility, Momentum

        # 1. Trend (Recent Avg vs Season Avg)
        recent_avg = sum(recent_list) / len(recent_list)
        trend = recent_avg - season_avg

        # 2. Volatility (Standard Deviation)
        try:
            volatility = statistics.stdev(recent_list)
        except Exception:
            volatility = 0.0

        # 3. Momentum (Weighted Average)
        # Weights: [0.1, 0.15, 0.2, 0.25, 0.3] (Most recent gets most weight)
        weights = [0.1, 0.15, 0.2, 0.25, 0.3]
        # Adjust weights if list is shorter than 5
        if len(recent_list) < 5:
            weights = [1.0 / len(recent_list)] * len(recent_list)
        else:
            weights = weights[-len(recent_list) :]

        momentum = sum(v * w for v, w in zip(recent_list, weights))

        return [
            round(float(trend), 3),
            round(float(volatility), 3),
            round(float(momentum), 3),
        ]

    @staticmethod
    def _get_win_rate(stats_dict: Optional[dict]) -> float:
        if not stats_dict:
            return 0.0
        mp = stats_dict.get("matches_played", 0)
        if mp == 0:
            return 0.0
        return float(stats_dict.get("wins", 0) / mp)

    @classmethod
    def _validate_feature_vector_length(cls, features: Sequence[float]) -> None:
        if len(features) != cls.FEATURE_VECTOR_LENGTH:
            raise ValueError(
                "Invalid ML feature vector length: "
                f"expected {cls.FEATURE_VECTOR_LENGTH}, got {len(features)}"
            )

    @staticmethod
    def extract_features(
        pick: SuggestedPick,
        match: Optional["Match"] = None,
        home_stats: Optional["TeamStatistics"] = None,
        away_stats: Optional["TeamStatistics"] = None,
    ) -> List[float]:
        """
        Extract a standardized feature vector from a suggested pick + match context.

        Feature groups:
        [0-3]: Basic pick features (probability, EV, risk, market hash)
        [4-12]: Shot/form features
        [13-20]: Advanced ESPN stats (possession, passes, tackles, interceptions)
        [21-26]: Corners and cards (home, away, total for each)
        """
        # 1. Market type hash for categorization
        market_type_str = (
            pick.market_type.value
            if hasattr(pick.market_type, "value")
            else str(pick.market_type)
        )
        mt_hash = zlib.adler32(market_type_str.encode("utf-8")) % 1000

        # 2. Basic Pick Features
        features = [
            float(pick.probability),
            float(pick.expected_value),
            float(pick.risk_level),
            float(mt_hash),
        ]

        # 3. Enhanced Match Stats (if available)
        if home_stats and away_stats:
            mp_h = max(1, home_stats.matches_played)
            mp_a = max(1, away_stats.matches_played)

            # Shot Dominance (Home vs Away)
            h_shots = float(getattr(home_stats, "total_shots", 0)) / mp_h
            a_shots = float(getattr(away_stats, "total_shots", 0)) / mp_a
            features.append(h_shots)
            features.append(a_shots)
            features.append(h_shots - a_shots)  # Shot diff

            # Efficiency (Shots on Target)
            h_sot = float(getattr(home_stats, "total_shots_on_target", 0)) / mp_h
            a_sot = float(getattr(away_stats, "total_shots_on_target", 0)) / mp_a
            features.append(h_sot)
            features.append(a_sot)

            # Aggression (Fouls)
            h_fouls = float(getattr(home_stats, "total_fouls", 0)) / mp_h
            a_fouls = float(getattr(away_stats, "total_fouls", 0)) / mp_a
            features.append(h_fouls - a_fouls)

            # Form (Last 5 matches points estimate)
            h_form_pts = (
                sum(
                    3 if c == "W" else 1 if c == "D" else 0
                    for c in home_stats.recent_form[-5:]
                )
                if home_stats.recent_form
                else 0
            )
            a_form_pts = (
                sum(
                    3 if c == "W" else 1 if c == "D" else 0
                    for c in away_stats.recent_form[-5:]
                )
                if away_stats.recent_form
                else 0
            )
            features.append(float(h_form_pts))
            features.append(float(a_form_pts))

            # ============================================================
            # ADVANCED ESPN STATS FEATURES (New)
            # ============================================================

            # Possession (0-1 normalized from percentage)
            h_poss = getattr(home_stats, "avg_possession", 0.5)
            a_poss = getattr(away_stats, "avg_possession", 0.5)
            # Convert percentage strings like "55.5%" to float if needed
            if isinstance(h_poss, str):
                h_poss = float(h_poss.replace("%", "")) / 100
            if isinstance(a_poss, str):
                a_poss = float(a_poss.replace("%", "")) / 100
            features.append(float(h_poss))
            features.append(float(a_poss))

            # Pass Accuracy (0-1)
            h_pass_acc = getattr(home_stats, "avg_pass_accuracy", 0.75)
            a_pass_acc = getattr(away_stats, "avg_pass_accuracy", 0.75)
            if isinstance(h_pass_acc, str):
                h_pass_acc = float(h_pass_acc.replace("%", "")) / 100
            if isinstance(a_pass_acc, str):
                a_pass_acc = float(a_pass_acc.replace("%", "")) / 100
            features.append(float(h_pass_acc))
            features.append(float(a_pass_acc))

            # Tackles per game
            h_tackles = float(getattr(home_stats, "total_tackles", 0)) / mp_h
            a_tackles = float(getattr(away_stats, "total_tackles", 0)) / mp_a
            features.append(h_tackles)
            features.append(a_tackles)

            # Interceptions per game
            h_interceptions = (
                float(getattr(home_stats, "total_interceptions", 0)) / mp_h
            )
            a_interceptions = (
                float(getattr(away_stats, "total_interceptions", 0)) / mp_a
            )
            features.append(h_interceptions)
            features.append(a_interceptions)

            # ============================================================
            # CORNERS AND CARDS FEATURES
            # ============================================================

            # Corners per game (uses matches_with_corners for accurate average)
            mc_h = getattr(home_stats, "matches_with_corners", 0) or mp_h
            mc_a = getattr(away_stats, "matches_with_corners", 0) or mp_a
            h_corners = float(getattr(home_stats, "total_corners", 0)) / max(1, mc_h)
            a_corners = float(getattr(away_stats, "total_corners", 0)) / max(1, mc_a)
            features.append(h_corners)
            features.append(a_corners)
            features.append(h_corners + a_corners)  # Total expected corners

            # Yellow cards per game
            mcy_h = getattr(home_stats, "matches_with_cards", 0) or mp_h
            mcy_a = getattr(away_stats, "matches_with_cards", 0) or mp_a
            h_yellows = float(getattr(home_stats, "total_yellow_cards", 0)) / max(
                1, mcy_h
            )
            a_yellows = float(getattr(away_stats, "total_yellow_cards", 0)) / max(
                1, mcy_a
            )
            features.append(h_yellows)
            features.append(a_yellows)
            features.append(h_yellows + a_yellows)  # Total expected cards

            # ============================================================
            # VARIANCE & FORM FEATURES (New for Mode Collapse Fix)
            # ============================================================

            # Extract Corner Variance
            h_corn_var = MLFeatureExtractor._calculate_variance_features(
                home_stats.recent_corners, h_corners
            )
            a_corn_var = MLFeatureExtractor._calculate_variance_features(
                away_stats.recent_corners, a_corners
            )
            features.extend(h_corn_var)  # [Trend, Vol, Mom]
            features.extend(a_corn_var)

            # Extract Card Variance
            h_card_var = MLFeatureExtractor._calculate_variance_features(
                home_stats.recent_yellow_cards, h_yellows
            )
            a_card_var = MLFeatureExtractor._calculate_variance_features(
                away_stats.recent_yellow_cards, a_yellows
            )
            features.extend(h_card_var)
            features.extend(a_card_var)

            # ============================================================
            # EFFICIENCY & INTERACTION FEATURES (New Intelligence Layer)
            # ============================================================

            # 1. Goal Conversion (Clinicality): Goals / Total Shots
            h_shots_total = getattr(home_stats, "total_shots", 0)
            a_shots_total = getattr(away_stats, "total_shots", 0)
            h_conversion = (
                home_stats.goals_scored / h_shots_total if h_shots_total > 0 else 0.0
            )
            a_conversion = (
                away_stats.goals_scored / a_shots_total if a_shots_total > 0 else 0.0
            )
            features.append(float(h_conversion))
            features.append(float(a_conversion))

            # 2. Interaction (Simple xG Proxy): Attack Strength * Defense Weakness
            features.append(
                float(
                    (home_stats.goals_scored / mp_h)
                    * (away_stats.goals_conceded / mp_a)
                )
            )
            features.append(
                float(
                    (away_stats.goals_scored / mp_a)
                    * (home_stats.goals_conceded / mp_h)
                )
            )

            # ============================================================
            # REFEREE FEATURES (New)
            # ============================================================
            # Placeholder: In the future, fetch actual referee stats from
            # StatisticsService
            # For now, default to 4.5 (Average strictness)
            ref_strictness = 4.5
            features.append(ref_strictness)

            # ============================================================
            # DOMESTIC VS INTERNATIONAL PERFORMANCE (Global Expansion)
            # ============================================================

            # Calculate win rates contextually
            h_dom_wr = MLFeatureExtractor._get_win_rate(
                getattr(home_stats, "domestic_stats", None)
            )
            h_intl_wr = MLFeatureExtractor._get_win_rate(
                getattr(home_stats, "international_stats", None)
            )
            a_dom_wr = MLFeatureExtractor._get_win_rate(
                getattr(away_stats, "domestic_stats", None)
            )
            a_intl_wr = MLFeatureExtractor._get_win_rate(
                getattr(away_stats, "international_stats", None)
            )

            # Feature: difference between intl performance and domestic performance
            # Positive means they perform better in international matches
            features.append(float(h_intl_wr - h_dom_wr))
            features.append(float(a_intl_wr - a_dom_wr))

        else:
            padding_length = MLFeatureExtractor.FEATURE_VECTOR_LENGTH - len(features)
            if padding_length < 0:
                raise ValueError("ML feature vector overflow while padding")
            features.extend([0.0] * padding_length)

        MLFeatureExtractor._validate_feature_vector_length(features)

        return features
