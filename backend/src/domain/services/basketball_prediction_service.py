import logging
import os
from typing import Any, Optional
from datetime import datetime

import joblib

from src.domain.entities.basketball_game import BasketballGame
from src.domain.services.basketball_feature_extractor import BasketballFeatureExtractor
from src.domain.services.sharp_detector import SharpMoneyDetector, SharpMoneySignal
from src.domain.services.kelly_sizer import KellySizer
from src.infrastructure.odds_feed import OddsFeed, OddsSnapshot, OddsProvider

logger = logging.getLogger(__name__)


class BasketballPrediction:
    """Container for basketball game prediction results."""

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


class BasketballPredictionService:
    """
    Service for predicting basketball game outcomes.
    Uses trained ML model with calibrated probabilities.
    Phase 3: Integrates OddsFeed, SharpMoneyDetector, KellySizer for market alignment.
    """

    MODEL_PATH = os.getenv("BASKETBALL_MODEL_PATH", "models/basketball_classifier.pkl")

    def __init__(
        self,
        feature_extractor: BasketballFeatureExtractor,
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
                logger.error(f"Failed to load basketball model: {e}")
        else:
            logger.warning(f"Basketball model not found at {self.MODEL_PATH}")
        return None

    def predict(self, game: BasketballGame) -> Optional[BasketballPrediction]:
        """
        Predict the outcome of a basketball game.
        Uses ML model when available, falls back to rule-based prediction.
        """
        try:
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
        self, features: dict, feature_names: list, game: BasketballGame
    ) -> Optional[BasketballPrediction]:
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

        # REAL-TIME ODDS FETCH
        real_time_odds: Optional[OddsSnapshot] = None
        home_odds = game.home_odds
        away_odds = game.away_odds

        if self.odds_feed and self.odds_feed.is_configured():
            try:
                import asyncio

                async def fetch_odds():
                    return await self.odds_feed.fetch_odds(
                        sport="basketball",
                        league=game.league or "NBA",
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

        # SHARP MONEY DETECTION
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
                        sport="basketball",
                        league=game.league or "NBA",
                        match_id=game.game_id,
                        odds=opening,
                        timestamp=game.game_date - timedelta(days=7) if game.game_date else datetime.utcnow(),
                    ),
                    OddsSnapshot(
                        provider=OddsProvider.PINNACLE,
                        sport="basketball",
                        league=game.league or "NBA",
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
                kelly_results = self.kelly_sizer.calculate_basketball_kelly(
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

        return BasketballPrediction(
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
        self, features: dict, game: BasketballGame
    ) -> BasketballPrediction:
        """Rule-based prediction based on efficiency ratings and form."""
        home_wr = features.get("home_win_rate_10", 0.5)
        away_wr = features.get("away_win_rate_10", 0.5)
        home_net = features.get("home_net_rating", 0.0)
        away_net = features.get("away_net_rating", 0.0)
        home_pts = features.get("home_pts_avg", 112.0)
        away_pts = features.get("away_pts_avg", 112.0)

        # Strength from win rate
        home_strength = home_wr * 0.35
        away_strength = away_wr * 0.35

        # Strength from net rating
        home_strength += max(0.0, min(1.0, (home_net + 5) / 20)) * 0.30
        away_strength += max(0.0, min(1.0, (away_net + 5) / 20)) * 0.30

        # Strength from scoring
        total_pts = home_pts + away_pts + 0.01
        home_strength += (home_pts / total_pts) * 0.35
        away_strength += (away_pts / total_pts) * 0.35

        # Home court advantage ~60% in NBA
        home_field_bonus = 0.06
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
                        sport="basketball",
                        league=game.league or "NBA",
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

        # SHARP MONEY DETECTION
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
                        sport="basketball",
                        league=game.league or "NBA",
                        match_id=game.game_id,
                        odds=opening,
                        timestamp=game.game_date - timedelta(days=7) if game.game_date else datetime.utcnow(),
                    ),
                    OddsSnapshot(
                        provider=OddsProvider.PINNACLE,
                        sport="basketball",
                        league=game.league or "NBA",
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
                kelly_results = self.kelly_sizer.calculate_basketball_kelly(
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

        return BasketballPrediction(
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

    def _get_h2h_context(self, game: BasketballGame) -> dict:
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

    def _get_form_context(self, game: BasketballGame) -> dict:
        """Get recent form (last 10 and 20 games)."""
        fe = self.feature_extractor
        home_10 = fe._get_recent_team_stats(
            game.home_team, window=10, before_date=game.game_date
        )
        away_10 = fe._get_recent_team_stats(
            game.away_team, window=10, before_date=game.game_date
        )
        home_20 = fe._get_recent_team_stats(
            game.home_team, window=20, before_date=game.game_date
        )
        away_20 = fe._get_recent_team_stats(
            game.away_team, window=20, before_date=game.game_date
        )
        return {
            "home_win_rate_10": home_10["win_rate"],
            "away_win_rate_10": away_10["win_rate"],
            "home_win_rate_20": home_20["win_rate"],
            "away_win_rate_20": away_20["win_rate"],
            "home_pts_avg": home_10["pts_scored_avg"],
            "away_pts_avg": away_10["pts_scored_avg"],
        }

    def _calculate_value_bets(
        self,
        game: BasketballGame,
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

    def _extract_key_factors(self, features: dict, game: BasketballGame) -> list:
        """Extract the most influential factors for the prediction."""
        factors = []
        # Recent form
        home_wr = features.get("home_win_rate_10", 0.5)
        away_wr = features.get("away_win_rate_10", 0.5)
        if home_wr > 0.7:
            factors.append(f"{game.home_team} on fire ({home_wr*100:.0f}% last 10)")
        if away_wr > 0.7:
            factors.append(f"{game.away_team} on fire ({away_wr*100:.0f}% last 10)")

        # Net rating
        home_net = features.get("home_net_rating", 0.0)
        away_net = features.get("away_net_rating", 0.0)
        net_diff = home_net - away_net
        if abs(net_diff) > 3.0:
            better = game.home_team if net_diff > 0 else game.away_team
            factors.append(f"{better} has better net rating (+{abs(net_diff):.1f})")

        # H2H dominance
        h2h_total = features.get("h2h_total", 0)
        if h2h_total >= 5:
            h2h_home = features.get("h2h_home_win_rate", 0.5)
            if h2h_home > 0.65:
                factors.append(
                    f"{game.home_team} dominates H2H ({int(h2h_home*h2h_total)}/{h2h_total})"
                )
            elif h2h_home < 0.35:
                factors.append(
                    f"{game.away_team} dominates H2H ({int((1-h2h_home)*h2h_total)}/{h2h_total})"
                )

        # Pace
        home_pace = features.get("home_pace", 100.0)
        away_pace = features.get("away_pace", 100.0)
        avg_pace = (home_pace + away_pace) / 2
        if avg_pace > 103:
            factors.append("High-pace matchup expected (over-friendly)")
        elif avg_pace < 96:
            factors.append("Slow-pace matchup expected (under-friendly)")

        # Back-to-back
        if game.is_back_to_back_home:
            factors.append(f"{game.home_team} on back-to-back (fatigue)")
        if game.is_back_to_back_away:
            factors.append(f"{game.away_team} on back-to-back (fatigue)")

        return factors[:5]

    def generate_basketball_markets(
        self, game: BasketballGame, home_prob: float, away_prob: float
    ) -> list:
        """Generate all 6 basketball betting markets."""
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
                f"{winner_team} wins",
                winner_prob,
                "ML_H" if home_prob > away_prob else "ML_A",
            )
        )

        # 2. Spread (typically -5.5 to +5.5)
        spread_fav_prob = max(0.15, min(home_prob * 0.75 + 0.12, 0.88))
        spread_dog_prob = max(0.15, min(away_prob * 0.75 + 0.12, 0.88))
        if spread_fav_prob > 0.45:
            markets.append(
                _m(
                    "spread",
                    f"{game.home_team} -5.5",
                    spread_fav_prob,
                    "SP_H",
                    0.55,
                    0.6,
                )
            )
        if spread_dog_prob > 0.45:
            markets.append(
                _m(
                    "spread",
                    f"{game.away_team} +5.5",
                    spread_dog_prob,
                    "SP_A",
                    0.55,
                    0.6,
                )
            )

        # 3. Total O/U (typically 210-225 range)
        closer = 1 - abs(home_prob - away_prob)
        for thr in [215.5, 220.5, 225.5]:
            base = 0.35 + closer * 0.3
            if thr > 223.0:
                base -= 0.08
            elif thr < 218.0:
                base += 0.08
            over_p = max(0.15, min(base, 0.85))
            markets.append(
                _m("total_over", f"Over {thr}", over_p, f"OU{int(thr*10)}_O", 0.55, 0.6)
            )
            markets.append(
                _m(
                    "total_under",
                    f"Under {thr}",
                    1 - over_p,
                    f"OU{int(thr*10)}_U",
                    0.55,
                    0.6,
                )
            )

        # 4. 1H Moneyline (first half)
        f1h_h = home_prob * 0.93 + 0.035
        f1h_a = 1.0 - f1h_h
        if f1h_h > 0.55:
            markets.append(
                _m(
                    "first_half_moneyline",
                    f"{game.home_team} 1H ML",
                    f1h_h,
                    "F1H_H",
                    0.6,
                    0.6,
                )
            )
        if f1h_a > 0.55:
            markets.append(
                _m(
                    "first_half_moneyline",
                    f"{game.away_team} 1H ML",
                    f1h_a,
                    "F1H_A",
                    0.6,
                    0.6,
                )
            )

        # 5. 1Q Moneyline (first quarter)
        f1q_h = home_prob * 0.90 + 0.05
        f1q_a = 1.0 - f1q_h
        if f1q_h > 0.55:
            markets.append(
                _m(
                    "first_quarter_moneyline",
                    f"{game.home_team} 1Q ML",
                    f1q_h,
                    "F1Q_H",
                    0.6,
                    0.6,
                )
            )
        if f1q_a > 0.55:
            markets.append(
                _m(
                    "first_quarter_moneyline",
                    f"{game.away_team} 1Q ML",
                    f1q_a,
                    "F1Q_A",
                    0.6,
                    0.6,
                )
            )

        # 6. Team Total (individual team points)
        for t_name, is_h in [(game.home_team, True), (game.away_team, False)]:
            t_pts = 112.0 + ((home_prob if is_h else away_prob) - 0.5) * 8.0
            t_pts = max(100.0, min(t_pts, 125.0))
            for ou_thr in [108.5, 112.5, 116.5]:
                tt_over = (
                    0.7 if t_pts > ou_thr + 3 else (0.55 if t_pts > ou_thr else 0.35)
                )
                markets.append(
                    _m(
                        "team_total",
                        f"{t_name} Over {ou_thr}",
                        tt_over,
                        f"TT{'H' if is_h else 'A'}_{int(ou_thr*10)}",
                        0.55,
                        0.6,
                    )
                )

        markets.sort(key=lambda x: (-int(x["is_recommended"]), -x["probability"]))
        return markets
