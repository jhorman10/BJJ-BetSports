"""
Matches API Routes

STRICT POLICY:
- NO MOCK DATA ALLOWED.
- All endpoints must return REAL data from aggregated sources.
- AGGREGATION REQUIRED: Combine data from all available providers (API-Football, etc.) to ensure complete coverage.
- If data is unavailable, return empty lists or appropriate error codes.
"""
from typing import List, Any
import logging
from fastapi import APIRouter, HTTPException, Depends, Query, Path
from src.application.dtos.dtos import MatchDTO, TeamDTO, LeagueDTO, ErrorResponseDTO, MatchPredictionDTO
from src.application.use_cases.use_cases import DataSources, GetTeamPredictionsUseCase
from src.application.use_cases.live_predictions_use_case import GetLivePredictionsUseCase
from src.api.dependencies import (
    get_data_sources,
    get_prediction_service,
    get_statistics_service,
    get_cache_service,
    get_picks_service,
)

router = APIRouter()
logger = logging.getLogger(__name__)

def _map_match_to_dto(match: Any) -> MatchDTO:
    """Helper function to convert domain Match object to MatchDTO."""
    return MatchDTO(
        id=match.id,
        home_team=TeamDTO(
            id=match.home_team.id,
            name=match.home_team.name,
            short_name=match.home_team.short_name,
            country=match.home_team.country,
        ),
        away_team=TeamDTO(
            id=match.away_team.id,
            name=match.away_team.name,
            short_name=match.away_team.short_name,
            country=match.away_team.country,
        ),
        league=LeagueDTO(
            id=match.league.id,
            name=match.league.name,
            country=match.league.country,
            season=match.league.season,
        ),
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

@router.get(
    "/live",
    response_model=List[MatchDTO],
    responses={
        500: {"model": ErrorResponseDTO, "description": "Internal server error"},
    },
    summary="Get global live matches (Real Data Only)",
    description="Returns a list of all matches currently in play globally. MUST aggregate data from all configured sources (API-Football, etc). NO MOCK DATA.",
)
async def get_live_matches(
    data_sources: DataSources = Depends(get_data_sources),
) -> List[MatchDTO]:
    """Get all live matches using aggregated sources (NO MOCK DATA)."""
    try:
        from src.application.use_cases.use_cases import GetGlobalLiveMatchesUseCase
        use_case = GetGlobalLiveMatchesUseCase(data_sources)
        return await use_case.execute()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving live matches: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error retrieving live matches: {str(e)}")


@router.get(
    "/daily",
    response_model=List[MatchDTO],
    responses={
        500: {"model": ErrorResponseDTO, "description": "Internal server error"},
    },
    summary="Get all matches for today (Real Data Only)",
    description="Returns a list of all matches scheduled or played today globally. MUST combine data from all sources. NO MOCK DATA.",
)
async def get_daily_matches(
    date_str: str = Query(None, description="Date in YYYY-MM-DD format"),
    data_sources: DataSources = Depends(get_data_sources),
) -> List[MatchDTO]:
    """Get all daily matches using aggregated sources (NO MOCK DATA)."""
    try:
        from src.application.use_cases.use_cases import GetGlobalDailyMatchesUseCase
        use_case = GetGlobalDailyMatchesUseCase(data_sources)
        return await use_case.execute(date_str)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving daily matches: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error retrieving daily matches: {str(e)}")


@router.get(
    "/live/with-predictions",
    response_model=List[MatchPredictionDTO],
    responses={
        500: {"model": ErrorResponseDTO, "description": "Internal server error"},
    },
    summary="Get live matches with predictions",
    description="""
    Returns live matches from target leagues (Premier League, La Liga, Serie A, Bundesliga)
    with AI-powered predictions based on historical data and Poisson distribution.
    
    **Note**: Predictions are optimized for accuracy over speed. Initial load may take
    a few seconds while data is processed. Subsequent requests use cached data.
    """,
)
async def get_live_matches_with_predictions(
    filter_target_leagues: bool = Query(
        default=True,
        description="Filter to show only Premier League, La Liga, Serie A, Bundesliga",
    ),
    data_sources: DataSources = Depends(get_data_sources),
) -> List[MatchPredictionDTO]:
    """
    Get live matches with AI predictions.
    
    Uses caching to optimize response times while maintaining prediction accuracy.
    """
    try:
        # Get services
        prediction_service = get_prediction_service()
        statistics_service = get_statistics_service()
        cache_service = get_cache_service()
        picks_service = get_picks_service()
        
        # Execute use case
        use_case = GetLivePredictionsUseCase(
            data_sources=data_sources,
            prediction_service=prediction_service,
            statistics_service=statistics_service,
            cache_service=cache_service,
            picks_service=picks_service,
        )
        
        results = await use_case.execute(filter_target_leagues=filter_target_leagues)
        return results
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing live matches with predictions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing live matches: {str(e)}")


@router.get(
    "/team/{team_name}",
    response_model=List[MatchPredictionDTO],
    responses={
        404: {"model": ErrorResponseDTO, "description": "Team not found"},
        500: {"model": ErrorResponseDTO, "description": "Internal server error"},
    },
    summary="Get matches for a specific team",
    description="Returns upcoming matches for a specific team by name, including AI predictions.",
)
async def get_team_matches(
    team_name: str = Path(..., min_length=1, description="Name of the team to search for"),
    data_sources: DataSources = Depends(get_data_sources),
) -> List[MatchPredictionDTO]:
    """Get matches for a specific team by name with predictions."""
    try:
        # Get services
        prediction_service = get_prediction_service()
        statistics_service = get_statistics_service()
        
        use_case = GetTeamPredictionsUseCase(
            data_sources=data_sources,
            prediction_service=prediction_service,
            statistics_service=statistics_service,
        )
        
        return await use_case.execute(team_name)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing team matches for {team_name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing team matches: {str(e)}")
