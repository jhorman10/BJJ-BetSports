"""Runtime tests for the MLOps pipeline final cleanup step (REQ-3).

Covers both scenarios of REQ-3 in `openspec/specs/ml-artifact-lifecycle/spec.md`:

* "Cleanup as final pipeline step" — the cleanup fragment embedded in
  `backend/scripts/local_mlops_pipeline.sh` executes as the final step and the
  pipeline exits 0, even when there is nothing to clean (runtime evidence).
* "Cleanup failure is non-fatal" — when cache.clear() or
  cleanup_model_artifacts() raises, the `|| true` guard keeps the pipeline at
  exit 0 with the failure logged (runtime evidence).

The full pipeline is NOT run (it would train for hours). Instead, the embedded
final-step heredoc fragment is extracted VERBATIM from the real script and
executed under `set -euo pipefail` exactly as the script would. The imported
helpers are stubbed with minimal shims so the test is deterministic, fast, and
touches no real files or directories.
"""

import subprocess
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
PIPELINE_SCRIPT = BACKEND_ROOT / "scripts" / "local_mlops_pipeline.sh"

# Exact heredoc markers used by local_mlops_pipeline.sh.
_HEREDOC_OPEN = "<<'PY'"
_HEREDOC_CLOSE = "PY"

_CACHE_SHIM_OK = """\
class _Cache:
    def clear(self):
        pass


def get_cache_service():
    return _Cache()
"""

_CACHE_SHIM_RAISES = """\
class _Cache:
    def clear(self):
        raise RuntimeError("simulated cache clear failure")


def get_cache_service():
    return _Cache()
"""

_CLEANUP_SHIM_OK = """\
import logging


def cleanup_model_artifacts(logger, cache=None):
    \"\"\"Shim: mimics the real cleanup when there is nothing to remove.\"\"\"
    if cache is not None:
        cache.clear()
    logger.info("No local ML artifacts found to remove.")
"""

_CLEANUP_SHIM_RAISES = """\
import logging


def cleanup_model_artifacts(logger, cache=None):
    \"\"\"Shim: simulates a hard failure inside the final cleanup step.\"\"\"
    logger.warning("simulated cleanup failure")
    raise RuntimeError("simulated cleanup failure")
"""


def _extract_cleanup_fragment() -> str:
    """Return the verbatim python fragment embedded in the pipeline script."""
    lines = PIPELINE_SCRIPT.read_text(encoding="utf-8").splitlines()
    start = next(i for i, line in enumerate(lines) if _HEREDOC_OPEN in line)
    end = next(
        i
        for i, line in enumerate(lines[start + 1 :], start + 1)
        if line.strip() == _HEREDOC_CLOSE
    )
    return "\n".join(lines[start + 1 : end])


def _write_shim(root: Path, cleanup_source: str, cache_source: str) -> Path:
    """Create an importable shim package overriding the cleanup helpers."""
    (root / "src" / "core").mkdir(parents=True)
    (root / "src" / "infrastructure").mkdir(parents=True)
    (root / "src" / "__init__.py").write_text("")
    (root / "src" / "core" / "__init__.py").write_text("")
    (root / "src" / "infrastructure" / "__init__.py").write_text("")
    (root / "src" / "core" / "model_artifacts.py").write_text(
        cleanup_source, encoding="utf-8"
    )
    (root / "src" / "infrastructure" / "cache.py").write_text(
        cache_source, encoding="utf-8"
    )
    return root


def _run_cleanup_fragment(tmp_path, cleanup_source, cache_source):
    """Run the script's real cleanup fragment under the pipeline's shell mode.

    Mirrors local_mlops_pipeline.sh: `set -euo pipefail`, the `python3 - <<'PY'
    ... PY` heredoc, and the trailing `|| true` that makes the step non-fatal.
    """
    shim = _write_shim(tmp_path / "shim", cleanup_source, cache_source)
    fragment = _extract_cleanup_fragment()
    command = (
        "set -euo pipefail\n"
        f'PYTHONPATH="{shim}" "{sys.executable}" - <<\'PY\' || true\n'
        f"{fragment}\n"
        "PY\n"
        "echo EXIT_OK\n"
    )
    return subprocess.run(
        ["bash", "-c", command],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )


def test_pipeline_script_bash_syntax_ok():
    result = subprocess.run(
        ["bash", "-n", str(PIPELINE_SCRIPT)], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr


def test_cleanup_step_is_final_and_non_fatal_guarded():
    """Static ordering guard: cleanup must be the LAST step, non-fatally."""
    lines = PIPELINE_SCRIPT.read_text(encoding="utf-8").splitlines()
    cli_lines = [i for i, line in enumerate(lines) if "orchestrator_cli.py" in line]
    heredoc_line = next(i for i, line in enumerate(lines) if _HEREDOC_OPEN in line)

    assert cli_lines, "script must invoke the orchestrator CLI steps"
    assert heredoc_line > max(
        cli_lines
    ), "cleanup must run AFTER top-picks (final step)"
    assert (
        "|| true" in lines[heredoc_line]
    ), "cleanup step must be non-fatal (|| true under set -e)"


def test_cleanup_final_step_runs_and_exits_zero(tmp_path):
    """REQ-3 'Cleanup as final pipeline step': nothing to clean -> exit 0."""
    result = _run_cleanup_fragment(tmp_path, _CLEANUP_SHIM_OK, _CACHE_SHIM_OK)

    assert result.returncode == 0, result.stderr
    assert "EXIT_OK" in result.stdout, "pipeline must continue after cleanup"
    assert (
        "Cleanup ML completado" in result.stdout
    ), "cleanup fragment must have executed"
    assert (
        "No local ML artifacts found to remove." in result.stderr
    ), "cleanup must log when there is nothing to remove"


def test_cleanup_failure_is_non_fatal(tmp_path):
    """REQ-3 'Cleanup failure is non-fatal': cleanup raises -> exit 0."""
    result = _run_cleanup_fragment(tmp_path, _CLEANUP_SHIM_RAISES, _CACHE_SHIM_OK)

    assert result.returncode == 0, result.stderr
    assert "EXIT_OK" in result.stdout, "pipeline must continue after failure"
    assert "simulated cleanup failure" in result.stderr, "failure must be logged"


def test_cache_clear_failure_is_non_fatal(tmp_path):
    """REQ-3: cache.clear() raising (before cleanup) must also be non-fatal."""
    result = _run_cleanup_fragment(tmp_path, _CLEANUP_SHIM_OK, _CACHE_SHIM_RAISES)

    assert result.returncode == 0, result.stderr
    assert "EXIT_OK" in result.stdout, "pipeline must continue after failure"
    assert "simulated cache clear failure" in result.stderr, "failure must be logged"
