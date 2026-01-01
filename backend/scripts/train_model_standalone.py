
import asyncio
import os
import sys
import logging
from datetime import datetime
import warnings

# Add backend directory to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("StandaloneTrainer")

# Lazy imports will happen inside main
# Suppress DeprecationWarnings from utcnow() used in ML libraries
warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*utcnow.*")

async def train_model():
    """
    Standalone function to run ML training.
    """
    logger.info("Starting Standalone Model Training...")
    
    # 1. Initialize Dependency Injection Container (Manual)
    from src.api.dependencies import (
        get_data_sources, 
        get_statistics_service, 
        get_learning_service, 
        get_prediction_service,
        get_pick_resolution_service,
        get_cache_service
    )
    from src.application.services.training_data_service import TrainingDataService
    from src.domain.services.match_enrichment_service import MatchEnrichmentService
    from src.application.services.ml_training_orchestrator import MLTrainingOrchestrator
    
    # Initialize Services
    data_sources = get_data_sources()
    cache_service = get_cache_service()
    statistics_service = get_statistics_service()
    enrichment_service = MatchEnrichmentService(statistics_service=statistics_service)
    training_data_service = TrainingDataService(data_sources=data_sources, enrichment_service=enrichment_service)
    learning_service = get_learning_service()
    prediction_service = get_prediction_service()
    resolution_service = get_pick_resolution_service()
    
    # Initialize Orchestrator
    orchestrator = MLTrainingOrchestrator(
        training_data_service=training_data_service,
        statistics_service=statistics_service,
        prediction_service=prediction_service,
        learning_service=learning_service,
        resolution_service=resolution_service,
        cache_service=cache_service
    )
    
    # 2. Run Training
    try:
        # Use 365 days back for robust training
        result = await orchestrator.run_training_pipeline(
            league_ids=None, # All default leagues
            days_back=365,
            force_refresh=True
        )
        
        logger.info(f"Training Complete!")
        logger.info(f"Accuracy: {result.accuracy * 100:.2f}%")
        logger.info(f"ROI: {result.roi}%")
        logger.info(f"Profit: {result.profit_units} units")
        
        # Check if joblib file exists
        if os.path.exists("ml_picks_classifier.joblib"):
             logger.info("SUCCESS: ml_picks_classifier.joblib generated.")
        else:
             logger.error("FAILURE: Model file not found after training.")
             sys.exit(1)
             
    except Exception as e:
        logger.error(f"Training Failed: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(train_model())
