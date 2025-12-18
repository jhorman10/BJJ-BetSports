
import asyncio
import os
import logging
import json
from dotenv import load_dotenv
from src.infrastructure.data_sources.football_data_org import FootballDataOrgSource

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    load_dotenv()
    
    source = FootballDataOrgSource()
    if not source.is_configured:
        print("API Key not found!")
        return

    # Fetch a recent PL match or list matches to find one
    # Let's list matches first to get a valid ID (e.g. for PL 'PL' -> 'E0')
    # Actually FD.org uses 'PL'
    
    # Let's get "PL" matches
    print("Fetching matches...")
    # Matches endpoint in source uses internal "E0"
    matches = await source.get_upcoming_matches("E0")
    
    if not matches:
        print("No upcoming matches found in PL. Trying a finished one via direct ID if possible, or source logic.")
        # Try to just make a direct raw request to a recent match ID if we knew one.
        # But let's rely on getting ANY match ID from the list
    
    if matches:
        match_id = matches[0].id
        print(f"Inspecting Match ID: {match_id}")
        
        # Now call the raw request method to see full JSON
        # We need to access the private method or just reuse the code
        # Let's use the public get_match_details and modify it to print raw data OR just subclass/hack it
        # Actually simpler: just use requests/httpx directly here for inspection
        import httpx
        
        url = f"https://api.football-data.org/v4/matches/{match_id}"
        headers = {"X-Auth-Token": os.getenv("FOOTBALL_DATA_ORG_KEY")}
        
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers)
            data = resp.json()
            print(json.dumps(data, indent=2))
            
    else:
        print("No matches to inspect.")

if __name__ == "__main__":
    asyncio.run(main())
