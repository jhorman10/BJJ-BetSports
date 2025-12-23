"""
Learning Service Module

Domain service for continuous learning based on betting feedback.
Persists learning weights to JSON file for cross-restart learning.
"""

import json
import os
import logging
from datetime import datetime
from typing import Optional
from dataclasses import asdict

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
    
    def __init__(self, weights_path: Optional[str] = None):
        """
        Initialize learning service.
        
        Args:
            weights_path: Path to JSON file for persisting weights
        """
        self.weights_path = weights_path or self.DEFAULT_WEIGHTS_PATH
        self._learning_weights: Optional[LearningWeights] = None
    
    @property
    def learning_weights(self) -> LearningWeights:
        """Lazily load and return the learning weights."""
        if self._learning_weights is None:
            self._learning_weights = self._load_weights()
        return self._learning_weights
    
    def _load_weights(self) -> LearningWeights:
        """Load learning weights from JSON file."""
        if not os.path.exists(self.weights_path):
            logger.info(f"No weights file found at {self.weights_path}, starting fresh")
            return LearningWeights()
        
        try:
            with open(self.weights_path, 'r') as f:
                data = json.load(f)
            
            # Reconstruct MarketPerformance objects
            market_perfs = {}
            for market_type, perf_data in data.get("market_performances", {}).items():
                # Handle datetime field
                if "last_updated" in perf_data and isinstance(perf_data["last_updated"], str):
                    perf_data["last_updated"] = datetime.fromisoformat(perf_data["last_updated"])
                market_perfs[market_type] = MarketPerformance(**perf_data)
            
            # Handle datetime field for LearningWeights
            last_saved = data.get("last_saved")
            if last_saved and isinstance(last_saved, str):
                last_saved = datetime.fromisoformat(last_saved)
            else:
                last_saved = datetime.utcnow()
            
            return LearningWeights(
                market_performances=market_perfs,
                global_adjustments=data.get("global_adjustments", {}),
                version=data.get("version", "1.0"),
                last_saved=last_saved,
            )
        except Exception as e:
            logger.error(f"Failed to load weights: {e}, starting fresh")
            return LearningWeights()
    
    def _save_weights(self) -> None:
        """Save learning weights to JSON file."""
        try:
            # Convert to serializable dict
            data = {
                "market_performances": {},
                "global_adjustments": self.learning_weights.global_adjustments,
                "version": self.learning_weights.version,
                "last_saved": datetime.utcnow().isoformat(),
            }
            
            for market_type, perf in self.learning_weights.market_performances.items():
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
            
            with open(self.weights_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Saved learning weights to {self.weights_path}")
        except Exception as e:
            logger.error(f"Failed to save weights: {e}")
    
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
    
    def get_market_adjustment(self, market_type: str) -> float:
        """
        Get confidence adjustment for a market type.
        
        Args:
            market_type: Type of market
            
        Returns:
            Adjustment multiplier (0.5 - 1.3)
        """
        return self.learning_weights.get_market_adjustment(market_type)
    
    def get_market_stats(self, market_type: str) -> Optional[MarketPerformance]:
        """
        Get performance statistics for a market type.
        
        Args:
            market_type: Type of market
            
        Returns:
            MarketPerformance or None if no data
        """
        return self.learning_weights.market_performances.get(market_type)
    
    def get_all_stats(self) -> dict[str, MarketPerformance]:
        """Get all market performance statistics."""
        return self.learning_weights.market_performances
    
    def get_learning_weights(self) -> LearningWeights:
        """Get the current learning weights object."""
        return self.learning_weights
    
    def reset_weights(self) -> None:
        """Reset all learning weights to default."""
        self.learning_weights = LearningWeights()
        self._save_weights()
        logger.info("Reset all learning weights to default")
