from collections import defaultdict
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from src.domain.entities.tennis_match import TennisMatch


class TennisFeatureExtractor:
    """
    Extracts features from TennisMatch objects for prediction.
    Uses historical data to compute rolling stats, H2H records, and betting odds.
    """

    SURFACES: List[str] = ["Hard", "Clay", "Grass", "Carpet"]
    LEVELS: List[str] = [
        "G",
        "A",
        "M",
        "D",
        "F",
    ]  # Grand Slam, ATP, Masters, Davis Cup, Finals

    def __init__(self, historical_data: Optional[pd.DataFrame] = None):
        """
        Initialize with historical data for computing rolling stats.

        Args:
            historical_data: DataFrame containing past match results.
        """
        self.historical_data = historical_data
        self.player_stats: Dict[str, Dict[str, float]] = (
            {}
        )  # Cache for player rolling stats
        self.h2h_stats: Dict[Tuple[str, str], Dict[str, int]] = (
            {}
        )  # Cache for H2H stats
        self.player_history: Dict[str, List[Dict[str, Any]]] = defaultdict(
            list
        )  # Per-player chronological match list

        if historical_data is not None:
            self._precompute_stats()

    def _precompute_stats(self) -> None:
        """Precompute rolling stats and H2H from historical data."""
        if self.historical_data is None:
            return

        # Sort by date
        self.historical_data = self.historical_data.sort_values("tourney_date")

        # Compute H2H
        self._compute_h2h()

        # Compute rolling player history (chronological)
        self._compute_rolling_history()

    def _compute_rolling_history(self) -> None:
        """
        Build per-player chronological history from match data.
        Each player gets a list of their match results in chronological order.
        """
        assert self.historical_data is not None
        for _, row in self.historical_data.iterrows():
            winner = row.get("winner_name", "")
            loser = row.get("loser_name", "")
            surface = row.get("surface", "Hard")

            if not winner or not loser:
                continue

            # Parse match date for temporal filtering
            try:
                match_date = pd.to_datetime(row.get("tourney_date")).date()
            except Exception:
                match_date = None

            # Winner record
            w_ace = self._safe_int(row.get("w_ace"))
            w_df = self._safe_int(row.get("w_df"))
            w_svpt = self._safe_int(row.get("w_svpt"))
            w_1stIn = self._safe_int(row.get("w_1stIn"))
            w_bpSaved = self._safe_int(row.get("w_bpSaved"))
            w_bpFaced = self._safe_int(row.get("w_bpFaced"))

            first_serve_pct = (w_1stIn / w_svpt) if w_svpt > 0 else 0.0
            bp_converted = (
                ((w_bpFaced - w_bpSaved) / w_bpFaced) if w_bpFaced > 0 else 0.0
            )

            self.player_history[winner].append(
                {
                    "won": 1,
                    "aces": w_ace,
                    "dfs": w_df,
                    "first_serve_pct": first_serve_pct,
                    "bp_converted": bp_converted,
                    "surface": surface,
                    "date": match_date,
                }
            )

            # Loser record
            l_ace = self._safe_int(row.get("l_ace"))
            l_df = self._safe_int(row.get("l_df"))
            l_svpt = self._safe_int(row.get("l_svpt"))
            l_1stIn = self._safe_int(row.get("l_1stIn"))
            l_bpSaved = self._safe_int(row.get("l_bpSaved"))
            l_bpFaced = self._safe_int(row.get("l_bpFaced"))

            first_serve_pct_l = (l_1stIn / l_svpt) if l_svpt > 0 else 0.0
            bp_converted_l = (
                ((l_bpFaced - l_bpSaved) / l_bpFaced) if l_bpFaced > 0 else 0.0
            )

            self.player_history[loser].append(
                {
                    "won": 0,
                    "aces": l_ace,
                    "dfs": l_df,
                    "first_serve_pct": first_serve_pct_l,
                    "bp_converted": bp_converted_l,
                    "surface": surface,
                    "date": match_date,
                }
            )

    def _compute_h2h(self) -> None:
        """Compute Head-to-Head records."""
        if self.historical_data is None:
            return

        for _, row in self.historical_data.iterrows():
            winner = row["winner_name"]
            loser = row["loser_name"]

            # Normalize key (alphabetical order)
            key = tuple(sorted([winner, loser]))

            if key not in self.h2h_stats:
                self.h2h_stats[key] = {"p1_wins": 0, "p2_wins": 0, "total": 0}

            self.h2h_stats[key]["total"] += 1
            if winner == key[0]:
                self.h2h_stats[key]["p1_wins"] += 1
            else:
                self.h2h_stats[key]["p2_wins"] += 1

    @staticmethod
    def _safe_int(val: Any) -> int:
        """Safely convert a value to int, returning 0 on failure."""
        try:
            if pd.isna(val):
                return 0
            return int(float(val))
        except (ValueError, TypeError):
            return 0

    def _get_recent_matches(
        self, player_name: str, window: int = 10, before_date: Optional[date] = None
    ) -> List[dict]:
        """
        Get the last `window` matches for a player, optionally filtered by date.
        """
        history = self.player_history.get(player_name, [])

        if before_date is not None:
            # Filter to matches strictly before the reference date
            filtered = [
                m for m in history if m["date"] is not None and m["date"] < before_date
            ]
        else:
            filtered = history

        return filtered[-window:] if len(filtered) > 0 else []

    def _get_rolling_stats(
        self, player_name: str, window: int = 10, before_date: Optional[date] = None
    ) -> Dict[str, float]:
        """Get rolling stats for a player over their last `window` matches."""
        recent = self._get_recent_matches(player_name, window, before_date)

        if not recent:
            return {
                "win_rate": 0.5,
                "ace_rate": 0.0,
                "df_rate": 0.0,
                "first_serve_pct": 0.0,
                "bp_converted": 0.0,
            }

        total = len(recent)
        return {
            "win_rate": sum(m["won"] for m in recent) / total,
            "ace_rate": sum(m["aces"] for m in recent) / total,
            "df_rate": sum(m["dfs"] for m in recent) / total,
            "first_serve_pct": sum(m["first_serve_pct"] for m in recent) / total,
            "bp_converted": sum(m["bp_converted"] for m in recent) / total,
        }

    def _get_surface_win_rate(
        self, player_name: str, surface: str, before_date: Optional[date] = None
    ) -> float:
        """Get win rate for a player on a specific surface."""
        history = self.player_history.get(player_name, [])

        if before_date is not None:
            history = [
                m for m in history if m["date"] is not None and m["date"] < before_date
            ]

        surface_matches = [m for m in history if m["surface"] == surface]

        if not surface_matches:
            return 0.5  # Default neutral

        return float(sum(m["won"] for m in surface_matches)) / len(surface_matches)

    def get_h2h_features(self, p1: str, p2: str) -> Dict[str, float]:
        """Get H2H features for two players."""
        key: Tuple[str, str] = tuple(sorted([p1, p2]))  # type: ignore[assignment]
        stats = self.h2h_stats.get(key, {"p1_wins": 0, "p2_wins": 0, "total": 0})

        total = stats["total"]
        if total == 0:
            return {"h2h_total": 0, "h2h_p1_win_rate": 0.5, "h2h_p2_win_rate": 0.5}

        p1_wins = stats["p1_wins"] if p1 == key[0] else stats["p2_wins"]
        p2_wins = stats["p2_wins"] if p1 == key[0] else stats["p1_wins"]

        return {
            "h2h_total": total,
            "h2h_p1_win_rate": p1_wins / total,
            "h2h_p2_win_rate": p2_wins / total,
        }

    def extract_features(self, match: TennisMatch) -> Dict[str, float]:
        """
        Extract features from a TennisMatch object.
        Uses temporal filtering to avoid data leakage in rolling stats.
        """
        features: Dict[str, float] = {}

        # 1. Rankings
        features["rank_diff"] = (match.p1_rank or 100) - (match.p2_rank or 100)
        features["rank_points_diff"] = (match.p1_rank_points or 0) - (
            match.p2_rank_points or 0
        )

        # 2. Player Attributes
        features["age_diff"] = (match.p1_age or 25) - (match.p2_age or 25)
        features["height_diff"] = (match.p1_height or 180) - (match.p2_height or 180)
        features["p1_is_lefty"] = 1 if match.p1_hand == "L" else 0
        features["p2_is_lefty"] = 1 if match.p2_hand == "L" else 0

        # 3. Match Context
        features["best_of"] = match.best_of

        # Surface (One-Hot Encoding)
        for surface in self.SURFACES:
            features[f"surface_{surface}"] = 1 if match.surface == surface else 0

        # Tournament Level (One-Hot Encoding)
        for level in self.LEVELS:
            features[f"level_{level}"] = 1 if match.tourney_level == level else 0

        # 4. H2H Features
        h2h = self.get_h2h_features(match.p1_name, match.p2_name)
        features.update(h2h)

        # 5. Seed/Entry Features
        features["p1_seed"] = match.p1_seed or 0
        features["p2_seed"] = match.p2_seed or 0
        features["p1_is_qualifier"] = 1 if match.p1_entry == "Q" else 0
        features["p2_is_qualifier"] = 1 if match.p2_entry == "Q" else 0

        # 6. Rolling Stats (last 10 matches) — BEFORE match date to avoid leakage
        p1_10 = self._get_rolling_stats(
            match.p1_name, window=10, before_date=match.match_date
        )
        p2_10 = self._get_rolling_stats(
            match.p2_name, window=10, before_date=match.match_date
        )
        features["p1_win_rate_10"] = p1_10["win_rate"]
        features["p2_win_rate_10"] = p2_10["win_rate"]
        features["p1_ace_rate_10"] = p1_10["ace_rate"]
        features["p2_ace_rate_10"] = p2_10["ace_rate"]
        features["p1_df_rate_10"] = p1_10["df_rate"]
        features["p2_df_rate_10"] = p2_10["df_rate"]
        features["p1_first_serve_pct_10"] = p1_10["first_serve_pct"]
        features["p2_first_serve_pct_10"] = p2_10["first_serve_pct"]
        features["p1_break_point_conv_10"] = p1_10["bp_converted"]
        features["p2_break_point_conv_10"] = p2_10["bp_converted"]

        # 7. Rolling Stats (last 20 matches — win rate only)
        p1_20 = self._get_rolling_stats(
            match.p1_name, window=20, before_date=match.match_date
        )
        p2_20 = self._get_rolling_stats(
            match.p2_name, window=20, before_date=match.match_date
        )
        features["p1_win_rate_20"] = p1_20["win_rate"]
        features["p2_win_rate_20"] = p2_20["win_rate"]

        # 8. Surface-specific win rate
        features["p1_surface_win_rate"] = self._get_surface_win_rate(
            match.p1_name, match.surface, before_date=match.match_date
        )
        features["p2_surface_win_rate"] = self._get_surface_win_rate(
            match.p2_name, match.surface, before_date=match.match_date
        )

        # 9. Betting Odds (optional — backward compatible)
        if match.p1_odds is not None and match.p2_odds is not None:
            features["p1_implied_prob"] = 1.0 / match.p1_odds
            features["p2_implied_prob"] = 1.0 / match.p2_odds
            features["odds_diff"] = (
                features["p1_implied_prob"] - features["p2_implied_prob"]
            )
        else:
            features["p1_implied_prob"] = 0.5
            features["p2_implied_prob"] = 0.5
            features["odds_diff"] = 0.0

        return features

    def get_feature_names(self) -> List[str]:
        """Return a list of all feature names in the correct order."""
        base_features = [
            "rank_diff",
            "rank_points_diff",
            "age_diff",
            "height_diff",
            "p1_is_lefty",
            "p2_is_lefty",
            "best_of",
            "h2h_total",
            "h2h_p1_win_rate",
            "h2h_p2_win_rate",
            "p1_seed",
            "p2_seed",
            "p1_is_qualifier",
            "p2_is_qualifier",
        ]

        surface_features = [f"surface_{s}" for s in self.SURFACES]
        level_features = [f"level_{l}" for l in self.LEVELS]

        rolling_features_10 = [
            "p1_win_rate_10",
            "p2_win_rate_10",
            "p1_ace_rate_10",
            "p2_ace_rate_10",
            "p1_df_rate_10",
            "p2_df_rate_10",
            "p1_first_serve_pct_10",
            "p2_first_serve_pct_10",
            "p1_break_point_conv_10",
            "p2_break_point_conv_10",
        ]

        rolling_features_20 = [
            "p1_win_rate_20",
            "p2_win_rate_20",
        ]

        surface_win_rate = [
            "p1_surface_win_rate",
            "p2_surface_win_rate",
        ]

        odds_features = [
            "p1_implied_prob",
            "p2_implied_prob",
            "odds_diff",
        ]

        return (
            base_features
            + surface_features
            + level_features
            + rolling_features_10
            + rolling_features_20
            + surface_win_rate
            + odds_features
        )
