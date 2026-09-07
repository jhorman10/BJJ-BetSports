from collections import defaultdict
from datetime import date
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from src.domain.entities.baseball_game import BaseballGame


class BaseballFeatureExtractor:
    """
    Extracts features from BaseballGame objects for prediction.
    46 features across 7 groups:
      1. Pitcher matchup (8)
      2. Team batting (10)
      3. Bullpen/pitching (8)
      4. Recent form (6)
      5. Head-to-head (3)
      6. Context (8)
      7. Betting odds (3)
    """

    DIVISIONS = {
        "AL": [
            "NYY",
            "BOS",
            "TB",
            "BAL",
            "TOR",
            "HOU",
            "SEA",
            "OAK",
            "TEX",
            "LAA",
            "CWS",
            "MIN",
            "DET",
            "CLE",
            "KC",
        ],
        "NL": [
            "LAD",
            "SF",
            "SD",
            "ARI",
            "COL",
            "ATL",
            "PHI",
            "NYM",
            "WSH",
            "MIA",
            "CHC",
            "MIL",
            "STL",
            "PIT",
            "CIN",
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
                game_date = pd.to_datetime(row.get("date")).date()
            except Exception:
                game_date = None

            home_score = self._safe_int(row.get("home_score"))
            away_score = self._safe_int(row.get("away_score"))
            home_win = 1 if home_score > away_score else 0

            self.team_history[home].append(
                {
                    "won": home_win,
                    "runs_scored": home_score,
                    "runs_allowed": away_score,
                    "date": game_date,
                    "is_home": 1,
                }
            )
            self.team_history[away].append(
                {
                    "won": 1 - home_win,
                    "runs_scored": away_score,
                    "runs_allowed": home_score,
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
                "runs_scored_avg": 4.5,
                "runs_allowed_avg": 4.5,
                "home_win_rate": 0.538,
                "away_win_rate": 0.462,
            }
        total = len(recent)
        home_games = [g for g in recent if g["is_home"]]
        away_games = [g for g in recent if not g["is_home"]]
        return {
            "win_rate": sum(g["won"] for g in recent) / total,
            "runs_scored_avg": sum(g["runs_scored"] for g in recent) / total,
            "runs_allowed_avg": sum(g["runs_allowed"] for g in recent) / total,
            "home_win_rate": (
                sum(g["won"] for g in home_games) / len(home_games)
                if home_games
                else 0.5
            ),
            "away_win_rate": (
                sum(g["won"] for g in away_games) / len(away_games)
                if away_games
                else 0.5
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

    def extract_features(self, game: BaseballGame) -> Dict[str, float]:
        """
        Extract 46 features from a BaseballGame object.
        Uses temporal filtering to avoid data leakage.
        """
        features = {}

        # Group 1: Pitcher Matchup (8 features)
        features["home_pitcher_available"] = 1.0 if game.home_pitcher_name else 0.0
        features["away_pitcher_available"] = 1.0 if game.away_pitcher_name else 0.0
        features["pitcher_matchup_known"] = (
            1.0 if (game.home_pitcher_name and game.away_pitcher_name) else 0.0
        )
        # Default neutral pitcher stats when unavailable
        features["home_pitcher_era"] = 4.00
        features["away_pitcher_era"] = 4.00
        features["home_pitcher_whip"] = 1.30
        features["away_pitcher_whip"] = 1.30
        features["pitcher_era_diff"] = 0.0

        # Group 2: Team Batting (10 features)
        home_bat = self._get_recent_team_stats(
            game.home_team, window=10, before_date=game.date
        )
        away_bat = self._get_recent_team_stats(
            game.away_team, window=10, before_date=game.date
        )
        features["home_runs_scored_avg"] = home_bat["runs_scored_avg"]
        features["away_runs_scored_avg"] = away_bat["runs_scored_avg"]
        features["home_runs_allowed_avg"] = home_bat["runs_allowed_avg"]
        features["away_runs_allowed_avg"] = away_bat["runs_allowed_avg"]
        features["run_diff_home"] = (
            home_bat["runs_scored_avg"] - home_bat["runs_allowed_avg"]
        )
        features["run_diff_away"] = (
            away_bat["runs_scored_avg"] - away_bat["runs_allowed_avg"]
        )
        features["run_diff_diff"] = (
            features["run_diff_home"] - features["run_diff_away"]
        )
        features["home_batting_avg"] = 0.250
        features["away_batting_avg"] = 0.250
        features["ops_diff"] = 0.0

        # Group 3: Bullpen/Pitching (8 features)
        features["home_era"] = 4.00
        features["away_era"] = 4.00
        features["home_whip"] = 1.30
        features["away_whip"] = 1.30
        features["era_diff"] = features["home_era"] - features["away_era"]
        features["whip_diff"] = features["home_whip"] - features["away_whip"]
        features["home_bullpen_era"] = 3.80
        features["away_bullpen_era"] = 3.80

        # Group 4: Recent Form (6 features)
        home_20 = self._get_recent_team_stats(
            game.home_team, window=20, before_date=game.date
        )
        away_20 = self._get_recent_team_stats(
            game.away_team, window=20, before_date=game.date
        )
        features["home_win_rate_10"] = home_bat["win_rate"]
        features["away_win_rate_10"] = away_bat["win_rate"]
        features["home_win_rate_20"] = home_20["win_rate"]
        features["away_win_rate_20"] = away_20["win_rate"]
        features["home_home_win_rate"] = home_bat["home_win_rate"]
        features["away_away_win_rate"] = away_bat["away_win_rate"]

        # Group 5: Head-to-Head (3 features)
        h2h = self.get_h2h_features(game.home_team, game.away_team)
        features["h2h_total"] = h2h["h2h_total"]
        features["h2h_home_win_rate"] = h2h["h2h_team1_win_rate"]
        features["h2h_away_win_rate"] = h2h["h2h_team2_win_rate"]

        # Group 6: Context (8 features)
        features["is_day_game"] = 1.0 if game.day_night == "day" else 0.0
        features["is_divisional"] = (
            1.0 if self._is_divisional(game.home_team, game.away_team) else 0.0
        )
        features["is_interleague"] = (
            1.0 if self._is_interleague(game.home_team, game.away_team) else 0.0
        )
        features["home_rest_days"] = 1.0
        features["away_rest_days"] = 1.0
        features["home_wins"] = 0.0
        features["away_wins"] = 0.0
        features["home_losses"] = 0.0

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

    def _is_divisional(self, team1: str, team2: str) -> bool:
        """Check if two teams are in the same division."""
        for div_teams in self.DIVISIONS.values():
            if team1 in div_teams and team2 in div_teams:
                return True
        return False

    def _is_interleague(self, team1: str, team2: str) -> bool:
        """Check if two teams are from different leagues."""
        al_teams = set(self.DIVISIONS.get("AL", []))
        nl_teams = set(self.DIVISIONS.get("NL", []))
        return (team1 in al_teams and team2 in nl_teams) or (
            team1 in nl_teams and team2 in al_teams
        )

    def get_feature_names(self) -> List[str]:
        """Return all 46 feature names in order."""
        return [
            # Group 1: Pitcher Matchup (8)
            "home_pitcher_available",
            "away_pitcher_available",
            "pitcher_matchup_known",
            "home_pitcher_era",
            "away_pitcher_era",
            "home_pitcher_whip",
            "away_pitcher_whip",
            "pitcher_era_diff",
            # Group 2: Team Batting (10)
            "home_runs_scored_avg",
            "away_runs_scored_avg",
            "home_runs_allowed_avg",
            "away_runs_allowed_avg",
            "run_diff_home",
            "run_diff_away",
            "run_diff_diff",
            "home_batting_avg",
            "away_batting_avg",
            "ops_diff",
            # Group 3: Bullpen/Pitching (8)
            "home_era",
            "away_era",
            "home_whip",
            "away_whip",
            "era_diff",
            "whip_diff",
            "home_bullpen_era",
            "away_bullpen_era",
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
            # Group 6: Context (8)
            "is_day_game",
            "is_divisional",
            "is_interleague",
            "home_rest_days",
            "away_rest_days",
            "home_wins",
            "away_wins",
            "home_losses",
            # Group 7: Betting Odds (3)
            "home_implied_prob",
            "away_implied_prob",
            "odds_diff",
        ]
