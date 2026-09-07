import logging
from fastapi import APIRouter, HTTPException, Query
from src.api.dtos.tennis_dtos import TennisMatchRequest, TennisPredictionResponse
from src.domain.entities.tennis_match import TennisMatch
from src.domain.services.tennis_prediction_service import TennisPredictionService
from src.domain.services.tennis_feature_extractor import TennisFeatureExtractor
from src.infrastructure.data_sources.tennis_data_source import TennisDataSource
from src.infrastructure.data_sources.tennis_fixture_source import TennisFixtureDataSource
from datetime import date
from typing import Optional
import uuid

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tennis", tags=["tennis"])

# Singleton instances
_data_source = TennisDataSource(tour="atp")
_fixture_source = TennisFixtureDataSource(tour="atp")
_feature_extractor = None
_prediction_service = None
_all_fixtures = None  # Cache all fixtures


def get_prediction_service():
    global _feature_extractor, _prediction_service
    if _prediction_service is None:
        logger.info("Initializing Tennis Prediction Service...")
        hist_df = _data_source.fetch_matches_range(2019, 2023)
        _feature_extractor = TennisFeatureExtractor(historical_data=hist_df)
        _prediction_service = TennisPredictionService(feature_extractor=_feature_extractor)
    return _prediction_service


def get_all_fixtures():
    """Fetch and cache all upcoming fixtures."""
    global _all_fixtures
    if _all_fixtures is None:
        _all_fixtures = _fixture_source.fetch_upcoming_fixtures()
    return _all_fixtures


@router.post("/predict", response_model=TennisPredictionResponse)
async def predict_tennis_match(request: TennisMatchRequest):
    """Predict the outcome of a single tennis match."""
    try:
        match_entity = TennisMatch(
            match_id=str(uuid.uuid4()),
            tournament_name=request.tournament_name,
            surface=request.surface,
            tourney_level=request.tourney_level,
            round_name=request.round_name,
            match_date=request.match_date,
            best_of=request.best_of,
            p1_name=request.p1_name,
            p1_rank=request.p1_rank,
            p1_rank_points=request.p1_rank_points,
            p1_age=request.p1_age,
            p1_hand=request.p1_hand,
            p1_height=request.p1_height,
            p1_seed=request.p1_seed,
            p1_entry=request.p1_entry,
            p1_odds=request.p1_odds,
            p2_name=request.p2_name,
            p2_rank=request.p2_rank,
            p2_rank_points=request.p2_rank_points,
            p2_age=request.p2_age,
            p2_hand=request.p2_hand,
            p2_height=request.p2_height,
            p2_seed=request.p2_seed,
            p2_entry=request.p2_entry,
            p2_odds=request.p2_odds
        )

        predictor = get_prediction_service()
        prediction = predictor.predict(match_entity)

        if not prediction:
            raise HTTPException(status_code=500, detail="Prediction failed")

        return TennisPredictionResponse(
            match_id=match_entity.match_id,
            p1_name=match_entity.p1_name,
            p2_name=match_entity.p2_name,
            p1_win_prob=prediction.p1_win_prob,
            p2_win_prob=prediction.p2_win_prob,
            predicted_winner=prediction.predicted_winner,
            confidence=prediction.confidence,
            surface=match_entity.surface,
            tournament_name=match_entity.tournament_name
        )

    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tournaments")
async def get_tournaments():
    """
    Get available tennis tournaments (like leagues endpoint for football).
    Returns tournaments grouped by surface, each with match count.
    """
    try:
        fixtures = get_all_fixtures()

        if not fixtures:
            return {"tournaments": [], "total_matches": 0}

        # Group by tournament
        tournaments_map = {}
        for f in fixtures:
            t_name = f['tournament']
            if t_name not in tournaments_map:
                tournaments_map[t_name] = {
                    "id": t_name.lower().replace(" ", "_"),
                    "name": t_name,
                    "surface": f['surface'],
                    "level": f['tourney_level'],
                    "match_count": 0,
                }
            tournaments_map[t_name]["match_count"] += 1

        tournaments = list(tournaments_map.values())

        return {
            "tournaments": tournaments,
            "total_matches": len(fixtures)
        }

    except Exception as e:
        logger.error(f"Error fetching tournaments: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/predictions/{tournament_id}")
async def get_predictions_by_tournament(tournament_id: str):
    """
    Get predictions for a specific tournament (like predictions by league for football).
    Returns all matches in the tournament with full predictions.
    """
    try:
        fixtures = get_all_fixtures()

        if not fixtures:
            return {"tournament": None, "matches": [], "generated_at": None}

        # Filter fixtures by tournament_id
        tournament_fixtures = [
            f for f in fixtures
            if f['tournament'].lower().replace(" ", "_") == tournament_id
        ]

        if not tournament_fixtures:
            return {"tournament": None, "matches": [], "generated_at": None}

        predictor = get_prediction_service()
        results = []

        for fixture in tournament_fixtures:
            try:
                p1 = fixture['player1']
                p2 = fixture['player2']

                match_date_str = fixture['match_date']
                if isinstance(match_date_str, str):
                    match_date = date.fromisoformat(match_date_str)
                else:
                    match_date = match_date_str

                match_entity = TennisMatch(
                    match_id=str(uuid.uuid4()),
                    tournament_name=fixture['tournament'],
                    surface=fixture['surface'],
                    tourney_level=fixture['tourney_level'],
                    round_name=fixture['round'],
                    match_date=match_date,
                    best_of=fixture.get('best_of', 3),
                    p1_name=p1['name'],
                    p1_rank=p1.get('rank'),
                    p1_rank_points=p1.get('rank_points'),
                    p1_age=p1.get('age'),
                    p1_hand=p1.get('hand', 'R'),
                    p1_height=p1.get('height'),
                    p1_seed=p1.get('seed'),
                    p2_name=p2['name'],
                    p2_rank=p2.get('rank'),
                    p2_rank_points=p2.get('rank_points'),
                    p2_age=p2.get('age'),
                    p2_hand=p2.get('hand', 'R'),
                    p2_height=p2.get('height'),
                    p2_seed=p2.get('seed'),
                )

                prediction = predictor.predict(match_entity)

                if prediction:
                    # Generate markets for this match
                    markets = predictor.generate_tennis_markets(match_entity, prediction.p1_win_prob, prediction.p2_win_prob)
                    
                    results.append({
                        'match_id': match_entity.match_id,
                        'tournament': fixture['tournament'],
                        'surface': fixture['surface'],
                        'round': fixture['round'],
                        'match_date': fixture['match_date'],
                        'best_of': fixture.get('best_of', 3),
                        'player1': {
                            'name': p1['name'],
                            'rank': p1.get('rank'),
                            'rank_points': p1.get('rank_points'),
                            'age': p1.get('age'),
                            'hand': p1.get('hand', 'R'),
                            'height': p1.get('height'),
                            'seed': p1.get('seed'),
                        },
                        'player2': {
                            'name': p2['name'],
                            'rank': p2.get('rank'),
                            'rank_points': p2.get('rank_points'),
                            'age': p2.get('age'),
                            'hand': p2.get('hand', 'R'),
                            'height': p2.get('height'),
                            'seed': p2.get('seed'),
                        },
                        'prediction': {
                            'p1_win_prob': prediction.p1_win_prob,
                            'p2_win_prob': prediction.p2_win_prob,
                            'predicted_winner': prediction.predicted_winner,
                            'confidence': prediction.confidence,
                            'h2h': prediction.h2h,
                            'surface_stats': prediction.surface_stats,
                            'form': prediction.form,
                            'value_bets': prediction.value_bets,
                            'key_factors': prediction.key_factors,
                            'markets': markets,
                        }
                    })
            except Exception as e:
                logger.warning(f"Failed to predict fixture: {e}")
                continue

        tournament_info = tournament_fixtures[0] if tournament_fixtures else None

        return {
            "tournament": {
                "id": tournament_id,
                "name": tournament_info['tournament'] if tournament_info else tournament_id,
                "surface": tournament_info['surface'] if tournament_info else "",
                "level": tournament_info['tourney_level'] if tournament_info else "",
            } if tournament_info else None,
            "matches": results,
            "generated_at": date.today().isoformat()
        }

    except Exception as e:
        logger.error(f"Error fetching predictions for tournament: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/upcoming")
async def get_upcoming_matches(tournament: Optional[str] = Query(None)):
    """
    Get upcoming tennis matches with predictions.
    Optional tournament filter.
    """
    try:
        fixtures = get_all_fixtures()

        if not fixtures:
            return {"matches": [], "message": "No upcoming matches found"}

        # Filter by tournament if specified
        if tournament:
            fixtures = [f for f in fixtures if f['tournament'].lower().replace(" ", "_") == tournament]

        predictor = get_prediction_service()
        results = []

        for fixture in fixtures:
            try:
                p1 = fixture['player1']
                p2 = fixture['player2']

                match_date_str = fixture['match_date']
                if isinstance(match_date_str, str):
                    match_date = date.fromisoformat(match_date_str)
                else:
                    match_date = match_date_str

                match_entity = TennisMatch(
                    match_id=str(uuid.uuid4()),
                    tournament_name=fixture['tournament'],
                    surface=fixture['surface'],
                    tourney_level=fixture['tourney_level'],
                    round_name=fixture['round'],
                    match_date=match_date,
                    best_of=fixture.get('best_of', 3),
                    p1_name=p1['name'],
                    p1_rank=p1.get('rank'),
                    p1_rank_points=p1.get('rank_points'),
                    p1_age=p1.get('age'),
                    p1_hand=p1.get('hand', 'R'),
                    p1_height=p1.get('height'),
                    p1_seed=p1.get('seed'),
                    p2_name=p2['name'],
                    p2_rank=p2.get('rank'),
                    p2_rank_points=p2.get('rank_points'),
                    p2_age=p2.get('age'),
                    p2_hand=p2.get('hand', 'R'),
                    p2_height=p2.get('height'),
                    p2_seed=p2.get('seed'),
                )

                prediction = predictor.predict(match_entity)

                if prediction:
                    # Generate markets for this match
                    markets = predictor.generate_tennis_markets(match_entity, prediction.p1_win_prob, prediction.p2_win_prob)

                    results.append({
                        'match_id': match_entity.match_id,
                        'tournament': fixture['tournament'],
                        'surface': fixture['surface'],
                        'round': fixture['round'],
                        'match_date': fixture['match_date'],
                        'best_of': fixture.get('best_of', 3),
                        'player1': {
                            'name': p1['name'],
                            'rank': p1.get('rank'),
                            'rank_points': p1.get('rank_points'),
                            'age': p1.get('age'),
                            'hand': p1.get('hand', 'R'),
                            'height': p1.get('height'),
                            'seed': p1.get('seed'),
                        },
                        'player2': {
                            'name': p2['name'],
                            'rank': p2.get('rank'),
                            'rank_points': p2.get('rank_points'),
                            'age': p2.get('age'),
                            'hand': p2.get('hand', 'R'),
                            'height': p2.get('height'),
                            'seed': p2.get('seed'),
                        },
                        'prediction': {
                            'p1_win_prob': prediction.p1_win_prob,
                            'p2_win_prob': prediction.p2_win_prob,
                            'predicted_winner': prediction.predicted_winner,
                            'confidence': prediction.confidence,
                            'h2h': prediction.h2h,
                            'surface_stats': prediction.surface_stats,
                            'form': prediction.form,
                            'value_bets': prediction.value_bets,
                            'key_factors': prediction.key_factors,
                            'markets': markets,
                        }
                    })
            except Exception as e:
                logger.warning(f"Failed to predict fixture: {e}")
                continue

        return {"matches": results}

    except Exception as e:
        logger.error(f"Error fetching upcoming matches: {e}")
        raise HTTPException(status_code=500, detail=str(e))
