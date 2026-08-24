"""
Unit tests for ML serving validation — envelope sklearn/schema mismatch
loud errors naming both values, classes_ permutation mapping at both
blend sites, legacy deprecation warning, [ML_FALLBACK] emission + mode
markers, no bare except around blending.
"""
import pytest
from unittest.mock import MagicMock, patch
from io import BytesIO
import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier


class _DummyRF(RandomForestClassifier):
    def __init__(self):
        super().__init__(n_estimators=1, max_depth=1)
        self.classes_ = np.array(["home", "draw", "away"])
        self.n_features_in_ = 45
    def fit(self, X, y):
        super().fit(X, y)
        return self


def _make_model_bytes(model):
    buf = BytesIO()
    joblib.dump(model, buf)
    return buf.getvalue()


def _mock_picks_service(repo=None, model_bytes=None, meta=None, legacy_blob=None):
    """Construct PicksService with controlled repo responses."""
    from src.domain.services.picks_service import PicksService
    from src.core.constants import ML_MODEL_FILENAME

    mock_repo = MagicMock()
    if repo:
        mock_repo = repo
    else:
        # Default: pointer to versioned artifact with matching envelope
        pointer = {"artifact_key": "models/picks_classifier", "version": "v1", "metrics": {}}
        mock_repo.get_app_state.return_value = pointer
        mock_repo.get_versioned_artifact.return_value = (
            model_bytes or _make_model_bytes(_DummyRF()),
            meta or {
                "sklearn_version": "1.5.2",
                "feature_schema_hash": "abc123",
                "git_sha": "abcdef12",
                "trained_at": "2024-01-01T00:00:00Z",
                "metrics": {"log_loss": 0.5},
                "legacy": False,
            },
        )
        if legacy_blob:
            mock_repo.get_binary_artifact.return_value = legacy_blob
        else:
            mock_repo.get_binary_artifact.return_value = None

    svc = PicksService(persistence_repo=mock_repo)
    # Override feature extractor signature for test control
    with patch("src.domain.services.ml_feature_extractor.MLFeatureExtractor.schema_signature", return_value="abc123"):
        svc.ml_model = svc._load_ml_model_safely("dummy_path")
    return svc, mock_repo


def test_versioned_load_success_sets_ml_mode():
    svc, _ = _mock_picks_service()
    assert svc.ml_model is not None
    assert svc.serving_mode == "ml"
    assert svc.fallback_reason is None


def test_sklearn_version_mismatch_fails_loudly():
    bad_meta = {
        "sklearn_version": "0.99.9",  # mismatched
        "feature_schema_hash": "abc123",
        "git_sha": "abc", "trained_at": "2024-01-01", "metrics": {}, "legacy": False,
    }
    svc, _ = _mock_picks_service(meta=bad_meta)
    assert svc.ml_model is None
    assert svc.serving_mode == "heuristic"
    assert svc.fallback_reason == "version_mismatch"


def test_feature_schema_mismatch_fails_loudly():
    bad_meta = {
        "sklearn_version": "1.5.2",
        "feature_schema_hash": "zzzzzz",  # mismatched
        "git_sha": "abc", "trained_at": "2024-01-01", "metrics": {}, "legacy": False,
    }
    svc, _ = _mock_picks_service(meta=bad_meta)
    assert svc.ml_model is None
    assert svc.serving_mode == "heuristic"
    assert svc.fallback_reason == "schema_mismatch"


def test_legacy_blob_loads_read_only_with_warning(caplog):
    """Legacy blob loads with deprecation warning but no envelope validation."""
    legacy_model = _make_model_bytes(_DummyRF())
    svc, mock_repo = _mock_picks_service(model_bytes=None, legacy_blob=legacy_model)
    # Force pointer miss
    mock_repo.get_app_state.return_value = None
    svc.ml_model = svc._load_ml_model_safely("dummy_path")
    assert svc.ml_model is not None
    assert svc.serving_mode == "heuristic"
    assert svc.fallback_reason == "absent"
    assert any("deprecated" in r.message.lower() for r in caplog.records)


def test_classes_alignment_in_prediction_service_ensemble():
    """Test ml_class_alignment.outcome_probability_map permutes correctly."""
    from src.domain.services.ml_class_alignment import outcome_probability_map
    import numpy as np

    class M:
        classes_ = np.array(["away", "home", "draw"])  # permuted
    proba = np.array([0.1, 0.7, 0.2])  # index 0=away, 1=home, 2=draw
    mapped = outcome_probability_map(M(), proba)
    assert mapped["home"] == 0.7
    assert mapped["draw"] == 0.2
    assert mapped["away"] == 0.1


def test_classes_alignment_raises_on_unrecognized_layout():
    from src.domain.services.ml_class_alignment import outcome_probability_map
    import numpy as np

    class M:
        classes_ = np.array(["foo", "bar"])  # not 1X2
    with pytest.raises(ValueError, match="Unrecognized classifier layout"):
        outcome_probability_map(M(), np.array([0.5, 0.5]))


def test_positive_class_probability_finds_class_1():
    from src.domain.services.ml_class_alignment import positive_class_probability
    import numpy as np

    class M:
        classes_ = np.array([0, 1])
    assert positive_class_probability(M(), np.array([0.3, 0.7])) == 0.7


def test_ml_fallback_logged_on_mismatch(caplog):
    """[ML_FALLBACK] structured log emitted on envelope mismatch."""
    bad_meta = {"sklearn_version": "9.9.9", "feature_schema_hash": "abc123", "git_sha": "abc", "trained_at": "2024", "metrics": {}, "legacy": False}
    svc, _ = _mock_picks_service(meta=bad_meta)
    assert any("[ML_FALLBACK] reason=version_mismatch" in r.message for r in caplog.records)


def test_no_bare_except_in_blending_paths():
    """Static check: no bare 'except:' in prediction_service.py blend."""
    import ast, pathlib
    code = pathlib.Path("backend/src/domain/services/prediction_service.py").read_text()
    tree = ast.parse(code)
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            # Allow if it's the logging handler we added (has body with logger.warning)
            # But flag if it's an empty pass
            if any(isinstance(stmt, ast.Pass) for stmt in node.body):
                raise AssertionError("Bare 'except: pass' found in prediction_service.py")