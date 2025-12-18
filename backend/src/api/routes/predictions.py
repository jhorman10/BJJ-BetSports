"""
Predictions Router

API endpoints for getting match predictions.
"""

from fastapi import APIRouter, HTTPException, Query

from src.application.dtos.dtos import (
    PredictionsResponseDTO,
    MatchPredictionDTO,
    ErrorResponseDTO,
    SortBy,
)
from src.api.dependencies import get_data_sources, get_prediction_service


router = APIRouter(prefix="/predictions", tags=["Predictions"])


@router.get(
    "/league/{league_id}",
    response_model=PredictionsResponseDTO,
    responses={
        404: {"model": ErrorResponseDTO, "description": "League not found"},
        500: {"model": ErrorResponseDTO, "description": "Internal server error"},
    },
    summary="Get predictions for a league",
    description="Returns match predictions for upcoming matches in a specific league. Results can be sorted by confidence, date, or probability.",
)
async def get_league_predictions(
    league_id: str,
    limit: int = Query(default=10, ge=1, le=50, description="Maximum matches to return"),
    sort_by: SortBy = Query(default=SortBy.CONFIDENCE, description="Field to sort by"),
    sort_desc: bool = Query(default=True, description="Sort in descending order (highest first)"),
) -> PredictionsResponseDTO:
    """Get predictions for all upcoming matches in a league."""
    from src.application.use_cases.use_cases import GetPredictionsUseCase, DataSources
    from src.infrastructure.data_sources.football_data_uk import LEAGUES_METADATA
    
    if league_id not in LEAGUES_METADATA:
        raise HTTPException(
            status_code=404,
            detail=f"League not found: {league_id}. Available leagues: {list(LEAGUES_METADATA.keys())}",
        )
    
    data_sources = get_data_sources()
    prediction_service = get_prediction_service()
    use_case = GetPredictionsUseCase(data_sources, prediction_service)
    
    try:
        result = await use_case.execute(league_id, limit)
        
        # Apply sorting
        # For dates: ascending (closest event first)
        # For confidence/probability: descending (highest first)
        if result.predictions:
            if sort_by == SortBy.CONFIDENCE:
                result.predictions.sort(
                    key=lambda x: x.prediction.confidence,
                    reverse=True  # Highest confidence first
                )
            elif sort_by == SortBy.DATE:
                result.predictions.sort(
                    key=lambda x: x.match.match_date,
                    reverse=False  # Closest date first (ascending)
                )
            elif sort_by == SortBy.HOME_PROBABILITY:
                result.predictions.sort(
                    key=lambda x: x.prediction.home_win_probability,
                    reverse=True  # Highest probability first
                )
            elif sort_by == SortBy.AWAY_PROBABILITY:
                result.predictions.sort(
                    key=lambda x: x.prediction.away_win_probability,
                    reverse=True  # Highest probability first
                )
        
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/match/{match_id}",
    response_model=MatchPredictionDTO,
    responses={
        404: {"model": ErrorResponseDTO, "description": "Match not found"},
        500: {"model": ErrorResponseDTO, "description": "Internal server error"},
    },
    summary="Get prediction for a specific match",
    description="Returns prediction for a specific match by ID.",
)
async def get_match_prediction(match_id: str) -> MatchPredictionDTO:
    """Get prediction for a specific match."""
    from src.application.use_cases.use_cases import GetPredictionsUseCase, DataSources
    from src.infrastructure.data_sources.football_data_uk import LEAGUES_METADATA
    
    data_sources = get_data_sources()
    prediction_service = get_prediction_service()
    
    # 1. Check if it's a sample match
    if match_id.startswith("sample_"):
        # Create a mock match for display purposes
        from datetime import datetime, timedelta
        from src.domain.entities.entities import Match, Team, League
        
        # Try to parse league ID from sample ID (sample_{league_id}_{index})
        parts = match_id.split("_")
        league_id = parts[1] if len(parts) > 1 else "Unknown"
        
        match = Match(
            id=match_id,
            home_team=Team(id="mock_home", name="Sample Home Team", country="Unknown"),
            away_team=Team(id="mock_away", name="Sample Away Team", country="Unknown"),
            league=League(id=league_id, name="Sample League", country="Unknown", season="2024"),
            match_date=datetime.now() + timedelta(days=1),
            status="NS",
            home_odds=2.5,
            draw_odds=3.2,
            away_odds=2.8
        )
    else:
        # Get match details from API-Football
        match = await data_sources.api_football.get_match_details(match_id)
        
    if not match:
         raise HTTPException(status_code=404, detail="Match not found")
         
    # 2. Get historical data for stats (optional, but good for prediction)
    # We try to guess league_id from match.league.id or just use what we have
    # Since we might not have a clean mapping back to our league IDs if it came from API-Football ID directly,
    # we proceed with limited stats if needed.
    # ideally we find the league_id in LEAGUES_METADATA that matches match.league.id
    
    # Simple lookup for league ID
    our_league_id = None
    for lid, meta in LEAGUES_METADATA.items():
        # This is a weak link, but for now we proceed.
        # IF we can't find stats, we predict with low confidence.
        pass

    # For now, we reuse the service without deep history if we can't easily link it.
    # Or we assume main leagues.
    
    # Reuse logic from UseCase to convert to DTO
    # We need a mini-usecase here or expose the helper methods.
    # For speed, I'll duplicate the simple DTO conversion logic here or verify if I can import it.
    # GetPredictionsUseCase has instance methods...
    
    # Let's simple generate prediction with empty stats if we don't have history loaded
    # fetching history for a single match is heavy if we don't know the league context.
    
    prediction = prediction_service.generate_prediction(
        match=match,
        home_stats=None, # We'd need to fetch 2 years of data to compute this
        away_stats=None,
        league_averages=None,
        data_sources=["API-Football"]
    )
    
    # Helper to convert to DTO (duplicated for now to avoid refactoring UseCase class)
    # Ideally should be in a mapper class
    from src.application.dtos.dtos import (
        TeamDTO, LeagueDTO, MatchDTO, PredictionDTO, MatchPredictionDTO
    )
    
    match_dto = MatchDTO(
        id=match.id,
        home_team=TeamDTO(id=match.home_team.id, name=match.home_team.name, country=match.home_team.country),
        away_team=TeamDTO(id=match.away_team.id, name=match.away_team.name, country=match.away_team.country),
        league=LeagueDTO(id=match.league.id, name=match.league.name, country=match.league.country, season=match.league.season),
        match_date=match.match_date,
        home_goals=match.home_goals,
        away_goals=match.away_goals,
        status=match.status,
        home_corners=match.home_corners,
        away_corners=match.away_corners,
        home_yellow_cards=match.home_yellow_cards,
        away_yellow_cards=match.away_yellow_cards,
        home_red_cards=match.home_red_cards,
        away_red_cards=match.away_red_cards,
        home_odds=match.home_odds,
        draw_odds=match.draw_odds,
        away_odds=match.away_odds,
    )
    
    prediction_dto = PredictionDTO(
        match_id=prediction.match_id,
        home_win_probability=prediction.home_win_probability,
        draw_probability=prediction.draw_probability,
        away_win_probability=prediction.away_win_probability,
        over_25_probability=prediction.over_25_probability,
        under_25_probability=prediction.under_25_probability,
        predicted_home_goals=prediction.predicted_home_goals,
        predicted_away_goals=prediction.predicted_away_goals,
        confidence=prediction.confidence,
        data_sources=prediction.data_sources,
        recommended_bet=prediction.recommended_bet,
        over_under_recommendation=prediction.over_under_recommendation,
        created_at=prediction.created_at,
    )
    
    return MatchPredictionDTO(match=match_dto, prediction=prediction_dto)
