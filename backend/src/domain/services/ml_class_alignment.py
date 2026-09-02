"""
ML Class Alignment

Aligns predict_proba outputs to outcome labels through ``model.classes_``
instead of positional index assumptions (ml-model-deployment spec:
"Probabilities mapped through classes_").
"""

from typing import Any, Sequence

# Canonical 1X2 outcome labels and the aliases they may appear as inside
# model.classes_. Order of lookup per label is alias priority.
_OUTCOME_ALIASES = {
    "home": ("home", "1", "h"),
    # "0"/"1"/"2" cover integer-encoded artifacts (legacy comment:
    # "Predict Probabilities [Draw(0), Home(1), Away(2)]").
    "draw": ("draw", "x", "empate", "d", "0"),
    "away": ("away", "2", "a"),
}


def _class_positions(classes: Sequence[Any]) -> dict[str, int]:
    normalized = [str(c).strip().lower() for c in classes]
    positions: dict[str, int] = {}
    for label, aliases in _OUTCOME_ALIASES.items():
        for alias in aliases:
            if alias in normalized:
                positions[label] = normalized.index(alias)
                break
    return positions


def outcome_probability_map(model: Any, proba_row: Sequence[float]) -> dict[str, float]:
    """Map one predict_proba row to {home, draw, away} via model.classes_.

    Raises ValueError when classes_ does not encode a recognizable 1X2
    layout — callers must treat that as an explicit blend failure, never
    silently fall back to positional indexing.
    """
    classes_attr = getattr(model, "classes_", None)
    classes = list(classes_attr) if classes_attr is not None else []
    positions = _class_positions(classes)
    if len(positions) != 3 or len(proba_row) < len(classes):
        raise ValueError(
            "Unrecognized classifier layout: "
            f"classes_={classes!r} proba_width={len(proba_row)}; "
            "cannot align 1X2 probabilities"
        )
    return {label: float(proba_row[pos]) for label, pos in positions.items()}


def positive_class_probability(model: Any, proba_row: Sequence[float]) -> float:
    """Probability of the positive class for pick-success classifiers.

    Locates class ``1`` inside classes_ rather than assuming column order;
    falls back to the last column when classes_ is unavailable.
    """
    if len(proba_row) == 0:
        raise ValueError("Empty probability row; cannot read positive class")
    classes_attr = getattr(model, "classes_", None)
    classes = list(classes_attr) if classes_attr is not None else []
    if len(classes) == len(proba_row):
        try:
            return float(proba_row[classes.index(1)])
        except ValueError:
            pass
    return float(proba_row[-1])
