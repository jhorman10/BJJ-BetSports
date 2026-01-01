
import asyncio
import logging
import concurrent.futures
from typing import List, Optional
import multiprocessing

from src.domain.entities.entities import Match, TeamStatistics
from src.application.dtos.dtos import MatchDTO, MatchPredictionDTO
from src.domain.services.picks_service import PicksService

logger = logging.getLogger(__name__)

# Global worker state
_picks_service: Optional[PicksService] = None

def _init_worker():
    """
    Initialize the worker process.
    This runs once per process to load the ML model and heavy dependencies.
    """
    global _picks_service
    # Initialize service (loads ML model)
    try:
        _picks_service = PicksService()
        logger.info(f"Worker process initialized PicksService (PID: {multiprocessing.current_process().pid})")
    except Exception as e:
        logger.error(f"Failed to initialize worker PicksService: {e}")

def _process_match_task(
    match: Match,
    home_stats: Optional[TeamStatistics],
    away_stats: Optional[TeamStatistics],
    league_averages: Optional[any], # localized type issue, passing object
    h2h_stats: Optional[any],
    prediction_data: dict
):
    """
    Worker function to process a single match.
    Uses the global _picks_service instance.
    """
    global _picks_service
    if _picks_service is None:
        return None
        
    try:
        # Extract prediction data
        pred_home = prediction_data.get('predicted_home_goals', 0.0)
        pred_away = prediction_data.get('predicted_away_goals', 0.0)
        p_home = prediction_data.get('home_win_probability', 0.0)
        p_draw = prediction_data.get('draw_probability', 0.0)
        p_away = prediction_data.get('away_win_probability', 0.0)
        
        # Generate picks
        suggested = _picks_service.generate_suggested_picks(
            match=match,
            home_stats=home_stats,
            away_stats=away_stats,
            league_averages=league_averages,
            h2h_stats=h2h_stats,
            predicted_home_goals=pred_home,
            predicted_away_goals=pred_away,
            home_win_prob=p_home,
            draw_prob=p_draw,
            away_win_prob=p_away
        )
        return suggested
        
    except Exception as e:
        logger.error(f"Error processing match {match.id} in worker: {e}")
        return None

class BackgroundProcessor:
    """
    Service to handle background processing and parallel execution.
    """
    
    def __init__(self, max_workers: int = None):
        # Default to CPU count or 4
        self.max_workers = max_workers or multiprocessing.cpu_count()
        self.executor = concurrent.futures.ProcessPoolExecutor(
            max_workers=self.max_workers,
            initializer=_init_worker
        )
        logger.info(f"BackgroundProcessor initialized with {self.max_workers} workers")

    async def process_matches_parallel(self, match_tasks: List[dict]) -> List[any]:
        """
        Process a batch of matches in parallel.
        
        Args:
            match_tasks: List of dicts containing arguments for _process_match_task
        
        Returns:
            List of results (MatchSuggestedPicks)
        """
        loop = asyncio.get_running_loop()
        
        # Dispatch tasks to executor
        futures = []
        for task in match_tasks:
            args = (
                task['match'],
                task['home_stats'],
                task['away_stats'],
                task['league_averages'],
                task['h2h_stats'],
                task['prediction_data']
            )
            futures.append(
                loop.run_in_executor(self.executor, _process_match_task, *args)
            )
            
        # Wait for all
        results = await asyncio.gather(*futures, return_exceptions=True)
        
        # Filter exceptions
        valid_results = []
        for r in results:
            if isinstance(r, Exception):
                logger.error(f"Parallel execution error: {r}")
            elif r:
                valid_results.append(r)
                
        return valid_results
        
    def shutdown(self):
        self.executor.shutdown()
