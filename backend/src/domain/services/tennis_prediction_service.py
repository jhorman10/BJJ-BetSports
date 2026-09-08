import logging
import os
from datetime import datetime
from typing import Any, Optional

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from src.domain.entities.tennis_match import TennisMatch
from src.domain.services.kelly_sizer import KellySizer
from src.domain.services.sharp_detector import SharpMoneyDetector, SharpMoneySignal
from src.domain.services.tennis_feature_extractor import TennisFeatureExtractor
from src.infrastructure.data_sources.tennis_data_source import TennisDataSource
from src.infrastructure.odds_feed import OddsFeed, OddsProvider, OddsSnapshot

logger = logging.getLogger(__name__)


class TennisPrediction:
    """Container for tennis match prediction results."""

    def __init__(
        self,
        p1_win_prob: float,
        p2_win_prob: float,
        confidence: float,
        h2h: Optional[dict] = None,
        surface_stats: Optional[dict] = None,
        form: Optional[dict] = None,
        value_bets: Optional[list] = None,
        key_factors: Optional[list] = None,
        # Phase 3: Advanced Market Alignment
        sharp_signal: Optional[SharpMoneySignal] = None,
        kelly_recommendations: Optional[list] = None,
        real_time_odds: Optional[OddsSnapshot] = None,
        market_metadata: Optional[dict] = None,
    ):
        self.p1_win_prob = p1_win_prob
        self.p2_win_prob = p2_win_prob
        self.confidence = confidence
        self.predicted_winner = "Player 1" if p1_win_prob > p2_win_prob else "Player 2"
        self.h2h = h2h or {}
        self.surface_stats = surface_stats or {}
        self.form = form or {}
        self.value_bets = value_bets or []
        self.key_factors = key_factors or []
        # Phase 3
        self.sharp_signal = sharp_signal
        self.kelly_recommendations = kelly_recommendations or []
        self.real_time_odds = real_time_odds
        self.market_metadata = market_metadata or {}


class TennisPredictionService:
    """
    Service for predicting tennis match outcomes using a trained ML model.
    Phase 3: Integrates OddsFeed, SharpMoneyDetector, KellySizer for market alignment.
    """

    MODEL_PATH = os.getenv("TENNIS_MODEL_PATH", "models/tennis_classifier.pkl")

    def __init__(
        self,
        feature_extractor: TennisFeatureExtractor,
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
        """Load the trained model from disk and calibrate it using historical data."""
        if not os.path.exists(self.MODEL_PATH):
            logger.warning(f"Tennis model not found at {self.MODEL_PATH}")
            return None

        try:
            base_model = joblib.load(self.MODEL_PATH)
            logger.info("Base tennis model loaded successfully")

            # Calibrate the model using isotonic regression with cross-validation
            calibrated_model = self._calibrate_model(base_model)
            if calibrated_model is not None:
                logger.info("Model calibrated successfully with isotonic regression")
                return calibrated_model

            logger.warning("Calibration failed, returning base model")
            return base_model

        except Exception as e:
            logger.error(f"Failed to load tennis model: {e}")
            return None

    def _calibrate_model(self, base_model: Any) -> Any:
        """
        Calibrate the base RandomForest model using CalibratedClassifierCV
        with isotonic regression.

        Uses historical match data as a holdout set for calibration.
        Falls back to 3-fold cross-validation if holdout data is insufficient.
        """
        try:
            # Load historical data for calibration (similar to test script)
            source = TennisDataSource(tour="atp")
            hist_df = source.fetch_matches_range(
                2020, 2023
            )  # Use recent 4 years for calibration

            if hist_df is None or len(hist_df) < 100:
                logger.warning(
                    "Insufficient historical data for calibration, using CV=3"
                )
                return CalibratedClassifierCV(base_model, method="isotonic", cv=3)

            # Prepare features and labels for calibration
            # Sort by date and use the last 20% as calibration holdout
            hist_df = hist_df.sort_values("tourney_date")
            split_idx = int(len(hist_df) * 0.8)
            calibration_df = hist_df.iloc[split_idx:]

            if len(calibration_df) < 50:
                logger.warning("Calibration holdout too small, using CV=3")
                return CalibratedClassifierCV(base_model, method="isotonic", cv=3)

            # Create feature extractor with training data (first 80%)
            train_df = hist_df.iloc[:split_idx]
            train_extractor = TennisFeatureExtractor(historical_data=train_df)

            # Extract features and labels from calibration set
            x_cal = []
            y_cal = []

            for _, row in calibration_df.iterrows():
                winner = row.get("winner_name", "")
                loser = row.get("loser_name", "")
                if not winner or not loser:
                    continue

                # Create a mock match for feature extraction
                try:
                    match = TennisMatch(
                        match_id=f"cal_{len(x_cal)}",
                        tournament_name=row.get("tourney_name", "Unknown"),
                        surface=row.get("surface", "Hard"),
                        tourney_level=row.get("tourney_level", "A"),
                        round_name=row.get("round", "R128"),
                        match_date=pd.to_datetime(row.get("tourney_date")).date(),
                        best_of=5 if row.get("best_of") == 5 else 3,
                        p1_name=winner,
                        p1_rank=row.get("winner_rank", 100),
                        p1_rank_points=row.get("winner_rank_points", 0),
                        p1_age=row.get("winner_age", 25.0),
                        p1_hand=row.get("winner_hand", "R"),
                        p1_height=row.get("winner_ht", 180),
                        p2_name=loser,
                        p2_rank=row.get("loser_rank", 100),
                        p2_rank_points=row.get("loser_rank_points", 0),
                        p2_age=row.get("loser_age", 25.0),
                        p2_hand=row.get("loser_hand", "R"),
                        p2_height=row.get("loser_ht", 180),
                        p1_odds=row.get("avgw"),
                        p2_odds=row.get("avgl"),
                    )

                    features = train_extractor.extract_features(match)
                    feature_names = train_extractor.get_feature_names()
                    x_cal.append([features[f] for f in feature_names])
                    y_cal.append(1)  # Winner is p1

                    # Also add the reverse (loser as p1) for balanced calibration
                    match_rev = TennisMatch(
                        match_id=f"cal_{len(x_cal)}",
                        tournament_name=row.get("tourney_name", "Unknown"),
                        surface=row.get("surface", "Hard"),
                        tourney_level=row.get("tourney_level", "A"),
                        round_name=row.get("round", "R128"),
                        match_date=pd.to_datetime(row.get("tourney_date")).date(),
                        best_of=5 if row.get("best_of") == 5 else 3,
                        p1_name=loser,
                        p1_rank=row.get("loser_rank", 100),
                        p1_rank_points=row.get("loser_rank_points", 0),
                        p1_age=row.get("loser_age", 25.0),
                        p1_hand=row.get("loser_hand", "R"),
                        p1_height=row.get("loser_ht", 180),
                        p2_name=winner,
                        p2_rank=row.get("winner_rank", 100),
                        p2_rank_points=row.get("winner_rank_points", 0),
                        p2_age=row.get("winner_age", 25.0),
                        p2_hand=row.get("winner_hand", "R"),
                        p2_height=row.get("winner_ht", 180),
                        p1_odds=row.get("avgl"),
                        p2_odds=row.get("avgw"),
                    )

                    features_rev = train_extractor.extract_features(match_rev)
                    x_cal.append([features_rev[f] for f in feature_names])
                    y_cal.append(0)  # Winner is p2

                except Exception:
                    continue  # Skip problematic matches

            if len(x_cal) < 50:
                logger.warning("Not enough calibration samples, using CV=3")
                return CalibratedClassifierCV(base_model, method="isotonic", cv=3)

            x_cal = np.array(x_cal)
            y_cal = np.array(y_cal)

            # Fit calibrated classifier on holdout set
            calibrated = CalibratedClassifierCV(
                base_model, method="isotonic", cv="prefit"
            )
            calibrated.fit(x_cal, y_cal)

            logger.info(
                f"Calibrated model on {len(x_cal)} samples from "
                f"{len(calibration_df)} matches"
            )
            return calibrated

        except Exception as e:
            logger.warning(f"Calibration failed: {e}, falling back to CV=3")
            return CalibratedClassifierCV(base_model, method="isotonic", cv=3)

    def predict(self, match: TennisMatch) -> Optional[TennisPrediction]:
        """
        Predict the outcome of a tennis match with full context.
        Phase 3: Includes real-time odds, sharp money detection, Kelly sizing.
        """
        if self.model is None:
            logger.error("Model not loaded, cannot predict.")
            return None

        try:
            # 1. Extract features and predict
            features, feature_names = self._extract_features(match)
            x = [[features[f] for f in feature_names]]
            p1_prob, p2_prob, confidence = self._get_predictions(x)

            # 2. Gather context from feature extractor
            h2h, surface_stats, form = self._build_context(match)

            # 3. Phase 3: Advanced market alignment
            p1_odds, p2_odds, real_time_odds = self._fetch_real_time_odds(match)

            value_bets = self._calculate_value_bets(
                match, p1_prob, p2_prob, p1_odds, p2_odds
            )

            sharp_signal = self._detect_sharp_money(match, p1_odds, p2_odds)

            kelly_recommendations = self._calculate_kelly(
                p1_prob, p2_prob, p1_odds, p2_odds, value_bets, confidence
            )

            # 4. Extract key factors (includes sharp money signals if detected)
            key_factors = self._extract_key_factors(features, match)

            # 5. Build market metadata
            market_metadata = self._build_market_metadata(
                sharp_signal, kelly_recommendations, real_time_odds
            )

            return TennisPrediction(
                p1_win_prob=p1_prob,
                p2_win_prob=p2_prob,
                confidence=confidence,
                h2h=h2h,
                surface_stats=surface_stats,
                form=form,
                value_bets=value_bets,
                key_factors=key_factors,
                sharp_signal=sharp_signal,
                kelly_recommendations=kelly_recommendations,
                real_time_odds=real_time_odds,
                market_metadata=market_metadata,
            )
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            return None

    def _extract_features(self, match: TennisMatch) -> tuple[dict, list]:
        """Extract features and feature names for a match."""
        features = self.feature_extractor.extract_features(match)
        feature_names = self.feature_extractor.get_feature_names()
        return features, feature_names

    def _get_predictions(self, x: list) -> tuple[float, float, float]:
        """Get model predictions and calculate confidence."""
        probs = self.model.predict_proba(x)[0]

        if 1 in self.model.classes_:
            p1_idx = list(self.model.classes_).index(1)
            p1_prob = probs[p1_idx]
            p2_prob = 1.0 - p1_prob
        else:
            p1_prob = probs[0]
            p2_prob = probs[1]

        confidence = abs(p1_prob - 0.5) * 2
        return p1_prob, p2_prob, confidence

    def _build_context(self, match: TennisMatch) -> tuple[dict, dict, dict]:
        """Gather context from feature extractor."""
        h2h = self._get_h2h_context(match)
        surface_stats = self._get_surface_stats(match)
        form = self._get_form_context(match)
        return h2h, surface_stats, form

    def _fetch_real_time_odds(
        self, match: TennisMatch
    ) -> tuple[Optional[float], Optional[float], Optional[OddsSnapshot]]:
        """Fetch real-time odds if odds feed is configured."""
        real_time_odds: Optional[OddsSnapshot] = None
        p1_odds = match.p1_odds
        p2_odds = match.p2_odds

        if self.odds_feed and self.odds_feed.is_configured():
            try:
                import asyncio

                async def fetch_odds():
                    return await self.odds_feed.fetch_odds(
                        sport="tennis",
                        league=match.tournament_name or "unknown",
                        match_id=match.match_id,
                    )

                try:
                    asyncio.get_running_loop()
                    import concurrent.futures

                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, fetch_odds())
                        real_time_odds = future.result(timeout=10)
                except RuntimeError:
                    real_time_odds = asyncio.run(fetch_odds())

                if real_time_odds:
                    # Use real-time odds (more accurate for value bets)
                    p1_odds = real_time_odds.odds.home
                    p2_odds = real_time_odds.odds.away

            except Exception as e:
                logger.debug(f"Real-time odds fetch failed for {match.match_id}: {e}")

        return p1_odds, p2_odds, real_time_odds

    def _detect_sharp_money(
        self, match: TennisMatch, p1_odds: Optional[float], p2_odds: Optional[float]
    ) -> Optional[SharpMoneySignal]:
        """Detect sharp money signals."""
        sharp_signal: Optional[SharpMoneySignal] = None
        has_opening = hasattr(match, "opening_odds") and match.opening_odds

        if not (p1_odds and p2_odds and has_opening):
            return None

        try:
            # Would need odds history - simplified with opening vs current
            from datetime import timedelta

            opening = match.opening_odds  # Should be Odds object
            current_odds = type(
                "Odds", (), {"home": p1_odds, "draw": 1.0, "away": p2_odds}
            )()

            odds_history = [
                OddsSnapshot(
                    provider=OddsProvider.PINNACLE,
                    sport="tennis",
                    league=match.tournament_name or "unknown",
                    match_id=match.match_id,
                    odds=opening,
                    timestamp=(
                        match.match_date - timedelta(days=7)
                        if match.match_date
                        else datetime.utcnow()
                    ),
                ),
                OddsSnapshot(
                    provider=OddsProvider.PINNACLE,
                    sport="tennis",
                    league=match.tournament_name or "unknown",
                    match_id=match.match_id,
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
            logger.debug(f"Sharp money detection failed for {match.match_id}: {e}")

        return sharp_signal

    def _calculate_kelly(
        self,
        p1_prob: float,
        p2_prob: float,
        p1_odds: Optional[float],
        p2_odds: Optional[float],
        value_bets: list,
        confidence: float,
    ) -> list:
        """Calculate Kelly criterion sizing."""
        kelly_recommendations = []

        if not (p1_odds and p2_odds and value_bets):
            return kelly_recommendations

        try:
            kelly_results = self.kelly_sizer.calculate_tennis_kelly(
                p1_prob=p1_prob,
                p2_prob=p2_prob,
                p1_odds=p1_odds,
                p2_odds=p2_odds,
                bankroll=100.0,  # Standard bankroll
                confidence=confidence,
            )

            kelly_recs = self.kelly_sizer.generate_stake_recommendations
            kelly_recommendations = kelly_recs(kelly_results, 100.0, confidence)

        except Exception as e:
            logger.debug(f"Kelly sizing failed: {e}")

        return kelly_recommendations

    def _build_market_metadata(
        self,
        sharp_signal: Optional[SharpMoneySignal],
        kelly_recommendations: list,
        real_time_odds: Optional[OddsSnapshot],
    ) -> dict:
        """Build market metadata for the prediction."""
        return {
            "sharp_money": (
                {
                    "smart_money_side": (
                        sharp_signal.smart_money_side if sharp_signal else None
                    ),
                    "steam_score": sharp_signal.steam_score if sharp_signal else 0.0,
                    "reverse_line_movement": (
                        sharp_signal.reverse_line_movement if sharp_signal else False
                    ),
                }
                if sharp_signal
                else None
            ),
            "kelly": (
                {
                    "total_stake": sum(r.stake_units for r in kelly_recommendations),
                    "recommendations": [
                        {
                            "outcome": r.outcome,
                            "stake_units": r.stake_units,
                            "risk_level": r.risk_level,
                        }
                        for r in kelly_recommendations
                    ],
                }
                if kelly_recommendations
                else None
            ),
            "real_time_odds_provider": (
                real_time_odds.provider.value if real_time_odds else None
            ),
        }

    def _get_h2h_context(self, match: TennisMatch) -> dict:
        """Get head-to-head context."""
        fe = self.feature_extractor
        h2h = fe.get_h2h_features(match.p1_name, match.p2_name)
        return {
            "total_matches": h2h.get("h2h_total", 0),
            "p1_wins": int(h2h.get("h2h_p1_win_rate", 0.5) * h2h.get("h2h_total", 0)),
            "p2_wins": int(h2h.get("h2h_p2_win_rate", 0.5) * h2h.get("h2h_total", 0)),
        }

    def _get_surface_stats(self, match: TennisMatch) -> dict:
        """Get surface-specific win rates."""
        fe = self.feature_extractor
        return {
            "p1_surface_win_rate": fe._get_surface_win_rate(
                match.p1_name, match.surface, match.match_date
            ),
            "p2_surface_win_rate": fe._get_surface_win_rate(
                match.p2_name, match.surface, match.match_date
            ),
            "surface": match.surface,
        }

    def _get_form_context(self, match: TennisMatch) -> dict:
        """Get recent form (last 5 and 10 matches)."""
        fe = self.feature_extractor
        p1_5 = fe._get_rolling_stats(
            match.p1_name, window=5, before_date=match.match_date
        )
        p2_5 = fe._get_rolling_stats(
            match.p2_name, window=5, before_date=match.match_date
        )
        p1_10 = fe._get_rolling_stats(
            match.p1_name, window=10, before_date=match.match_date
        )
        p2_10 = fe._get_rolling_stats(
            match.p2_name, window=10, before_date=match.match_date
        )
        return {
            "p1_win_rate_5": p1_5["win_rate"],
            "p2_win_rate_5": p2_5["win_rate"],
            "p1_win_rate_10": p1_10["win_rate"],
            "p2_win_rate_10": p2_10["win_rate"],
            "p1_ace_rate": p1_10["ace_rate"],
            "p2_ace_rate": p2_10["ace_rate"],
            "p1_first_serve_pct": p1_10["first_serve_pct"],
            "p2_first_serve_pct": p2_10["first_serve_pct"],
        }

    def _calculate_value_bets(
        self,
        match: TennisMatch,
        p1_prob: float,
        p2_prob: float,
        p1_odds: Optional[float] = None,
        p2_odds: Optional[float] = None,
    ) -> list:
        """Calculate value bets by comparing model probability
        vs implied odds probability."""
        value_bets = []

        # Use provided odds (real-time) or fall back to match odds
        odds_p1 = p1_odds if p1_odds is not None else match.p1_odds
        odds_p2 = p2_odds if p2_odds is not None else match.p2_odds

        if odds_p1 and odds_p2:
            implied_p1 = 1.0 / odds_p1
            implied_p2 = 1.0 / odds_p2

            # Value = model probability - implied probability
            p1_value = p1_prob - implied_p1
            p2_value = p2_prob - implied_p2

            # Positive value = good bet
            if p1_value > 0.05:  # 5% edge threshold
                value_bets.append(
                    {
                        "player": match.p1_name,
                        "odds": odds_p1,
                        "implied_prob": round(implied_p1 * 100, 1),
                        "model_prob": round(p1_prob * 100, 1),
                        "edge": round(p1_value * 100, 1),
                        "type": "value",
                    }
                )
            if p2_value > 0.05:
                value_bets.append(
                    {
                        "player": match.p2_name,
                        "odds": odds_p2,
                        "implied_prob": round(implied_p2 * 100, 1),
                        "model_prob": round(p2_prob * 100, 1),
                        "edge": round(p2_value * 100, 1),
                        "type": "value",
                    }
                )

        return value_bets

    def _extract_key_factors(self, features: dict, match: TennisMatch) -> list:
        """Extract the most influential factors for the prediction."""
        factors = []

        factors.extend(self._get_rank_factor(features, match))
        factors.extend(self._get_surface_factor(features, match))
        factors.extend(self._get_form_factor(features, match))
        factors.extend(self._get_h2h_factor(features, match))
        factors.extend(self._get_serve_factor(features, match))

        return factors[:5]

    def _get_rank_factor(self, features: dict, match: TennisMatch) -> list:
        """Extract ranking advantage factor."""
        rank_diff = features.get("rank_diff", 0)
        if abs(rank_diff) > 3:
            better = match.p1_name if rank_diff < 0 else match.p2_name
            return [f"{better} tiene mejor ranking por {abs(rank_diff)} posiciones"]
        return []

    def _get_surface_factor(self, features: dict, match: TennisMatch) -> list:
        """Extract surface dominance factor."""
        factors = []
        p1_surface = features.get("p1_surface_win_rate", 0.5)
        p2_surface = features.get("p2_surface_win_rate", 0.5)
        if p1_surface > 0.7:
            factors.append(
                f"{match.p1_name} domina en {match.surface} "
                f"({p1_surface*100:.0f}% victorias)"
            )
        if p2_surface > 0.7:
            factors.append(
                f"{match.p2_name} domina en {match.surface} "
                f"({p2_surface*100:.0f}% victorias)"
            )
        return factors

    def _get_form_factor(self, features: dict, match: TennisMatch) -> list:
        """Extract recent form factor."""
        factors = []
        p1_form = features.get("p1_win_rate_10", 0.5)
        p2_form = features.get("p2_win_rate_10", 0.5)
        if p1_form > 0.8:
            factors.append(
                f"{match.p1_name} en racha ({p1_form*100:.0f}% en últimos 10)"
            )
        if p2_form > 0.8:
            factors.append(
                f"{match.p2_name} en racha ({p2_form*100:.0f}% en últimos 10)"
            )
        return factors

    def _get_h2h_factor(self, features: dict, match: TennisMatch) -> list:
        """Extract H2H dominance factor."""
        factors = []
        h2h_total = features.get("h2h_total", 0)
        if h2h_total >= 3:
            h2h_p1 = features.get("h2h_p1_win_rate", 0.5)
            if h2h_p1 > 0.7:
                factors.append(
                    f"{match.p1_name} domina el H2H "
                    f"({int(h2h_p1*h2h_total)}/{h2h_total})"
                )
            elif h2h_p1 < 0.3:
                factors.append(
                    f"{match.p2_name} domina el H2H "
                    f"({int((1-h2h_p1)*h2h_total)}/{h2h_total})"
                )
        return factors

    def _get_serve_factor(self, features: dict, match: TennisMatch) -> list:
        """Extract first serve advantage factor."""
        factors = []
        p1_serve = features.get("p1_first_serve_pct_10", 0)
        p2_serve = features.get("p2_first_serve_pct_10", 0)
        if p1_serve > 0.65:
            factors.append(
                f"{match.p1_name} tiene buen primer servicio ({p1_serve*100:.0f}%)"
            )
        if p2_serve > 0.65:
            factors.append(
                f"{match.p2_name} tiene buen primer servicio ({p2_serve*100:.0f}%)"
            )
        return factors

    def generate_tennis_markets(
        self, match: TennisMatch, p1_prob: float, p2_prob: float
    ) -> list:
        """Generate all tennis betting markets as suggested picks."""
        # Cast to native Python floats to avoid numpy serialization issues
        p1_prob = float(p1_prob)
        p2_prob = float(p2_prob)
        markets = []

        # 1. MATCH WINNER (Money Line)
        markets.extend(self._create_moneyline(match, p1_prob, p2_prob))

        # 2. SET HANDICAP (based on best_of and probability)
        markets.extend(self._create_set_handicap(match, p1_prob, p2_prob))

        # 3. TOTAL SETS OVER/UNDER (2.5 for best of 3, 3.5 for best of 5)
        markets.extend(self._create_sets_over_under(match, p1_prob, p2_prob))

        # 4. FIRST SET WINNER
        markets.extend(self._create_first_set_winner(match, p1_prob, p2_prob))

        # 5. CORRECT SCORE (set score)
        markets.extend(self._create_correct_score(match, p1_prob))

        # 6. TOTAL GAMES OVER/UNDER (estimated)
        markets.extend(self._create_games_over_under(match, p1_prob))

        # Sort by priority (recommended first, then by probability)
        markets.sort(key=lambda x: (-int(x["is_recommended"]), -x["probability"]))  # type: ignore[call-overload,operator]

        return markets

    def _create_moneyline(
        self, match: TennisMatch, p1_prob: float, p2_prob: float
    ) -> list:
        """Create match winner (moneyline) markets."""
        markets = []

        if p1_prob > p2_prob:
            markets.append(
                {
                    "market_type": "match_winner",
                    "market_label": f"Gana {match.p1_name}",
                    "probability": round(p1_prob, 3),
                    "confidence_level": self._get_confidence_level(p1_prob),
                    "reasoning": (
                        f"{match.p1_name} tiene {p1_prob*100:.1f}% "
                        f"de probabilidad de victoria"
                    ),
                    "risk_level": round((1 - p1_prob) * 10, 1),
                    "is_recommended": p1_prob > 0.6,
                    "priority_score": round(p1_prob * 100, 1),
                    "pick_code": "ML1",
                }
            )
        else:
            markets.append(
                {
                    "market_type": "match_winner",
                    "market_label": f"Gana {match.p2_name}",
                    "probability": round(p2_prob, 3),
                    "confidence_level": self._get_confidence_level(p2_prob),
                    "reasoning": (
                        f"{match.p2_name} tiene {p2_prob*100:.1f}% "
                        f"de probabilidad de victoria"
                    ),
                    "risk_level": round((1 - p2_prob) * 10, 1),
                    "is_recommended": p2_prob > 0.6,
                    "priority_score": round(p2_prob * 100, 1),
                    "pick_code": "ML2",
                }
            )
        return markets

    def _create_set_handicap(
        self, match: TennisMatch, p1_prob: float, p2_prob: float
    ) -> list:
        """Create set handicap markets."""
        markets = []
        p1_handicap_prob = self._estimate_handicap_prob(p1_prob, match.best_of)
        p2_handicap_prob = self._estimate_handicap_prob(p2_prob, match.best_of)

        if p1_prob > 0.55:
            markets.append(
                {
                    "market_type": "set_handicap",
                    "market_label": f"{match.p1_name} -1.5 sets",
                    "probability": round(p1_handicap_prob, 3),
                    "confidence_level": "high" if p1_handicap_prob > 0.5 else "medium",
                    "reasoning": (
                        f"{match.p1_name} ganaría por 2+ sets con "
                        f"probabilidad {p1_handicap_prob*100:.1f}%"
                    ),
                    "risk_level": round((1 - p1_handicap_prob) * 10, 1),
                    "is_recommended": p1_handicap_prob > 0.5,
                    "priority_score": round(p1_handicap_prob * 100, 1),
                    "pick_code": "SH1",
                }
            )
        if p2_prob > 0.55:
            markets.append(
                {
                    "market_type": "set_handicap",
                    "market_label": f"{match.p2_name} -1.5 sets",
                    "probability": round(p2_handicap_prob, 3),
                    "confidence_level": "high" if p2_handicap_prob > 0.5 else "medium",
                    "reasoning": (
                        f"{match.p2_name} ganaría por 2+ sets con "
                        f"probabilidad {p2_handicap_prob*100:.1f}%"
                    ),
                    "risk_level": round((1 - p2_handicap_prob) * 10, 1),
                    "is_recommended": p2_handicap_prob > 0.5,
                    "priority_score": round(p2_handicap_prob * 100, 1),
                    "pick_code": "SH2",
                }
            )
        return markets

    def _create_sets_over_under(
        self, match: TennisMatch, p1_prob: float, p2_prob: float
    ) -> list:
        """Create total sets over/under markets."""
        markets = []
        threshold = 3.5 if match.best_of == 5 else 2.5
        over_prob = self._estimate_sets_over_prob(p1_prob, p2_prob, threshold)
        under_prob = 1 - over_prob

        markets.append(
            {
                "market_type": "total_sets_over",
                "market_label": f"Más de {threshold} sets",
                "probability": round(over_prob, 3),
                "confidence_level": self._get_confidence_level(over_prob),
                "reasoning": (
                    f"Se esperan más de {threshold} sets con "
                    f"probabilidad {over_prob*100:.1f}%"
                ),
                "risk_level": round((1 - over_prob) * 10, 1),
                "is_recommended": over_prob > 0.55,
                "priority_score": round(over_prob * 100, 1),
                "pick_code": f"O{threshold}",
            }
        )
        markets.append(
            {
                "market_type": "total_sets_under",
                "market_label": f"Menos de {threshold} sets",
                "probability": round(under_prob, 3),
                "confidence_level": self._get_confidence_level(under_prob),
                "reasoning": (
                    f"Se esperan menos de {threshold} sets con "
                    f"probabilidad {under_prob*100:.1f}%"
                ),
                "risk_level": round((1 - under_prob) * 10, 1),
                "is_recommended": under_prob > 0.55,
                "priority_score": round(under_prob * 100, 1),
                "pick_code": f"U{threshold}",
            }
        )
        return markets

    def _create_first_set_winner(
        self, match: TennisMatch, p1_prob: float, p2_prob: float
    ) -> list:
        """Create first set winner markets."""
        markets = []
        # Slightly different from match winner - closer to 50/50
        p1_first_set = 0.5 + (p1_prob - 0.5) * 0.7  # Dampened
        p2_first_set = 1 - p1_first_set

        if p1_first_set > 0.55:
            markets.append(
                {
                    "market_type": "first_set_winner",
                    "market_label": f"{match.p1_name} gana primer set",
                    "probability": round(p1_first_set, 3),
                    "confidence_level": "medium",
                    "reasoning": (
                        f"{match.p1_name} tiene {p1_first_set*100:.1f}% "
                        f"de probabilidad de ganar el primer set"
                    ),
                    "risk_level": round((1 - p1_first_set) * 10, 1),
                    "is_recommended": p1_first_set > 0.6,
                    "priority_score": round(p1_first_set * 100, 1),
                    "pick_code": "FS1",
                }
            )
        if p2_first_set > 0.55:
            markets.append(
                {
                    "market_type": "first_set_winner",
                    "market_label": f"{match.p2_name} gana primer set",
                    "probability": round(p2_first_set, 3),
                    "confidence_level": "medium",
                    "reasoning": (
                        f"{match.p2_name} tiene {p2_first_set*100:.1f}% "
                        f"de probabilidad de ganar el primer set"
                    ),
                    "risk_level": round((1 - p2_first_set) * 10, 1),
                    "is_recommended": p2_first_set > 0.6,
                    "priority_score": round(p2_first_set * 100, 1),
                    "pick_code": "FS2",
                }
            )
        return markets

    def _create_correct_score(self, match: TennisMatch, p1_prob: float) -> list:
        """Create correct score markets."""
        markets = []
        best_of = match.best_of
        scores = self._estimate_set_scores(p1_prob, best_of)

        for score, prob in scores.items():
            if prob > 0.1:
                markets.append(
                    {
                        "market_type": "correct_score",
                        "market_label": f"Resultado final: {score}",
                        "probability": round(prob, 3),
                        "confidence_level": "low",
                        "reasoning": (
                            f"Probabilidad de resultado {score}: {prob*100:.1f}%"
                        ),
                        "risk_level": round((1 - prob) * 10, 1),
                        "is_recommended": prob > 0.25,
                        "priority_score": round(prob * 100, 1),
                        "pick_code": f"CS_{score.replace('-', '')}",
                    }
                )
        return markets

    def _create_games_over_under(self, match: TennisMatch, p1_prob: float) -> list:
        """Create total games over/under markets."""
        markets = []
        for threshold in [19.5, 21.5, 23.5]:
            if match.best_of == 3 and threshold <= 21.5:
                markets.append(self._create_game_market(match, p1_prob, threshold))
            elif match.best_of == 5 and threshold >= 21.5:
                markets.append(self._create_game_market(match, p1_prob, threshold))
        return markets

    def _create_game_market(
        self, match: TennisMatch, p1_prob: float, threshold: float
    ) -> dict:
        """Create a single total games over market."""
        over_prob = self._games_over_prob(p1_prob, threshold)
        reasoning = f"Estimación de más de {threshold} juegos: {over_prob*100:.1f}%"
        return {
            "market_type": "total_games_over",
            "market_label": f"Más de {threshold} juegos",
            "probability": round(over_prob, 3),
            "confidence_level": "medium",
            "reasoning": reasoning,
            "risk_level": round((1 - over_prob) * 10, 1),
            "is_recommended": over_prob > 0.55,
            "priority_score": round(over_prob * 100, 1),
            "pick_code": f"TG{int(threshold)}",
        }

    def _get_confidence_level(self, prob: float) -> str:
        """Get confidence level based on probability."""
        if prob > 0.6:
            return "high"
        elif prob > 0.5:
            return "medium"
        return "low"

    def _estimate_handicap_prob(self, win_prob: float, best_of: int) -> float:
        """Estimate probability of winning by 2+ sets."""
        if best_of == 5:
            # Best of 5: need to win 3-0 or 3-1
            p_sweep = win_prob**3
            p_3_1 = 3 * (win_prob**3) * (1 - win_prob)
            return min(p_sweep + p_3_1, 0.95)
        else:
            # Best of 3: need to win 2-0
            return win_prob**2

    def _estimate_sets_over_prob(self, p1: float, p2: float, threshold: float) -> float:
        """Estimate probability of total sets over threshold."""
        # Higher threshold = lower probability
        # threshold 2.5 for best of 3, 3.5 for best of 5
        closer_match = 1 - abs(p1 - p2)
        base_prob = 0.3 + closer_match * 0.4
        return min(base_prob, 0.9)

    def _estimate_set_scores(self, p1: float, best_of: int) -> dict:
        """Estimate set score probabilities."""
        if best_of == 5:
            return {
                "3-0": p1**3 + (1 - p1) ** 3,
                "3-1": 3 * p1**3 * (1 - p1) + 3 * (1 - p1) ** 3 * p1,
                "3-2": 6 * p1**3 * (1 - p1) ** 2 + 6 * (1 - p1) ** 3 * p1**2,
            }
        else:
            return {
                "2-0": p1**2 + (1 - p1) ** 2,
                "2-1": 2 * p1**2 * (1 - p1) + 2 * (1 - p1) ** 2 * p1,
            }

    def _estimate_total_games(self, p1: float, best_of: int) -> float:
        """Estimate total games in the match."""
        # Closer matches have more games
        closer = 1 - abs(p1 - 0.5) * 2
        if best_of == 5:
            return 22 + closer * 6  # 22-28 games
        else:
            return 18 + closer * 5  # 18-23 games

    def _games_over_prob(self, p1: float, threshold: float) -> float:
        """Estimate probability of total games over threshold."""
        closer = 1 - abs(p1 - 0.5) * 2
        base = 0.3 + closer * 0.4
        # Adjust based on threshold
        if threshold > 22:
            base -= 0.1
        elif threshold < 20:
            base += 0.1
        return max(0.1, min(base, 0.9))  # Top 5 factors
