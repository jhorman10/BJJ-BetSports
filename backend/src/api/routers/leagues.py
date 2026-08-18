from __future__ import annotations

from fastapi import APIRouter
from src.api.mappers.league_mapper import build_leagues_response, find_league
from src.api.schemas.leagues import LeagueModel, LeaguesResponse

router = APIRouter(prefix="/api/v1/leagues", tags=["leagues"])


@router.get("", response_model=LeaguesResponse)
def get_leagues() -> LeaguesResponse:
    return build_leagues_response()


@router.get("/{league_id}", response_model=LeagueModel)
def get_league(league_id: str) -> LeagueModel:
    return find_league(league_id)
