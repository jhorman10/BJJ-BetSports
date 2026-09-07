from collections import defaultdict
from datetime import date
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from src.domain.entities.basketball_game import BasketballGame


class BasketballFeatureExtractor:
    """
    Extracts features from BasketballGame objects for prediction.
    40 features across 7 groups:
      1. Offense (8)
      2. Defense (8)
      3. Pace & Efficiency (6)
      4. Recent Form (6)
      5. Head-to-Head (3)
      6. Context (6)
      7. Betting Odds (3)
    """

    CONFERENCES = {
        "East": [
            "BOS",
            "NYK",
            "PHI",
            "MIL",
            "CLE",
            "IND",
            "MIA",
            "CHI",
            "ATL",
            "BKN",
            "TOR",
            "WAS",
            "DET",
            "CHA",
            "ORL",
        ],
        "West": [
            "DEN",
            "OKC",
            "MIN",
            "LAC",
            "DAL",
            "PHX",
            "LAL",
            "SAC",
            "GSW",
            "NOP",
            "HOU",
            "SAS",
            "POR",
            "UTA",
            "MEM",
        ],
    }

    def __init__(self, historical_data: Optional[pd.DataFrame] = None):
        self.historical_data = historical_data
        self.team_stats: Dict[str, dict] = {}
        self.h2h_stats: Dict[tuple, dict] = {}
        self.team_history: Dict[str, List[dict]] = defaultdict(list)

        if historical_data is not None and not historical_data.empty:
            self._precompute_stats()

    def _precompute_stats(self) -> None:
        """Precompute team stats and H2H from historical data."""
        if self.historical_data is None:
            return
        self._compute_h2h()
        self._compute_team_history()

    def _compute_team_history(self) -> None:
        """Build per-team game history."""
        assert self.historical_data is not None
        for _, row in self.historical_data.iterrows():
            home = row.get("home_team", "")
            away = row.get("away_team", "")
            if not home or not away:
                continue
            try:
                game_date = pd.to_datetime(row.get("game_date")).date()
            except Exception:
                game_date = None

            home_score = self._safe_int(row.get("home_score"))
            away_score = self._safe_int(row.get("away_score"))
            home_win = 1 if home_score > away_score else 0

            self.team_history[home].append(
                {
                    "won": home_win,
                    "pts_scored": home_score,
                    "pts_allowed": away_score,
                    "date": game_date,
                    "is_home": 1,
                }
            )
            self.team_history[away].append(
                {
                    "won": 1 - home_win,
                    "pts_scored": away_score,
                    "pts_allowed": home_score,
                    "date": game_date,
                    "is_home": 0,
                }
            )

    def _compute_h2h(self) -> None:
        """Compute Head-to-Head records."""
        if self.historical_data is None:
            return
        for _, row in self.historical_data.iterrows():
            home = row.get("home_team", "")
            away = row.get("away_team", "")
            home_score = self._safe_int(row.get("home_score"))
            away_score = self._safe_int(row.get("away_score"))
            if not home or not away:
                continue

            key = tuple(sorted([home, away]))
            if key not in self.h2h_stats:
                self.h2h_stats[key] = {"home_wins": 0, "away_wins": 0, "total": 0}
            self.h2h_stats[key]["total"] += 1
            home_won = home_score > away_score
            if home_won:
                self.h2h_stats[key]["home_wins" if home == key[0] else "away_wins"] += 1
            else:
                self.h2h_stats[key]["away_wins" if home == key[0] else "home_wins"] += 1

    @staticmethod
    def _safe_int(val: Any) -> int:
        try:
            if pd.isna(val):
                return 0
            return int(float(val))
        except (ValueError, TypeError):
            return 0

    def _get_recent_team_stats(
        self, team: str, window: int = 10, before_date: Optional[date] = None
    ) -> Dict[str, float]:
        """Get rolling stats for a team over their last N games."""
        history = self.team_history.get(team, [])
        if before_date is not None:
            history = [
                g for g in history if g["date"] is not None and g["date"] < before_date
            ]
        recent = history[-window:] if len(history) > 0 else []
        if not recent:
            return {
                "win_rate": 0.5,
                "pts_scored_avg": 112.0,
                "pts_allowed_avg": 112.0,
                "home_win_rate": 0.550,
                "away_win_rate": 0.450,
            }
        total = len(recent)
        home_games = [g for g in recent if g["is_home"]]
        away_games = [g for g in recent if not g["is_home"]]
        return {
            "win_rate": sum(g["won"] for g in recent) / total,
            "pts_scored_avg": sum(g["pts_scored"] for g in recent) / total,
            "pts_allowed_avg": sum(g["pts_allowed"] for g in recent) / total,
            "home_win_rate": (
                sum(g["won"] for g in home_games) / len(home_games)
                if home_games
                else 0.550
            ),
            "away_win_rate": (
                sum(g["won"] for g in away_games) / len(away_games)
                if away_games
                else 0.450
            ),
        }

    def get_h2h_features(self, team1: str, team2: str) -> Dict[str, float]:
        """Get H2H features for two teams."""
        key = tuple(sorted([team1, team2]))
        stats = self.h2h_stats.get(key, {"home_wins": 0, "away_wins": 0, "total": 0})
        total = stats["total"]
        if total == 0:
            return {
                "h2h_total": 0,
                "h2h_team1_win_rate": 0.5,
                "h2h_team2_win_rate": 0.5,
            }
        t1_wins = stats["home_wins"] if team1 == key[0] else stats["away_wins"]
        return {
            "h2h_total": total,
            "h2h_team1_win_rate": t1_wins / total,
            "h2h_team2_win_rate": (total - t1_wins) / total,
        }

    def extract_features(self, game: BasketballGame) -> Dict[str, float]:
        """
        Extract 40 features from a BasketballGame object.
        Uses temporal filtering to avoid data leakage.
        """
        features = {}

        # Group 1: Offense (8 features)
        home_form = self._get_recent_team_stats(
            game.home_team, window=10, before_date=game.game_date
        )
        away_form = self._get_recent_team_stats(
            game.away_team, window=10, before_date=game.game_date
        )
        features["home_pts_avg"] = (
            game.home_pts_avg
            if game.home_pts_avg is not None
            else home_form["pts_scored_avg"]
        )
        features["away_pts_avg"] = (
            game.away_pts_avg
            if game.away_pts_avg is not None
            else away_form["pts_scored_avg"]
        )
        features["home_fg_pct"] = (
            game.home_fg_pct if game.home_fg_pct is not None else 0.465
        )
        features["away_fg_pct"] = (
            game.away_fg_pct if game.away_fg_pct is not None else 0.465
        )
        features["home_3pt_pct"] = (
            game.home_3pt_pct if game.home_3pt_pct is not None else 0.360
        )
        features["away_3pt_pct"] = (
            game.away_3pt_pct if game.away_3pt_pct is not None else 0.360
        )
        features["pts_avg_diff"] = features["home_pts_avg"] - features["away_pts_avg"]
        features["fg_pct_diff"] = features["home_fg_pct"] - features["away_fg_pct"]

        # Group 2: Defense (8 features)
        features["home_pts_allowed_avg"] = (
            game.home_pts_allowed_avg
            if game.home_pts_allowed_avg is not None
            else home_form["pts_allowed_avg"]
        )
        features["away_pts_allowed_avg"] = (
            game.away_pts_allowed_avg
            if game.away_pts_allowed_avg is not None
            else away_form["pts_allowed_avg"]
        )
        features["home_def_rating"] = (
            game.home_def_rating if game.home_def_rating is not None else 112.0
        )
        features["away_def_rating"] = (
            game.away_def_rating if game.away_def_rating is not None else 112.0
        )
        features["def_rating_diff"] = (
            features["home_def_rating"] - features["away_def_rating"]
        )
        features["home_net_rating"] = (
            game.home_off_rating if game.home_off_rating is not None else 112.0
        ) - features["home_def_rating"]
        features["away_net_rating"] = (
            game.away_off_rating if game.away_off_rating is not None else 112.0
        ) - features["away_def_rating"]
        features["net_rating_diff"] = (
            features["home_net_rating"] - features["away_net_rating"]
        )

        # Group 3: Pace & Efficiency (6 features)
        features["home_pace"] = game.home_pace if game.home_pace is not None else 100.0
        features["away_pace"] = game.away_pace if game.away_pace is not None else 100.0
        features["pace_diff"] = features["home_pace"] - features["away_pace"]
        features["home_off_rating"] = (
            game.home_off_rating if game.home_off_rating is not None else 112.0
        )
        features["away_off_rating"] = (
            game.away_off_rating if game.away_off_rating is not None else 112.0
        )
        features["off_rating_diff"] = (
            features["home_off_rating"] - features["away_off_rating"]
        )

        # Group 4: Recent Form (6 features)
        home_20 = self._get_recent_team_stats(
            game.home_team, window=20, before_date=game.game_date
        )
        away_20 = self._get_recent_team_stats(
            game.away_team, window=20, before_date=game.game_date
        )
        features["home_win_rate_10"] = home_form["win_rate"]
        features["away_win_rate_10"] = away_form["win_rate"]
        features["home_win_rate_20"] = home_20["win_rate"]
        features["away_win_rate_20"] = away_20["win_rate"]
        features["home_home_win_rate"] = home_form["home_win_rate"]
        features["away_away_win_rate"] = away_form["away_win_rate"]

        # Group 5: Head-to-Head (3 features)
        h2h = self.get_h2h_features(game.home_team, game.away_team)
        features["h2h_total"] = h2h["h2h_total"]
        features["h2h_home_win_rate"] = h2h["h2h_team1_win_rate"]
        features["h2h_away_win_rate"] = h2h["h2h_team2_win_rate"]

        # Group 6: Context (6 features)
        features["is_conference"] = (
            1.0 if self._is_conference(game.home_team, game.away_team) else 0.0
        )
        features["home_rest_days"] = (
            float(game.home_rest_days) if game.home_rest_days is not None else 1.0
        )
        features["away_rest_days"] = (
            float(game.away_rest_days) if game.away_rest_days is not None else 1.0
        )
        features["is_b2b_home"] = 1.0 if game.is_back_to_back_home else 0.0
        features["is_b2b_away"] = 1.0 if game.is_back_to_back_away else 0.0
        features["rest_diff"] = features["home_rest_days"] - features["away_rest_days"]

        # Group 7: Betting Odds (3 features)
        if game.home_odds is not None and game.away_odds is not None:
            features["home_implied_prob"] = 1.0 / game.home_odds
            features["away_implied_prob"] = 1.0 / game.away_odds
            features["odds_diff"] = (
                features["home_implied_prob"] - features["away_implied_prob"]
            )
        else:
            features["home_implied_prob"] = 0.5
            features["away_implied_prob"] = 0.5
            features["odds_diff"] = 0.0

        return features

    def _is_conference(self, team1: str, team2: str) -> bool:
        """Check if two teams are in the same conference."""
        for conf_teams in self.CONFERENCES.values():
            if team1 in conf_teams and team2 in conf_teams:
                return True
        return False

    def get_feature_names(self) -> List[str]:
        """Return all 40 feature names in order."""
        return [
            # Group 1: Offense (8)
            "home_pts_avg",
            "away_pts_avg",
            "home_fg_pct",
            "away_fg_pct",
            "home_3pt_pct",
            "away_3pt_pct",
            "pts_avg_diff",
            "fg_pct_diff",
            # Group 2: Defense (8)
            "home_pts_allowed_avg",
            "away_pts_allowed_avg",
            "home_def_rating",
            "away_def_rating",
            "def_rating_diff",
            "home_net_rating",
            "away_net_rating",
            "net_rating_diff",
            # Group 3: Pace & Efficiency (6)
            "home_pace",
            "away_pace",
            "pace_diff",
            "home_off_rating",
            "away_off_rating",
            "off_rating_diff",
            # Group 4: Recent Form (6)
            "home_win_rate_10",
            "away_win_rate_10",
            "home_win_rate_20",
            "away_win_rate_20",
            "home_home_win_rate",
            "away_away_win_rate",
            # Group 5: H2H (3)
            "h2h_total",
            "h2h_home_win_rate",
            "h2h_away_win_rate",
            # Group 6: Context (6)
            "is_conference",
            "home_rest_days",
            "away_rest_days",
            "is_b2b_home",
            "is_b2b_away",
            "rest_diff",
            # Group 7: Betting Odds (3)
            "home_implied_prob",
            "away_implied_prob",
            "odds_diff",
        ]
