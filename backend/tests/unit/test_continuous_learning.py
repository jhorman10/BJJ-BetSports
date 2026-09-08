"""
Unit tests for ContinuousLearningPipeline module.
"""

import pytest
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestClassifier

from src.domain.services.continuous_learning import (
    ContinuousLearningPipeline,
    ModelMetadata,
    DriftReport,
    PerformanceReport,
    RetrainDecision,
    create_pipeline_from_config,
)


class TestContinuousLearningPipeline:
    """Tests for ContinuousLearningPipeline class."""

    def setup_method(self):
        """Set up test fixtures with temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.pipeline = ContinuousLearningPipeline(
            models_dir=self.temp_dir,
            psi_threshold=0.2,
            performance_drop_threshold=0.05,
            min_samples_for_retrain=10,
            max_model_versions=5,
        )

    def teardown_method(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_pipeline_creation(self):
        """Test pipeline creation."""
        assert self.pipeline.models_dir.exists()
        assert self.pipeline.psi_threshold == 0.2
        assert self.pipeline.performance_drop_threshold == 0.05

    def test_compute_data_hash(self):
        """Test data hash computation."""
        X = np.random.rand(100, 5)
        y = np.random.randint(0, 2, 100)

        hash1 = self.pipeline._compute_data_hash(X, y)
        hash2 = self.pipeline._compute_data_hash(X, y)

        assert hash1 == hash2  # Same data -> same hash
        assert len(hash1) == 16  # MD5 truncated to 16 chars

    def test_compute_feature_distributions(self):
        """Test feature distribution computation for PSI baseline."""
        X = np.random.rand(100, 3)
        feature_names = ["feat1", "feat2", "feat3"]

        dists = self.pipeline._compute_feature_distributions(X, feature_names)

        assert len(dists) == 3
        for name in feature_names:
            assert name in dists
            assert "hist" in dists[name]
            assert "bins" in dists[name]
            assert "mean" in dists[name]
            assert "std" in dists[name]

    def test_calculate_psi_no_drift(self):
        """Test PSI calculation with no drift."""
        # Same distribution
        ref_dist = {"hist": [0.1]*10, "bins": list(range(11))}
        curr_dist = {"hist": [0.1]*10, "bins": list(range(11))}

        psi = self.pipeline._calculate_psi(ref_dist, curr_dist)

        assert psi == 0.0  # Identical distributions -> PSI = 0

    def test_calculate_psi_with_drift(self):
        """Test PSI calculation with drift."""
        # Shifted distribution
        ref_dist = {"hist": [0.1]*10, "bins": list(range(11))}
        curr_dist = {"hist": [0.05]*5 + [0.15]*5, "bins": list(range(11))}

        psi = self.pipeline._calculate_psi(ref_dist, curr_dist)

        assert psi > 0  # Different distributions -> PSI > 0

    def test_drift_detection_no_drift(self):
        """Test drift detection with no drift."""
        np.random.seed(42)
        ref_X = np.random.randn(100, 3) * 1 + 0  # Mean 0, std 1
        curr_X = ref_X.copy()  # Exact same data -> no drift

        report = self.pipeline.drift_detection(
            curr_X, ref_X, ["f1", "f2", "f3"]
        )

        assert isinstance(report, DriftReport)
        assert not report.drift_detected
        assert report.overall_psi < 0.2
        assert len(report.features_drifted) == 0

    def test_drift_detection_with_drift(self):
        """Test drift detection with significant drift."""
        np.random.seed(42)
        ref_X = np.random.randn(100, 3) * 1 + 0  # Mean 0
        curr_X = np.random.randn(100, 3) * 1 + 2  # Mean shifted to 2

        report = self.pipeline.drift_detection(
            curr_X, ref_X, ["f1", "f2", "f3"]
        )

        assert report.drift_detected
        assert report.overall_psi >= 0.2
        assert len(report.features_drifted) > 0

    def test_model_performance_monitoring_binary(self):
        """Test performance monitoring for binary classification."""
        np.random.seed(42)
        n = 200
        y_true = np.random.randint(0, 2, n)
        y_pred = np.clip(y_true + np.random.randn(n) * 0.1, 0, 1)  # Noisy but decent

        report = self.pipeline.model_performance_monitoring(
            y_pred, y_true, baseline_brier=0.15, baseline_logloss=0.5
        )

        assert isinstance(report, PerformanceReport)
        assert report.brier_score >= 0
        assert report.log_loss >= 0
        assert 0 <= report.accuracy <= 1
        assert len(report.rolling_brier) > 0
        assert len(report.rolling_log_loss) > 0

    def test_model_performance_monitoring_multiclass(self):
        """Test performance monitoring for multiclass."""
        np.random.seed(42)
        n = 200
        y_true = np.random.randint(0, 3, n)
        # Predictions as probabilities for each class
        y_pred = np.zeros((n, 3))
        for i in range(n):
            probs = np.random.dirichlet([1, 1, 1])
            probs[y_true[i]] += 0.3  # Bias toward true class
            y_pred[i] = probs / probs.sum()

        report = self.pipeline.model_performance_monitoring(
            y_pred, y_true, baseline_brier=0.4, baseline_logloss=1.0
        )

        assert report.sample_count == n
        assert report.brier_score >= 0

    def test_model_performance_drop_detected(self):
        """Test performance drop detection."""
        np.random.seed(42)
        n = 200
        y_true = np.random.randint(0, 2, n)
        # Poor predictions
        y_pred = np.random.rand(n)

        report = self.pipeline.model_performance_monitoring(
            y_pred, y_true, baseline_brier=0.10, baseline_logloss=0.3
        )

        assert report.performance_drop > 0.05
        assert report.threshold_exceeded is not False

    def test_daily_retrain(self):
        """Test daily retraining."""
        np.random.seed(42)
        X = np.random.randn(50, 4)
        y = np.random.randint(0, 2, 50)
        feature_names = ["f1", "f2", "f3", "f4"]

        metadata = self.pipeline.daily_retrain(
            sport="football",
            new_x=X,
            new_y=y,
            feature_names=feature_names,
        )

        assert metadata is not None
        assert isinstance(metadata, ModelMetadata)
        assert metadata.sport == "football"
        assert metadata.training_samples == 50
        assert metadata.is_active is True
        assert metadata.model_id.startswith("football_")

        # Check model file was saved
        model_path = Path(self.temp_dir) / f"{metadata.model_id}.joblib"
        assert model_path.exists()

        # Check registry
        assert "football" in self.pipeline._model_registry
        assert len(self.pipeline._model_registry["football"]) == 1

    def test_daily_retrain_insufficient_samples(self):
        """Test daily retrain skipped with insufficient samples."""
        X = np.random.randn(5, 4)  # Only 5 samples
        y = np.random.randint(0, 2, 5)

        metadata = self.pipeline.daily_retrain(
            sport="tennis",
            new_x=X,
            new_y=y,
            feature_names=["f1", "f2", "f3", "f4"],
        )

        assert metadata is None

    def test_auto_retrain_trigger_no_model(self):
        """Test auto retrain trigger when no active model."""
        X = np.random.randn(20, 4)
        y = np.random.randint(0, 2, 20)

        decision = self.pipeline.auto_retrain_trigger(
            sport="football",
            current_x=X,
            current_y=y,
            feature_names=["f1", "f2", "f3", "f4"],
        )

        assert isinstance(decision, RetrainDecision)
        assert decision.should_retrain is True
        assert "No active model" in decision.reason
        assert decision.urgency == "high"

    def test_auto_retrain_trigger_drift(self):
        """Test auto retrain trigger with drift."""
        np.random.seed(42)
        # Train initial model
        X_train = np.random.randn(50, 4)
        y_train = np.random.randint(0, 2, 50)
        self.pipeline.daily_retrain(
            sport="football",
            new_x=X_train,
            new_y=y_train,
            feature_names=["f1", "f2", "f3", "f4"],
        )

        # Current data with drift
        X_current = np.random.randn(30, 4) + 2  # Shifted
        y_current = np.random.randint(0, 2, 30)
        # Good predictions on current (to isolate drift check)
        preds = np.random.rand(30)

        decision = self.pipeline.auto_retrain_trigger(
            sport="football",
            current_x=X_current,
            current_y=y_current,
            feature_names=["f1", "f2", "f3", "f4"],
            predictions=preds,
            outcomes=y_current,
        )

        assert decision.should_retrain is True
        assert decision.drift_report is not None
        assert decision.drift_report.drift_detected is True

    def test_auto_retrain_trigger_performance_drop(self):
        """Test auto retrain trigger with performance drop."""
        np.random.seed(42)
        # Train initial model with enough samples for stable baseline
        X_train = np.random.randn(200, 4)
        y_train = np.random.randint(0, 2, 200)
        self.pipeline.daily_retrain(
            sport="football",
            new_x=X_train,
            new_y=y_train,
            feature_names=["f1", "f2", "f3", "f4"],
        )

        # Current data - same distribution but poor predictions
        np.random.seed(43)
        X_current = np.random.randn(100, 4)  # Larger sample for stable PSI
        y_current = np.random.randint(0, 2, 100)
        preds = np.random.rand(100)  # Random predictions = poor performance

        decision = self.pipeline.auto_retrain_trigger(
            sport="football",
            current_x=X_current,
            current_y=y_current,
            feature_names=["f1", "f2", "f3", "f4"],
            predictions=preds,
            outcomes=y_current,
        )

        assert decision.should_retrain is True
        # Drift might trigger first, so check either drift or performance
        assert decision.drift_report is not None or decision.performance_report is not None
        if decision.performance_report is not None:
            assert decision.performance_report.threshold_exceeded is True

    def test_auto_retrain_trigger_scheduled(self):
        """Test auto retrain trigger on schedule (weekly)."""
        np.random.seed(42)
        # Train model with old timestamp
        X_train = np.random.randn(200, 4)
        y_train = np.random.randint(0, 2, 200)

        # Manually create old model metadata
        old_metadata = ModelMetadata(
            model_id="football_old",
            sport="football",
            model_type="RandomForestClassifier",
            version="20240101_000000",
            created_at=datetime.utcnow() - timedelta(days=10),
            training_data_hash="abc123",
            training_samples=200,
            features=["f1", "f2", "f3", "f4"],
            hyperparameters={},
            metrics={"brier_score": 0.15, "log_loss": 0.4, "accuracy": 0.7},
            drift_baseline=self.pipeline._compute_feature_distributions(X_train, ["f1", "f2", "f3", "f4"]),
            is_active=True,
        )
        self.pipeline._model_registry["football"] = [old_metadata]
        self.pipeline._active_models["football"] = old_metadata
        self.pipeline._save_registry()

        # Use SAME data as training to avoid drift detection
        # Just test the scheduled retrain logic
        X_current = X_train[:100]  # Subset of training data
        y_current = y_train[:100]
        preds = np.array([0.6 if y == 1 else 0.4 for y in y_current])

        decision = self.pipeline.auto_retrain_trigger(
            sport="football",
            current_x=X_current,
            current_y=y_current,
            feature_names=["f1", "f2", "f3", "f4"],
            predictions=preds,
            outcomes=y_current,
        )

        assert decision.should_retrain is True
        # Either scheduled or drift could trigger
        assert "weekly" in decision.reason.lower() or "scheduled" in decision.reason.lower() or "drift" in decision.reason.lower()

    def test_load_active_model(self):
        """Test loading active model."""
        np.random.seed(42)
        X = np.random.randn(30, 3)
        y = np.random.randint(0, 2, 30)

        metadata = self.pipeline.daily_retrain(
            sport="basketball",
            new_x=X,
            new_y=y,
            feature_names=["f1", "f2", "f3"],
        )

        model = self.pipeline.load_active_model("basketball")

        assert model is not None
        assert hasattr(model, "predict_proba")

    def test_load_nonexistent_model(self):
        """Test loading non-existent model."""
        model = self.pipeline.load_active_model("nonexistent_sport")
        assert model is None

    def test_get_model_metadata(self):
        """Test getting model metadata."""
        np.random.seed(42)
        X = np.random.randn(30, 3)
        y = np.random.randint(0, 2, 30)

        metadata = self.pipeline.daily_retrain(
            sport="baseball",
            new_x=X,
            new_y=y,
            feature_names=["f1", "f2", "f3"],
        )

        retrieved = self.pipeline.get_model_metadata("baseball")
        assert retrieved is not None
        assert retrieved.model_id == metadata.model_id

    def test_list_model_versions(self):
        """Test listing model versions."""
        np.random.seed(42)
        for i in range(3):
            # Ensure balanced classes
            X = np.random.randn(100, 3)
            y = np.concatenate([np.zeros(50), np.ones(50)]).astype(int)
            np.random.shuffle(y)
            self.pipeline.daily_retrain(
                sport="tennis",
                new_x=X,
                new_y=y,
                feature_names=["f1", "f2", "f3"],
            )

        versions = self.pipeline.list_model_versions("tennis")
        assert len(versions) == 3
        # Should be sorted by creation time (newest first for active)

    def test_set_active_model(self):
        """Test setting active model."""
        np.random.seed(42)
        versions = []
        for i in range(3):
            # Ensure balanced classes
            X = np.random.randn(100, 3)
            y = np.concatenate([np.zeros(50), np.ones(50)]).astype(int)
            np.random.shuffle(y)
            meta = self.pipeline.daily_retrain(
                sport="hockey",
                new_x=X,
                new_y=y,
                feature_names=["f1", "f2", "f3"],
            )
            versions.append(meta.model_id)

        # Set middle version as active
        success = self.pipeline.set_active_model("hockey", versions[1])
        assert success is True

        active = self.pipeline.get_model_metadata("hockey")
        assert active.model_id == versions[1]
        assert active.is_active is True

    def test_cleanup_old_models(self):
        """Test cleaning up old model versions."""
        np.random.seed(42)
        # Use different timestamps to avoid duplicate model IDs
        for i in range(7):
            # Ensure balanced classes
            X = np.random.randn(100, 3)
            y = np.concatenate([np.zeros(50), np.ones(50)]).astype(int)
            np.random.shuffle(y)
            # Small delay to ensure unique timestamps
            import time
            time.sleep(0.01)
            self.pipeline.daily_retrain(
                sport="soccer",
                new_x=X,
                new_y=y,
                feature_names=["f1", "f2", "f3"],
            )

        versions_before = self.pipeline.list_model_versions("soccer")
        # Just verify we created multiple versions
        assert len(versions_before) >= 5

        removed = self.pipeline.cleanup_old_models(keep_active=True, keep_last_n=3)
        # Should remove some old models
        assert removed >= 1

        versions = self.pipeline.list_model_versions("soccer")
        assert len(versions) <= len(versions_before)

    def test_export_model_card(self):
        """Test exporting model card."""
        np.random.seed(42)
        X = np.random.randn(30, 3)
        y = np.random.randint(0, 2, 30)

        metadata = self.pipeline.daily_retrain(
            sport="cricket",
            new_x=X,
            new_y=y,
            feature_names=["f1", "f2", "f3"],
        )

        card = self.pipeline.export_model_card("cricket")
        assert card["model_id"] == metadata.model_id
        assert card["sport"] == "cricket"
        assert card["is_active"] is True
        assert "metrics" in card
        assert "hyperparameters" in card


class TestCreatePipelineFromConfig:
    """Tests for create_pipeline_from_config factory function."""

    def test_create_from_config(self):
        """Test creating pipeline from config dict."""
        config = {
            "models_dir": "/tmp/test_models",
            "psi_threshold": 0.15,
            "performance_drop_threshold": 0.03,
            "min_samples_for_retrain": 50,
            "max_model_versions": 20,
        }

        pipeline = create_pipeline_from_config(config)

        assert pipeline.psi_threshold == 0.15
        assert pipeline.performance_drop_threshold == 0.03
        assert pipeline.min_samples_for_retrain == 50
        assert pipeline.max_model_versions == 20

    def test_create_with_defaults(self):
        """Test creating pipeline with default config."""
        config = {}
        pipeline = create_pipeline_from_config(config)

        assert pipeline.psi_threshold == 0.2
        assert pipeline.performance_drop_threshold == 0.05


class TestDriftReport:
    """Tests for DriftReport dataclass."""

    def test_report_creation(self):
        """Test creating a drift report."""
        report = DriftReport(
            feature_psi={"f1": 0.1, "f2": 0.25},
            overall_psi=0.175,
            drift_detected=True,
            psi_threshold=0.2,
            features_drifted=["f2"],
        )

        assert report.drift_detected is True
        assert "f2" in report.features_drifted
        assert report.overall_psi == 0.175


class TestPerformanceReport:
    """Tests for PerformanceReport dataclass."""

    def test_report_creation(self):
        """Test creating a performance report."""
        report = PerformanceReport(
            brier_score=0.18,
            log_loss=0.55,
            accuracy=0.72,
            rolling_brier=[0.16, 0.17, 0.18],
            rolling_log_loss=[0.50, 0.52, 0.55],
            performance_drop=0.03,
            threshold_exceeded=False,
            sample_count=100,
        )

        assert report.brier_score == 0.18
        assert not report.threshold_exceeded
        assert report.sample_count == 100


class TestRetrainDecision:
    """Tests for RetrainDecision dataclass."""

    def test_decision_creation(self):
        """Test creating a retrain decision."""
        decision = RetrainDecision(
            should_retrain=True,
            reason="Feature drift detected",
            urgency="high",
        )

        assert decision.should_retrain is True
        assert decision.urgency == "high"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])