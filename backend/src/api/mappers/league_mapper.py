from __future__ import annotations

from collections import defaultdict

from fastapi import HTTPException
from src.api.schemas.leagues import CountryModel, LeagueModel, LeaguesResponse
from src.domain.constants import LEAGUES_METADATA


def build_leagues_response(sport: str = "soccer") -> LeaguesResponse:
    grouped: dict[str, list[LeagueModel]] = defaultdict(list)
    for league_id, metadata in LEAGUES_METADATA.items():
        league_sport = metadata.get("sport", "soccer")
        if league_sport != sport:
            continue
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
            leagues=sorted(leagues, key=lambda league: league.name),
        )
        for country, leagues in sorted(grouped.items(), key=lambda item: item[0])
    ]
    total = sum(len(leagues) for leagues in grouped.values())
    return LeaguesResponse(countries=countries, total_leagues=total)


def find_league(league_id: str, sport: str = "soccer") -> LeagueModel:
    metadata = LEAGUES_METADATA.get(league_id)
    if metadata is None:
        raise HTTPException(status_code=404, detail="Liga no encontrada")
    league_sport = metadata.get("sport", "soccer")
    if league_sport != sport:
        raise HTTPException(status_code=404, detail="Liga no encontrada para este deporte")
    return LeagueModel(
        id=league_id,
        name=metadata["name"],
        country=metadata["country"],
        sport=league_sport,
    )
