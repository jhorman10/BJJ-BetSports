"""
Suggested Picks Use Case Module

Use case for generating AI-suggested betting picks for a match.
"""

import logging
from datetime import datetime
from typing import Optional
import uuid

from src.domain.entities.entities import Match, League
from src.domain.entities.suggested_pick import MatchSuggestedPicks, SuggestedPick
from src.domain.entities.betting_feedback import BettingFeedback
from src.domain.services.picks_service import PicksService
from src.domain.services.learning_service import LearningService
from src.domain.services.prediction_service import PredictionService
from src.domain.services.statistics_service import StatisticsService
from src.application.dtos.dtos import (
    SuggestedPickDTO,
    MatchSuggestedPicksDTO,
    BettingFeedbackRequestDTO,
    BettingFeedbackResponseDTO,
    MarketPerformanceDTO,
    LearningStatsResponseDTO,
)


logger = logging.getLogger(__name__)


class GetSuggestedPicksUseCase:
    """Use case for getting AI-suggested picks for a match."""
    
    def __init__(
        self,
        data_sources,  # DataSources from use_cases.py
        prediction_service: PredictionService,
        statistics_service: StatisticsService,
        learning_service: LearningService,
    ):
        self.data_sources = data_sources
        self.prediction_service = prediction_service
        self.statistics_service = statistics_service
        self.learning_service = learning_service
        self.picks_service = PicksService(
            learning_weights=learning_service.get_learning_weights()
        )
    
    async def execute(self, match_id: str) -> Optional[MatchSuggestedPicksDTO]:
        """
        Generate suggested picks for a match.
        
        Args:
            match_id: ID of the match
            
        Returns:
            MatchSuggestedPicksDTO with AI suggestions, or None if match not found
        """
        try:
            # 1. Get match details
            match = await self._get_match(match_id)
            if not match:
                logger.warning(f"Match {match_id} not found in any data source")
                return None
            
            # 2. Get historical data for statistics
            historical_matches = await self._get_historical_matches(match)
            
            # 3. Calculate team statistics
            home_stats = self.statistics_service.calculate_team_statistics(
                match.home_team.name,
                historical_matches,
            )
            away_stats = self.statistics_service.calculate_team_statistics(
                match.away_team.name,
                historical_matches,
            )
            
            # 4. Generate base prediction for expected goals
            prediction = self.prediction_service.generate_prediction(
                match=match,
                home_stats=home_stats,
                away_stats=away_stats,
                league_averages=None,
                data_sources=[],
            )
            
            # Use actual prediction values (don't force defaults here, let service handle it)
            predicted_home = prediction.predicted_home_goals
            predicted_away = prediction.predicted_away_goals
            
            # Get win probabilities
            home_win_prob = prediction.home_win_probability
            draw_prob = prediction.draw_probability
            away_win_prob = prediction.away_win_probability
            
            # 5. Generate suggested picks with all data
            suggested_picks = self.picks_service.generate_suggested_picks(
                match=match,
                home_stats=home_stats if home_stats and home_stats.matches_played > 0 else None,
                away_stats=away_stats if away_stats and away_stats.matches_played > 0 else None,
                predicted_home_goals=predicted_home,
                predicted_away_goals=predicted_away,
                home_win_prob=home_win_prob,
                draw_prob=draw_prob,
                away_win_prob=away_win_prob,
            )
            
            # 6. Convert to DTO
            return self._to_dto(suggested_picks)
        except Exception as e:
            logger.error(f"Error generating suggested picks for match {match_id}: {e}", exc_info=True)
            # Return empty picks instead of failing
            return MatchSuggestedPicksDTO(
                match_id=match_id,
                suggested_picks=[],
                combination_warning="No se pudieron generar picks debido a datos insuficientes.",
                generated_at=datetime.utcnow(),
            )
    
    async def _get_match(self, match_id: str) -> Optional[Match]:
        """Get match details from available sources."""
        # Try API-Football first
        if self.data_sources.api_football.is_configured:
            match = await self.data_sources.api_football.get_match_details(match_id)
            if match:
                return match
        
        # Try Football-Data.org
        if self.data_sources.football_data_org.is_configured:
            match = await self.data_sources.football_data_org.get_match_details(match_id)
            if match:
                return match
        
        
        return None
    
    async def _get_historical_matches(self, match: Match) -> list[Match]:
        """Get historical matches for context."""
        from src.infrastructure.data_sources.api_football import LEAGUE_ID_MAPPING
        
        # Create reverse mapping
        api_id_to_code = {v: k for k, v in LEAGUE_ID_MAPPING.items()}
        
        internal_league_code = None
        try:
            lid = int(match.league.id)
            if lid in api_id_to_code:
                internal_league_code = api_id_to_code[lid]
        except (ValueError, TypeError):
            pass
        
        if not internal_league_code:
            return []
        
        # Try Football-Data.co.uk
        try:
            matches = await self.data_sources.football_data_uk.get_historical_matches(
                internal_league_code,
                seasons=["2425", "2324"],
            )
            if matches:
                return matches
        except Exception as e:
            logger.warning(f"Failed to fetch CSV history: {e}")
        
        # Try OpenFootball
        if self.data_sources.openfootball:
            try:
                from src.infrastructure.data_sources.football_data_uk import LEAGUES_METADATA
                if internal_league_code in LEAGUES_METADATA:
                    meta = LEAGUES_METADATA[internal_league_code]
                    temp_league = League(
                        id=internal_league_code,
                        name=meta["name"],
                        country=meta["country"],
                    )
                    open_matches = await self.data_sources.openfootball.get_matches(temp_league)
                    return [m for m in open_matches if m.status in ["FT", "AET", "PEN"]]
            except Exception as e:
                logger.warning(f"Failed to fetch OpenFootball history: {e}")
        
        return []
    
    def _to_dto(self, picks: MatchSuggestedPicks) -> MatchSuggestedPicksDTO:
        """Convert domain object to DTO."""
        pick_dtos = [
            SuggestedPickDTO(
                market_type=p.market_type.value,
                market_label=p.market_label,
                probability=p.probability,
                confidence_level=p.confidence_level.value,
                reasoning=p.reasoning,
                risk_level=p.risk_level,
                is_recommended=p.is_recommended,
                priority_score=p.priority_score,
            )
            for p in picks.suggested_picks
        ]
        
        return MatchSuggestedPicksDTO(
            match_id=picks.match_id,
            suggested_picks=pick_dtos,
            combination_warning=picks.combination_warning,
            generated_at=picks.generated_at,
        )


class RegisterFeedbackUseCase:
    """Use case for registering betting feedback."""
    
    def __init__(self, learning_service: LearningService):
        self.learning_service = learning_service
    
    def execute(self, request: BettingFeedbackRequestDTO) -> BettingFeedbackResponseDTO:
        """
        Register betting feedback and update learning weights.
        
        Args:
            request: Feedback request with bet outcome
            
        Returns:
            Response with new confidence adjustment
        """
        # Create feedback entity
        feedback = BettingFeedback(
            bet_id=str(uuid.uuid4()),
            match_id=request.match_id,
            market_type=request.market_type,
            prediction=request.prediction,
            actual_outcome=request.actual_outcome,
            was_correct=request.was_correct,
            odds=request.odds,
            stake=request.stake,
        )
        
        # Register with learning service
        self.learning_service.register_feedback(feedback)
        
        # Get new adjustment
        new_adjustment = self.learning_service.get_market_adjustment(request.market_type)
        
        return BettingFeedbackResponseDTO(
            success=True,
            message=f"Feedback registered for {request.market_type}",
            market_type=request.market_type,
            new_confidence_adjustment=new_adjustment,
        )


class GetLearningStatsUseCase:
    """Use case for getting learning statistics."""
    
    def __init__(self, learning_service: LearningService):
        self.learning_service = learning_service
    
    def execute(self) -> LearningStatsResponseDTO:
        """
        Get all learning statistics.
        
        Returns:
            Response with market performance data
        """
        all_stats = self.learning_service.get_all_stats()
        
        performance_dtos = [
            MarketPerformanceDTO(
                market_type=perf.market_type,
                total_predictions=perf.total_predictions,
                correct_predictions=perf.correct_predictions,
                success_rate=perf.success_rate,
                avg_odds=perf.avg_odds,
                total_profit_loss=perf.total_profit_loss,
                confidence_adjustment=perf.confidence_adjustment,
                last_updated=perf.last_updated,
            )
            for perf in all_stats.values()
        ]
        
        total_count = sum(p.total_predictions for p in all_stats.values())
        last_updated = max(
            (p.last_updated for p in all_stats.values()),
            default=datetime.utcnow()
        )
        
        return LearningStatsResponseDTO(
            market_performances=performance_dtos,
            total_feedback_count=total_count,
            last_updated=last_updated,
        )
