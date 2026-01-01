"""
API Dependencies Module

Provides dependency injection for FastAPI routes.
Contains factory functions for creating use case dependencies.
"""

from functools import lru_cache

from src.infrastructure.data_sources.football_data_uk import FootballDataUKSource
from src.infrastructure.data_sources.football_data_org import FootballDataOrgSource
from src.infrastructure.data_sources.openfootball import OpenFootballSource
from src.infrastructure.data_sources.thesportsdb import TheSportsDBClient
from src.infrastructure.cache.cache_service import CacheService, get_cache_service
from src.domain.services.prediction_service import PredictionService
from src.domain.services.statistics_service import StatisticsService
from src.domain.services.match_enrichment_service import MatchEnrichmentService
from src.domain.services.pick_resolution_service import PickResolutionService
from src.application.services.training_data_service import TrainingDataService
from src.application.use_cases.use_cases import DataSources


@lru_cache()
def get_football_data_uk() -> FootballDataUKSource:
    """Get Football-Data.co.uk data source (cached)."""
    return FootballDataUKSource()


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

@lru_cache()
def get_match_enrichment_service() -> MatchEnrichmentService:
    """Get match enrichment service (cached)."""
    return MatchEnrichmentService(statistics_service=get_statistics_service())

@lru_cache()
def get_pick_resolution_service() -> PickResolutionService:
    """Get pick resolution service (cached)."""
    return PickResolutionService()

@lru_cache()
def get_training_data_service() -> TrainingDataService:
    """Get training data service (cached)."""
    return TrainingDataService(
        data_sources=get_data_sources(),
        enrichment_service=get_match_enrichment_service()
    )
from src.application.services.ml_training_orchestrator import MLTrainingOrchestrator

@lru_cache()
def get_ml_training_orchestrator() -> MLTrainingOrchestrator:
    """Get ML training orchestrator service (cached)."""
    return MLTrainingOrchestrator(
        training_data_service=get_training_data_service(),
        statistics_service=get_statistics_service(),
        prediction_service=get_prediction_service(),
        learning_service=get_learning_service(),
        resolution_service=get_pick_resolution_service(),
        cache_service=get_cache_service()
    )

from src.domain.services.audit_service import AuditService

@lru_cache()
def get_audit_service() -> AuditService:
    """Get audit service (cached)."""
    return AuditService(
        training_orchestrator=get_ml_training_orchestrator()
    )
