from __future__ import annotations

from typing import Any, cast

from src.api.schemas.leagues import LeagueModel
from src.api.schemas.predictions import MatchPredictionModel
from src.api.utils.serializers import _serialize_datetimes


def normalize_prediction_document(
    document: dict[str, Any], league: LeagueModel
) -> MatchPredictionModel | None:
    payload = document.get("prediction") or document.get("data") or document
    if not isinstance(payload, dict):
        return None

    match_payload = payload.get("match")
    prediction_payload = payload.get("prediction")

    match_payload = (
        _serialize_datetimes(match_payload)
        if isinstance(match_payload, dict)
        else match_payload
    )
    prediction_payload = (
        _serialize_datetimes(prediction_payload)
        if isinstance(prediction_payload, dict)
        else prediction_payload
    )

    if not isinstance(match_payload, dict) or not isinstance(prediction_payload, dict):
        return None

    try:
        return cast(
            MatchPredictionModel,
            MatchPredictionModel.model_validate(
                {
                    "match": {
                        **match_payload,
                        "league": match_payload.get("league")
                        or {
                            "id": league.id,
                            "name": league.name,
                            "country": league.country,
                            "sport": league.sport,
                        },
                    },
                    "prediction": prediction_payload,
                    "top_ml_picks": payload.get("top_ml_picks", []),
                }
            ),
        )
    except Exception:
        return None
