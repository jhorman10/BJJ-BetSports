# mypy: ignore-errors
"""
Sharp Money Detection Module

Detects professional/smart money activity in betting markets:
- Steam moves (sudden line movements with volume)
- Reverse line movement (line moves against public %)
- Smart money side identification
- Line movement analysis
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from src.domain.value_objects.value_objects import Odds
from src.infrastructure.odds_feed import OddsProvider, OddsSnapshot

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SteamMove:
    """Represents a detected steam move."""

    outcome: str  # 'home', 'draw', 'away'
    movement_pct: float  # Percentage line movement
    volume: float  # Matched volume at time of move
    time_window_minutes: int  # Time window of the move
    timestamp: datetime
    provider: OddsProvider
    confidence: float  # 0-1 confidence in detection


@dataclass(frozen=True)
class SharpMoneySignal:
    """Complete sharp money analysis result."""

    smart_money_side: Optional[str]  # 'home', 'draw', 'away', or None
    steam_score: float  # 0-1 overall steam score
    reverse_line_movement: bool  # True if RLM detected
    steam_moves: list[SteamMove] = field(default_factory=list)
    line_movement_analysis: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0  # Overall confidence 0-1
    timestamp: datetime = field(default_factory=datetime.utcnow)


class SharpMoneyDetector:
    """
    Detects sharp/smart money activity in betting markets.

    Features:
    - Steam move detection (sudden odds shifts with volume)
    - Reverse line movement (line moves against public betting %)
    - Smart money side identification
    - Volume-weighted line movement analysis
    - Time-windowed movement scoring
    """

    # Thresholds for detection
    MIN_MOVEMENT_PCT = 0.01  # 1% minimum line movement
    MIN_VOLUME_THRESHOLD = 1000  # Minimum volume for steam consideration
    STEAM_TIME_WINDOW = 60  # Minutes to consider a move "steam"
    RLM_PUBLIC_THRESHOLD = 0.6  # Public % threshold for RLM
    MIN_STEAM_SCORE = 0.3  # Minimum steam score for signal

    def __init__(
        self,
        min_movement_pct: float = MIN_MOVEMENT_PCT,
        min_volume: float = MIN_VOLUME_THRESHOLD,
        steam_window_minutes: int = STEAM_TIME_WINDOW,
    ):
        self.min_movement_pct = min_movement_pct
        self.min_volume = min_volume
        self.steam_window_minutes = steam_window_minutes

    def analyze_line_movement(
        self,
        opening_odds: Odds,
        current_odds: Odds,
        volumes: Optional[dict[str, float]] = None,
        public_percentages: Optional[dict[str, float]] = None,
        odds_history: Optional[list[OddsSnapshot]] = None,
    ) -> SharpMoneySignal:
        """
        Comprehensive line movement analysis.

        Args:
            opening_odds: Opening odds for the match
            current_odds: Current odds
            volumes: Dict of outcome -> matched volume (from exchanges)
            public_percentages: Dict of outcome -> public betting % (0-1)
            odds_history: Full odds history for detailed analysis

        Returns:
            SharpMoneySignal with all detected signals
        """
        # Calculate basic line movements
        movements = self._calculate_movements(opening_odds, current_odds)

        # Detect steam moves
        steam_moves = []
        if odds_history:
            steam_moves = self._detect_steam_moves(odds_history)

        # Calculate steam score
        steam_score = self.calculate_steam_score(movements, volumes, steam_moves)

        # Detect reverse line movement
        rlm = False
        if public_percentages:
            rlm = self._detect_reverse_line_movement(movements, public_percentages)

        # Identify smart money side
        smart_side = self.identify_smart_money_side(
            odds_history=odds_history,
            public_percentages=public_percentages,
        )

        # Line movement analysis details
        movement_analysis = {
            "movements_pct": movements,
            "max_movement": max(movements.items(), key=lambda x: abs(x[1])),
            "total_movement": sum(abs(v) for v in movements.values()),
            "steam_move_count": len(steam_moves),
            "volumes": volumes or {},
            "public_percentages": public_percentages or {},
        }

        # Overall confidence
        confidence = self._calculate_confidence(
            steam_score, rlm, smart_side, steam_moves, movements
        )

        return SharpMoneySignal(
            smart_money_side=smart_side,
            steam_score=steam_score,
            reverse_line_movement=rlm,
            steam_moves=steam_moves,
            line_movement_analysis=movement_analysis,
            confidence=confidence,
        )

    def _calculate_movements(self, opening: Odds, current: Odds) -> dict[str, float]:
        """Calculate percentage movements for each outcome."""
        return {
            "home": (current.home - opening.home) / opening.home,
            "draw": (current.draw - opening.draw) / opening.draw,
            "away": (current.away - opening.away) / opening.away,
        }

    def calculate_steam_score(
        self,
        movement_pct: dict[str, float],
        volume_pct: Optional[dict[str, float]] = None,
        time_window_minutes: Optional[int] = None,
    ) -> float:
        """
        Calculate steam score (0-1) based on movement, volume, and time.

        Steam score factors:
        - Movement magnitude (bigger move = higher score)
        - Volume confirmation (high volume = higher score)
        - Speed of move (fast move = higher score)
        - Consistency across providers
        """
        if not movement_pct:
            return 0.0

        # Base score from movement magnitude
        max_movement = max(abs(v) for v in movement_pct.values())
        movement_score = min(max_movement * 20, 1.0)  # 5% move = 1.0

        # Volume confirmation
        volume_score = 0.0
        if volume_pct:
            total_vol = sum(volume_pct.values())
            if total_vol > 0:
                # Weight by volume on the moving side
                max_move_outcome = max(movement_pct, key=lambda k: abs(movement_pct[k]))
                vol_on_move = volume_pct.get(max_move_outcome, 0)
                volume_score = min(vol_on_move / (self.min_volume * 10), 1.0)

        # Time factor (faster moves = more steam-like)
        time_score = 1.0
        if time_window_minutes:
            # Moves within 30 min are most steam-like
            time_score = max(0.3, 1.0 - (time_window_minutes / 120))

        # Combined steam score (weighted)
        steam_score = movement_score * 0.5 + volume_score * 0.3 + time_score * 0.2

        return min(max(steam_score, 0.0), 1.0)

    def _detect_steam_moves(self, odds_history: list[OddsSnapshot]) -> list[SteamMove]:
        """Detect individual steam moves in odds history."""
        if len(odds_history) < 2:
            return []

        sorted_history = sorted(odds_history, key=lambda s: s.timestamp)
        steam_moves = []

        for i in range(1, len(sorted_history)):
            prev = sorted_history[i - 1]
            curr = sorted_history[i]
            time_diff = (curr.timestamp - prev.timestamp).total_seconds() / 60

            if time_diff > self.steam_window_minutes:
                continue

            moves = self._calculate_outcome_movements(prev, curr, time_diff)
            steam_moves.extend(moves)

        steam_moves.sort(key=lambda s: (s.confidence, s.movement_pct), reverse=True)
        return steam_moves

    def _calculate_outcome_movements(
        self, prev: OddsSnapshot, curr: OddsSnapshot, time_diff: float
    ) -> list[SteamMove]:
        """Calculate movements for each outcome and create SteamMove objects."""
        steam_moves = []
        for outcome in ["home", "draw", "away"]:
            prev_odds = getattr(prev.odds, outcome)
            curr_odds = getattr(curr.odds, outcome)

            if prev_odds <= 0:
                continue

            movement_pct = abs(curr_odds - prev_odds) / prev_odds
            if movement_pct < self.min_movement_pct:
                continue

            volume = curr.volume or 0
            confidence = self._calculate_steam_confidence(
                volume, time_diff, curr.provider
            )

            steam_moves.append(
                SteamMove(
                    outcome=outcome,
                    movement_pct=movement_pct,
                    volume=volume,
                    time_window_minutes=int(time_diff),
                    timestamp=curr.timestamp,
                    provider=curr.provider,
                    confidence=min(confidence, 1.0),
                )
            )
        return steam_moves

    def _calculate_steam_confidence(
        self, volume: float, time_diff: float, provider: OddsProvider
    ) -> float:
        """Calculate confidence for a steam move."""
        volume_confirmed = volume >= self.min_volume
        confidence = 0.5
        if volume_confirmed:
            confidence += 0.3
        if time_diff <= 15:
            confidence += 0.2
        if provider == OddsProvider.BETFAIR:
            confidence += 0.1
        elif provider == OddsProvider.PINNACLE:
            confidence += 0.05
        return confidence

    def _detect_reverse_line_movement(
        self,
        movements: dict[str, float],
        public_percentages: dict[str, float],
    ) -> bool:
        """
        Detect reverse line movement.

        RLM occurs when the line moves in the opposite direction
        of the public betting percentages.
        """
        if not public_percentages:
            return False

        # Find the outcome with highest public betting %
        public_favorite = max(public_percentages, key=public_percentages.get)
        public_pct = public_percentages[public_favorite]

        # Only consider RLM if public is heavily on one side (>60%)
        if public_pct < self.RLM_PUBLIC_THRESHOLD:
            return False

        # Check if line moved AGAINST the public favorite
        # (odds shortened for public favorite = line moved toward them)
        # (odds lengthened for public favorite = line moved against them = RLM)
        favorite_movement = movements.get(public_favorite, 0)

        # RLM: public bets heavily on X, but odds for X INCREASE (lengthen)
        # This means sharp money is on the other side
        is_rlm = favorite_movement > 0.005  # Odds lengthened by >0.5%

        if is_rlm:
            logger.info(
                f"Reverse Line Movement detected: Public {public_pct:.1%} on "
                f"{public_favorite}, but odds moved {favorite_movement:.2%} against"
            )

        return is_rlm

    def identify_smart_money_side(
        self,
        odds_history: list[OddsSnapshot],
        public_percentages: Optional[dict[str, float]] = None,
    ) -> Optional[str]:
        """
        Identify which side the smart money is on.

        Uses multiple signals:
        1. Steam moves (direction of biggest moves)
        2. Reverse line movement (opposite of public)
        3. Pinnacle/Betfair line movement (sharp books)
        4. Volume-weighted moves
        """
        if not odds_history:
            return None

        sorted_history = sorted(odds_history, key=lambda s: s.timestamp)
        opening = sorted_history[0].odds
        closing = sorted_history[-1].odds

        movements = self._calculate_movements(opening, closing)

        sharp_movements = self._calculate_sharp_book_movements(sorted_history, opening)
        volume_movements = self._calculate_volume_movements(sorted_history, opening)
        rlm_side = self._calculate_rlm_side(
            movements, sharp_movements, public_percentages
        )

        scores = self._combine_smart_money_signals(
            sharp_movements, volume_movements, rlm_side
        )

        smart_side = min(scores, key=scores.get)
        if scores[smart_side] < -0.1:
            return smart_side
        return None

    def _calculate_sharp_book_movements(
        self, sorted_history: list[OddsSnapshot], opening: Odds
    ) -> dict[str, float]:
        """Calculate average movements from sharp bookmakers."""
        sharp_books = [OddsProvider.PINNACLE, OddsProvider.BETFAIR]
        sharp_movements = {k: 0.0 for k in ["home", "draw", "away"]}
        sharp_count = 0

        for snapshot in sorted_history:
            if snapshot.provider in sharp_books:
                for outcome in ["home", "draw", "away"]:
                    prev = getattr(opening, outcome)
                    curr = getattr(snapshot.odds, outcome)
                    if prev > 0:
                        sharp_movements[outcome] += (curr - prev) / prev
                sharp_count += 1

        if sharp_count > 0:
            for k in sharp_movements:
                sharp_movements[k] /= sharp_count
        return sharp_movements

    def _calculate_volume_movements(
        self, sorted_history: list[OddsSnapshot], opening: Odds
    ) -> dict[str, float]:
        """Calculate volume-weighted movements from Betfair."""
        volume_movements = {k: 0.0 for k in ["home", "draw", "away"]}
        total_vol = 0.0

        betfair_snapshots = [
            s for s in sorted_history if s.provider == OddsProvider.BETFAIR
        ]
        if betfair_snapshots:
            for s in betfair_snapshots:
                vol = s.volume or 0
                total_vol += vol
                for outcome in ["home", "draw", "away"]:
                    prev = getattr(opening, outcome)
                    curr = getattr(s.odds, outcome)
                    if prev > 0 and vol > 0:
                        volume_movements[outcome] += ((curr - prev) / prev) * vol

            if total_vol > 0:
                for k in volume_movements:
                    volume_movements[k] /= total_vol
        return volume_movements

    def _calculate_rlm_side(
        self,
        movements: dict[str, float],
        sharp_movements: dict[str, float],
        public_percentages: Optional[dict[str, float]],
    ) -> Optional[str]:
        """Calculate RLM side if applicable."""
        if not public_percentages:
            return None

        public_fav = max(public_percentages, key=public_percentages.get)
        if public_percentages[public_fav] <= self.RLM_PUBLIC_THRESHOLD:
            return None

        fav_movement = movements.get(public_fav, 0)
        if fav_movement <= 0.005:
            return None

        other_sides = [s for s in ["home", "draw", "away"] if s != public_fav]
        return max(other_sides, key=lambda s: sharp_movements.get(s, 0))

    def _combine_smart_money_signals(
        self,
        sharp_movements: dict[str, float],
        volume_movements: dict[str, float],
        rlm_side: Optional[str],
    ) -> dict[str, float]:
        """Combine smart money signals with weights."""
        scores = {k: 0.0 for k in ["home", "draw", "away"]}

        # Weight 1: Sharp book movement (40%)
        max_sharp = max(abs(v) for v in sharp_movements.values())
        if max_sharp > 0:
            for k, v in sharp_movements.items():
                scores[k] -= (abs(v) / max_sharp) * 0.4 * (1 if v < 0 else -1)

        # Weight 2: Volume-weighted movement (30%)
        max_vol = max(abs(v) for v in volume_movements.values())
        if max_vol > 0:
            for k, v in volume_movements.items():
                scores[k] -= (abs(v) / max_vol) * 0.3 * (1 if v < 0 else -1)

        # Weight 3: RLM signal (30%)
        if rlm_side:
            scores[rlm_side] -= 0.3

        return scores

    def _calculate_confidence(
        self,
        steam_score: float,
        rlm: bool,
        smart_side: Optional[str],
        steam_moves: list[SteamMove],
        movements: dict[str, float],
    ) -> float:
        """Calculate overall confidence in sharp money detection."""
        confidence = 0.0

        # Steam score contribution (40%)
        confidence += steam_score * 0.4

        # RLM confirmation (20%)
        if rlm:
            confidence += 0.2

        # Smart side identified (20%)
        if smart_side:
            confidence += 0.2

        # Multiple confirming steam moves (10%)
        if len(steam_moves) >= 2:
            confidence += 0.1
        elif len(steam_moves) == 1:
            confidence += 0.05

        # Significant total movement (10%)
        total_movement = sum(abs(v) for v in movements.values())
        if total_movement > 0.05:  # >5% total movement
            confidence += 0.1

        return min(confidence, 1.0)

    def analyze_odds_series(self, odds_series: list[OddsSnapshot]) -> SharpMoneySignal:
        """
        Full analysis of an odds time series.

        Convenience method that extracts opening/closing odds and calls
        analyze_line_movement with full history.
        """
        if not odds_series:
            return SharpMoneySignal(
                smart_money_side=None,
                steam_score=0.0,
                reverse_line_movement=False,
            )

        sorted_series = sorted(odds_series, key=lambda s: s.timestamp)
        opening = sorted_series[0].odds
        closing = sorted_series[-1].odds

        # Aggregate volumes by outcome from Betfair
        volumes = {}
        for s in sorted_series:
            if s.provider == OddsProvider.BETFAIR and s.volume:
                # We'd need outcome-specific volume - simplified here
                pass

        return self.analyze_line_movement(
            opening_odds=opening,
            current_odds=closing,
            volumes=volumes,
            odds_history=sorted_series,
        )

    def get_movement_direction(self, opening: Odds, current: Odds) -> dict[str, str]:
        """
        Get human-readable movement direction for each outcome.

        Returns dict like:
        {'home': 'shortened', 'draw': 'lengthened', 'away': 'unchanged'}
        """
        directions = {}
        for outcome in ["home", "draw", "away"]:
            open_odds = getattr(opening, outcome)
            curr_odds = getattr(current, outcome)

            if curr_odds < open_odds * 0.995:
                directions[outcome] = "shortened"  # Odds dropped = money came in
            elif curr_odds > open_odds * 1.005:
                directions[outcome] = "lengthened"  # Odds rose = money went out
            else:
                directions[outcome] = "unchanged"

        return directions

    def calculate_closing_line_value(
        self,
        model_probabilities: dict[str, float],
        closing_odds: Odds,
    ) -> dict[str, float]:
        """
        Calculate Closing Line Value (CLV) for each outcome.

        CLV = (Model Probability * Closing Odds) - 1
        Positive CLV = model beat the closing line = value bet
        """
        clv = {}
        for outcome in ["home", "draw", "away"]:
            model_prob = model_probabilities.get(outcome, 0)
            odds = getattr(closing_odds, outcome)
            clv[outcome] = (model_prob * odds) - 1

        return clv
