"""
Continuous Learning Pipeline Module

Implements automated ML model retraining and monitoring:
- Daily incremental retraining with new data
- Drift detection using Population Stability Index (PSI)
- Model performance monitoring (rolling Brier score, log-loss)
- Auto-retrain triggers based on drift/performance thresholds
- Model versioning with metadata storage
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import joblib
import numpy as np
from sklearn.base import BaseEstimator
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import brier_score_loss, log_loss
from sklearn.model_selection import TimeSeriesSplit

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ModelMetadata:
    """Metadata for a trained model version."""

    model_id: str
    sport: str
    model_type: str  # 'classifier', 'regressor', etc.
    version: str
    created_at: datetime
    training_data_hash: str
    training_samples: int
    features: list[str]
    hyperparameters: dict[str, Any]
    metrics: dict[str, float]  # brier, log_loss, accuracy, etc.
    drift_baseline: Optional[dict[str, float]] = None  # Feature distributions for PSI
    parent_model_id: Optional[str] = None
    is_active: bool = False
    notes: str = ""


@dataclass(frozen=True)
class DriftReport:
    """Population Stability Index (PSI) drift report."""

    feature_psi: dict[str, float]
    overall_psi: float
    drift_detected: bool
    psi_threshold: float
    features_drifted: list[str]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    reference_period: str = ""
    current_period: str = ""


@dataclass(frozen=True)
class PerformanceReport:
    """Model performance monitoring report."""

    brier_score: float
    log_loss: float
    accuracy: float
    rolling_brier: list[float]
    rolling_log_loss: list[float]
    performance_drop: float  # Compared to baseline
    threshold_exceeded: bool
    timestamp: datetime = field(default_factory=datetime.utcnow)
    sample_count: int = 0


@dataclass(frozen=True)
class RetrainDecision:
    """Decision on whether to retrain."""

    should_retrain: bool
    reason: str
    drift_report: Optional[DriftReport] = None
    performance_report: Optional[PerformanceReport] = None
    urgency: str = "low"  # low, medium, high, critical


class ContinuousLearningPipeline:
    """
    Automated continuous learning pipeline for ML models.

    Features:
    - Incremental daily retraining
    - Population Stability Index (PSI) drift detection
    - Rolling performance monitoring (Brier, log-loss)
    - Automated retrain triggers
    - Model versioning with full metadata
    - A/B testing support for new models
    """

    def __init__(
        self,
        models_dir: str = "models",
        psi_threshold: float = 0.2,
        performance_drop_threshold: float = 0.05,
        min_samples_for_retrain: int = 100,
        max_model_versions: int = 10,
    ):
        """
        Initialize the continuous learning pipeline.

        Args:
            models_dir: Directory to store model versions
            psi_threshold: PSI threshold for drift detection (0.1-0.25 typical)
            performance_drop_threshold: Max performance drop before retrain
            min_samples_for_retrain: Minimum new samples to trigger retrain
            max_model_versions: Maximum model versions to keep
        """
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)

        self.psi_threshold = psi_threshold
        self.performance_drop_threshold = performance_drop_threshold
        self.min_samples_for_retrain = min_samples_for_retrain
        self.max_model_versions = max_model_versions

        # Model registry
        self._model_registry: dict[str, list[ModelMetadata]] = {}
        self._active_models: dict[str, ModelMetadata] = {}

        # Load existing registry
        self._load_registry()

    def _load_registry(self) -> None:
        """Load model registry from disk."""
        registry_path = self.models_dir / "model_registry.json"
        if registry_path.exists():
            try:
                with open(registry_path) as f:
                    data = json.load(f)
                for sport, models in data.items():
                    self._model_registry[sport] = [
                        ModelMetadata(
                            model_id=m["model_id"],
                            sport=m["sport"],
                            model_type=m["model_type"],
                            version=m["version"],
                            created_at=datetime.fromisoformat(m["created_at"]),
                            training_data_hash=m["training_data_hash"],
                            training_samples=m["training_samples"],
                            features=m["features"],
                            hyperparameters=m["hyperparameters"],
                            metrics=m["metrics"],
                            drift_baseline=m.get("drift_baseline"),
                            parent_model_id=m.get("parent_model_id"),
                            is_active=m.get("is_active", False),
                            notes=m.get("notes", ""),
                        )
                        for m in models
                    ]
                    # Find active model
                    for m in self._model_registry[sport]:
                        if m.is_active:
                            self._active_models[sport] = m
                            break
            except Exception as e:
                logger.warning(f"Failed to load model registry: {e}")

    def _save_registry(self) -> None:
        """Save model registry to disk."""
        registry_path = self.models_dir / "model_registry.json"
        data = {}
        for sport, models in self._model_registry.items():
            data[sport] = [
                {
                    "model_id": m.model_id,
                    "sport": m.sport,
                    "model_type": m.model_type,
                    "version": m.version,
                    "created_at": m.created_at.isoformat(),
                    "training_data_hash": m.training_data_hash,
                    "training_samples": m.training_samples,
                    "features": m.features,
                    "hyperparameters": m.hyperparameters,
                    "metrics": m.metrics,
                    "drift_baseline": m.drift_baseline,
                    "parent_model_id": m.parent_model_id,
                    "is_active": m.is_active,
                    "notes": m.notes,
                }
                for m in models
            ]
        try:
            with open(registry_path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save model registry: {e}")

    def _compute_data_hash(self, x: np.ndarray, y: np.ndarray) -> str:
        """Compute hash of training data for versioning."""
        # Use deterministic sampling for reproducibility
        sample_size = min(1000, len(x))
        # Use fixed seed based on data shape for deterministic but varied sampling
        rng = np.random.default_rng(seed=hash((x.shape, y.shape)) % (2**32))
        indices = rng.choice(len(x), sample_size, replace=False)
        x_sample = x[indices]
        y_sample = y[indices]

        # Hash the data
        hasher = hashlib.md5()
        hasher.update(x_sample.tobytes())
        hasher.update(y_sample.tobytes())
        return hasher.hexdigest()[:16]

    def _compute_feature_distributions(
        self, x: np.ndarray, feature_names: list[str]
    ) -> dict[str, np.ndarray]:
        """Compute feature distributions for PSI baseline."""
        distributions = {}
        for i, name in enumerate(feature_names):
            if i < x.shape[1]:
                # Use histogram bins
                hist, bins = np.histogram(x[:, i], bins=10, density=True)
                distributions[name] = {
                    "hist": hist.tolist(),
                    "bins": bins.tolist(),
                    "mean": float(np.mean(x[:, i])),
                    "std": float(np.std(x[:, i])),
                }
        return distributions

    def _calculate_psi(
        self,
        reference_dist: dict[str, Any],
        current_dist: dict[str, Any],
    ) -> float:
        """
        Calculate Population Stability Index (PSI) for a single feature.

        PSI = Σ (actual% - expected%) * ln(actual% / expected%)
        """
        ref_hist = np.array(reference_dist["hist"])
        curr_hist = np.array(current_dist["hist"])

        # Avoid division by zero
        ref_hist = np.where(ref_hist == 0, 0.0001, ref_hist)
        curr_hist = np.where(curr_hist == 0, 0.0001, curr_hist)

        # Normalize to percentages
        ref_pct = ref_hist / ref_hist.sum()
        curr_pct = curr_hist / curr_hist.sum()

        # PSI formula
        psi = np.sum((curr_pct - ref_pct) * np.log(curr_pct / ref_pct))
        return float(psi)

    def drift_detection(
        self,
        current_features: np.ndarray,
        reference_features: np.ndarray,
        feature_names: list[str],
        reference_period: str = "training",
        current_period: str = "current",
    ) -> DriftReport:
        """
        Detect feature drift using Population Stability Index (PSI).

        PSI Interpretation:
        - PSI < 0.1: No significant drift
        - 0.1 <= PSI < 0.2: Moderate drift (monitor)
        - PSI >= 0.2: Significant drift (retrain recommended)

        Args:
            current_features: Current feature matrix (n_samples, n_features)
            reference_features: Reference feature matrix (training data)
            feature_names: List of feature names
            reference_period: Description of reference period
            current_period: Description of current period

        Returns:
            DriftReport with per-feature and overall PSI
        """
        feature_psi = {}
        features_drifted = []

        for i, name in enumerate(feature_names):
            if i >= current_features.shape[1] or i >= reference_features.shape[1]:
                continue

            # Compute distributions
            ref_hist, bins = np.histogram(
                reference_features[:, i], bins=10, density=True
            )
            curr_hist, _ = np.histogram(
                current_features[:, i], bins=bins, density=True
            )

            # Avoid zeros
            ref_hist = np.where(ref_hist == 0, 0.0001, ref_hist)
            curr_hist = np.where(curr_hist == 0, 0.0001, curr_hist)

            ref_pct = ref_hist / ref_hist.sum()
            curr_pct = curr_hist / curr_hist.sum()

            psi = np.sum((curr_pct - ref_pct) * np.log(curr_pct / ref_pct))
            feature_psi[name] = float(psi)

            if psi >= self.psi_threshold:
                features_drifted.append(name)

        overall_psi = float(np.mean(list(feature_psi.values()))) if feature_psi else 0.0
        drift_detected = overall_psi >= self.psi_threshold or len(features_drifted) > 0

        return DriftReport(
            feature_psi=feature_psi,
            overall_psi=overall_psi,
            drift_detected=drift_detected,
            psi_threshold=self.psi_threshold,
            features_drifted=features_drifted,
            reference_period=reference_period,
            current_period=current_period,
        )

    def model_performance_monitoring(
        self,
        predictions: np.ndarray,
        outcomes: np.ndarray,
        baseline_brier: Optional[float] = None,
        baseline_logloss: Optional[float] = None,
        window_size: int = 100,
    ) -> PerformanceReport:
        """
        Monitor model performance with rolling metrics.

        Args:
            predictions: Predicted probabilities (n_samples, n_classes) or (n_samples,)
            outcomes: Actual outcomes (0/1 for binary, class indices for multiclass)
            baseline_brier: Baseline Brier score for comparison
            baseline_logloss: Baseline log-loss for comparison
            window_size: Rolling window size

        Returns:
            PerformanceReport with current and rolling metrics
        """
        # Ensure predictions are probabilities
        if predictions.ndim == 1:
            # Binary case: predictions are P(class=1)
            y_pred = predictions
            y_true = outcomes
            n_classes = 2
        else:
            # Multiclass
            y_true = outcomes
            n_classes = predictions.shape[1]
            y_pred = predictions[np.arange(len(outcomes)), outcomes]

        # Current metrics
        # For multiclass, compute Brier score as mean squared error
        # between predictions and one-hot encoded labels
        if n_classes == 2:
            brier = brier_score_loss(y_true, y_pred)
        else:
            # Multiclass Brier: mean squared error of probability vectors
            y_onehot = np.eye(n_classes)[y_true]
            brier = np.mean(np.sum((predictions - y_onehot) ** 2, axis=1))

        ll = log_loss(
            y_true,
            np.clip(
                predictions if n_classes > 2 else y_pred,
                1e-15,
                1 - 1e-15,
            ),
        )
        accuracy = np.mean(
            (y_pred > 0.5) == y_true
            if n_classes == 2
            else np.argmax(predictions, axis=1) == outcomes
        )

        # Rolling metrics
        rolling_brier = []
        rolling_log_loss = []

        for i in range(window_size, len(y_pred) + 1, window_size):
            start = max(0, i - window_size)
            end = i
            if n_classes == 2:
                rb = brier_score_loss(y_true[start:end], y_pred[start:end])
            else:
                y_onehot_roll = np.eye(n_classes)[y_true[start:end]]
                rb = np.mean(
                    np.sum(
                        (predictions[start:end] - y_onehot_roll) ** 2,
                        axis=1,
                    )
                )

            rl = log_loss(
                y_true[start:end],
                np.clip(
                    predictions[start:end] if n_classes > 2 else y_pred[start:end],
                    1e-15,
                    1 - 1e-15,
                ),
            )
            rolling_brier.append(rb)
            rolling_log_loss.append(rl)

        # Performance drop vs baseline
        performance_drop = 0.0
        if baseline_brier is not None:
            performance_drop = max(0, brier - baseline_brier)

        threshold_exceeded = performance_drop >= self.performance_drop_threshold

        return PerformanceReport(
            brier_score=brier,
            log_loss=ll,
            accuracy=accuracy,
            rolling_brier=rolling_brier,
            rolling_log_loss=rolling_log_loss,
            performance_drop=performance_drop,
            threshold_exceeded=threshold_exceeded,
            sample_count=len(y_true),
        )

    def daily_retrain(
        self,
        sport: str,
        new_x: np.ndarray,
        new_y: np.ndarray,
        feature_names: list[str],
        model_class: type = RandomForestClassifier,
        model_params: Optional[dict[str, Any]] = None,
        calibrate: bool = True,
    ) -> Optional[ModelMetadata]:
        """
        Perform daily incremental retraining.

        Args:
            sport: Sport identifier
            new_x: New feature data
            new_y: New labels
            feature_names: Feature names
            model_class: Model class to use
            model_params: Model hyperparameters
            calibrate: Whether to calibrate probabilities

        Returns:
            ModelMetadata for new model version, or None if skipped
        """
        if not self._has_sufficient_data(new_x, sport):
            return None

        active_model = self._active_models.get(sport)
        parent_id = active_model.model_id if active_model else None

        x_train = new_x
        y_train = new_y

        model, params = self._train_model(
            x_train, y_train, model_class, model_params, calibrate
        )
        brier, ll, accuracy = self._evaluate_model(model, x_train, y_train)

        metadata = self._create_model_metadata(
            sport, model_class, x_train, y_train, feature_names,
            brier, ll, accuracy, parent_id, params
        )

        # Save model
        model_path = self.models_dir / f"{metadata.model_id}.joblib"
        joblib.dump(model, model_path)

        # Update registry with new active model
        self._update_registry(sport, metadata)

        logger.info(
            f"Retrained {sport} model: {metadata.model_id} "
            f"(Brier={metadata.metrics['brier_score']:.4f}, Acc={accuracy:.4f})"
        )
        return metadata

    def _has_sufficient_data(self, new_x: np.ndarray, sport: str) -> bool:
        """Check if there's enough data for retraining."""
        if len(new_x) >= self.min_samples_for_retrain:
            return True
        logger.info(
            "Insufficient new data for "
            f"{sport}: {len(new_x)} < {self.min_samples_for_retrain}"
        )
        return False

    def _train_model(
        self,
        x_train: np.ndarray,
        y_train: np.ndarray,
        model_class: type,
        model_params: Optional[dict[str, Any]],
        calibrate: bool,
    ) -> tuple[BaseEstimator, dict[str, Any]]:
        """Train a new model with optional calibration."""
        params = model_params or {
            "n_estimators": 200,
            "max_depth": 10,
            "min_samples_split": 10,
            "min_samples_leaf": 5,
            "random_state": 42,
            "n_jobs": -1,
        }

        base_model = model_class(**params)
        base_model.fit(x_train, y_train)

        if calibrate:
            tscv = TimeSeriesSplit(n_splits=3)
            model = CalibratedClassifierCV(base_model, method="isotonic", cv=tscv)
            model.fit(x_train, y_train)
        else:
            model = base_model
        return model, params

    def _evaluate_model(
        self, model: BaseEstimator, x_train: np.ndarray, y_train: np.ndarray
    ) -> tuple[float, float, float]:
        """Evaluate model on training data."""
        train_preds = model.predict_proba(x_train)
        if train_preds.ndim > 1 and train_preds.shape[1] > 1:
            train_pred_probs = train_preds[np.arange(len(y_train)), y_train]
        else:
            train_pred_probs = train_preds

        brier = brier_score_loss(y_train, train_pred_probs)
        ll = log_loss(y_train, np.clip(train_pred_probs, 1e-15, 1 - 1e-15))
        accuracy = np.mean(model.predict(x_train) == y_train)
        return brier, ll, accuracy

    def _create_model_metadata(
        self,
        sport: str,
        model_class: type,
        x_train: np.ndarray,
        y_train: np.ndarray,
        feature_names: list[str],
        brier: float,
        ll: float,
        accuracy: float,
        parent_id: Optional[str],
        params: dict[str, Any],
    ) -> ModelMetadata:
        """Create model metadata."""
        data_hash = self._compute_data_hash(x_train, y_train)
        version = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        model_id = f"{sport}_{version}"

        counter = 0
        original_model_id = model_id
        while any(
            m.model_id == model_id
            for m in self._model_registry.get(sport, [])
        ):
            counter += 1
            model_id = f"{original_model_id}_{counter}"

        drift_baseline = self._compute_feature_distributions(x_train, feature_names)

        return ModelMetadata(
            model_id=model_id,
            sport=sport,
            model_type=model_class.__name__,
            version=version,
            created_at=datetime.utcnow(),
            training_data_hash=data_hash,
            training_samples=len(x_train),
            features=feature_names,
            hyperparameters=params,
            metrics={
                "brier_score": brier,
                "log_loss": ll,
                "accuracy": accuracy,
            },
            drift_baseline=drift_baseline,
            parent_model_id=parent_id,
            is_active=True,
            notes=f"Daily retrain with {len(x_train)} new samples",
        )

    def _update_registry(self, sport: str, metadata: ModelMetadata) -> None:
        """Update model registry with new active model."""
        if sport not in self._model_registry:
            self._model_registry[sport] = []

        new_registry = []
        for m in self._model_registry[sport]:
            if m.is_active:
                new_registry.append(
                    ModelMetadata(
                        model_id=m.model_id,
                        sport=m.sport,
                        model_type=m.model_type,
                        version=m.version,
                        created_at=m.created_at,
                        training_data_hash=m.training_data_hash,
                        training_samples=m.training_samples,
                        features=m.features,
                        hyperparameters=m.hyperparameters,
                        metrics=m.metrics,
                        drift_baseline=m.drift_baseline,
                        parent_model_id=m.parent_model_id,
                        is_active=False,
                        notes=m.notes,
                    )
                )
            else:
                new_registry.append(m)

        new_registry.append(metadata)

        # Trim old versions
        if len(new_registry) > self.max_model_versions:
            # Keep active + most recent inactive
            active = [m for m in new_registry if m.is_active]
            inactive = [m for m in new_registry if not m.is_active]
            inactive.sort(key=lambda m: m.created_at, reverse=True)
            new_registry = active + inactive[: self.max_model_versions - 1]

        self._model_registry[sport] = new_registry
        self._active_models[sport] = metadata
        self._save_registry()

        logger.info(
            f"Retrained {sport} model: {metadata.model_id} "
            f"(Brier={metadata.metrics['brier_score']:.4f}, "
            f"Acc={metadata.metrics['accuracy']:.4f})"
        )
        return metadata

    def auto_retrain_trigger(
        self,
        sport: str,
        current_x: np.ndarray,
        current_y: np.ndarray,
        feature_names: list[str],
        predictions: Optional[np.ndarray] = None,
        outcomes: Optional[np.ndarray] = None,
    ) -> RetrainDecision:
        """
        Check if auto-retrain should be triggered.

        Checks:
        1. Feature drift (PSI)
        2. Performance degradation
        3. Minimum new samples

        Args:
            sport: Sport identifier
            current_x: Current feature data
            current_y: Current labels
            feature_names: Feature names
            predictions: Recent model predictions (for performance)
            outcomes: Recent actual outcomes (for performance)

        Returns:
            RetrainDecision with recommendation
        """
        active_model = self._active_models.get(sport)
        if not active_model:
            return RetrainDecision(
                should_retrain=True,
                reason="No active model found",
                urgency="high",
            )

        # Check 1: Drift detection
        if active_model.drift_baseline:
            # Reconstruct reference distributions from baseline
            ref_dists = active_model.drift_baseline
            # For PSI, we need reference feature arrays -
            # approximate from baseline stats
            # Simplified: use current model's training data hash to load reference
            # In practice, would store reference samples
            drift_report = self._check_drift_from_baseline(
                current_x, ref_dists, feature_names
            )

            if drift_report.drift_detected:
                return RetrainDecision(
                    should_retrain=True,
                    reason=(
                        f"Feature drift detected "
                        f"(PSI={drift_report.overall_psi:.3f})"
                    ),
                    drift_report=drift_report,
                    urgency=(
                        "high" if drift_report.overall_psi > 0.3 else "medium"
                    ),
                )

        # Check 2: Performance degradation
        if predictions is not None and outcomes is not None:
            baseline_brier = active_model.metrics.get("brier_score")
            baseline_ll = active_model.metrics.get("log_loss")

            perf_report = self.model_performance_monitoring(
                predictions, outcomes, baseline_brier, baseline_ll
            )

            if perf_report.threshold_exceeded:
                return RetrainDecision(
                    should_retrain=True,
                    reason=(
                        "Performance drop: Brier increased by "
                        f"{perf_report.performance_drop:.4f}"
                    ),
                    performance_report=perf_report,
                    urgency="high",
                )

        # Check 3: Minimum new samples
        # Would need to track new samples since last train
        # For now, check if enough time has passed
        days_since_train = (datetime.utcnow() - active_model.created_at).days
        if days_since_train >= 7:  # Weekly retrain at minimum
            return RetrainDecision(
                should_retrain=True,
                reason=f"Scheduled weekly retrain ({days_since_train} days since last)",
                urgency="low",
            )

        return RetrainDecision(
            should_retrain=False,
            reason="No retrain triggers activated",
            urgency="low",
        )

    def _check_drift_from_baseline(
        self,
        current_x: np.ndarray,
        baseline_dists: dict[str, Any],
        feature_names: list[str],
    ) -> DriftReport:
        """Check drift using stored baseline distributions."""
        feature_psi = {}
        features_drifted = []

        for i, name in enumerate(feature_names):
            if i >= current_x.shape[1] or name not in baseline_dists:
                continue

            baseline = baseline_dists[name]
            ref_hist = np.array(baseline["hist"])
            bins = np.array(baseline["bins"])

            curr_hist, _ = np.histogram(current_x[:, i], bins=bins, density=True)

            ref_hist = np.where(ref_hist == 0, 0.0001, ref_hist)
            curr_hist = np.where(curr_hist == 0, 0.0001, curr_hist)

            ref_pct = ref_hist / ref_hist.sum()
            curr_pct = curr_hist / curr_hist.sum()

            psi = np.sum((curr_pct - ref_pct) * np.log(curr_pct / ref_pct))
            feature_psi[name] = float(psi)

            if psi >= self.psi_threshold:
                features_drifted.append(name)

        overall_psi = float(np.mean(list(feature_psi.values()))) if feature_psi else 0.0

        return DriftReport(
            feature_psi=feature_psi,
            overall_psi=overall_psi,
            drift_detected=overall_psi >= self.psi_threshold,
            psi_threshold=self.psi_threshold,
            features_drifted=features_drifted,
        )

    def load_active_model(self, sport: str) -> Optional[BaseEstimator]:
        """Load the currently active model for a sport."""
        active = self._active_models.get(sport)
        if not active:
            return None

        model_path = self.models_dir / f"{active.model_id}.joblib"
        if not model_path.exists():
            logger.error(f"Model file not found: {model_path}")
            return None

        return joblib.load(model_path)

    def load_model(self, model_id: str) -> Optional[BaseEstimator]:
        """Load a specific model version by ID."""
        model_path = self.models_dir / f"{model_id}.joblib"
        if not model_path.exists():
            return None
        return joblib.load(model_path)

    def get_model_metadata(
        self, sport: str, model_id: Optional[str] = None
    ) -> Optional[ModelMetadata]:
        """Get metadata for a model."""
        if model_id:
            for sport_models in self._model_registry.values():
                for m in sport_models:
                    if m.model_id == model_id:
                        return m
            return None

        return self._active_models.get(sport)

    def list_model_versions(self, sport: str) -> list[ModelMetadata]:
        """List all model versions for a sport."""
        return self._model_registry.get(sport, [])

    def set_active_model(self, sport: str, model_id: str) -> bool:
        """Set a specific model version as active."""
        if sport not in self._model_registry:
            return False

        for m in self._model_registry[sport]:
            if m.model_id == model_id:
                # Recreate with is_active=True
                new_registry = []
                for m2 in self._model_registry[sport]:
                    if m2.model_id == model_id:
                        new_registry.append(
                            ModelMetadata(
                                model_id=m2.model_id,
                                sport=m2.sport,
                                model_type=m2.model_type,
                                version=m2.version,
                                created_at=m2.created_at,
                                training_data_hash=m2.training_data_hash,
                                training_samples=m2.training_samples,
                                features=m2.features,
                                hyperparameters=m2.hyperparameters,
                                metrics=m2.metrics,
                                drift_baseline=m2.drift_baseline,
                                parent_model_id=m2.parent_model_id,
                                is_active=True,
                                notes=m2.notes,
                            )
                        )
                    else:
                        new_registry.append(
                            ModelMetadata(
                                model_id=m2.model_id,
                                sport=m2.sport,
                                model_type=m2.model_type,
                                version=m2.version,
                                created_at=m2.created_at,
                                training_data_hash=m2.training_data_hash,
                                training_samples=m2.training_samples,
                                features=m2.features,
                                hyperparameters=m2.hyperparameters,
                                metrics=m2.metrics,
                                drift_baseline=m2.drift_baseline,
                                parent_model_id=m2.parent_model_id,
                                is_active=False,
                                notes=m2.notes,
                            )
                        )
                self._model_registry[sport] = new_registry
                # Find the active model in the new registry
                for m in new_registry:
                    if m.is_active:
                        self._active_models[sport] = m
                        break
                self._save_registry()
                return True

        return False

    def cleanup_old_models(self, keep_active: bool = True, keep_last_n: int = 5) -> int:
        """Remove old model files and metadata."""
        removed = 0
        for sport, models in self._model_registry.items():
            active_models = [m for m in models if m.is_active]
            inactive_models = [m for m in models if not m.is_active]
            inactive_models.sort(key=lambda m: m.created_at, reverse=True)

            to_remove = inactive_models[keep_last_n:]
            for m in to_remove:
                model_path = self.models_dir / f"{m.model_id}.joblib"
                if model_path.exists():
                    model_path.unlink()
                    removed += 1

            # Update registry
            if keep_active:
                self._model_registry[sport] = active_models + inactive_models[
                    :keep_last_n
                ]
            else:
                self._model_registry[sport] = inactive_models[:keep_last_n]

        self._save_registry()
        return removed

    def export_model_card(
        self, sport: str, model_id: Optional[str] = None
    ) -> dict[str, Any]:
        """Export model card for documentation/audit."""
        metadata = self.get_model_metadata(sport, model_id)
        if not metadata:
            return {}

        return {
            "model_id": metadata.model_id,
            "sport": metadata.sport,
            "model_type": metadata.model_type,
            "version": metadata.version,
            "created_at": metadata.created_at.isoformat(),
            "training_samples": metadata.training_samples,
            "features": metadata.features,
            "hyperparameters": metadata.hyperparameters,
            "metrics": metadata.metrics,
            "parent_model_id": metadata.parent_model_id,
            "is_active": metadata.is_active,
            "notes": metadata.notes,
        }


def create_pipeline_from_config(config: dict[str, Any]) -> ContinuousLearningPipeline:
    """Create ContinuousLearningPipeline from configuration."""
    return ContinuousLearningPipeline(
        models_dir=config.get("models_dir", "models"),
        psi_threshold=config.get("psi_threshold", 0.2),
        performance_drop_threshold=config.get("performance_drop_threshold", 0.05),
        min_samples_for_retrain=config.get("min_samples_for_retrain", 100),
        max_model_versions=config.get("max_model_versions", 10),
    )
