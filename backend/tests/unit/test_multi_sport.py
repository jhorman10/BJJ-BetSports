"""Tests for multi-sport plumbing (sport catalog, enum, mapper, loader)."""

import pytest

from src.domain.constants import DEFAULT_SPORT, Sport, LEAGUES_METADATA


class TestSportEnum:
    """Sport enum exposes exactly the four supported sports."""

    def test_enum_values(self):
        assert Sport.SOCCER.value == "soccer"
        assert Sport.TENNIS.value == "tennis"
        assert Sport.BASEBALL.value == "baseball"
        assert Sport.BASKETBALL.value == "basketball"
        assert set(Sport.__members__) == {
            "SOCCER",
            "TENNIS",
            "BASEBALL",
            "BASKETBALL",
        }

    def test_default_sport(self):
        assert DEFAULT_SPORT == "soccer"


class TestSportFieldInMetadata:
    """All leagues carry a sport field, defaulting to soccer."""

    def test_existing_leagues_default_to_soccer(self):
        # Every league in metadata must have sport, defaulting to soccer
        for league_id, meta in LEAGUES_METADATA.items():
            sport = meta.get("sport", "soccer")
            assert sport in ("soccer", "tennis", "baseball", "basketball")

    def test_new_sport_placeholders_exist(self):
        # Tennis, baseball, basketball placeholders present in dataset
        from src.infrastructure.data.league_loader import dataset

        tennis = dataset.get_by_sport("tennis")
        baseball = dataset.get_by_sport("baseball")
        basketball = dataset.get_by_sport("basketball")

        assert len(tennis) > 0
        assert len(baseball) > 0
        assert len(basketball) > 0

        # Placeholder leagues are inactive
        for league in tennis + baseball + basketball:
            assert league.get("active") is False

    def test_sport_prefixed_ids_unique(self):
        from src.infrastructure.data.league_loader import dataset

        # Sport-prefixed league IDs exist (B_, T_, K_)
        ids = {league["id"] for league in dataset.get_by_sport("baseball")}
        assert any(i.startswith("B_") for i in ids)
        tennis_ids = {league["id"] for league in dataset.get_by_sport("tennis")}
        assert any(i.startswith("T_") for i in tennis_ids)
        basketball_ids = {league["id"] for league in dataset.get_by_sport("basketball")}
        assert any(i.startswith("K_") for i in basketball_ids)


class TestLeagueDatasetSportIndex:
    """LeagueDataset.get_by_sport returns only leagues for that sport."""

    def test_get_by_sport_tennis(self):
        from src.infrastructure.data.league_loader import dataset

        tennis = dataset.get_by_sport("tennis")
        assert all(l.get("sport") == "tennis" for l in tennis)

    def test_get_by_sport_soccer_returns_all_soccer(self):
        from src.infrastructure.data.league_loader import dataset

        soccer = dataset.get_by_sport("soccer")
        # All original football leagues are soccer
        for league in soccer:
            assert league.get("sport") == "soccer"

    def test_unknown_sport_empty(self):
        from src.infrastructure.data.league_loader import dataset

        assert dataset.get_by_sport("cricket") == []

    def test_to_leagues_metadata_sport_filter(self):
        import src.infrastructure.data.league_loader as loader

        dataset = loader.dataset
        baseball_meta = dataset.to_leagues_metadata(sport="baseball")
        assert len(baseball_meta) > 0
        assert all(
            meta.get("sport", "soccer") == "baseball" for meta in baseball_meta.values()
        )


class TestLeagueMapperSportFilter:
    """build_leagues_response filters by sport."""

    def test_build_leagues_response_filters_soccer(self):
        from src.api.mappers.league_mapper import build_leagues_response

        resp = build_leagues_response(sport="soccer")
        assert resp.total_leagues > 0
        for country in resp.countries:
            for league in country.leagues:
                assert league.sport == "soccer"

    def test_build_leagues_response_tennis(self):
        from src.api.mappers.league_mapper import build_leagues_response

        resp = build_leagues_response(sport="tennis")
        assert resp.total_leagues > 0
        for country in resp.countries:
            for league in country.leagues:
                assert league.sport == "tennis"

    def test_build_leagues_response_unknown_empty(self):
        from src.api.mappers.league_mapper import build_leagues_response

        resp = build_leagues_response(sport="cricket")
        assert resp.countries == []
        assert resp.total_leagues == 0

    def test_find_league_with_sport(self):
        from src.api.mappers.league_mapper import find_league

        league = find_league("E0", sport="soccer")
        assert league.id == "E0"
        assert league.sport == "soccer"

    def test_find_league_sport_mismatch_raises(self):
        import pytest as _pytest

        from src.api.mappers.league_mapper import find_league
        from fastapi import HTTPException

        with _pytest.raises(HTTPException) as excinfo:
            find_league("B_MLB", sport="soccer")
        assert excinfo.value.status_code == 404


class TestLeagueEntitySport:
    """League entity carries sport field with default."""

    def test_default_sport(self):
        from src.domain.entities.entities import League

        league = League(id="E0", name="Premier League", country="England")
        assert league.sport == "soccer"

    def test_explicit_sport(self):
        from src.domain.entities.entities import League

        league = League(
            id="B_MLB", name="MLB", country="United States", sport="baseball"
        )
        assert league.sport == "baseball"
