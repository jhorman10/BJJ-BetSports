import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from dotenv import load_dotenv
load_dotenv()

from src.infrastructure.data_sources.api_football import APIFootballSource

async def search_team_league():
    source = APIFootballSource()
    print("Searching for Peterborough United...")
    team_id = await source.search_team("Peterborough United")
    
    if team_id:
        print(f"Found Team ID: {team_id}")
        # Get next match to see league
        matches = await source.get_team_matches("Peterborough United")
        if matches:
            m = matches[0]
            print(f"Next Match League: {m.league.name} (ID: {m.league.id})")
        else:
            print("No upcoming matches found to identify league.")
    else:
        print("Team not found.")

if __name__ == "__main__":
    asyncio.run(search_team_league())
