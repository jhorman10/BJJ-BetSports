"""
Live Predictions Use Case Module

Use case for generating predictions for live matches,
combining real-time data with historical statistics.
"""

from datetime import datetime
from typing import Optional, List
from dataclasses import dataclass
import logging

from src.domain.entities.entities import Match, Prediction
from src.domain.services.prediction_service import PredictionService
from src.domain.services.statistics_service import StatisticsService
from src.infrastructure.cache.cache_service import CacheService
from src.infrastructure.data_sources.football_data_uk import (
    FootballDataUKSource,
    LEAGUES_METADATA,
)
from src.infrastructure.data_sources.api_football import (
    APIFootballSource,
    LEAGUE_ID_MAPPING,
    TARGET_LEAGUE_IDS,
)
from src.application.dtos.dtos import (
    TeamDTO,
    LeagueDTO,
    MatchDTO,
    PredictionDTO,
    MatchPredictionDTO,
)
from src.application.use_cases.use_cases import DataSources


logger = logging.getLogger(__name__)


@dataclass
class LiveMatchPrediction:
    """Combined live match data with prediction."""
    match: Match
    prediction: Optional[Prediction]
    is_processing: bool = False
    processing_message: Optional[str] = None


class GetLivePredictionsUseCase:
    """
    Use case for getting live matches with predictions.
    
    Prioritizes accuracy over speed for predictions,
    while using caching to optimize response times.
    """
    
    PROCESSING_MESSAGE = "Estamos procesando la información para darte las probabilidades con mayor precisión"
    
    def __init__(
        self,
        data_sources: DataSources,
        prediction_service: PredictionService,
        statistics_service: StatisticsService,
        cache_service: CacheService,
    ):
        self.data_sources = data_sources
        self.prediction_service = prediction_service
        self.statistics_service = statistics_service
        self.cache_service = cache_service
    
    async def execute(
        self,
        filter_target_leagues: bool = True,
    ) -> List[MatchPredictionDTO]:
        """
        Get live matches with predictions.
        
        Args:
            filter_target_leagues: If True, only returns matches from
                                   Premier League, La Liga, Serie A, Bundesliga
            
        Returns:
            List of MatchPredictionDTO with predictions
        """
        # Check cache first
        cache_key = "filtered" if filter_target_leagues else "all"
        cached = self.cache_service.get_live_matches(cache_key)
        if cached is not None:
            logger.info(f"Returning {len(cached)} cached live matches")
            return cached
        
        # Get live matches
        if filter_target_leagues:
            matches = await self.data_sources.api_football.get_live_matches_filtered()
        else:
            matches = await self.data_sources.api_football.get_live_matches()
        
        if not matches:
            # Cache empty result for short period to avoid hammering API
            self.cache_service.set_live_matches([], cache_key)
            return []
        
        # Generate predictions for each match
        results: List[MatchPredictionDTO] = []
        
        for match in matches:
            try:
                prediction_dto = await self._generate_prediction(match)
                match_dto = self._match_to_dto(match)
                
                results.append(MatchPredictionDTO(
                    match=match_dto,
                    prediction=prediction_dto,
                ))
            except Exception as e:
                logger.warning(f"Failed to generate prediction for match {match.id}: {e}")
                # Still include match without prediction
                results.append(MatchPredictionDTO(
                    match=self._match_to_dto(match),
                    prediction=self._empty_prediction(match.id),
                ))
        
        # Cache results
        self.cache_service.set_live_matches(results, cache_key)
        logger.info(f"Generated {len(results)} live match predictions")
        
        return results
    
    async def _generate_prediction(self, match: Match) -> PredictionDTO:
        """
        Generate prediction for a single match.
        
        Uses all available historical data for maximum accuracy.
        """
        # Check prediction cache
        cached_pred = self.cache_service.get_predictions(match.id)
        if cached_pred is not None:
            return cached_pred
        
        # Get internal league code
        internal_code = self._get_internal_league_code(match)
        
        # Load historical data (from cache if available)
        historical_matches = await self._get_historical_data(internal_code)
        
        # Calculate team statistics
        home_stats = self.statistics_service.calculate_team_statistics(
            match.home_team.name,
            historical_matches,
        )
        away_stats = self.statistics_service.calculate_team_statistics(
            match.away_team.name,
            historical_matches,
        )
        
        # Calculate league averages
        league_averages = self.statistics_service.calculate_league_averages(
            historical_matches
        ) if historical_matches else None
        
        # Generate prediction using full analysis
        data_sources_used = [APIFootballSource.SOURCE_NAME]
        if historical_matches:
            data_sources_used.append(FootballDataUKSource.SOURCE_NAME)
        
        prediction = self.prediction_service.generate_prediction(
            match=match,
            home_stats=home_stats,
            away_stats=away_stats,
            league_averages=league_averages,
            data_sources=data_sources_used,
        )
        
        # Convert to DTO
        prediction_dto = self._prediction_to_dto(prediction)
        
        # Cache the prediction
        self.cache_service.set_predictions(match.id, prediction_dto)
        
        return prediction_dto
    
    async def _get_historical_data(self, league_code: Optional[str]) -> List[Match]:
        """Get historical data for a league, using cache when available."""
        if not league_code or league_code == "UNKNOWN":
            return []
        
        seasons_key = "2425_2324"
        
        # Check cache
        cached = self.cache_service.get_historical(league_code, seasons_key)
        if cached is not None:
            return cached
        
        # Fetch from data source
        try:
            historical = await self.data_sources.football_data_uk.get_historical_matches(
                league_code,
                seasons=["2425", "2324"],
            )
            
            if historical:
                self.cache_service.set_historical(league_code, seasons_key, historical)
            
            return historical
        except Exception as e:
            logger.warning(f"Failed to fetch historical data for {league_code}: {e}")
            return []
    
    def _get_internal_league_code(self, match: Match) -> Optional[str]:
        """Map API-Football league ID to internal code."""
        try:
            api_id = int(match.league.id)
            for code, mapped_id in LEAGUE_ID_MAPPING.items():
                if mapped_id == api_id:
                    return code
        except (ValueError, TypeError):
            pass
        return None
    
    def _match_to_dto(self, match: Match) -> MatchDTO:
        """Convert Match entity to DTO."""
        return MatchDTO(
            id=match.id,
            home_team=TeamDTO(
                id=match.home_team.id,
                name=match.home_team.name,
                short_name=match.home_team.short_name,
                country=match.home_team.country,
            ),
            away_team=TeamDTO(
                id=match.away_team.id,
                name=match.away_team.name,
                short_name=match.away_team.short_name,
                country=match.away_team.country,
            ),
            league=LeagueDTO(
                id=match.league.id,
                name=match.league.name,
                country=match.league.country,
                season=match.league.season,
            ),
            match_date=match.match_date,
            home_goals=match.home_goals,
            away_goals=match.away_goals,
            status=match.status,
            home_corners=match.home_corners,
            away_corners=match.away_corners,
            home_yellow_cards=match.home_yellow_cards,
            away_yellow_cards=match.away_yellow_cards,
            home_red_cards=match.home_red_cards,
            away_red_cards=match.away_red_cards,
            home_odds=match.home_odds,
            draw_odds=match.draw_odds,
            away_odds=match.away_odds,
        )
    
    def _prediction_to_dto(self, prediction: Prediction) -> PredictionDTO:
        """Convert Prediction entity to DTO."""
        return PredictionDTO(
            match_id=prediction.match_id,
            home_win_probability=prediction.home_win_probability,
            draw_probability=prediction.draw_probability,
            away_win_probability=prediction.away_win_probability,
            over_25_probability=prediction.over_25_probability,
            under_25_probability=prediction.under_25_probability,
            predicted_home_goals=prediction.predicted_home_goals,
            predicted_away_goals=prediction.predicted_away_goals,
            confidence=prediction.confidence,
            data_sources=prediction.data_sources,
            recommended_bet=prediction.recommended_bet,
            over_under_recommendation=prediction.over_under_recommendation,
            created_at=prediction.created_at,
        )
    
    def _empty_prediction(self, match_id: str) -> PredictionDTO:
        """Create an empty prediction DTO for when prediction fails."""
        return PredictionDTO(
            match_id=match_id,
            home_win_probability=0.0,
            draw_probability=0.0,
            away_win_probability=0.0,
            over_25_probability=0.0,
            under_25_probability=0.0,
            predicted_home_goals=0.0,
            predicted_away_goals=0.0,
            confidence=0.0,
            data_sources=[],
            recommended_bet="N/A",
            over_under_recommendation="N/A",
            created_at=datetime.utcnow(),
        )
