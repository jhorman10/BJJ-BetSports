"""
Local GitHub Data Source

This module processes the large historical dataset from GitHub:
Club-Football-Match-Data-2000-2025

Contains ~226k matches with stats, odds, and Elo ratings.
Path: src/infrastructure/data_sources/local_data/matches_github.csv
"""

import os
import csv
import logging
from typing import List, Optional
from datetime import datetime
from src.domain.entities.entities import Match, Team, League

logger = logging.getLogger(__name__)

class LocalGithubDataSource:
    """
    Data source for local GitHub dataset CSV.
    """
    
    SOURCE_NAME = "GitHub_Dataset"
    CSV_PATH = "src/infrastructure/data_sources/local_data/matches_github.csv"
    
    LEAGUE_MAPPING = {
        "E0": "Premier League",
        "SP1": "La Liga",
        "D1": "Bundesliga",
        "I1": "Serie A",
        "F1": "Ligue 1",
        "P1": "Primeira Liga",
        "N1": "Eredivisie",
        # Add more as needed based on CSV "Division" column
    }
    
    def __init__(self):
        self.file_path = os.path.join(os.getcwd(), self.CSV_PATH)
        
    async def get_finished_matches(
        self,
        league_codes: Optional[List[str]] = None,
        date_from: Optional[datetime] = None,
    ) -> List[Match]:
        """
        Get matches from local CSV.
        
        Args:
            league_codes: List of league codes to filter (e.g., ["E0"])
            date_from: Filter matches after this date
            
        Returns:
            List of Match entities
        """
        if not os.path.exists(self.file_path):
            logger.warning(f"GitHub dataset not found at {self.file_path}")
            return []
            
        matches = []
        target_divisions = set(league_codes) if league_codes else None
        
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                rows_checked = 0
                for row in reader:
                    rows_checked += 1
                    try:
                        # Filter by division
                        division = row.get("Division")
                        if target_divisions and division not in target_divisions:
                            if rows_checked < 5:
                                logger.debug(f"Skipping division: {division} (Target: {target_divisions})")
                            continue
                            
                        # Parse date
                        date_str = row.get("MatchDate")
                        if not date_str:
                            continue
                            
                        match_date = datetime.strptime(date_str, "%Y-%m-%d")
                        
                        # Filter by date
                        if date_from and match_date < date_from:
                            if rows_checked < 5:
                                logger.debug(f"Skipping date: {match_date} (From: {date_from})")
                            continue
                            
                        # Create match entity
                        match = self._parse_row(row, match_date)
                        if match:
                            matches.append(match)
                        else:
                            if rows_checked < 20:
                                logger.debug(f"Failed to parse row: {row}")
                            
                    except Exception as e:
                        if rows_checked < 20:
                            logger.debug(f"Error processing row {rows_checked}: {e}")
                        continue
                
                logger.info(f"GitHub Dataset: Checked {rows_checked} rows")
                        
        except Exception as e:
            logger.error(f"Error reading GitHub dataset: {e}")
            return []
            
        logger.info(f"GitHub Dataset: loaded {len(matches)} matches")
        return matches

    def _parse_row(self, row: dict, match_date: datetime) -> Optional[Match]:
        """Parse CSV row to Match entity."""
        try:
            division = row.get("Division")
            home_team_name = row.get("HomeTeam")
            away_team_name = row.get("AwayTeam")
            
            # Helper to parse float or int string to int safely
            def safe_int(val):
                if not val:
                    return None
                try:
                    return int(float(val))
                except (ValueError, TypeError):
                    return None
            
            def safe_float(val):
                if not val:
                    return None
                try:
                    return float(val)
                except (ValueError, TypeError):
                    return None

            home_goals = safe_int(row.get("FTHome"))
            away_goals = safe_int(row.get("FTAway"))
            
            if home_goals is None or away_goals is None:
                return None
            
            # Additional stats
            home_corners = safe_int(row.get("HomeCorners"))
            away_corners = safe_int(row.get("AwayCorners"))
            
            home_yellow = safe_int(row.get("HomeYellow"))
            away_yellow = safe_int(row.get("AwayYellow"))
            
            home_red = safe_int(row.get("HomeRed"))
            away_red = safe_int(row.get("AwayRed"))
            
            # Betting Odds
            home_odds = safe_float(row.get("OddHome"))
            draw_odds = safe_float(row.get("OddDraw"))
            away_odds = safe_float(row.get("OddAway"))
            
            # Shots
            home_shots_on = safe_int(row.get("HomeTarget"))
            away_shots_on = safe_int(row.get("AwayTarget"))
            home_total_shots = safe_int(row.get("HomeShots"))
            away_total_shots = safe_int(row.get("AwayShots"))
            
            # Simple ID generation
            match_id = f"gh_{division}_{match_date.strftime('%Y%m%d')}_{home_team_name[:3]}_{away_team_name[:3]}"
            
            home_team = Team(id=home_team_name, name=home_team_name)
            away_team = Team(id=away_team_name, name=away_team_name)
            
            league = League(
                id=division,
                name=self.LEAGUE_MAPPING.get(division, division),
                country="International"
            )
            
            return Match(
                id=match_id,
                home_team=home_team,
                away_team=away_team,
                league=league,
                match_date=match_date,
                home_goals=home_goals,
                away_goals=away_goals,
                status="FT",
                home_corners=home_corners,
                away_corners=away_corners,
                home_yellow_cards=home_yellow,
                away_yellow_cards=away_yellow,
                home_red_cards=home_red,
                away_red_cards=away_red,
                home_odds=home_odds,
                draw_odds=draw_odds,
                away_odds=away_odds,
                home_shots_on_target=home_shots_on,
                away_shots_on_target=away_shots_on,
                home_total_shots=home_total_shots,
                away_total_shots=away_total_shots
            )
        except Exception:
            return None
