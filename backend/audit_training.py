
import json
from datetime import datetime
import os

def audit_training_data():
    cache_path = "/tmp/bjj-betsports-cache/training_20251231.json"
    if not os.path.exists(cache_path):
        print(f"Error: Cache file not found at {cache_path}")
        return

    with open(cache_path, 'r') as f:
        data = json.load(f)

    last_update = data.get("last_update")
    training_results = data.get("results", {}).get("training_results", {})
    match_history = training_results.get("match_history", [])

    if not match_history:
        print("Error: No match history found in cache.")
        return

    # Sort match history by date descending
    # Dates are in ISO format
    sorted_history = sorted(match_history, key=lambda x: x.get("match_date", ""), reverse=True)

    latest_match = sorted_history[0]
    latest_matches = sorted_history[:10]

    print(f"Last Update: {last_update}")
    print(f"Latest Match: {latest_match.get('home_team')} vs {latest_match.get('away_team')} - {latest_match.get('match_date')}")
    print(f"Match Keys: {list(latest_match.keys())}")
    
    # Sources used in recent matches
    sources = set()
    for m in latest_matches:
        if 'data_sources' in m:
            sources.update(m['data_sources'])
        # Try to find it in picks if not in top level
        for p in m.get('picks', []):
            if 'source' in p:
                sources.add(p['source'])
            if 'data_sources' in p:
                sources.update(p['data_sources'])
    
    print(f"Fuentes Detectadas: {list(sources)}")
    print("Top 10 Latest Matches:")
    for m in latest_matches:
        print(f"- {m.get('match_date')}: {m.get('home_team')} vs {m.get('away_team')} (ID: {m.get('match_id')})")

if __name__ == "__main__":
    audit_training_data()
