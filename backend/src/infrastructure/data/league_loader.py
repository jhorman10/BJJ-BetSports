"""
League Loader Module

Loads and provides access to the comprehensive global multi-sport leagues dataset.
Provides fast lookup by league ID, country, confederation, tier, and sport.
"""

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Path to the global leagues dataset
_DATA_DIR = Path(__file__).parent
_DATASET_PATH = _DATA_DIR / "leagues_global.json"

DEFAULT_SPORT = "soccer"


class LeagueDataset:
    """
    Singleton loader for the global multi-sport leagues dataset.
    
    Usage:
        from src.infrastructure.data.league_loader import dataset
        
        # Get league by ID
        league = dataset.get("E0")
        
        # Get all leagues for a country
        leagues = dataset.get_by_country("England")
        
        # Get all leagues for a confederation
        leagues = dataset.get_by_confederation("UEFA")
        
        # Get leagues by tier
        leagues = dataset.get_by_tier(1)
        
        # Get all active leagues
        leagues = dataset.get_active()
        
        # Get leagues by sport
        leagues = dataset.get_by_sport("tennis")
    """

    _instance: Optional["LeagueDataset"] = None
    _loaded: bool = False

    def __new__(cls) -> "LeagueDataset":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if not self._loaded:
            self._load()

    def _load(self) -> None:
        """Load the dataset from JSON file."""
        try:
            with open(_DATASET_PATH, "r", encoding="utf-8") as f:
                raw = json.load(f)

            self._metadata = raw.get("_metadata", {})
            self._continents = raw.get("continents", {})
            self._international = raw.get("international", {})

            # Build fast lookup indices
            self._by_id: dict[str, dict] = {}
            self._by_country: dict[str, list[dict]] = {}
            self._by_confederation: dict[str, list[dict]] = {}
            self._by_tier: dict[int, list[dict]] = {}
            self._by_type: dict[str, list[dict]] = {}
            self._by_sport: dict[str, list[dict]] = {}
            self._active: list[dict] = []
            self._all_leagues: list[dict] = []

            # Index domestic leagues from main continents (soccer)
            for conf_name, conf_data in self._continents.items():
                countries = conf_data.get("countries", {})
                for country_name, country_data in countries.items():
                    country_code = country_data.get("code", "")
                    flag = country_data.get("flag", "")
                    leagues = country_data.get("leagues", [])

                    for league in leagues:
                        league.setdefault("sport", DEFAULT_SPORT)
                        league["country_name"] = country_name
                        league["country_code"] = country_code
                        league["country_flag"] = flag
                        league["confederation"] = conf_data.get("confederation", conf_name)
                        league["scope"] = "domestic"

                        self._index_league(league)

            # Index international leagues
            for conf_name, conf_data in self._international.items():
                for category in ["clubs", "national_teams", "global"]:
                    for league in conf_data.get(category, []):
                        league.setdefault("sport", DEFAULT_SPORT)
                        league["confederation"] = conf_name
                        league["scope"] = "international"
                        self._index_league(league)

            # Index leagues from additional sport sections (tennis, baseball, basketball)
            for sport_key in ("tennis", "baseball", "basketball"):
                sport_data = raw.get(sport_key, {})
                for conf_name, conf_data in sport_data.get("continents", {}).items():
                    countries = conf_data.get("countries", {})
                    for country_name, country_data in countries.items():
                        country_code = country_data.get("code", "")
                        flag = country_data.get("flag", "")
                        for league in country_data.get("leagues", []):
                            league.setdefault("sport", sport_key)
                            league["country_name"] = country_name
                            league["country_code"] = country_code
                            league["country_flag"] = flag
                            league["confederation"] = conf_data.get("confederation", conf_name)
                            league["scope"] = "domestic"
                            self._index_league(league)

            self._loaded = True
            logger.info(
                "Loaded %d leagues from %d countries across %d confederations",
                len(self._all_leagues),
                len(self._by_country),
                len(self._by_confederation),
            )

        except FileNotFoundError:
            logger.error("Leagues dataset not found at %s", _DATASET_PATH)
            self._continents = {}
            self._international = {}
            self._loaded = True
        except Exception as e:
            logger.error("Failed to load leagues dataset: %s", e)
            self._continents = {}
            self._international = {}
            self._loaded = True

    def _index_league(self, league: dict) -> None:
        """Add a league to all indices."""
        league_id = league.get("id")
        if not league_id:
            return

        self._all_leagues.append(league)
        self._by_id[league_id] = league

        # Index by country
        country = league.get("country_name", "")
        if country:
            self._by_country.setdefault(country, []).append(league)

        # Index by confederation
        conf = league.get("confederation", "")
        if conf:
            self._by_confederation.setdefault(conf, []).append(league)

        # Index by tier
        tier = league.get("tier", 0)
        self._by_tier.setdefault(tier, []).append(league)

        # Index by type
        league_type = league.get("type", "")
        if league_type:
            self._by_type.setdefault(league_type, []).append(league)

        # Index by sport
        sport = league.get("sport", DEFAULT_SPORT)
        self._by_sport.setdefault(sport, []).append(league)

        # Index active leagues
        if league.get("active", True):
            self._active.append(league)

    # ─── Public API ─────────────────────────────────────────────────────

    def get(self, league_id: str) -> Optional[dict]:
        """Get a league by its ID."""
        return self._by_id.get(league_id)

    def get_by_country(self, country: str) -> list[dict]:
        """Get all leagues for a specific country."""
        return self._by_country.get(country, [])

    def get_by_confederation(self, confederation: str) -> list[dict]:
        """Get all leagues for a specific confederation."""
        return self._by_confederation.get(confederation, [])

    def get_by_tier(self, tier: int) -> list[dict]:
        """Get all leagues of a specific tier (1 = top division)."""
        return self._by_tier.get(tier, [])

    def get_by_type(self, league_type: str) -> list[dict]:
        """Get all leagues of a specific type (league, cup, etc.)."""
        return self._by_type.get(league_type, [])

    def get_by_sport(self, sport: str) -> list[dict]:
        """Get all leagues for a specific sport."""
        return self._by_sport.get(sport, [])

    def get_active(self) -> list[dict]:
        """Get all active leagues."""
        return self._active

    def get_all(self) -> list[dict]:
        """Get all leagues."""
        return self._all_leagues

    def get_metadata(self) -> dict:
        """Get dataset metadata."""
        return self._metadata

    def search(self, query: str) -> list[dict]:
        """Search leagues by name, country, or alias (case-insensitive)."""
        query_lower = query.lower()
        results = []

        for league in self._all_leagues:
            # Check name
            if query_lower in league.get("name", "").lower():
                results.append(league)
                continue

            # Check country
            if query_lower in league.get("country_name", "").lower():
                results.append(league)
                continue

            # Check aliases
            for alias in league.get("aliases", []):
                if query_lower in alias.lower():
                    results.append(league)
                    break

        return results

    def to_metadata_format(self, league_id: str) -> Optional[dict]:
        """Convert a league to the LEAGUES_METADATA format for backward compatibility."""
        league = self.get(league_id)
        if not league:
            return None

        # International leagues don't have a country_name — default to "International"
        country = league.get("country_name") or league.get("country") or ""
        if not country and league.get("scope") == "international":
            country = "International"

        return {
            "name": league.get("name", ""),
            "country": country,
            "sport": league.get("sport", DEFAULT_SPORT),
        }

    def to_leagues_metadata(self, sport: Optional[str] = None) -> dict[str, dict]:
        """Convert leagues to the LEAGUES_METADATA format, optionally filtered by sport."""
        result = {}
        for league in self._all_leagues:
            if sport and league.get("sport", DEFAULT_SPORT) != sport:
                continue
            league_id = league.get("id")
            if league_id:
                result[league_id] = self.to_metadata_format(league_id)
        return result

    def get_default_leagues(self) -> list[str]:
        """Get default league IDs for training/predictions (top tiers + international)."""
        defaults = []

        # Top domestic leagues (tier 1)
        for league in self.get_by_tier(1):
            if league.get("active", True):
                defaults.append(league["id"])

        # International competitions
        for league in self.get_by_type("international_club"):
            if league.get("active", True):
                defaults.append(league["id"])

        for league in self.get_by_type("international_national"):
            if league.get("active", True):
                defaults.append(league["id"])

        return defaults

    def get_stats(self) -> dict:
        """Get dataset statistics."""
        return {
            "total_leagues": len(self._all_leagues),
            "active_leagues": len(self._active),
            "countries": len(self._by_country),
            "confederations": len(self._by_confederation),
            "by_tier": {str(tier): len(leagues) for tier, leagues in sorted(self._by_tier.items())},
            "by_type": {ltype: len(leagues) for ltype, leagues in self._by_type.items()},
        }


# Module-level singleton
dataset = LeagueDataset()
