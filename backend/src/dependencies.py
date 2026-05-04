"""
API Dependencies Module

Provides dependency injection for FastAPI routes.
Contains factory functions for creating use case dependencies.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from src.application.services.ml_training_orchestrator import MLTrainingOrchestrator
from src.application.services.training_data_service import TrainingDataService
from src.application.training.catalog import (
    ModelRegistryService,
    TrainingCapabilityService,
    TrainingExecutorRegistry,
)
from src.application.training.executors import PassiveTrainingExecutor
from src.application.training.job_service import TrainingJobService
from src.application.training.result_reader import TrainingResultReader
from src.application.use_cases.use_cases import DataSources
from src.domain.services.ai_picks_service import AIPicksService
from src.domain.services.audit_service import AuditService
from src.domain.services.learning_service import LearningService
from src.domain.services.match_aggregator_service import MatchAggregatorService
from src.domain.services.match_enrichment_service import MatchEnrichmentService
from src.domain.services.parley_service import ParleyService
from src.domain.services.pick_resolution_service import PickResolutionService
from src.domain.services.prediction_service import PredictionService
from src.domain.services.risk_management.risk_manager import RiskManager
from src.domain.services.statistics_service import StatisticsService
from src.infrastructure.cache.cache_service import get_cache_service
from src.infrastructure.data_sources.espn import ESPNSource
from src.infrastructure.data_sources.football_data_org import FootballDataOrgSource
from src.infrastructure.data_sources.football_data_uk import FootballDataUKSource
from src.infrastructure.data_sources.openfootball import OpenFootballSource
from src.infrastructure.data_sources.thesportsdb import TheSportsDBClient
from src.infrastructure.repositories.async_mongo_adapter import (
    get_async_mongo_repository,
)
from src.infrastructure.repositories.mongo_repository import (
    MongoRepository,
    get_mongo_repository,
)
from src.infrastructure.services.background_processor import BackgroundProcessor
from src.infrastructure.training.repositories import (
    TrainingJobEventRepository,
    TrainingJobRepository,
)


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


@lru_cache()
def get_espn_source() -> ESPNSource:
    """Get ESPN data source (cached)."""
    return ESPNSource()


def get_data_sources() -> DataSources:
    """Get all data sources container."""
    return DataSources(
        football_data_uk=get_football_data_uk(),
        football_data_org=get_football_data_org(),
        openfootball=get_openfootball(),
        thesportsdb=get_thesportsdb(),
        espn=get_espn_source(),
    )


# ... (Keeping existing code) ...


@lru_cache()
def get_match_aggregator_service() -> MatchAggregatorService:
    """Get MatchAggregatorService (cached)."""
    return MatchAggregatorService(
        football_data_uk=get_football_data_uk(),
        football_data_org=get_football_data_org(),
        openfootball=get_openfootball(),
        thesportsdb=get_thesportsdb(),
        espn=get_espn_source(),
    )


@lru_cache()
def get_prediction_service() -> PredictionService:
    """Get prediction service (cached)."""
    return PredictionService()


@lru_cache()
def get_statistics_service() -> StatisticsService:
    """Get statistics service (cached)."""
    return StatisticsService()


@lru_cache()
def get_learning_service() -> LearningService:
    """Get learning service (cached)."""
    return LearningService(persistence_repo=get_persistence_repository())


@lru_cache()
def get_parley_service() -> ParleyService:
    """Get parley service (cached)."""
    return ParleyService()


@lru_cache()
def get_picks_service() -> AIPicksService:
    """Get AI picks service (cached)."""
    return AIPicksService(
        learning_weights=get_learning_service().learning_weights,
        persistence_repo=get_persistence_repository(),
    )


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
        enrichment_service=get_match_enrichment_service(),
    )


@lru_cache()
def get_persistence_repository() -> MongoRepository:
    """Get the mongo repository instance (cached singleton)."""
    return get_mongo_repository()


def get_async_persistence_repository() -> Any:
    """Return an async-friendly persistence repository (Motor-native when available).

    Use this in FastAPI async handlers to avoid blocking the event loop.
    """
    return get_async_mongo_repository()


@lru_cache()
def get_training_model_registry() -> ModelRegistryService:
    """Get the model registry service for training capabilities."""
    return ModelRegistryService.build_default()


@lru_cache()
def get_training_executor_registry() -> TrainingExecutorRegistry:
    """Get the executor registry service for training capabilities."""
    return TrainingExecutorRegistry.build_default()


@lru_cache()
def get_training_capability_service() -> TrainingCapabilityService:
    """Get the training capability service (cached)."""
    return TrainingCapabilityService(
        model_registry=get_training_model_registry(),
        executor_registry=get_training_executor_registry(),
    )


@lru_cache()
def get_training_result_reader() -> TrainingResultReader:
    """Get the reader for the latest persisted training result."""
    return TrainingResultReader(repository=get_persistence_repository())


@lru_cache()
def get_training_job_service() -> TrainingJobService:
    """Get the training job control-plane service (cached)."""
    persistence_repo = get_persistence_repository()
    return TrainingJobService(
        job_repository=TrainingJobRepository(persistence_repo=persistence_repo),
        event_repository=TrainingJobEventRepository(persistence_repo=persistence_repo),
        executor=PassiveTrainingExecutor(),
        model_registry=get_training_model_registry(),
        executor_registry=get_training_executor_registry(),
    )


async def get_async_learning_service() -> "LearningService":
    """Async factory that returns a LearningService-like object preloaded with
    learning weights fetched from the async repository.

    This avoids calling the sync `LearningService._load_weights` inside the
    event loop.
    """
    repo = get_async_persistence_repository()
    svc = LearningService(persistence_repo=None)
    try:
        data = await repo.get_app_state(LearningService.MONGO_KEY)
    except Exception:
        data = None

    if data:
        try:
            svc._learning_weights = svc._reconstruct_weights(data)
        except Exception:
            svc._learning_weights = svc.learning_weights
    else:
        svc._learning_weights = svc.learning_weights

    return svc


@lru_cache()
def get_ml_training_orchestrator() -> "MLTrainingOrchestrator":
    """Get ML training orchestrator service (cached)."""
    # Import inside the factory to avoid importing heavy training modules at import-time
    # and to reduce risk of circular imports during module initialization.
    from src.application.services.ml_training_orchestrator import MLTrainingOrchestrator

    return MLTrainingOrchestrator(
        training_data_service=get_training_data_service(),
        statistics_service=get_statistics_service(),
        prediction_service=get_prediction_service(),
        learning_service=get_learning_service(),
        resolution_service=get_pick_resolution_service(),
        cache_service=get_cache_service(),
        persistence_repo=get_persistence_repository(),
    )


@lru_cache()
def get_audit_service() -> AuditService:
    """Get audit service (cached)."""
    return AuditService(training_orchestrator=get_ml_training_orchestrator())


@lru_cache()
def get_background_processor() -> BackgroundProcessor:
    """Get background processor (cached singleton)."""
    return BackgroundProcessor()


@lru_cache()
def get_risk_manager() -> RiskManager:
    """Get RiskManager (cached)."""
    return RiskManager()
