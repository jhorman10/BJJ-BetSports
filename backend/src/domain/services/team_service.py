import json
import os
import logging
from typing import Optional
from src.domain.services.statistics_service import StatisticsService

logger = logging.getLogger(__name__)

class TeamService:
    """
    Domain service for team-related operations, primarily serving logos.
    """
    
    _logos: dict = {}
    _loaded: bool = False
    
    DATA_FILE = os.path.join(os.path.dirname(__file__), "../../../data/team_logos.json")
    DATA_FILE_SHORT_NAMES = os.path.join(os.path.dirname(__file__), "../../../data/team_short_names.json")
    
    _short_names: dict = {}
    _short_names_loaded: bool = False

    @classmethod
    def load_logos(cls):
        """Load logos from the JSON file into memory."""
        if cls._loaded:
            return
            
        if not os.path.exists(cls.DATA_FILE):
            logger.warning(f"Logo file not found at {cls.DATA_FILE}. Logos will be missing.")
            return
            
        try:
            with open(cls.DATA_FILE, "r") as f:
                cls._logos = json.load(f)
            cls._loaded = True
            logger.info(f"Loaded {len(cls._logos)} team logos.")
        except Exception as e:
            logger.error(f"Failed to load team logos: {e}")

    @classmethod
    def load_short_names(cls):
        """Load short names from the JSON file into memory."""
        if cls._short_names_loaded:
            return
            
        if not os.path.exists(cls.DATA_FILE_SHORT_NAMES):
            logger.warning(f"Short names file not found at {cls.DATA_FILE_SHORT_NAMES}.")
            # Fallback to empty
            cls._short_names = {}
            cls._short_names_loaded = True
            return

        try:
            with open(cls.DATA_FILE_SHORT_NAMES, "r") as f:
                cls._short_names = json.load(f)
            cls._short_names_loaded = True
            logger.info(f"Loaded {len(cls._short_names)} team short names.")
        except Exception as e:
            logger.error(f"Failed to load team short names: {e}")

    @classmethod
    def get_team_logo(cls, team_name: str) -> Optional[str]:
        """
        Get the logo URL for a team name.
        Handles normalization to ensure matching.
        """
        if not cls._loaded:
            cls.load_logos()
            
        if not team_name:
            return None
            
        # 1. Try exact match (unlikely if source differs)
        if team_name in cls._logos:
            return cls._logos[team_name]
            
        # 2. Try normalized match (most likely)
        normalized = StatisticsService._normalize_name(team_name)
        if normalized in cls._logos:
            return cls._logos[normalized]
            
        # 3. Try lowercase (fallback)
        lower = team_name.lower()
        if lower in cls._logos:
            return cls._logos[lower]
            
        return None

    @classmethod
    def get_team_short_name(cls, team_name: str) -> Optional[str]:
        """
        Get the short display name for a team.
        e.g. "Paris Saint-Germain" -> "PSG"
        """
        if not cls._short_names_loaded:
            cls.load_short_names()
            
        if not team_name:
            return None

        # Normalize logic similar to logo lookup
        
        # 1. Try exact match (lowercased)
        lower = team_name.lower()
        if lower in cls._short_names:
            return cls._short_names[lower]
            
        # 2. Try normalized match
        normalized = StatisticsService._normalize_name(team_name)
        if normalized in cls._short_names:
            return cls._short_names[normalized]

        return None
