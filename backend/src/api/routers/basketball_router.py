import logging
from fastapi import APIRouter, HTTPException, Query
from src.api.dtos.basketball_dtos import (
    BasketballPredictRequest, BasketballPredictResponse,
    BasketballGamesResponse, BasketballGameResponse,
    BasketballGameWithPrediction, BasketballConferenceResponse,
    BasketballConferenceGamesResponse, BasketballPredictionDetail,
)
from src.domain.entities.basketball_game import BasketballGame
from src.domain.services.basketball_prediction_service import BasketballPredictionService
from src.domain.services.basketball_feature_extractor import BasketballFeatureExtractor
from src.infrastructure.data_sources.nba_data_source import NBADataSource
from src.infrastructure.data_sources.nba_fixture_source import NBAFixtureSource
from datetime import date
from typing import Optional
import uuid

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/basketball", tags=["basketball"])

# Singleton instances
_data_source = NBADataSource()
_fixture_source = NBAFixtureSource()
_feature_extractor = None
_prediction_service = None
_all_games = None  # Cache


def get_prediction_service():
    global _feature_extractor, _prediction_service
    if _prediction_service is None:
        logger.info("Initializing Basketball Prediction Service...")
        _feature_extractor = BasketballFeatureExtractor()
        _prediction_service = BasketballPredictionService(feature_extractor=_feature_extractor)
    return _prediction_service


def get_all_games():
    global _all_games
    if _all_games is None:
        _all_games = _fixture_source.get_upcoming_games(days=14)
    return _all_games


def _game_data_to_entity(game_data: dict) -> BasketballGame:
    """Convert a fixture dict to a BasketballGame entity."""
    return BasketballGame(
        game_id=game_data.get("game_id", str(uuid.uuid4())),
        game_date=date.fromisoformat(game_data["date"]),
        home_team=game_data["home_team"],
        away_team=game_data["away_team"],
        venue=game_data.get("venue"),
    )


@router.post("/predict", response_model=BasketballPredictResponse)
async def predict_basketball_game(request: BasketballPredictRequest):
    """Predict the outcome of a single basketball game."""
    try:
        game_entity = BasketballGame(
            game_id=str(uuid.uuid4()),
            game_date=request.date,
            home_team=request.home_team,
            away_team=request.away_team,
            venue=request.venue,
            season=request.season or "2025-26",
            game_type=request.game_type or "R",
            home_odds=request.home_odds,
            away_odds=request.away_odds,
            spread=request.spread,
            total=request.total,
        )
        predictor = get_prediction_service()
        prediction = predictor.predict(game_entity)
        if not prediction:
            raise HTTPException(status_code=500, detail="Prediction failed")
        return BasketballPredictResponse(
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
    """Get upcoming basketball games."""
    try:
        all_games = get_all_games()
        if not all_games:
            return BasketballGamesResponse(games=[], generated_at=date.today().isoformat())
        if team:
            team = team.upper()
            all_games = [g for g in all_games if g.get("home_team") == team or g.get("away_team") == team]
        results = []
        for gd in all_games:
            try:
                ent = _game_data_to_entity(gd)
                results.append(BasketballGameResponse(
                    game_id=ent.game_id, date=ent.game_date.isoformat(),
                    home_team=ent.home_team, away_team=ent.away_team,
                    venue=ent.venue,
                    home_team_name=gd.get("home_team_name"),
                    away_team_name=gd.get("away_team_name"),
                ))
            except Exception as e:
                logger.warning(f"Failed to process game: {e}")
        return BasketballGamesResponse(games=results, generated_at=date.today().isoformat())
    except Exception as e:
        logger.error(f"Error fetching games: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conferences")
async def get_conferences():
    """Get available conferences."""
    try:
        conferences = [
            {"id": "east", "name": "Eastern Conference", "teams": BasketballFeatureExtractor.CONFERENCES["East"]},
            {"id": "west", "name": "Western Conference", "teams": BasketballFeatureExtractor.CONFERENCES["West"]},
        ]
        return BasketballConferenceResponse(
            conferences=conferences,
            generated_at=date.today().isoformat(),
        )
    except Exception as e:
        logger.error(f"Error fetching conferences: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/predictions/{conference_id}")
async def get_conference_predictions(conference_id: str):
    """Get predictions for games in a specific conference."""
    try:
        all_games = get_all_games()
        conf_teams = BasketballFeatureExtractor.CONFERENCES.get(conference_id.capitalize(), [])
        if not conf_teams:
            raise HTTPException(status_code=404, detail=f"Conference '{conference_id}' not found")

        # Filter games involving conference teams
        conference_games = [
            g for g in all_games
            if g.get("home_team") in conf_teams or g.get("away_team") in conf_teams
        ]

        predictor = get_prediction_service()
        results = []
        for gd in conference_games:
            try:
                ent = _game_data_to_entity(gd)
                pred = predictor.predict(ent)
                markets = []
                kf = []
                if pred:
                    markets = predictor.generate_basketball_markets(ent, pred.home_win_prob, pred.away_win_prob)
                    kf = pred.key_factors
                results.append(BasketballGameWithPrediction(
                    game_id=ent.game_id, date=ent.game_date.isoformat(),
                    home_team=ent.home_team, away_team=ent.away_team,
                    venue=ent.venue,
                    home_team_name=gd.get("home_team_name"),
                    away_team_name=gd.get("away_team_name"),
                    prediction=BasketballPredictionDetail(
                        home_win_prob=pred.home_win_prob, away_win_prob=pred.away_win_prob,
                        predicted_winner=pred.predicted_winner, confidence=pred.confidence,
                        key_factors=kf, markets=markets,
                    ) if pred else None,
                ))
            except Exception as e:
                logger.warning(f"Failed to process game: {e}")

        conf_name = "Eastern Conference" if conference_id.lower() == "east" else "Western Conference"
        return BasketballConferenceGamesResponse(
            conference_id=conference_id,
            conference_name=conf_name,
            games=results,
            generated_at=date.today().isoformat(),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching conference predictions: {e}")
        raise HTTPException(status_code=500, detail=str(e))
