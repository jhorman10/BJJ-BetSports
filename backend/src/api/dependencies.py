"""
API Dependencies Module

Provides dependency injection for FastAPI routes.
Contains factory functions for creating use case dependencies.
"""

from functools import lru_cache

from src.infrastructure.data_sources.football_data_uk import FootballDataUKSource
from src.infrastructure.data_sources.api_football import APIFootballSource
from src.infrastructure.data_sources.football_data_org import FootballDataOrgSource
from src.domain.services.prediction_service import PredictionService
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


def get_data_sources() -> DataSources:
    """Get all data sources container."""
    return DataSources(
        football_data_uk=get_football_data_uk(),
        api_football=get_api_football(),
        football_data_org=get_football_data_org(),
    )


@lru_cache()
def get_prediction_service() -> PredictionService:
    """Get prediction service (cached)."""
    return PredictionService()
