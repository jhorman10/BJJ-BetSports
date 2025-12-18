"""
Leagues Router

API endpoints for managing leagues and countries.
"""

from fastapi import APIRouter, HTTPException

from src.application.dtos.dtos import LeaguesResponseDTO, ErrorResponseDTO
from src.api.dependencies import get_data_sources


router = APIRouter(prefix="/leagues", tags=["Leagues"])


@router.get(
    "",
    response_model=LeaguesResponseDTO,
    responses={
        500: {"model": ErrorResponseDTO, "description": "Internal server error"},
    },
    summary="Get all available leagues",
    description="Returns a list of all available football leagues grouped by country.",
)
async def get_leagues() -> LeaguesResponseDTO:
    """Get all available leagues."""
    from src.application.use_cases.use_cases import GetLeaguesUseCase, DataSources
    
    data_sources = get_data_sources()
    use_case = GetLeaguesUseCase(data_sources)
    
    try:
        return await use_case.execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{league_id}",
    summary="Get league details",
    description="Get details for a specific league by ID.",
)
async def get_league(league_id: str):
    """Get details for a specific league."""
    from src.infrastructure.data_sources.football_data_uk import LEAGUES_METADATA
    from src.application.dtos.dtos import LeagueDTO
    
    if league_id not in LEAGUES_METADATA:
        raise HTTPException(status_code=404, detail=f"League not found: {league_id}")
    
    meta = LEAGUES_METADATA[league_id]
    return LeagueDTO(
        id=league_id,
        name=meta["name"],
        country=meta["country"],
    )
