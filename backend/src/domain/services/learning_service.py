"""
Learning Service Module

Domain service for continuous learning based on betting feedback.
Persists learning weights to JSON file for cross-restart learning.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, cast

from pytz import timezone
from src.core.paths import BACKEND_ROOT, PROJECT_ROOT
from src.domain.entities.betting_feedback import (
    BettingFeedback,
    LearningWeights,
    MarketPerformance,
)

logger = logging.getLogger(__name__)


class LearningService:
    """
    Service for managing continuous learning from betting feedback.

    Responsibilities:
    - Load/save learning weights to persistent storage
    - Process betting feedback and update weights
    - Provide market-specific confidence adjustments
    """

    DEFAULT_WEIGHTS_PATH = "learning_weights.json"
    MONGO_KEY = "learning_weights"

    def __init__(
        self,
        weights_path: Optional[str] = None,
        persistence_repo: Optional[Any] = None,
    ):
        """
        Initialize learning service.

        Args:
            weights_path: Path to JSON file for persisting weights (fallback/migration)
            persistence_repo: Repository for DB persistence
        """
        # Legacy locations
        self.legacy_paths = [
            PROJECT_ROOT / "learning_weights.json",
            BACKEND_ROOT / "learning_weights.json",
            BACKEND_ROOT / self.DEFAULT_WEIGHTS_PATH,
        ]
        self.repo = persistence_repo
        self._learning_weights: Optional[LearningWeights] = None
        self.active_legacy_path: Optional[Path] = None

    @property
    def learning_weights(self) -> LearningWeights:
        """Lazily load and return the learning weights."""
        if self._learning_weights is None:
            self._learning_weights = self._load_weights()
        return self._learning_weights

    def _load_weights(self) -> LearningWeights:
        """Load learning weights. Prioritizes Legacy Migration to ensure cleanup."""
        # 1. Check for legacy local files first to ensure migration/cleanup
        legacy_weights = None
        for path in self.legacy_paths:
            if path.exists():
                try:
                    logger.info(f"🔄 Legacy weights file found at {path}. Migrating...")
                    with open(path, "r") as f:
                        data = json.load(f)

                    legacy_weights = self._reconstruct_weights(data)

                    # Save to DB immediately to finalize migration
                    if self.repo:
                        self._save_to_db(legacy_weights)
                        # Cleanup local file
                        try:
                            path.unlink()
                            logger.info(
                                f"🗑️ Cleaned up legacy file after migration: {path}"
                            )
                        except Exception as del_err:
                            logger.warning(f"Failed to remove migrated file: {del_err}")

                    # If we found and processed a legacy file, we use it as truth
                    return legacy_weights
                except Exception as e:
                    logger.debug(f"Failed to process legacy weights from {path}: {e}")

        # 2. If no legacy file, try DB
        if self.repo:
            try:
                data = self.repo.get_app_state(self.MONGO_KEY)
                if data:
                    return self._reconstruct_weights(data)
            except Exception as e:
                logger.warning("Failed to read learning weights from repo: %s", e)

        logger.info("No weights found in DB or legacy files, starting fresh")
        return LearningWeights()

    def _reconstruct_weights(self, data: dict) -> LearningWeights:
        """Helper to reconstruct LearningWeights from dict."""
        # Reconstruct MarketPerformance objects
        market_perfs = {}
        for market_type, perf_data in data.get("market_performances", {}).items():
            # Handle datetime field
            if "last_updated" in perf_data and isinstance(
                perf_data["last_updated"], str
            ):
                perf_data["last_updated"] = datetime.fromisoformat(
                    perf_data["last_updated"]
                )
            market_perfs[market_type] = MarketPerformance(**perf_data)

        # Handle datetime field for LearningWeights
        last_saved = data.get("last_saved")
        if last_saved and isinstance(last_saved, str):
            last_saved = datetime.fromisoformat(last_saved)
        else:
            last_saved = datetime.now(timezone("America/Bogota"))

        return LearningWeights(
            market_performances=market_perfs,
            global_adjustments=data.get("global_adjustments", {}),
            version=data.get("version", "1.0"),
            last_saved=last_saved,
        )

    def _save_weights(self) -> None:
        """Save learning weights to DB (primary). No more local disk writes."""
        if self.repo:
            self._save_to_db(self.learning_weights)
        else:
            logger.warning("No persistence repository available, weights not saved.")

    def _save_to_db(self, weights: LearningWeights) -> None:
        """Save weights to MongoDB."""
        if not self.repo:
            return
        try:
            data = self._serialize_weights(weights)
            self.repo.save_app_state(self.MONGO_KEY, data)
            logger.debug("Saved learning weights to Database")
        except Exception as e:
            logger.error(f"Failed to save weights to DB: {e}")

    def _serialize_weights(self, weights: LearningWeights) -> Dict[str, Any]:
        """Helper to serialize LearningWeights to dict."""
        data: Dict[str, Any] = {
            "market_performances": {},
            "global_adjustments": weights.global_adjustments,
            "version": weights.version,
            "last_saved": datetime.now(timezone("America/Bogota")).isoformat(),
        }

        for market_type, perf in weights.market_performances.items():
            perf_dict = {
                "market_type": perf.market_type,
                "total_predictions": perf.total_predictions,
                "correct_predictions": perf.correct_predictions,
                "success_rate": perf.success_rate,
                "avg_odds": perf.avg_odds,
                "total_profit_loss": perf.total_profit_loss,
                "confidence_adjustment": perf.confidence_adjustment,
                "last_updated": perf.last_updated.isoformat(),
            }
            data["market_performances"][market_type] = perf_dict
        return data

    def register_feedback(self, feedback: BettingFeedback) -> None:
        """
        Register betting feedback and update learning weights.

        Args:
            feedback: Betting outcome feedback
        """
        self.learning_weights.update_with_feedback(feedback)
        self._save_weights()

        logger.info(
            f"Registered feedback for market {feedback.market_type}: "
            f"{'correct' if feedback.was_correct else 'incorrect'}"
        )

    def get_market_adjustment(self, market: str) -> float:
        """
        Get the current confidence adjustment for a specific market.

        Args:
            market: Market identifier (e.g., 'O2.5', 'Match Winner')

        Returns:
            Adjustment factor (0.0 to 1.0)
        """
        if not self._learning_weights:
            self._load_weights()

        if not self._learning_weights:
            return 1.0

        market_perf = self._learning_weights.market_performances.get(market)
        if not market_perf:
            return 1.0

        # Adjust based on accuracy (normalized)
        return float(market_perf.success_rate)

    def get_market_stats(self, market_type: str) -> Optional[MarketPerformance]:
        """
        Get performance statistics for a market type.

        Args:
            market_type: Type of market

        Returns:
            MarketPerformance or None if no data
        """
        return self.learning_weights.market_performances.get(market_type)

    def get_all_stats(self) -> Dict[str, MarketPerformance]:
        """Get all market performance statistics."""
        return cast(
            Dict[str, MarketPerformance],
            self.learning_weights.market_performances,
        )

    def get_learning_weights(self) -> LearningWeights:
        """Get the current learning weights as a domain entity."""
        return self.learning_weights

    def reset_weights(self) -> None:
        """Reset all learning weights to default."""
        self._learning_weights = LearningWeights()
        self._save_weights()
        logger.info("Reset all learning weights to default")
