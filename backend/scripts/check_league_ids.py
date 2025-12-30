import asyncio
import sys
import os
from dotenv import load_dotenv

sys.path.append(os.getcwd())
load_dotenv()

from src.infrastructure.data_sources.api_football import APIFootballSource

async def list_leagues():
    source = APIFootballSource()
    # League One England is usually ID 40 or 41. Let's fetch fixtures for England (Country) if possible, 
    # but search APIs can be restrictive.
    # Instead, let's try to get live matches or just use a known list if possible.
    # Actually, the best way if search fails is to assume standard IDs.
    # League One is 41. Championship is 40. Premier is 39.
    # Let's verify by fetching fixtures for league 41.
    
    league_id = 41 # Expected League One
    print(f"Checking League ID {league_id}...")
    
    matches = await source.get_upcoming_fixtures("UNKNOWN_CHECK", next_n=5)
    
    # We can't pass 'UNKNOWN_CHECK' because it needs to be in the mapping to even TRY.
    # So we need to modify the Mapping locally or just hit the API directly.
    # Let's use _make_request directly.
    
    print("Directly querying league 41...")
    data = await source._make_request("/leagues", {"id": 41})
    print(f"Data 41: {data}")
    if data and data.get('response'):
        l = data['response'][0]['league']
        c = data['response'][0]['country']
        print(f"ID 41: {l['name']} ({c['name']})")
        
    print("Directly querying league 40...")
    data = await source._make_request("/leagues", {"id": 40})
    if data and data['response']:
        l = data['response'][0]['league']
        c = data['response'][0]['country']
        print(f"ID 40: {l['name']} ({c['name']})")

if __name__ == "__main__":
    asyncio.run(list_leagues())
