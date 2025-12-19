from typing import List
from fastapi import APIRouter, HTTPException, Depends, Query
from src.application.dtos.dtos import MatchDTO, TeamDTO, LeagueDTO, ErrorResponseDTO, MatchPredictionDTO
from src.application.use_cases.use_cases import DataSources
from src.application.use_cases.live_predictions_use_case import GetLivePredictionsUseCase
from src.api.dependencies import (
    get_data_sources,
    get_prediction_service,
    get_statistics_service,
    get_cache_service,
)

router = APIRouter()

@router.get(
    "/live",
    response_model=List[MatchDTO],
    responses={
        500: {"model": ErrorResponseDTO, "description": "Internal server error"},
    },
    summary="Get global live matches",
    description="Returns a list of all matches currently in play globally.",
)
async def get_live_matches(
    data_sources: DataSources = Depends(get_data_sources),
) -> List[MatchDTO]:
    """Get all live matches."""
    matches = await data_sources.api_football.get_live_matches()
    
    # Convert to DTOs
    match_dtos = []
    for match in matches:
        match_dtos.append(MatchDTO(
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
        ))
        
    return match_dtos


@router.get(
    "/daily",
    response_model=List[MatchDTO],
    responses={
        500: {"model": ErrorResponseDTO, "description": "Internal server error"},
    },
    summary="Get all matches for today",
    description="Returns a list of all matches scheduled or played today globally.",
)
async def get_daily_matches(
    data_sources: DataSources = Depends(get_data_sources),
) -> List[MatchDTO]:
    """Get all daily matches."""
    matches = await data_sources.api_football.get_daily_matches()
    
    # Convert to DTOs
    match_dtos = []
    for match in matches:
        match_dtos.append(MatchDTO(
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
        ))
        
    return match_dtos


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
        
        # Execute use case
        use_case = GetLivePredictionsUseCase(
            data_sources=data_sources,
            prediction_service=prediction_service,
            statistics_service=statistics_service,
            cache_service=cache_service,
        )
        
        results = await use_case.execute(filter_target_leagues=filter_target_leagues)
        return results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing live matches: {str(e)}")


@router.get(
    "/team/{team_name}",
    response_model=List[MatchDTO],
    responses={
        500: {"model": ErrorResponseDTO, "description": "Internal server error"},
    },
    summary="Get matches for a specific team",
    description="Returns upcoming matches for a specific team by name.",
)
async def get_team_matches(
    team_name: str,
    data_sources: DataSources = Depends(get_data_sources),
) -> List[MatchDTO]:
    """Get matches for a specific team by name."""
    matches = await data_sources.api_football.get_team_matches(team_name)
    
    # Convert to DTOs
    match_dtos = []
    for match in matches:
        match_dtos.append(MatchDTO(
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
        ))
        
    return match_dtos
