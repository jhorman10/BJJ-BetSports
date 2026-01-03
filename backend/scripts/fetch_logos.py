import asyncio
import json
import os
import sys
import logging
import httpx
from datetime import datetime

# Add project root to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), "../"))

from src.infrastructure.data_sources.espn import ESPN_LEAGUE_MAPPING
from src.domain.services.statistics_service import StatisticsService

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DATA_FILE = os.path.join(os.path.dirname(__file__), "../data/team_logos.json")
BASE_URL = "http://site.api.espn.com/apis/site/v2/sports/soccer"

async def fetch_league_teams(client, league_code, slug):
    """Fetch all teams for a given league slug."""
    url = f"{BASE_URL}/{slug}/teams"
    logger.info(f"Fetching teams for {league_code} ({slug})...")
    
    try:
        # ESPN API usually restricts result size, but for teams it often returns all for a league
        # If pagination is needed, we might need 'limit=1000'
        response = await client.get(url, params={"limit": 1000})
        response.raise_for_status()
        data = response.json()
        
        teams_data = {}
        
        if "sports" not in data:
            logger.warning(f"No sports data found for {slug}")
            return {}

        leagues = data["sports"][0].get("leagues", [])
        if not leagues:
            return {}
            
        teams_list = leagues[0].get("teams", [])
        logger.info(f"Found {len(teams_list)} teams in {slug}")
        
        for item in teams_list:
            team = item.get("team", {})
            name = team.get("displayName")
            logos = team.get("logos", [])
            
            if not name or not logos:
                continue
                
            # Get the first logo (usually higher res or default)
            logo_url = logos[0].get("href")
            
            # Normalize the name using our service to match internal keys
            normalized_name = StatisticsService._normalize_name(name)
            
            teams_data[normalized_name] = logo_url
            
            # Also save raw name just in case
            teams_data[name.lower()] = logo_url
            
        return teams_data

    except Exception as e:
        logger.error(f"Error fetching {slug}: {e}")
        return {}

async def main():
    logger.info("Starting ESPN Logo Fetcher...")
    
    all_logos = {}
    
    # Load existing if available to merge? 
    # For now, let's overwrite to ensure freshness, or merge?
    # Overwrite is cleaner to remove stale data.
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        tasks = []
        for code, slug in ESPN_LEAGUE_MAPPING.items():
            tasks.append(fetch_league_teams(client, code, slug))
            
        results = await asyncio.gather(*tasks)
        
        for res in results:
            all_logos.update(res)
            
    logger.info(f"Total logos fetched: {len(all_logos)}")
    
    # Save to JSON
    with open(DATA_FILE, "w") as f:
        json.dump(all_logos, f, indent=2)
        
    logger.info(f"Saved logo mappings to {DATA_FILE}")

if __name__ == "__main__":
    asyncio.run(main())
