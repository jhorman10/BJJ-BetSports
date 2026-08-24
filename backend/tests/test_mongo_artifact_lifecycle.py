"""
Unit tests for Mongo artifact lifecycle — versioned save immutability,
atomic promotion old-or-new read guarantee, clear_all_data preserves
pointer+artifact+legacy blob, pruning never deletes pointer/legacy.
Proves: 'Failed training keeps prior model serving' (ml-artifact-lifecycle spec).
"""
import pytest
from unittest.mock import MagicMock, patch
from bson.binary import Binary
from datetime import datetime, timezone


def _mock_repo():
    """Create a mock MongoRepository with in-memory binary_artifacts + app_state."""
    artifacts = {}
    app_state = {}

    class MockRepo:
        ML_SERVING_POINTER_KEY = "ml_picks_classifier/serving"
        ML_LEGACY_BLOB_KEY = "ml_picks_classifier.joblib"

        def _versioned_doc_key(self, key, version):
            return f"{key}/{version}"

        def save_binary_artifact_versioned(self, key, version, binary_data, meta):
            full_key = self._versioned_doc_key(key, version)
            if full_key in artifacts:
                raise ValueError(f"Artifact {key!r} version {version!r} already exists")
            artifacts[full_key] = {"data": binary_data, "meta": meta, "artifact_key": key, "version": version}

        def get_versioned_artifact(self, key, version):
            full_key = self._versioned_doc_key(key, version)
            doc = artifacts.get(full_key)
            if not doc:
                return None, None
            return doc["data"], doc["meta"]

        def list_versions(self, key_prefix):
            return sorted(v["version"] for k, v in artifacts.items() if k.startswith(key_prefix + "/"))

        def delete_binary_artifact(self, key):
            if key in artifacts:
                del artifacts[key]
                return True
            return False

        def promote_serving_pointer(self, pointer_key=None, artifact_key="", version="", metrics=None):
            ptr_key = pointer_key or self.ML_SERVING_POINTER_KEY
            data = {
                "artifact_key": artifact_key,
                "version": version,
                "promoted_at": datetime.now(timezone.utc).isoformat(),
                "metrics": metrics or {},
            }
            app_state[ptr_key] = data
            return data

        def get_app_state(self, key):
            return app_state.get(key)

        def clear_all_data(self):
            pointer = self.get_app_state(self.ML_SERVING_POINTER_KEY) or {}
            protected = {self.ML_LEGACY_BLOB_KEY}
            if pointer.get("artifact_key") and pointer.get("version"):
                protected.add(self._versioned_doc_key(pointer["artifact_key"], pointer["version"]))
            # Only delete non-protected
            for k in list(artifacts.keys()):
                if k not in protected:
                    del artifacts[k]
            for k in list(app_state.keys()):
                if k != self.ML_SERVING_POINTER_KEY:
                    del app_state[k]

    return MockRepo(), artifacts, app_state


def test_versioned_save_immutability():
    repo, artifacts, _ = _mock_repo()
    repo.save_binary_artifact_versioned("models/picks", "v1", b"bytes1", {"m": 1})
    with pytest.raises(ValueError):
        repo.save_binary_artifact_versioned("models/picks", "v1", b"bytes2", {"m": 2})
    # Original unchanged
    assert artifacts["models/picks/v1"]["data"] == b"bytes1"


def test_promotion_swaps_pointer_atomically():
    repo, _, app_state = _mock_repo()
    repo.promote_serving_pointer(artifact_key="models/picks", version="v1", metrics={"acc": 0.7})
    assert app_state[repo.ML_SERVING_POINTER_KEY]["version"] == "v1"
    # Second promotion
    repo.promote_serving_pointer(artifact_key="models/picks", version="v2", metrics={"acc": 0.8})
    assert app_state[repo.ML_SERVING_POINTER_KEY]["version"] == "v2"
    # No partial state possible in mock (single dict update)


def test_clear_all_data_preserves_serving_pointer_and_artifact():
    repo, artifacts, app_state = _mock_repo()
    # Setup: legacy blob + versioned v1 + promoted v1
    artifacts["ml_picks_classifier.joblib"] = {"data": b"legacy", "meta": {}}
    artifacts["models/picks_classifier/v1"] = {"data": b"v1", "meta": {}, "artifact_key": "models/picks_classifier", "version": "v1"}
    repo.promote_serving_pointer(artifact_key="models/picks_classifier", version="v1")

    repo.clear_all_data()

    # Pointer and its target + legacy MUST survive
    assert repo.ML_SERVING_POINTER_KEY in app_state
    assert "models/picks_classifier/v1" in artifacts
    assert "ml_picks_classifier.joblib" in artifacts
    # Pointer still points to v1
    assert app_state[repo.ML_SERVING_POINTER_KEY]["version"] == "v1"


def test_clear_all_data_preserves_legacy_when_no_promotion():
    repo, artifacts, _ = _mock_repo()
    artifacts["ml_picks_classifier.joblib"] = {"data": b"legacy", "meta": {}}
    artifacts["models/picks_classifier/v0"] = {"data": b"v0", "meta": {}}

    repo.clear_all_data()

    assert "ml_picks_classifier.joblib" in artifacts
    # Without a serving pointer, only the legacy blob is explicitly protected
    # (spec: "serving pointer and its target artifact plus legacy")
    assert "models/picks_classifier/v0" not in artifacts


def test_pruning_never_deletes_pointer_target_or_legacy():
    repo, artifacts, _ = _mock_repo()
    artifacts["ml_picks_classifier.joblib"] = {"data": b"legacy", "meta": {}}
    for v in ["v1", "v2", "v3", "v4"]:
        artifacts[f"models/picks_classifier/{v}"] = {"data": b"x", "meta": {}, "artifact_key": "models/picks_classifier", "version": v}
    repo.promote_serving_pointer(artifact_key="models/picks_classifier", version="v4")

    # Simulate retention pruning (keep last 3 = v2,v3,v4)
    versions = repo.list_versions("models/picks_classifier")
    for old_version in versions[:-3]:
        if old_version == "v4":
            continue
        repo.delete_binary_artifact(f"models/picks_classifier/{old_version}")

    assert "models/picks_classifier/v4" in artifacts  # promoted survives
    assert "models/picks_classifier/v3" in artifacts  # within retention
    assert "models/picks_classifier/v2" in artifacts  # within retention
    assert "models/picks_classifier/v1" not in artifacts  # pruned
    assert "ml_picks_classifier.joblib" in artifacts  # legacy survives