from typing import List
from dataclasses import dataclass
from datetime import datetime
from ..services.parley_service import ParleyService, ParleyConfig
from ...domain.entities.parley import Parley
from ...domain.entities.entities import MatchPrediction, Match, Prediction, Team, League
from .use_cases import GetPredictionsUseCase

@dataclass
class GetParleysRequest:
    min_probability: float = 0.60
    min_picks: int = 3
    max_picks: int = 5
    count: int = 3
    
class GetParleysUseCase:
    """
    Application service to get suggested parleys.
    Orchestrates fetching predictions for multiple leagues and generating parleys.
    """
    
    def __init__(self, get_predictions_use_case: GetPredictionsUseCase, parley_service: ParleyService):
        self.get_predictions_use_case = get_predictions_use_case
        self.parley_service = parley_service
        
    async def execute(self, request: GetParleysRequest) -> List[Parley]:
        # 1. Fetch available predictions for popular leagues
        popular_leagues = ["eng_1", "esp_1", "ita_1", "ger_1", "fra_1"] 
        all_match_predictions: List[MatchPrediction] = []
        
        for league_id in popular_leagues:
            try:
                # Use existing use case to fetch and generate predictions
                response_dto = await self.get_predictions_use_case.execute(league_id, limit=10)
                
                # Convert DTOs back to Domain Entities for ParleyService
                for pdto in response_dto.predictions:
                    match_entity = self._map_dto_to_match(pdto.match)
                    prediction_entity = self._map_dto_to_prediction(pdto.prediction)
                    
                    all_match_predictions.append(MatchPrediction(
                        match=match_entity,
                        prediction=prediction_entity
                    ))
            except Exception as e:
                # Log error but continue with other leagues
                print(f"Failed to fetch predictions for {league_id}: {e}")
                continue
            
        # 2. Configure Parley Generation
        config = ParleyConfig(
            min_probability=request.min_probability,
            min_picks=request.min_picks,
            max_picks=request.max_picks,
            count=request.count
        )
        
        # 3. Generate
        parleys = self.parley_service.generate_parleys(all_match_predictions, config)
        
        return parleys

    def _map_dto_to_match(self, dto) -> Match:
        return Match(
            id=dto.id,
            home_team=Team(id=dto.home_team.id, name=dto.home_team.name, short_name=dto.home_team.short_name, country=dto.home_team.country, logo_url=dto.home_team.logo_url),
            away_team=Team(id=dto.away_team.id, name=dto.away_team.name, short_name=dto.away_team.short_name, country=dto.away_team.country, logo_url=dto.away_team.logo_url),
            league=League(id=dto.league.id, name=dto.league.name, country=dto.league.country, season=dto.league.season),
            match_date=dto.match_date,
            home_goals=dto.home_goals,
            away_goals=dto.away_goals,
            status=dto.status,
            home_corners=dto.home_corners,
            away_corners=dto.away_corners,
            home_yellow_cards=dto.home_yellow_cards,
            away_yellow_cards=dto.away_yellow_cards,
            home_red_cards=dto.home_red_cards,
            away_red_cards=dto.away_red_cards,
            home_odds=dto.home_odds,
            draw_odds=dto.draw_odds,
            away_odds=dto.away_odds
        )

    def _map_dto_to_prediction(self, dto) -> Prediction:
        return Prediction(
            match_id=dto.match_id,
            home_win_probability=dto.home_win_probability,
            draw_probability=dto.draw_probability,
            away_win_probability=dto.away_win_probability,
            over_25_probability=dto.over_25_probability,
            under_25_probability=dto.under_25_probability,
            predicted_home_goals=dto.predicted_home_goals,
            predicted_away_goals=dto.predicted_away_goals,
            confidence=dto.confidence,
            data_sources=dto.data_sources,
            created_at=dto.created_at
        )

