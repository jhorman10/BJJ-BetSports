import logging
from fastapi import APIRouter, HTTPException, Query
from src.api.dtos.baseball_dtos import (
    BaseballPredictRequest, BaseballPredictResponse,
    BaseballGamesResponse, BaseballSeriesResponse,
    BaseballGameResponse, BaseballSeriesGame, BaseballPredictionDetail,
)
from src.domain.entities.baseball_game import BaseballGame
from src.domain.services.baseball_prediction_service import BaseballPredictionService
from src.domain.services.baseball_feature_extractor import BaseballFeatureExtractor
from src.infrastructure.data_sources.retrosheet_data_source import RetrosheetDataSource
from src.infrastructure.data_sources.mlb_fixture_source import MLBFixtureSource
from datetime import date
from typing import Optional
import uuid

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/baseball", tags=["baseball"])

# Singleton instances
_data_source = RetrosheetDataSource()
_fixture_source = MLBFixtureSource()
_feature_extractor = None
_prediction_service = None
_all_games = None  # Cache


def get_prediction_service():
    global _feature_extractor, _prediction_service
    if _prediction_service is None:
        logger.info("Initializing Baseball Prediction Service...")
        _feature_extractor = BaseballFeatureExtractor()
        _prediction_service = BaseballPredictionService(feature_extractor=_feature_extractor)
    return _prediction_service


def get_all_games():
    global _all_games
    if _all_games is None:
        _all_games = _fixture_source.get_upcoming_games(days=14)
    return _all_games


def _game_data_to_entity(game_data: dict, series_id: str = None) -> BaseballGame:
    """Convert a fixture dict to a BaseballGame entity."""
    return BaseballGame(
        game_id=game_data.get("game_id", str(uuid.uuid4())),
        date=date.fromisoformat(game_data["date"]),
        home_team=game_data["home_team"],
        away_team=game_data["away_team"],
        venue=game_data.get("venue"),
        day_night=game_data.get("day_night", "day"),
        home_pitcher_name=game_data.get("home_pitcher_name"),
        away_pitcher_name=game_data.get("away_pitcher_name"),
        series_id=series_id or game_data.get("series_id"),
    )


@router.post("/predict", response_model=BaseballPredictResponse)
async def predict_baseball_game(request: BaseballPredictRequest):
    """Predict the outcome of a single baseball game."""
    try:
        game_entity = BaseballGame(
            game_id=str(uuid.uuid4()), date=request.date,
            home_team=request.home_team, away_team=request.away_team,
            venue=request.venue, day_night=request.day_night or "day",
            home_pitcher_name=request.home_pitcher_name,
            away_pitcher_name=request.away_pitcher_name,
            season=request.season, series_id=request.series_id,
            home_odds=request.home_odds, away_odds=request.away_odds,
        )
        predictor = get_prediction_service()
        prediction = predictor.predict(game_entity)
        if not prediction:
            raise HTTPException(status_code=500, detail="Prediction failed")
        return BaseballPredictResponse(
            game_id=game_entity.game_id, home_team=game_entity.home_team,
            away_team=game_entity.away_team,
            home_win_prob=prediction.home_win_prob, away_win_prob=prediction.away_win_prob,
            predicted_winner=prediction.predicted_winner, confidence=prediction.confidence,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/games")
async def get_upcoming_games(team: Optional[str] = Query(None)):
    """Get upcoming baseball games."""
    try:
        all_games = get_all_games()
        if not all_games:
            return BaseballGamesResponse(games=[], generated_at=date.today().isoformat())
        if team:
            team = team.upper()
            all_games = [g for g in all_games if g.get("home_team") == team or g.get("away_team") == team]
        results = []
        for gd in all_games:
            try:
                ent = _game_data_to_entity(gd)
                results.append(BaseballGameResponse(
                    game_id=ent.game_id, date=ent.date.isoformat(),
                    home_team=ent.home_team, away_team=ent.away_team,
                    venue=ent.venue, day_night=ent.day_night,
                    home_pitcher_name=ent.home_pitcher_name,
                    away_pitcher_name=ent.away_pitcher_name,
                ))
            except Exception as e:
                logger.warning(f"Failed to process game: {e}")
        return BaseballGamesResponse(games=results, generated_at=date.today().isoformat())
    except Exception as e:
        logger.error(f"Error fetching games: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/series")
async def get_series(team: Optional[str] = Query(None)):
    """Get upcoming games grouped into series with predictions."""
    try:
        series_list = _fixture_source.get_series(days=14, team=team)
        predictor = get_prediction_service()
        is_demo = len(get_all_games()) > 0 and get_all_games()[0].get("game_id", "").startswith("demo_")
        series_results = []
        for series_games in series_list:
            game_list = []
            for gd in series_games:
                try:
                    ent = _game_data_to_entity(gd)
                    pred = predictor.predict(ent)
                    markets, kf = (pred.key_factors, []) if pred else ([], [])
                    if pred:
                        markets = predictor.generate_baseball_markets(ent, pred.home_win_prob, pred.away_win_prob)
                        kf = pred.key_factors
                    game_list.append(BaseballSeriesGame(
                        game_id=ent.game_id, date=ent.date.isoformat(),
                        home_team=ent.home_team, away_team=ent.away_team,
                        venue=ent.venue, day_night=ent.day_night,
                        home_pitcher_name=ent.home_pitcher_name,
                        away_pitcher_name=ent.away_pitcher_name,
                        prediction=BaseballPredictionDetail(
                            home_win_prob=pred.home_win_prob, away_win_prob=pred.away_win_prob,
                            predicted_winner=pred.predicted_winner, confidence=pred.confidence,
                            key_factors=kf, markets=markets,
                        ) if pred else None,
                    ))
                except Exception as e:
                    logger.warning(f"Failed to process game in series: {e}")
            if game_list:
                series_results.append(game_list)
        return BaseballSeriesResponse(series=series_results, generated_at=date.today().isoformat(), is_demo=is_demo)
    except Exception as e:
        logger.error(f"Error fetching series: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/predictions/{series_id}")
async def get_series_predictions(series_id: str):
    """Get predictions for a specific series."""
    try:
        all_games = get_all_games()
        series_games = [g for g in all_games if g.get("series_id") == series_id]
        if not series_games:
            return {"series_id": series_id, "games": [], "generated_at": date.today().isoformat()}
        predictor = get_prediction_service()
        results = []
        for gd in series_games:
            try:
                ent = _game_data_to_entity(gd, series_id)
                pred = predictor.predict(ent)
                if pred:
                    markets = predictor.generate_baseball_markets(ent, pred.home_win_prob, pred.away_win_prob)
                    results.append({
                        "game_id": ent.game_id, "date": ent.date.isoformat(),
                        "home_team": ent.home_team, "away_team": ent.away_team,
                        "venue": ent.venue, "day_night": ent.day_night,
                        "home_pitcher_name": ent.home_pitcher_name,
                        "away_pitcher_name": ent.away_pitcher_name,
                        "prediction": {
                            "home_win_prob": pred.home_win_prob, "away_win_prob": pred.away_win_prob,
                            "predicted_winner": pred.predicted_winner, "confidence": pred.confidence,
                            "key_factors": pred.key_factors, "markets": markets,
                        },
                    })
            except Exception as e:
                logger.warning(f"Failed to predict game: {e}")
        return {"series_id": series_id, "games": results, "generated_at": date.today().isoformat()}
    except Exception as e:
        logger.error(f"Error fetching series predictions: {e}")
        raise HTTPException(status_code=500, detail=str(e))
