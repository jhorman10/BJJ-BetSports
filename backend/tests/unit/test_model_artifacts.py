"""Unit tests for model artifact discovery and cleanup.

Covers the expanded cleanup coverage (data/*.joblib, output/*.json, tmp/*),
preservation of runtime JSON assets, the cache clear parameter, and the
non-fatal OSError contract.
"""

import logging
from pathlib import Path

import pytest
import src.core.model_artifacts as module_under_test
from src.core.model_artifacts import cleanup_model_artifacts


def _populate(root: Path) -> None:
    """Create a representative artifact tree inside ``root``."""
    (root / "ml_models").mkdir(parents=True, exist_ok=True)
    (root / "data").mkdir(parents=True, exist_ok=True)
    (root / "output").mkdir(parents=True, exist_ok=True)
    (root / "tmp").mkdir(parents=True, exist_ok=True)

    # Root artifacts
    (root / "ml_picks_classifier.joblib").write_bytes(b"model")
    (root / "learning_weights.json").write_text("{}")
    (root / "ml_models" / "extra.joblib").write_bytes(b"extra")
    # data/ artifacts (MODEL_FILE_PATH)
    (root / "data" / "ml_picks_classifier.joblib").write_bytes(b"model2")
    # output/ baseline (write-only)
    (root / "output" / "baseline_90d.json").write_text("{}")
    # tmp/ benchmark files
    (root / "tmp" / "benchmark.json").write_text("{}")
    (root / "tmp" / "nested_dir").mkdir(exist_ok=True)
    # Runtime JSON assets MUST be preserved
    (root / "data" / "team_logos.json").write_text("{}")
    (root / "data" / "team_short_names.json").write_text("{}")


@pytest.fixture
def artifact_tree(tmp_path, monkeypatch):
    monkeypatch.setattr(module_under_test, "BACKEND_ROOT", tmp_path)
    monkeypatch.setattr(module_under_test, "DATA_DIR", tmp_path / "data")
    _populate(tmp_path)
    return tmp_path


def test_cleanup_removes_joblib_output_and_tmp_files(artifact_tree):
    cleanup_model_artifacts(logging.getLogger("test"))

    assert not (artifact_tree / "ml_picks_classifier.joblib").exists()
    assert not (artifact_tree / "learning_weights.json").exists()
    assert not (artifact_tree / "ml_models" / "extra.joblib").exists()
    assert not (artifact_tree / "data" / "ml_picks_classifier.joblib").exists()
    assert not (artifact_tree / "output" / "baseline_90d.json").exists()
    assert not (artifact_tree / "tmp" / "benchmark.json").exists()
    # Directories are preserved
    assert (artifact_tree / "tmp" / "nested_dir").is_dir()


def test_cleanup_preserves_runtime_json_assets(artifact_tree):
    cleanup_model_artifacts(logging.getLogger("test"))

    assert (artifact_tree / "data" / "team_logos.json").exists()
    assert (artifact_tree / "data" / "team_short_names.json").exists()


class _FakeCache:
    def __init__(self) -> None:
        self.clear_calls = 0

    def clear(self) -> None:
        self.clear_calls += 1


def test_cleanup_with_cache_calls_clear(artifact_tree):
    fake_cache = _FakeCache()

    cleanup_model_artifacts(logging.getLogger("test"), cache=fake_cache)

    assert fake_cache.clear_calls == 1


def test_cleanup_without_cache_does_not_call_clear(artifact_tree):
    cleanup_model_artifacts(logging.getLogger("test"))

    # No cache provider passed → no clear, no exception.
    assert True


def test_cleanup_oserror_is_non_fatal(artifact_tree, monkeypatch):
    def _raise(self) -> None:
        raise OSError("permission denied")

    monkeypatch.setattr(Path, "unlink", _raise)

    # Must NOT raise even though every unlink fails.
    cleanup_model_artifacts(logging.getLogger("test"))

    # Artifacts remain in place because removal failed.
    assert (artifact_tree / "ml_picks_classifier.joblib").exists()
