import asyncio
import logging
import sys
import os
from fastapi import FastAPI
import uvicorn

# Ensure the root directory is in the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from src.api.dependencies import get_ml_training_orchestrator
from src.core.constants import DEFAULT_LEAGUES

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def start_health_check_server():
    """
    Starts a lightweight web server to satisfy Render's port binding requirement.
    This prevents the deployment from timing out while the script runs.
    """
    app = FastAPI()
    
    @app.get("/")
    async def root():
        return {"status": "training_in_progress"}
        
    port = int(os.environ.get("PORT", 10000))
    logger.info(f"Starting health check server on port {port}")
    
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="warning")
    server = uvicorn.Server(config)
    await server.serve()

async def main():
    """
    Main entry point for standalone ML training.
    Uses the same orchestrator as the API to ensure logic parity.
    """
    # Start health check server immediately to satisfy Render's port requirement
    asyncio.create_task(start_health_check_server())
    
    logger.info("Starting standalone ML Training Session...")
    
    # Get the orchestrator instance
    # Note: In a real CLI, you might want to bypass lru_cache for a fresh start
    orchestrator = get_ml_training_orchestrator()
    
    # Run the full training pipeline
    try:
        result = await orchestrator.run_training_pipeline(
            league_ids=DEFAULT_LEAGUES,
            days_back=365
        )
        
        logger.info("Training session completed successfully.")
        logger.info(f"Processed Matches: {result.matches_processed}")
        logger.info(f"Accuracy: {result.accuracy * 100:.2f}%")
        logger.info(f"ROI: {result.roi:.2f}%")
        logger.info(f"Profit Units: {result.profit_units:.2f}")
        
        # PERSIST TO CACHE
        from src.infrastructure.cache import get_training_cache
        cache = get_training_cache()
        
        # Convert Result to the same structure expected by the BotStore/Dashboard
        # (This matches the transformation in learning.py)
        history_limit = 500
        display_history = result.match_history[-history_limit:] if len(result.match_history) > history_limit else result.match_history
        
        cache_data = {
            "matches_processed": result.matches_processed,
            "correct_predictions": result.correct_predictions,
            "accuracy": result.accuracy,
            "total_bets": result.total_bets,
            "roi": result.roi,
            "profit_units": result.profit_units,
            "market_stats": result.market_stats,
            "match_history": display_history,
            "roi_evolution": result.roi_evolution,
            "pick_efficiency": result.pick_efficiency,
            "team_stats": result.team_stats
        }
        
        cache.set_training_results(cache_data)
        logger.info("Training results persisted to application cache.")
        
        # Keep the process alive if running on Render to prevent restart loops
        if os.environ.get("RENDER"):
            logger.info("Running on Render: Keeping process alive to serve health checks.")
            await asyncio.Event().wait()
        
    except Exception as e:
        logger.error(f"Training session failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
