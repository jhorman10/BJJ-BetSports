
import asyncio
import os
from datetime import datetime
from src.infrastructure.data_sources.football_data_org import FootballDataOrgSource
from src.infrastructure.data_sources.espn import ESPNSource
from src.utils.time_utils import get_current_time

async def test_sources():
    os.environ["FOOTBALL_DATA_ORG_KEY"] = "ee86afdbe1b14dd1af531d9a5cf88994"
    
    today = get_current_time()
    today_str = today.strftime("%Y-%m-%d")
    print(f"Testing sources for today: {today_str}")
    
    # Test Football-Data.org (Finished)
    fd_org = FootballDataOrgSource()
    fd_matches = await fd_org.get_finished_matches(today_str, today_str)
    print(f"Football-Data.org found {len(fd_matches)} finished matches for today.")
    
    # Test Football-Data.org (Scheduled)
    all_leagues = ["E0", "SP1", "D1", "I1", "F1", "N1", "P1", "B1"]
    for league in all_leagues:
        scheduled = await fd_org.get_upcoming_matches(league)
        if scheduled:
            today_scheduled = [m for m in scheduled if m.match_date.date() == today.date()]
            if today_scheduled:
                print(f"League {league} has {len(today_scheduled)} matches scheduled for today.")
                for m in today_scheduled:
                    print(f"- {m.home_team.name} vs {m.away_team.name} ({m.match_date})")
            else:
                print(f"League {league}: No matches today.")

    # Test ESPN (modified to include today i=0)
    espn = ESPNSource()
    # Manual test for i=0
    date_str = today.strftime("%Y%m%d")
    url = f"{espn.BASE_URL}/eng.1/scoreboard" # Test PL
    data = await espn._make_request(url, {"dates": date_str})
    if data and "events" in data:
        events = data["events"]
        print(f"ESPN found {len(events)} events for today (PL).")
        for e in events:
            status = e.get("status", {}).get("type", {}).get("state")
            print(f"- {e.get('name')} status={status}")
    else:
        print("ESPN found no events for today (PL).")

if __name__ == "__main__":
    asyncio.run(test_sources())
