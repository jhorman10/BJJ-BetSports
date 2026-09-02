from __future__ import annotations

from pydantic import BaseModel


class LeagueModel(BaseModel):
    id: str
    name: str
    country: str
    sport: str = "soccer"


class CountryModel(BaseModel):
    name: str
    code: str
    flag: str | None = None
    leagues: list[LeagueModel]


class LeaguesResponse(BaseModel):
    countries: list[CountryModel]
    total_leagues: int
