from typing import List
from fastapi import APIRouter, HTTPException, Depends
from src.application.dtos.dtos import MatchDTO, TeamDTO, LeagueDTO, ErrorResponseDTO
from src.application.use_cases.use_cases import DataSources
from src.api.dependencies import get_data_sources

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
