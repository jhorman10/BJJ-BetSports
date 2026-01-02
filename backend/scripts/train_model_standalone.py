import asyncio
import os
import sys
import argparse
import logging

# Ensure backend directory is in the path so we can import src
# This script is expected to be run from the 'backend' directory
sys.path.append(os.getcwd())

from src.api.dependencies import get_ml_training_orchestrator
from src.infrastructure.cache.cache_service import get_cache_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("train_model_standalone")

async def main():
    parser = argparse.ArgumentParser(description="Standalone ML Training Script")
    parser.add_argument("--days-back", type=int, default=365, help="Number of days of historical data to fetch")
    parser.add_argument("--leagues", type=str, nargs="+", default=None, help="List of league IDs to train on")
    parser.add_argument("--force-refresh", action="store_true", help="Force refresh of external data")
    
    args = parser.parse_args()
    
    logger.info("Initializing ML Training Orchestrator...")
    orchestrator = get_ml_training_orchestrator()
    
    # Check if disabled by env var (as in the workflow)
    if os.getenv("DISABLE_ML_TRAINING", "false").lower() == "true":
        logger.info("ML training is disabled via environment variable. Skipping.")
        return

    logger.info(f"Starting training pipeline (days_back={args.days_back}, leagues={args.leagues}, force_refresh={args.force_refresh})")
    
    try:
        result = await orchestrator.run_training_pipeline(
            league_ids=args.leagues,
            days_back=args.days_back,
            force_refresh=args.force_refresh
        )
        
        logger.info("Training completed successfully!")
        logger.info(f"Matches Processed: {result.matches_processed}")
        logger.info(f"Accuracy: {result.accuracy:.4f}")
        logger.info(f"ROI: {result.roi:.2f}%")
        logger.info(f"Profit Units: {result.profit_units:.2f}")
        
    except Exception as e:
        logger.error(f"Training failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
