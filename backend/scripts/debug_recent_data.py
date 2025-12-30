import asyncio
import sys
import os
from datetime import datetime
import pandas as pd

# Add project root to path
sys.path.append(os.getcwd())

from src.application.services.training_data_service import TrainingDataService
from src.api.dependencies import get_data_sources, get_match_enrichment_service

async def check_recent_data():
    # Instantiate service with dependencies
    data_sources = get_data_sources()
    enrichment_service = get_match_enrichment_service()
    service = TrainingDataService(data_sources, enrichment_service)
    
    league_code = "E0" # Premier League
    
    print(f"--- Fetching Backfilled Data for {league_code} ---")
    # This calls fetch_comprehensive_training_data which HAS the backfill logic
    matches = await service.fetch_comprehensive_training_data([league_code], days_back=30, force_refresh=True)
    
    print(f"Total Matches Found: {len(matches)}")
    
    if not matches:
        print("No matches found.")
        return

    # Sort by date descending
    # Sort by date descending (handle TZ issues)
    from src.utils.time_utils import COLOMBIA_TZ
    def get_sort_key(m):
        dt = m.match_date
        return COLOMBIA_TZ.localize(dt) if dt.tzinfo is None else dt
        
    matches.sort(key=get_sort_key, reverse=True)
    
    print("\n--- Latest 10 Matches ---")
    for m in matches[:10]:
        print(f"Date: {m.match_date} | {m.home_team.name} vs {m.away_team.name} | Score: {m.home_goals}-{m.away_goals}")

    # Check specifically for Dec 28/29
    dec_matches = [m for m in matches if m.match_date.month == 12 and m.match_date.day in [28, 29] and m.match_date.year == 2025] # Wait, user said Dec 28/29... presumably 2024? The user prompt date is Dec 30, 2025. Wait.
    # User State Time: 2025-12-30.
    # User says "matches from Dec 28 and 29 like Bundesliga".
    # Assuming user means Dec 28/29, 2025.
    
    print(f"\n--- Matches on Dec 28/29 ---")
    if dec_matches:
        for m in dec_matches:
            print(f"FOUND: {m.match_date} | {m.home_team.name} vs {m.away_team.name}")
    else:
        print("No matches found for Dec 28/29.")

if __name__ == "__main__":
    asyncio.run(check_recent_data())
