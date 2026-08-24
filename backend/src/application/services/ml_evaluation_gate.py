"""
ML Evaluation Gate

Out-of-time quality gate applied to every candidate pick-classifier BEFORE
promotion. A candidate serves only if it strictly beats an always-favorite
baseline on BOTH required metrics (multiclass log loss and multiclass Brier
score) over a chronological holdout split.
"""

import logging
import numpy as np
from dataclasses import dataclass
from datetime import datetime
from typing import Any, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

MIN_HOLDOUT_SAMPLES = 30

# Canonical 1X2 label aliases accepted in model.classes_ for odds mapping.
_OUTCOME_ALIASES = {
    "home": {"home", "1", "h"},
    "draw": {"draw", "x", "empate", "d"},
    "away": {"away", "2", "a"},
}


@dataclass
class GateReport:
    """Result of one gate evaluation; persisted to training_results either way."""

    passed: bool
    log_loss: float
    brier: float
    baseline_log_loss: float
    baseline_brier: float
    n_holdout: int
    reason: str


def chronological_split(
    sample_dates: Sequence[Any], ratio: float = 0.2
) -> Tuple[List[int], List[int]]:
    """Split sample indices into (train, holdout) by event date.

    Holdout contains strictly later dates than every training sample: the
    boundary advances past any timestamp tie so the chronology invariant
    always holds. Returns an empty holdout when too few samples remain.
    """
    ordered = sorted(range(len(sample_dates)), key=lambda i: sample_dates[i])
    n = len(ordered)
    holdout_size = int(n * ratio)
    split_idx = max(n - holdout_size, 0)

    # Push equal timestamps at the boundary into train (holdout strictly later).
    while 0 < split_idx < n:
        if _normalize_date(sample_dates[ordered[split_idx]]) <= _normalize_date(
            sample_dates[ordered[split_idx - 1]]
        ):
            split_idx += 1
        else:
            break

    train_idx = sorted(ordered[:split_idx])
    holdout_idx = sorted(ordered[split_idx:])
    return train_idx, holdout_idx


def _normalize_date(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


def _proba_to_alphabetical(proba: np.ndarray, classes: Sequence[str]) -> np.ndarray:
    """Reorder probability columns to sklearn's expected alphabetical label order.

    sklearn's log_loss expects columns in alphabetical order of unique labels,
    regardless of the order specified in the 'labels' parameter.
    """
    classes_list = list(classes)
    if not classes_list:
        return proba
    alpha_order = sorted(classes_list)
    if alpha_order == classes_list:
        return proba
    # Build index mapping from model order to alphabetical order
    model_to_alpha = [classes_list.index(c) for c in alpha_order]
    return proba[:, model_to_alpha]


def run_gate(
    model: Any,
    X_holdout: Sequence[Any],
    y_holdout: Sequence[Any],
    baseline_probs: Sequence[Sequence[float]],
) -> GateReport:
    """Evaluate candidate vs baseline on the out-of-time holdout.

    PASS requires strictly better log loss AND strictly better Brier score.
    Fewer than MIN_HOLDOUT_SAMPLES rows fails with ``insufficient_data``.
    """
    n_holdout = len(X_holdout)
    classes = [str(c) for c in getattr(model, "classes_", [])]

    if n_holdout < MIN_HOLDOUT_SAMPLES:
        return GateReport(
            passed=False,
            log_loss=float("nan"),
            brier=float("nan"),
            baseline_log_loss=float("nan"),
            baseline_brier=float("nan"),
            n_holdout=n_holdout,
            reason="insufficient_data",
        )

    try:
        from sklearn.metrics import log_loss as sklearn_log_loss
    except ImportError:
        logger.error("[GATE] sklearn unavailable; cannot evaluate candidate")
        raise

    proba = model.predict_proba(list(X_holdout))
    proba_alpha = _proba_to_alphabetical(np.asarray(proba), classes)
    cand_loss = float(sklearn_log_loss(y_holdout, proba_alpha, labels=sorted(classes)))
    cand_brier = _multiclass_brier(proba, y_holdout, classes)

    base_rows = [list(row) for row in baseline_probs]
    base_alpha = _proba_to_alphabetical(np.asarray(base_rows), classes)
    base_loss = float(sklearn_log_loss(y_holdout, base_alpha, labels=sorted(classes)))
    base_brier = _multiclass_brier(base_rows, y_holdout, classes)

    passed = cand_loss < base_loss and cand_brier < base_brier
    reason = "passed" if passed else "worse_than_baseline"
    logger.info(
        "[GATE] n=%d candidate(log_loss=%.4f brier=%.4f) "
        "baseline(log_loss=%.4f brier=%.4f) -> %s",
        n_holdout,
        cand_loss,
        cand_brier,
        base_loss,
        base_brier,
        reason,
    )
    return GateReport(
        passed=passed,
        log_loss=cand_loss,
        brier=cand_brier,
        baseline_log_loss=base_loss,
        baseline_brier=base_brier,
        n_holdout=n_holdout,
        reason=reason,
    )


def _multiclass_brier(
    probs: Sequence[Sequence[float]], y_true: Sequence[Any], classes: Sequence[str]
) -> float:
    """Mean over samples of the sum of squared errors across all classes."""
    class_pos = {label: idx for idx, label in enumerate(classes)}
    total = 0.0
    for row, actual in zip(probs, y_true):
        target_pos = class_pos.get(str(actual))
        for pos, p in enumerate(row):
            target = 1.0 if pos == target_pos else 0.0
            total += (float(p) - target) ** 2
    return total / len(y_true)


def build_baseline_probs(
    odds_triples: Sequence[Optional[Sequence[Optional[float]]]],
    classes: Sequence[Any],
) -> List[List[float]]:
    """Odds-implied normalized favorite probabilities aligned to model classes.

    Rows map bookmaker odds (home, draw, away) through 1/odds normalization;
    uniform 1/n when odds are absent or labels are not a recognized 1X2 set.
    """
    n_labels = len(classes)
    uniform = [1.0 / n_labels] * n_labels
    str_to_pos = {str(c): i for i, c in enumerate(classes)}
    # Outcome order must match the odds triple order: (home, draw, away).
    label_positions: "dict[str, int]" = {}
    for outcome in ("home", "draw", "away"):
        for alias in _OUTCOME_ALIASES[outcome]:
            if alias in str_to_pos:
                label_positions[outcome] = str_to_pos[alias]
                break
    is_1x2 = len(label_positions) == 3

    rows: List[List[float]] = []
    for triple in odds_triples:
        row = list(uniform)
        if is_1x2 and triple and all(o and o > 0 for o in triple):
            implied = {
                outcome: 1.0 / float(o)
                for outcome, o in zip(("home", "draw", "away"), triple)
            }
            z = sum(implied.values())
            if z > 0:
                row = [0.0] * n_labels
                for outcome, weight in implied.items():
                    row[label_positions[outcome]] = weight / z
        rows.append(row)
    return rows
