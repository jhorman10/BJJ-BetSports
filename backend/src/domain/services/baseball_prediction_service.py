import logging
import os
from typing import Any, Optional
from datetime import datetime

import joblib
from src.domain.entities.baseball_game import BaseballGame
from src.domain.services.baseball_feature_extractor import BaseballFeatureExtractor
from src.domain.services.sharp_detector import SharpMoneyDetector, SharpMoneySignal
from src.domain.services.kelly_sizer import KellySizer
from src.infrastructure.odds_feed import OddsFeed, OddsSnapshot, OddsProvider

logger = logging.getLogger(__name__)


class BaseballPrediction:
    """Container for baseball game prediction results."""

    def __init__(
        self,
        home_win_prob: float,
        away_win_prob: float,
        confidence: float,
        h2h: Optional[dict] = None,
        form: Optional[dict] = None,
        value_bets: Optional[list] = None,
        key_factors: Optional[list] = None,
        # Phase 3: Advanced Market Alignment
        sharp_signal: Optional[SharpMoneySignal] = None,
        kelly_recommendations: Optional[list] = None,
        real_time_odds: Optional[OddsSnapshot] = None,
        market_metadata: Optional[dict] = None,
    ):
        self.home_win_prob = float(home_win_prob)
        self.away_win_prob = float(away_win_prob)
        self.confidence = float(confidence)
        self.predicted_winner = "Home" if home_win_prob > away_win_prob else "Away"
        self.h2h = h2h or {}
        self.form = form or {}
        self.value_bets = value_bets or []
        self.key_factors = key_factors or []
        # Phase 3
        self.sharp_signal = sharp_signal
        self.kelly_recommendations = kelly_recommendations or []
        self.real_time_odds = real_time_odds
        self.market_metadata = market_metadata or {}


class BaseballPredictionService:
    """
    Service for predicting baseball game outcomes using a trained ML model.
    Phase 3: Integrates OddsFeed, SharpMoneyDetector, KellySizer for market alignment.
    """

    MODEL_PATH = os.getenv("BASEBALL_MODEL_PATH", "models/baseball_classifier.pkl")

    def __init__(
        self,
        feature_extractor: BaseballFeatureExtractor,
        odds_feed: Optional[OddsFeed] = None,
        sharp_detector: Optional[SharpMoneyDetector] = None,
        kelly_sizer: Optional[KellySizer] = None,
    ):
        self.feature_extractor = feature_extractor
        self.odds_feed = odds_feed
        self.sharp_detector = sharp_detector or SharpMoneyDetector()
        self.kelly_sizer = kelly_sizer or KellySizer()
        self.model = self._load_model()

    def _load_model(self) -> Any:
        """Load the trained model from disk."""
        if os.path.exists(self.MODEL_PATH):
            try:
                return joblib.load(self.MODEL_PATH)
            except Exception as e:
                logger.error(f"Failed to load baseball model: {e}")
        else:
            logger.warning(f"Baseball model not found at {self.MODEL_PATH}")
        return None

    def predict(self, game: BaseballGame) -> Optional[BaseballPrediction]:
        """
        Predict the outcome of a baseball game.
        Falls back to rule-based prediction when ML model is unavailable.
        """
        try:
            # 1. Extract features
            features = self.feature_extractor.extract_features(game)
            feature_names = self.feature_extractor.get_feature_names()

            if self.model is not None:
                return self._predict_with_model(features, feature_names, game)
            else:
                return self._predict_rule_based(features, game)
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            return None

    def _predict_with_model(
        self, features: dict, feature_names: list, game: BaseballGame
    ) -> Optional[BaseballPrediction]:
        """Use ML model for prediction with Phase 3 market alignment."""
        X = [[features[f] for f in feature_names]]
        probs = self.model.predict_proba(X)[0]

        if 1 in self.model.classes_:
            home_idx = list(self.model.classes_).index(1)
            home_prob = float(probs[home_idx])
            away_prob = 1.0 - home_prob
        else:
            home_prob = float(probs[0])
            away_prob = float(probs[1])

        confidence = abs(home_prob - 0.5) * 2

        # ============================================================
        # PHASE 3: ADVANCED MARKET ALIGNMENT
        # ============================================================

        # 5. REAL-TIME ODDS FETCH
        real_time_odds: Optional[OddsSnapshot] = None
        home_odds = game.home_odds
        away_odds = game.away_odds

        if self.odds_feed and self.odds_feed.is_configured():
            try:
                import asyncio

                async def fetch_odds():
                    return await self.odds_feed.fetch_odds(
                        sport="baseball",
                        league=game.league or "MLB",
                        match_id=game.game_id,
                    )

                try:
                    loop = asyncio.get_running_loop()
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, fetch_odds())
                        real_time_odds = future.result(timeout=10)
                except RuntimeError:
                    real_time_odds = asyncio.run(fetch_odds())

                if real_time_odds:
                    home_odds = real_time_odds.odds.home
                    away_odds = real_time_odds.odds.away

            except Exception as e:
                logger.debug(f"Real-time odds fetch failed for {game.game_id}: {e}")

        # Calculate value bets with real-time odds
        value_bets = self._calculate_value_bets(game, home_prob, away_prob, home_odds, away_odds)

        # 6. SHARP MONEY DETECTION
        sharp_signal: Optional[SharpMoneySignal] = None
        if home_odds and away_odds and hasattr(game, "opening_odds") and game.opening_odds:
            try:
                from src.infrastructure.odds_feed import OddsSnapshot, OddsProvider
                from datetime import timedelta

                opening = game.opening_odds
                current_odds = type('Odds', (), {'home': home_odds, 'draw': 1.0, 'away': away_odds})()

                odds_history = [
                    OddsSnapshot(
                        provider=OddsProvider.PINNACLE,
                        sport="baseball",
                        league=game.league or "MLB",
                        match_id=game.game_id,
                        odds=opening,
                        timestamp=game.date - timedelta(days=7) if game.date else datetime.utcnow(),
                    ),
                    OddsSnapshot(
                        provider=OddsProvider.PINNACLE,
                        sport="baseball",
                        league=game.league or "MLB",
                        match_id=game.game_id,
                        odds=current_odds,
                        timestamp=datetime.utcnow(),
                    ),
                ]

                sharp_signal = self.sharp_detector.analyze_line_movement(
                    opening_odds=opening,
                    current_odds=current_odds,
                    odds_history=odds_history,
                )

                # Add sharp money signals to key_factors
                if sharp_signal and sharp_signal.confidence > 0.5:
                    if sharp_signal.reverse_line_movement:
                        key_factors = self._extract_key_factors(features, game)
                        key_factors.append("⚠️ Reverse Line Movement detected")
                    if sharp_signal.smart_money_side:
                        side_name = game.home_team if sharp_signal.smart_money_side == "home" else game.away_team
                        key_factors.append(f"💰 Sharp money on {side_name} (score: {sharp_signal.steam_score:.0%})")

            except Exception as e:
                logger.debug(f"Sharp money detection failed for {game.game_id}: {e}")

        # 7. KELLY CRITERION SIZING
        kelly_recommendations = []
        if home_odds and away_odds and value_bets:
            try:
                kelly_results = self.kelly_sizer.calculate_baseball_kelly(
                    home_prob=home_prob,
                    away_prob=away_prob,
                    home_odds=home_odds,
                    away_odds=away_odds,
                    bankroll=100.0,
                    confidence=confidence,
                )

                kelly_recommendations = self.kelly_sizer.generate_stake_recommendations(
                    kelly_results, 100.0, confidence
                )

            except Exception as e:
                logger.debug(f"Kelly sizing failed for {game.game_id}: {e}")

        # Extract key factors
        key_factors = self._extract_key_factors(features, game)

        # Market metadata
        market_metadata = {
            "sharp_money": {
                "smart_money_side": sharp_signal.smart_money_side if sharp_signal else None,
                "steam_score": sharp_signal.steam_score if sharp_signal else 0.0,
                "reverse_line_movement": sharp_signal.reverse_line_movement if sharp_signal else False,
            } if sharp_signal else None,
            "kelly": {
                "total_stake": sum(r.stake_units for r in kelly_recommendations),
                "recommendations": [
                    {"outcome": r.outcome, "stake_units": r.stake_units, "risk_level": r.risk_level}
                    for r in kelly_recommendations
                ],
            } if kelly_recommendations else None,
            "real_time_odds_provider": real_time_odds.provider.value if real_time_odds else None,
        }

        return BaseballPrediction(
            home_win_prob=home_prob,
            away_win_prob=away_prob,
            confidence=confidence,
            h2h=self._get_h2h_context(game),
            form=self._get_form_context(game),
            value_bets=value_bets,
            key_factors=key_factors,
            sharp_signal=sharp_signal,
            kelly_recommendations=kelly_recommendations,
            real_time_odds=real_time_odds,
            market_metadata=market_metadata,
        )

    def _predict_rule_based(
        self, features: dict, game: BaseballGame
    ) -> BaseballPrediction:
        """Fallback rule-based prediction when no ML model is available."""
        home_wr = features.get("home_win_rate_10", 0.5)
        away_wr = features.get("away_win_rate_10", 0.5)
        home_rsg = features.get("home_runs_scored_avg", 4.5)
        away_rsg = features.get("away_runs_scored_avg", 4.5)
        home_ra = features.get("home_runs_allowed_avg", 4.5)
        away_ra = features.get("away_runs_allowed_avg", 4.5)

        home_strength = (
            (home_wr * 0.4)
            + ((home_rsg / (home_rsg + away_rsg + 0.01)) * 0.3)
            + ((1 - home_ra / (home_ra + away_ra + 0.01)) * 0.3)
        )
        away_strength = (
            (away_wr * 0.4)
            + ((away_rsg / (home_rsg + away_rsg + 0.01)) * 0.3)
            + ((1 - away_ra / (home_ra + away_ra + 0.01)) * 0.3)
        )

        # Home field advantage ~54%
        home_field_bonus = 0.04
        home_strength += home_field_bonus

        total = home_strength + away_strength + 0.001
        home_prob = min(max(home_strength / total, 0.15), 0.85)
        away_prob = 1.0 - home_prob

        confidence = abs(home_prob - 0.5) * 2

        # ============================================================
        # PHASE 3: ADVANCED MARKET ALIGNMENT (Rule-based fallback)
        # ============================================================

        # REAL-TIME ODDS FETCH
        real_time_odds: Optional[OddsSnapshot] = None
        home_odds = game.home_odds
        away_odds = game.away_odds

        if self.odds_feed and self.odds_feed.is_configured():
            try:
                import asyncio

                async def fetch_odds():
                    return await self.odds_feed.fetch_odds(
                        sport="baseball",
                        league=game.league or "MLB",
                        match_id=game.game_id,
                    )

                try:
                    loop = asyncio.get_running_loop()
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, fetch_odds())
                        real_time_odds = future.result(timeout=10)
                except RuntimeError:
                    real_time_odds = asyncio.run(fetch_odds())

                if real_time_odds:
                    home_odds = real_time_odds.odds.home
                    away_odds = real_time_odds.odds.away

            except Exception as e:
                logger.debug(f"Real-time odds fetch failed for {game.game_id}: {e}")

        # Calculate value bets with real-time odds
        value_bets = self._calculate_value_bets(game, home_prob, away_prob, home_odds, away_odds)

        # SHARP MONEY DETECTION (simplified for rule-based)
        sharp_signal: Optional[SharpMoneySignal] = None
        if home_odds and away_odds and hasattr(game, "opening_odds") and game.opening_odds:
            try:
                from src.infrastructure.odds_feed import OddsSnapshot, OddsProvider
                from datetime import timedelta

                opening = game.opening_odds
                current_odds = type('Odds', (), {'home': home_odds, 'draw': 1.0, 'away': away_odds})()

                odds_history = [
                    OddsSnapshot(
                        provider=OddsProvider.PINNACLE,
                        sport="baseball",
                        league=game.league or "MLB",
                        match_id=game.game_id,
                        odds=opening,
                        timestamp=game.date - timedelta(days=7) if game.date else datetime.utcnow(),
                    ),
                    OddsSnapshot(
                        provider=OddsProvider.PINNACLE,
                        sport="baseball",
                        league=game.league or "MLB",
                        match_id=game.game_id,
                        odds=current_odds,
                        timestamp=datetime.utcnow(),
                    ),
                ]

                sharp_signal = self.sharp_detector.analyze_line_movement(
                    opening_odds=opening,
                    current_odds=current_odds,
                    odds_history=odds_history,
                )

            except Exception as e:
                logger.debug(f"Sharp money detection failed for {game.game_id}: {e}")

        # KELLY CRITERION SIZING
        kelly_recommendations = []
        if home_odds and away_odds and value_bets:
            try:
                kelly_results = self.kelly_sizer.calculate_baseball_kelly(
                    home_prob=home_prob,
                    away_prob=away_prob,
                    home_odds=home_odds,
                    away_odds=away_odds,
                    bankroll=100.0,
                    confidence=confidence,
                )

                kelly_recommendations = self.kelly_sizer.generate_stake_recommendations(
                    kelly_results, 100.0, confidence
                )

            except Exception as e:
                logger.debug(f"Kelly sizing failed for {game.game_id}: {e}")

        # Extract key factors
        key_factors = self._extract_key_factors(features, game)

        # Add sharp money signals to key_factors if detected
        if sharp_signal and sharp_signal.confidence > 0.5:
            if sharp_signal.reverse_line_movement:
                key_factors.append("⚠️ Reverse Line Movement detected")
            if sharp_signal.smart_money_side:
                side_name = game.home_team if sharp_signal.smart_money_side == "home" else game.away_team
                key_factors.append(f"💰 Sharp money on {side_name} (score: {sharp_signal.steam_score:.0%})")

        # Market metadata
        market_metadata = {
            "sharp_money": {
                "smart_money_side": sharp_signal.smart_money_side if sharp_signal else None,
                "steam_score": sharp_signal.steam_score if sharp_signal else 0.0,
                "reverse_line_movement": sharp_signal.reverse_line_movement if sharp_signal else False,
            } if sharp_signal else None,
            "kelly": {
                "total_stake": sum(r.stake_units for r in kelly_recommendations),
                "recommendations": [
                    {"outcome": r.outcome, "stake_units": r.stake_units, "risk_level": r.risk_level}
                    for r in kelly_recommendations
                ],
            } if kelly_recommendations else None,
            "real_time_odds_provider": real_time_odds.provider.value if real_time_odds else None,
        }

        return BaseballPrediction(
            home_win_prob=home_prob,
            away_win_prob=away_prob,
            confidence=confidence,
            h2h=self._get_h2h_context(game),
            form=self._get_form_context(game),
            value_bets=value_bets,
            key_factors=key_factors,
            sharp_signal=sharp_signal,
            kelly_recommendations=kelly_recommendations,
            real_time_odds=real_time_odds,
            market_metadata=market_metadata,
        )

    def _get_h2h_context(self, game: BaseballGame) -> dict:
        """Get head-to-head context."""
        fe = self.feature_extractor
        h2h = fe.get_h2h_features(game.home_team, game.away_team)
        return {
            "total_games": h2h.get("h2h_total", 0),
            "home_wins": int(
                h2h.get("h2h_team1_win_rate", 0.5) * h2h.get("h2h_total", 0)
            ),
            "away_wins": int(
                h2h.get("h2h_team2_win_rate", 0.5) * h2h.get("h2h_total", 0)
            ),
        }

    def _get_form_context(self, game: BaseballGame) -> dict:
        """Get recent form (last 5 and 10 games)."""
        fe = self.feature_extractor
        home_10 = fe._get_recent_team_stats(
            game.home_team, window=10, before_date=game.date
        )
        away_10 = fe._get_recent_team_stats(
            game.away_team, window=10, before_date=game.date
        )
        home_20 = fe._get_recent_team_stats(
            game.home_team, window=20, before_date=game.date
        )
        away_20 = fe._get_recent_team_stats(
            game.away_team, window=20, before_date=game.date
        )
        return {
            "home_win_rate_10": home_10["win_rate"],
            "away_win_rate_10": away_10["win_rate"],
            "home_win_rate_20": home_20["win_rate"],
            "away_win_rate_20": away_20["win_rate"],
            "home_runs_avg": home_10["runs_scored_avg"],
            "away_runs_avg": away_10["runs_scored_avg"],
        }

    def _calculate_value_bets(
        self,
        game: BaseballGame,
        home_prob: float,
        away_prob: float,
        home_odds: Optional[float] = None,
        away_odds: Optional[float] = None,
    ) -> list:
        """Calculate value bets by comparing model probability vs implied odds probability."""
        value_bets = []

        # Use provided odds (real-time) or fall back to game odds
        odds_home = home_odds if home_odds is not None else game.home_odds
        odds_away = away_odds if away_odds is not None else game.away_odds

        if odds_home and odds_away:
            implied_home = 1.0 / odds_home
            implied_away = 1.0 / odds_away
            home_edge = home_prob - implied_home
            away_edge = away_prob - implied_away
            if home_edge > 0.02:
                value_bets.append(
                    {
                        "team": game.home_team,
                        "odds": odds_home,
                        "implied_prob": round(implied_home * 100, 1),
                        "model_prob": round(home_prob * 100, 1),
                        "edge": round(home_edge * 100, 1),
                        "type": "value",
                    }
                )
            if away_edge > 0.02:
                value_bets.append(
                    {
                        "team": game.away_team,
                        "odds": odds_away,
                        "implied_prob": round(implied_away * 100, 1),
                        "model_prob": round(away_prob * 100, 1),
                        "edge": round(away_edge * 100, 1),
                        "type": "value",
                    }
                )
        return value_bets

    def _extract_key_factors(self, features: dict, game: BaseballGame) -> list:
        """Extract the most influential factors for the prediction."""
        factors = []
        # Recent form
        home_wr = features.get("home_win_rate_10", 0.5)
        away_wr = features.get("away_win_rate_10", 0.5)
        if home_wr > 0.7:
            factors.append(
                f"{game.home_team} en racha ({home_wr*100:.0f}% en últimos 10)"
            )
        if away_wr > 0.7:
            factors.append(
                f"{game.away_team} en racha ({away_wr*100:.0f}% en últimos 10)"
            )

        # Run differential
        run_diff = features.get("run_diff_diff", 0)
        if abs(run_diff) > 1.0:
            better = game.home_team if run_diff > 0 else game.away_team
            factors.append(
                f"{better} tiene mejor diferencia de carreras (+{abs(run_diff):.1f})"
            )

        # H2H dominance
        h2h_total = features.get("h2h_total", 0)
        if h2h_total >= 5:
            h2h_home = features.get("h2h_home_win_rate", 0.5)
            if h2h_home > 0.65:
                factors.append(
                    f"{game.home_team} domina el H2H ({int(h2h_home*h2h_total)}/{h2h_total})"
                )
            elif h2h_home < 0.35:
                factors.append(
                    f"{game.away_team} domina el H2H ({int((1-h2h_home)*h2h_total)}/{h2h_total})"
                )

        # Pitcher matchup
        if features.get("pitcher_matchup_known"):
            home_era = features.get("home_pitcher_era", 4.0)
            away_era = features.get("away_pitcher_era", 4.0)
            if home_era < 3.0:
                factors.append(
                    f"{game.home_pitcher_name or game.home_team} tiene ERA bajo ({home_era:.2f})"
                )
            if away_era < 3.0:
                factors.append(
                    f"{game.away_pitcher_name or game.away_team} tiene ERA bajo ({away_era:.2f})"
                )

        return factors[:5]

    def generate_baseball_markets(
        self, game: BaseballGame, home_prob: float, away_prob: float
    ) -> list:
        """Generate all 6 baseball betting markets."""
        home_prob, away_prob = float(home_prob), float(away_prob)
        markets = []

        def _m(
            mtype: str,
            label: str,
            prob: float,
            code: str,
            rec_thresh: float = 0.6,
            conf_thresh: float = 0.65,
        ) -> dict[str, Any]:
            cl = "high" if prob > conf_thresh else "medium" if prob > 0.55 else "low"
            return {
                "market_type": mtype,
                "market_label": label,
                "probability": round(prob, 3),
                "confidence_level": cl,
                "reasoning": f"{label}: {prob*100:.1f}%",
                "risk_level": round((1 - prob) * 10, 1),
                "is_recommended": prob > rec_thresh,
                "priority_score": round(prob * 100, 1),
                "pick_code": code,
            }

        # 1. Moneyline
        winner_prob = max(home_prob, away_prob)
        winner_team = game.home_team if home_prob > away_prob else game.away_team
        markets.append(
            _m(
                "moneyline",
                f"{winner_team} gana",
                winner_prob,
                "ML_H" if home_prob > away_prob else "ML_A",
            )
        )

        # 2. Run Line (-1.5 / +1.5)
        rl_home = max(0.1, min(home_prob * 0.65 + 0.1, 0.9))
        rl_away = max(0.1, min(away_prob * 0.65 + 0.1, 0.9))
        if rl_home > 0.4:
            markets.append(
                _m("run_line", f"{game.home_team} -1.5", rl_home, "RL_H", 0.5)
            )
        if rl_away > 0.4:
            markets.append(
                _m("run_line", f"{game.away_team} +1.5", rl_away, "RL_A", 0.5)
            )

        # 3. Total Runs O/U
        closer = 1 - abs(home_prob - away_prob)
        for thr in [7.5, 8.5, 9.5]:
            base = 0.35 + closer * 0.3
            if thr > 9.0:
                base -= 0.1
            elif thr < 8.0:
                base += 0.1
            over_p = max(0.1, min(base, 0.9))
            markets.append(
                _m(
                    "total_runs_over",
                    f"Más de {thr} carreras",
                    over_p,
                    f"OU{int(thr*10)}_O",
                    0.55,
                    0.6,
                )
            )
            markets.append(
                _m(
                    "total_runs_under",
                    f"Menos de {thr} carreras",
                    1 - over_p,
                    f"OU{int(thr*10)}_U",
                    0.55,
                    0.6,
                )
            )

        # 4. First 5 Innings
        f5_h = home_prob * 0.92 + 0.04
        f5_a = 1.0 - f5_h
        if f5_h > 0.55:
            markets.append(
                _m(
                    "first_5_innings",
                    f"{game.home_team} gana F5",
                    f5_h,
                    "F5_H",
                    0.6,
                    0.6,
                )
            )
        if f5_a > 0.55:
            markets.append(
                _m(
                    "first_5_innings",
                    f"{game.away_team} gana F5",
                    f5_a,
                    "F5_A",
                    0.6,
                    0.6,
                )
            )

        # 5. Team Total Runs
        for t_name, is_h in [(game.home_team, True), (game.away_team, False)]:
            t_total = 4.5 + ((home_prob if is_h else away_prob) - 0.5) * 1.5
            t_total = max(2.5, min(t_total, 7.0))
            for ou_thr in [3.5, 4.5]:
                tt_over = (
                    0.7
                    if t_total > ou_thr + 1
                    else (0.55 if t_total > ou_thr else 0.35)
                )
                markets.append(
                    _m(
                        "team_total_runs",
                        f"{t_name} más de {ou_thr} carreras",
                        tt_over,
                        f"TT{'H' if is_h else 'A'}_{int(ou_thr*10)}",
                        0.55,
                        0.6,
                    )
                )

        # 6. Both Teams Score
        bts = min(0.5 + closer * 0.35, 0.9)
        markets.append(
            _m("both_teams_score", "Ambos equipos anotan", bts, "BTS_Y", 0.6, 0.7)
        )
        markets.append(
            _m(
                "both_teams_score_no",
                "Al menos uno no anota",
                1 - bts,
                "BTS_N",
                0.6,
                0.7,
            )
        )

        markets.sort(key=lambda x: (-int(x["is_recommended"]), -x["probability"]))
        return markets
