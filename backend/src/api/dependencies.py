"""
API Dependencies Module

Provides dependency injection for FastAPI routes.
Contains factory functions for creating use case dependencies.
"""

from functools import lru_cache

from src.infrastructure.data_sources.football_data_uk import FootballDataUKSource
from src.infrastructure.data_sources.api_football import APIFootballSource
from src.infrastructure.data_sources.football_data_org import FootballDataOrgSource
from src.infrastructure.data_sources.openfootball import OpenFootballSource
from src.infrastructure.data_sources.thesportsdb import TheSportsDBClient
from src.infrastructure.cache.cache_service import CacheService, get_cache_service
from src.domain.services.prediction_service import PredictionService
from src.domain.services.statistics_service import StatisticsService
from src.application.use_cases.use_cases import DataSources


@lru_cache()
def get_football_data_uk() -> FootballDataUKSource:
    """Get Football-Data.co.uk data source (cached)."""
    return FootballDataUKSource()


@lru_cache()
def get_api_football() -> APIFootballSource:
    """Get API-Football data source (cached)."""
    return APIFootballSource()


@lru_cache()
def get_football_data_org() -> FootballDataOrgSource:
    """Get Football-Data.org data source (cached)."""
    return FootballDataOrgSource()


@lru_cache()
def get_openfootball() -> OpenFootballSource:
    """Get OpenFootball data source (cached)."""
    return OpenFootballSource()


@lru_cache()
def get_thesportsdb() -> TheSportsDBClient:
    """Get TheSportsDB data source (cached)."""
    return TheSportsDBClient()


def get_data_sources() -> DataSources:
    """Get all data sources container."""
    return DataSources(
        football_data_uk=get_football_data_uk(),
        api_football=get_api_football(),
        football_data_org=get_football_data_org(),
        openfootball=get_openfootball(),
        thesportsdb=get_thesportsdb(),
    )


from src.domain.services.statistics_service import StatisticsService


@lru_cache()
def get_prediction_service() -> PredictionService:
    """Get prediction service (cached)."""
    return PredictionService()


@lru_cache()
def get_statistics_service() -> StatisticsService:
    """Get statistics service (cached)."""
    return StatisticsService()


from src.domain.services.learning_service import LearningService


@lru_cache()
def get_learning_service() -> LearningService:
    """Get learning service (cached)."""
    return LearningService()


from src.domain.services.parley_service import ParleyService

@lru_cache()
def get_parley_service() -> ParleyService:
    """Get parley service (cached)."""
    return ParleyService()

from src.domain.services.picks_service import PicksService

@lru_cache()
def get_picks_service() -> PicksService:
    """Get picks service (cached)."""
    return PicksService()
