#!/usr/bin/env python3
"""
Verify the global leagues dataset loads correctly.

Usage:
    cd backend
    python -m src.infrastructure.data.verify_dataset
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))


def main() -> None:
    """Verify dataset loads and print stats."""
    print("=" * 60)
    print("🌍 GLOBAL FOOTBALL LEAGUES DATASET VERIFICATION")
    print("=" * 60)
    print()

    try:
        from src.infrastructure.data.league_loader import dataset
        from src.domain.constants import LEAGUES_METADATA, DEFAULT_LEAGUES
        from src.core.constants import DEFAULT_LEAGUES as CORE_DEFAULT_LEAGUES
    except ImportError as e:
        print(f"❌ Import error: {e}")
        sys.exit(1)

    # Dataset stats
    stats = dataset.get_stats()
    print("📊 Dataset Statistics:")
    print(f"   Total leagues: {stats['total_leagues']}")
    print(f"   Active leagues: {stats['active_leagues']}")
    print(f"   Countries: {stats['countries']}")
    print(f"   Confederations: {stats['confederations']}")
    print()
    print("   By Tier:")
    for tier, count in stats['by_tier'].items():
        print(f"     Tier {tier}: {count} leagues")
    print()
    print("   By Type:")
    for ltype, count in stats['by_type'].items():
        print(f"     {ltype}: {count}")

    # Sample lookups
    print()
    print("🔍 Sample Lookups:")
    sample_ids = ["E0", "BRA1", "UCL", "J1", "MLS", "WC"]
    for lid in sample_ids:
        league = dataset.get(lid)
        if league:
            print(f"   {lid}: {league.get('name')} ({league.get('country_name', 'International')})")
        else:
            print(f"   {lid}: ❌ NOT FOUND")

    # Country examples
    print()
    print("🌍 Country Examples:")
    for country in ["England", "Brazil", "Japan", "Mexico", "South Africa"]:
        leagues = dataset.get_by_country(country)
        print(f"   {country}: {len(leagues)} leagues")

    # Confederation examples
    print()
    print("🏛️  Confederation Examples:")
    for conf in ["UEFA", "CONMEBOL", "AFC", "CAF"]:
        leagues = dataset.get_by_confederation(conf)
        print(f"   {conf}: {len(leagues)} leagues")

    # Backward compatibility
    print()
    print("🔗 Backward Compatibility:")
    print(f"   LEAGUES_METADATA entries: {len(LEAGUES_METADATA)}")
    print(f"   DEFAULT_LEAGUES (domain): {len(DEFAULT_LEAGUES)}")
    print(f"   DEFAULT_LEAGUES (core): {len(CORE_DEFAULT_LEAGUES)}")

    # Search test
    print()
    print("🔎 Search Tests:")
    results = dataset.search("Premier")
    print(f"   'Premier': {len(results)} results")
    results = dataset.search("Liga")
    print(f"   'Liga': {len(results)} results")

    print()
    print("=" * 60)
    print("✅ VERIFICATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
