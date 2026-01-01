
import asyncio
import os
from dotenv import load_dotenv
from src.infrastructure.data_sources.football_data_org import FootballDataOrgSource

async def verify():
    load_dotenv()
    api_key = os.getenv("FOOTBALL_DATA_ORG_KEY")
    if not api_key:
        print("❌ FOOTBALL_DATA_ORG_KEY not found in .env")
        return

    from src.infrastructure.data_sources.football_data_org import FootballDataOrgSource, FootballDataOrgConfig

    source = FootballDataOrgSource(config=FootballDataOrgConfig(api_key=api_key))
    print(f"Testing Football-Data.org with key: {api_key[:5]}...")
    
    try:
        # Test fetching upcoming matches for multiple leagues
        from src.infrastructure.data_sources.football_data_org import COMPETITION_CODE_MAPPING
        
        for internal_code, org_code in COMPETITION_CODE_MAPPING.items():
            try:
                matches = await source.get_upcoming_matches(org_code)
                if matches:
                    print(f"✅ Successfully fetched {len(matches)} upcoming matches for {org_code} ({internal_code})")
                    for m in matches[:2]:
                        print(f"  - {m.home_team.name} vs {m.away_team.name} ({m.match_date})")
                    break # Found some matches, good enough
                else:
                    print(f"⚠ No upcoming matches for {org_code}")
            except Exception as e:
                print(f"❌ Error fetching {org_code}: {e}")
                
        # Test live matches
        live = await source.get_live_matches()
        print(f"✅ Live matches fetch returned {len(live)} matches")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(verify())
