import logging
import os
from typing import Any, Optional

import joblib
from src.domain.entities.tennis_match import TennisMatch
from src.domain.services.tennis_feature_extractor import TennisFeatureExtractor

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


class TennisPredictionService:
    """
    Service for predicting tennis match outcomes using a trained ML model.
    """

    MODEL_PATH = os.getenv("TENNIS_MODEL_PATH", "models/tennis_classifier.pkl")

    def __init__(self, feature_extractor: TennisFeatureExtractor):
        self.feature_extractor = feature_extractor
        self.model = self._load_model()

    def _load_model(self) -> Any:
        """Load the trained model from disk."""
        if os.path.exists(self.MODEL_PATH):
            try:
                return joblib.load(self.MODEL_PATH)
            except Exception as e:
                logger.error(f"Failed to load tennis model: {e}")
        else:
            logger.warning(f"Tennis model not found at {self.MODEL_PATH}")
        return None

    def predict(self, match: TennisMatch) -> Optional[TennisPrediction]:
        """
        Predict the outcome of a tennis match with full context.
        """
        if self.model is None:
            logger.error("Model not loaded, cannot predict.")
            return None

        try:
            # 1. Extract features
            features = self.feature_extractor.extract_features(match)
            feature_names = self.feature_extractor.get_feature_names()

            # Convert to array in the correct order
            X = [[features[f] for f in feature_names]]

            # 2. Predict probabilities
            probs = self.model.predict_proba(X)[0]

            if 1 in self.model.classes_:
                p1_idx = list(self.model.classes_).index(1)
                p1_prob = probs[p1_idx]
                p2_prob = 1.0 - p1_prob
            else:
                p1_prob = probs[0]
                p2_prob = probs[1]

            # 3. Calculate confidence
            confidence = abs(p1_prob - 0.5) * 2

            # 4. Gather context from feature extractor
            h2h = self._get_h2h_context(match)
            surface_stats = self._get_surface_stats(match)
            form = self._get_form_context(match)
            value_bets = self._calculate_value_bets(match, p1_prob, p2_prob)
            key_factors = self._extract_key_factors(features, match)

            return TennisPrediction(
                p1_win_prob=p1_prob,
                p2_win_prob=p2_prob,
                confidence=confidence,
                h2h=h2h,
                surface_stats=surface_stats,
                form=form,
                value_bets=value_bets,
                key_factors=key_factors,
            )
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            return None

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
        self, match: TennisMatch, p1_prob: float, p2_prob: float
    ) -> list:
        """Calculate value bets by comparing model probability vs implied odds probability."""
        value_bets = []

        if match.p1_odds and match.p2_odds:
            implied_p1 = 1.0 / match.p1_odds
            implied_p2 = 1.0 / match.p2_odds

            # Value = model probability - implied probability
            p1_value = p1_prob - implied_p1
            p2_value = p2_prob - implied_p2

            # Positive value = good bet
            if p1_value > 0.05:  # 5% edge threshold
                value_bets.append(
                    {
                        "player": match.p1_name,
                        "odds": match.p1_odds,
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
                        "odds": match.p2_odds,
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

        # Ranking advantage
        rank_diff = features.get("rank_diff", 0)
        if abs(rank_diff) > 3:
            better = match.p1_name if rank_diff < 0 else match.p2_name
            factors.append(
                f"{better} tiene mejor ranking por {abs(rank_diff)} posiciones"
            )

        # Surface dominance
        p1_surface = features.get("p1_surface_win_rate", 0.5)
        p2_surface = features.get("p2_surface_win_rate", 0.5)
        if p1_surface > 0.7:
            factors.append(
                f"{match.p1_name} domina en {match.surface} ({p1_surface*100:.0f}% victorias)"
            )
        if p2_surface > 0.7:
            factors.append(
                f"{match.p2_name} domina en {match.surface} ({p2_surface*100:.0f}% victorias)"
            )

        # Recent form
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

        # H2H dominance
        h2h_total = features.get("h2h_total", 0)
        if h2h_total >= 3:
            h2h_p1 = features.get("h2h_p1_win_rate", 0.5)
            if h2h_p1 > 0.7:
                factors.append(
                    f"{match.p1_name} domina el H2H ({int(h2h_p1*h2h_total)}/{h2h_total})"
                )
            elif h2h_p1 < 0.3:
                factors.append(
                    f"{match.p2_name} domina el H2H ({int((1-h2h_p1)*h2h_total)}/{h2h_total})"
                )

        # First serve advantage
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

        return factors[:5]

    def generate_tennis_markets(
        self, match: TennisMatch, p1_prob: float, p2_prob: float
    ) -> list:
        """Generate all tennis betting markets as suggested picks."""
        # Cast to native Python floats to avoid numpy serialization issues
        p1_prob = float(p1_prob)
        p2_prob = float(p2_prob)
        markets = []

        # 1. MATCH WINNER (Money Line)
        if p1_prob > p2_prob:
            markets.append(
                {
                    "market_type": "match_winner",
                    "market_label": f"Gana {match.p1_name}",
                    "probability": round(p1_prob, 3),
                    "confidence_level": (
                        "high"
                        if p1_prob > 0.65
                        else "medium" if p1_prob > 0.55 else "low"
                    ),
                    "reasoning": f"{match.p1_name} tiene {p1_prob*100:.1f}% de probabilidad de victoria",
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
                    "confidence_level": (
                        "high"
                        if p2_prob > 0.65
                        else "medium" if p2_prob > 0.55 else "low"
                    ),
                    "reasoning": f"{match.p2_name} tiene {p2_prob*100:.1f}% de probabilidad de victoria",
                    "risk_level": round((1 - p2_prob) * 10, 1),
                    "is_recommended": p2_prob > 0.6,
                    "priority_score": round(p2_prob * 100, 1),
                    "pick_code": "ML2",
                }
            )

        # 2. SET HANDICAP (based on best_of and probability)
        handicap = -1.5 if match.best_of == 5 else -1.5
        # Probability of winning by 2+ sets
        p1_handicap_prob = self._estimate_handicap_prob(p1_prob, match.best_of)
        p2_handicap_prob = self._estimate_handicap_prob(p2_prob, match.best_of)

        if p1_prob > 0.55:
            markets.append(
                {
                    "market_type": "set_handicap",
                    "market_label": f"{match.p1_name} -1.5 sets",
                    "probability": round(p1_handicap_prob, 3),
                    "confidence_level": "high" if p1_handicap_prob > 0.5 else "medium",
                    "reasoning": f"{match.p1_name} ganaría por 2+ sets con probabilidad {p1_handicap_prob*100:.1f}%",
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
                    "reasoning": f"{match.p2_name} ganaría por 2+ sets con probabilidad {p2_handicap_prob*100:.1f}%",
                    "risk_level": round((1 - p2_handicap_prob) * 10, 1),
                    "is_recommended": p2_handicap_prob > 0.5,
                    "priority_score": round(p2_handicap_prob * 100, 1),
                    "pick_code": "SH2",
                }
            )

        # 3. TOTAL SETS OVER/UNDER (2.5 for best of 3, 3.5 for best of 5)
        threshold = 3.5 if match.best_of == 5 else 2.5
        # Higher prob match = fewer sets likely
        over_prob = self._estimate_sets_over_prob(p1_prob, p2_prob, threshold)
        under_prob = 1 - over_prob

        markets.append(
            {
                "market_type": "total_sets_over",
                "market_label": f"Más de {threshold} sets",
                "probability": round(over_prob, 3),
                "confidence_level": (
                    "high"
                    if over_prob > 0.6
                    else "medium" if over_prob > 0.5 else "low"
                ),
                "reasoning": f"Se esperan más de {threshold} sets con probabilidad {over_prob*100:.1f}%",
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
                "confidence_level": (
                    "high"
                    if under_prob > 0.6
                    else "medium" if under_prob > 0.5 else "low"
                ),
                "reasoning": f"Se esperan menos de {threshold} sets con probabilidad {under_prob*100:.1f}%",
                "risk_level": round((1 - under_prob) * 10, 1),
                "is_recommended": under_prob > 0.55,
                "priority_score": round(under_prob * 100, 1),
                "pick_code": f"U{threshold}",
            }
        )

        # 4. FIRST SET WINNER
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
                    "reasoning": f"{match.p1_name} tiene {p1_first_set*100:.1f}% de probabilidad de ganar el primer set",
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
                    "reasoning": f"{match.p2_name} tiene {p2_first_set*100:.1f}% de probabilidad de ganar el primer set",
                    "risk_level": round((1 - p2_first_set) * 10, 1),
                    "is_recommended": p2_first_set > 0.6,
                    "priority_score": round(p2_first_set * 100, 1),
                    "pick_code": "FS2",
                }
            )

        # 5. CORRECT SCORE (set score)
        if match.best_of == 5:
            # 3-0, 3-1, 3-2
            scores = self._estimate_set_scores(p1_prob, 5)
            for score, prob in scores.items():
                if prob > 0.1:
                    markets.append(
                        {
                            "market_type": "correct_score",
                            "market_label": f"Resultado final: {score}",
                            "probability": round(prob, 3),
                            "confidence_level": "low",
                            "reasoning": f"Probabilidad de resultado {score}: {prob*100:.1f}%",
                            "risk_level": round((1 - prob) * 10, 1),
                            "is_recommended": prob > 0.25,
                            "priority_score": round(prob * 100, 1),
                            "pick_code": f"CS_{score.replace('-', '')}",
                        }
                    )
        else:
            # 2-0, 2-1
            scores = self._estimate_set_scores(p1_prob, 3)
            for score, prob in scores.items():
                if prob > 0.1:
                    markets.append(
                        {
                            "market_type": "correct_score",
                            "market_label": f"Resultado final: {score}",
                            "probability": round(prob, 3),
                            "confidence_level": "low",
                            "reasoning": f"Probabilidad de resultado {score}: {prob*100:.1f}%",
                            "risk_level": round((1 - prob) * 10, 1),
                            "is_recommended": prob > 0.25,
                            "priority_score": round(prob * 100, 1),
                            "pick_code": f"CS_{score.replace('-', '')}",
                        }
                    )

        # 6. TOTAL GAMES OVER/UNDER (estimated)
        total_games_est = self._estimate_total_games(p1_prob, match.best_of)
        for threshold in [19.5, 21.5, 23.5]:
            if match.best_of == 3 and threshold <= 21.5:
                over_prob = self._games_over_prob(p1_prob, threshold)
                markets.append(
                    {
                        "market_type": "total_games_over",
                        "market_label": f"Más de {threshold} juegos",
                        "probability": round(over_prob, 3),
                        "confidence_level": "medium",
                        "reasoning": f"Estimación de más de {threshold} juegos: {over_prob*100:.1f}%",
                        "risk_level": round((1 - over_prob) * 10, 1),
                        "is_recommended": over_prob > 0.55,
                        "priority_score": round(over_prob * 100, 1),
                        "pick_code": f"TG{int(threshold)}",
                    }
                )
            elif match.best_of == 5 and threshold >= 21.5:
                over_prob = self._games_over_prob(p1_prob, threshold)
                markets.append(
                    {
                        "market_type": "total_games_over",
                        "market_label": f"Más de {threshold} juegos",
                        "probability": round(over_prob, 3),
                        "confidence_level": "medium",
                        "reasoning": f"Estimación de más de {threshold} juegos: {over_prob*100:.1f}%",
                        "risk_level": round((1 - over_prob) * 10, 1),
                        "is_recommended": over_prob > 0.55,
                        "priority_score": round(over_prob * 100, 1),
                        "pick_code": f"TG{int(threshold)}",
                    }
                )

        # Sort by priority (recommended first, then by probability)
        markets.sort(key=lambda x: (-int(x["is_recommended"]), -x["probability"]))  # type: ignore[call-overload,operator]

        return markets

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
