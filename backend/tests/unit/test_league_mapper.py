from src.api.mappers.league_mapper import build_leagues_response, find_league
from src.domain.constants import LEAGUES_METADATA


def test_build_leagues_response_contains_metadata():
    resp = build_leagues_response(sport="soccer")
    # build_leagues_response filters to soccer only; LEAGUES_METADATA now includes
    # placeholder sports, so assert every returned league is soccer rather than
    # a raw count comparison.
    assert resp.total_leagues > 0
    all_leagues = [
        league for country in resp.countries for league in country.leagues
    ]
    assert all(league.sport == "soccer" for league in all_leagues)


def test_find_league_valid():
    # pick a known league id from constants
    league_id = next(iter(LEAGUES_METADATA.keys()))
    league = find_league(league_id, sport="soccer")
    assert league.id == league_id
