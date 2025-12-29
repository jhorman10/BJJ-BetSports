
import logging
import asyncio
from typing import List, Optional, Dict
from datetime import datetime
from pytz import timezone
from src.domain.entities.entities import Match
from src.application.use_cases.suggested_picks_use_case import GetSuggestedPicksUseCase
from src.infrastructure.cache.cache_service import CacheService
from src.application.use_cases.use_cases import DataSources
from src.domain.services.prediction_service import PredictionService
from src.domain.services.statistics_service import StatisticsService
from src.domain.services.learning_service import LearningService
from src.application.dtos.dtos import (
    MatchSuggestedPicksDTO, 
    MatchPredictionDTO, 
    PredictionsResponseDTO, 
    LeagueDTO
)

logger = logging.getLogger(__name__)

class CacheWarmupService:
    """
    Service responsible for warming up the cache on startup.
    Pre-generates suggested picks for all upcoming matches to ensure zero-latency for users.
    """
    
    def __init__(
        self,
        data_sources: DataSources,
        cache_service: CacheService,
        prediction_service: PredictionService,
        statistics_service: StatisticsService,
        learning_service: LearningService,
    ):
        self.data_sources = data_sources
        self.cache_service = cache_service
        self.prediction_service = prediction_service
        self.statistics_service = statistics_service
        self.learning_service = learning_service
        
        self.picks_use_case = GetSuggestedPicksUseCase(
            data_sources=data_sources,
            prediction_service=prediction_service,
            statistics_service=statistics_service,
            learning_service=learning_service,
        )

    async def warm_up_predictions(self, lookahead_days: int = 7):
        """
        Main entry point for cache warmup.
        Fetches upcoming matches and generates/caches picks (predicted & suggested) for all of them.
        """
        logger.info(f"🔥 Starting Cache Warmup (Lookahead: {lookahead_days} days)...")
        
        # 1. Fetch all upcoming matches
        upcoming_matches = await self._fetch_all_upcoming_matches(lookahead_days)
        logger.info(f"🔥 Found {len(upcoming_matches)} upcoming matches to process.")
        
        if not upcoming_matches:
            logger.warning("No matches found for warmup.")
            return

        # 2. Process sequentially
        total_processed = 0
        league_predictions: Dict[str, List[MatchPredictionDTO]] = {}
        processed_leagues = {} # To keep track of league details for DTO
        
        for match in upcoming_matches:
            # Run one by one
            result = await self._process_single_match(match)
            total_processed += 1
            
            # 3. Aggregate for League Cache
            if result:
                league_id = match.league.id
                if league_id not in league_predictions:
                    league_predictions[league_id] = []
                    processed_leagues[league_id] = match.league

                # Convert MatchSuggestedPicksDTO to MatchPredictionDTO for the list view
                mp_dto = MatchPredictionDTO(
                    match=result.match,
                    prediction=result.prediction,
                )
                
                league_predictions[league_id].append(mp_dto)
            
            if total_processed % 5 == 0:
                 logger.info(f"🔥 Warmup Progress: {total_processed}/{len(upcoming_matches)} matches processed")
            
            # Polite delay
            await asyncio.sleep(7) 

        # 4. Save Aggregated League Caches
        COLOMBIA_TZ = timezone('America/Bogota')
        today_str = datetime.now(COLOMBIA_TZ).strftime("%Y-%m-%d")
        
        for league_id, preds in league_predictions.items():
            if not preds:
                continue
                
            league_obj = processed_leagues[league_id]
            
            response_dto = PredictionsResponseDTO(
                league=LeagueDTO(
                    id=league_obj.id,
                    name=league_obj.name,
                    country=league_obj.country,
                    season=league_obj.season
                ),
                predictions=preds,
                generated_at=datetime.utcnow()
            )
            
            cache_key = f"forecasts:league_{league_id}:date_{today_str}"
            self.cache_service.set(cache_key, response_dto.model_dump(), ttl_seconds=3600*24)
            logger.info(f"✅ Cached Aggregated Predictions for League {league_id} ({len(preds)} matches)")

        logger.info("🔥 Cache Warmup Complete! All matches are pre-cached.")

    # ... (rest of _fetch_all_upcoming_matches is unchanged, skipping in replacement content if not replaced)

    async def _process_single_match(self, match: Match) -> Optional[MatchSuggestedPicksDTO]:
        """Generate and cache picks for a single match."""
        try:
            result = await self.picks_use_case.execute(match.id)
            
            if result:
                cache_key = f"forecasts:match_{match.id}"
                self.cache_service.set(cache_key, result.model_dump(), ttl_seconds=3600*24) # 24h cache
                logger.info(f"  ✓ Cached: {match.home_team.name} vs {match.away_team.name}")
                return result
            else:
                logger.warning(f"  ✗ Failed to generate picks for: {match.id}")
                return None
                
        except Exception as e:
            logger.error(f"  ⚠ Warmup Error for {match.id}: {e}")
            return None

    async def _fetch_all_upcoming_matches(self, days: int) -> List[Match]:
        """Aggegated fetch of upcoming matches from all configured sources."""
        matches = []
        
        # Strategy A: Football-Data.org (Scheduled matches)
        if self.data_sources.football_data_org.is_configured:
            try:
                from datetime import datetime, timedelta
                from src.utils.time_utils import get_current_time
                
                now = get_current_time()
                end_date = now + timedelta(days=days)
                
                # List of leagues we want to warmup
                # We interpret "supported_leagues" as our INTERNAL codes
                # Prioritizing I1 (Serie A) for debugging user request
                supported_leagues = ["I1", "E0", "SP1", "D1", "F1", "N1", "P1"] 
                
                tasks = []
                # NOTE: We must run these SEQUENTIALLY to avoid rate limits (10 req/min for free tier)
                # Parallel execution (asyncio.gather) triggers 429 errors instantly.
                for internal_code in supported_leagues:
                    try:
                        # Fetch
                        res = await self.data_sources.football_data_org.get_upcoming_matches(
                            league_code=internal_code
                        )

                        # Handle Rate Limit (None)
                        if res is None:
                            logger.warning(f"Rate limit hit for {internal_code}. Sleeping 65s before retry...")
                            await asyncio.sleep(65)
                            # Retry ONCE
                            res = await self.data_sources.football_data_org.get_upcoming_matches(
                                league_code=internal_code
                            )
                        
                        # Process results immediately
                        if isinstance(res, list):
                            for m in res:
                                if m.match_date:
                                    # Simple date comparison
                                    m_date = m.match_date
                                    if now.date() <= m_date.date() <= end_date.date():
                                        matches.append(m)
                                        
                        # Polite delay increased to avoid consecutive 429s
                        await asyncio.sleep(12) 
                        
                    except Exception as e:
                         logger.error(f"Error fetching warmup matches for league {internal_code}: {e}")
                        
            except Exception as e:
                logger.error(f"Error fetching upcoming matches for warmup: {e}")
        
        # Deduplicate
        unique = {}
        for m in matches:
            if m.id not in unique:
                 unique[m.id] = m
                 
        return list(unique.values())

    async def _process_single_match(self, match: Match):
        """Generate and cache picks for a single match."""
        try:
            # This calls the use case which does ALL the heavy lifting:
            # - History Aggregation
            # - Stats Calc
            # - Prediction Engine
            # - Pick Generation
            result = await self.picks_use_case.execute(match.id)
            
            if result:
                # The Use Case returns DTO but doesn't explicitly cache it in Redis under the simplistic key?
                # The Use Case actually *generates* it.
                # We need to manually cache it here to ensure the API finds it immediately.
                
                # The API endpoint looks for: f"forecasts:match_{match_id}"
                # We should serialize the result and store it there.
                
                # Wait, the API endpoint code says:
                # cached_match = cache.get(cache_key)
                # if cached_match... return MatchSuggestedPicksDTO...
                
                # So we just cache the DTO.
                cache_key = f"forecasts:match_{match.id}"
                
                # We can store the whole object as dict
                self.cache_service.set(cache_key, result.model_dump(), ttl_seconds=3600*24) # 24h cache
                
                logger.info(f"  ✓ Cached: {match.home_team.name} vs {match.away_team.name}")
            else:
                logger.warning(f"  ✗ Failed to generate picks for: {match.id}")
                
        except Exception as e:
            logger.error(f"  ⚠ Warmup Error for {match.id}: {e}")
