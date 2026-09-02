from __future__ import annotations

from collections import defaultdict

from fastapi import APIRouter, Query
from src.api.mappers.league_mapper import build_leagues_response, find_league
from src.api.schemas.leagues import CountryModel, LeagueModel, LeaguesResponse
from src.domain.constants import DEFAULT_SPORT
from src.infrastructure.repositories.async_mongo_adapter import (
    get_async_mongo_repository,
)

router = APIRouter(prefix="/api/v1/leagues", tags=["leagues"])


@router.get("", response_model=LeaguesResponse)
def get_leagues(sport: str = Query(DEFAULT_SPORT)) -> LeaguesResponse:
    return build_leagues_response(sport=sport)


@router.get("/active", response_model=LeaguesResponse)
async def get_leagues_with_predictions(
    sport: str = Query(DEFAULT_SPORT),
) -> LeaguesResponse:
    """Return only leagues that have active predictions in the database."""
    repo = get_async_mongo_repository()
    active_league_ids = await repo.get_league_ids_with_predictions(sport=sport)

    if not active_league_ids:
        return LeaguesResponse(countries=[], total_leagues=0)

    from src.domain.constants import LEAGUES_METADATA

    grouped: dict[str, list[LeagueModel]] = defaultdict(list)
    for league_id in active_league_ids:
        metadata = LEAGUES_METADATA.get(league_id)
        if metadata:
            league_sport = metadata.get("sport", "soccer")
            grouped[metadata["country"]].append(
                LeagueModel(
                    id=league_id,
                    name=metadata["name"],
                    country=metadata["country"],
                    sport=league_sport,
                )
            )

    countries = [
        CountryModel(
            name=country,
            code=country[:2].upper(),
            leagues=sorted(leagues, key=lambda l: l.name),
        )
        for country, leagues in sorted(grouped.items(), key=lambda item: item[0])
    ]
    return LeaguesResponse(countries=countries, total_leagues=len(active_league_ids))


@router.get("/{league_id}", response_model=LeagueModel)
def get_league(league_id: str, sport: str = Query(DEFAULT_SPORT)) -> LeagueModel:
    return find_league(league_id, sport=sport)
