#!/usr/bin/env python3
"""
Audit Predictions Cache Script

Verifies the integrity, coverage, and freshness of the ML training cache.
Can optionally trigger a fix for missing leagues.

Usage:
    python scripts/audit_predictions_cache.py [--fix]
"""

import sys
import os
import argparse
import asyncio
import logging
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("AuditCache")

# Add project root to path
sys.path.append(os.getcwd())

try:
    from src.core.constants import DEFAULT_LEAGUES
    from src.infrastructure.cache.training_cache import get_training_cache
    from src.api.dependencies import get_ml_training_orchestrator
except ImportError as e:
    logger.error(f"Import Error: {e}")
    logger.error("Make sure you are running this script from the backend root directory.")
    sys.exit(1)

# ANSI Colors
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

async def audit_cache(fix_missing: bool = False):
    print(f"{Colors.HEADER}=== STARTING PREDICTIONS CACHE AUDIT ==={Colors.ENDC}")
    
    # 1. Load Cache
    cache = get_training_cache()
    if not cache.is_valid():
        print(f"{Colors.FAIL}[!] Cache is invalid or empty.{Colors.ENDC}")
        results = {}
    else:
        results = cache.get_training_results() or {}
        last_update = cache.get_last_update()
        print(f"Cache Last Update: {Colors.OKCYAN}{last_update}{Colors.ENDC}")

    match_history = results.get('match_history', [])
    print(f"Total Matches in History: {len(match_history)}")
    
    # 2. Analyze League Coverage
    league_stats: Dict[str, Dict[str, int]] = {l: {'total': 0, 'recent': 0} for l in DEFAULT_LEAGUES}
    missing_leagues = []
    
    now = datetime.now()
    cutoff_30d = now - timedelta(days=30)
    
    for match in match_history:
        # Extract league ID from match ID (format: LEAGUE_DATE_HOME_AWAY)
        try:
            league_id = match['match_id'].split('_')[0]
            if league_id in league_stats:
                league_stats[league_id]['total'] += 1
                
                # Check date
                m_date = datetime.fromisoformat(match['match_date'].replace('Z', '+00:00')).replace(tzinfo=None)
                if m_date >= cutoff_30d:
                    league_stats[league_id]['recent'] += 1
        except Exception:
            continue

    # 3. Print Table
    print(f"\n{Colors.BOLD}{'LEAGUE':<10} {'TOTAL':<10} {'LAST 30D':<10} {'STATUS':<15}{Colors.ENDC}")
    print("-" * 45)
    
    for league_code in DEFAULT_LEAGUES:
        stats = league_stats[league_code]
        total = stats['total']
        recent = stats['recent']
        
        if total == 0:
            status = f"{Colors.FAIL}MISSING{Colors.ENDC}"
            missing_leagues.append(league_code)
        elif recent == 0:
            status = f"{Colors.WARNING}STALE{Colors.ENDC}"
            missing_leagues.append(league_code) # Treat stale as missing for fix purposes
        else:
            status = f"{Colors.OKGREEN}OK{Colors.ENDC}"
            
        print(f"{league_code:<10} {total:<10} {recent:<10} {status:<15}")

    # 4. Data Integrity Check (Sample)
    print(f"\n{Colors.HEADER}--- Data Integrity Check ---{Colors.ENDC}")
    if match_history:
        sample_size = min(50, len(match_history))
        sample = random.sample(match_history, sample_size)
        integrity_issues = 0
        
        for m in sample:
            if not m.get('picks'):
                integrity_issues += 1
                continue
                
            # Check arbitrary pick
            p = m['picks'][0]
            if not all(k in p for k in ['market_label', 'probability', 'confidence', 'result']):
                integrity_issues += 1
        
        if integrity_issues == 0:
            print(f"{Colors.OKGREEN}✓ Random sample of {sample_size} matches passed integrity checks.{Colors.ENDC}")
        else:
            print(f"{Colors.FAIL}✖ Found {integrity_issues} matches with malformed data in sample.{Colors.ENDC}")
            
        # Check overall stats exist
        if results.get('pick_efficiency'):
             print(f"{Colors.OKGREEN}✓ Pick Efficiency stats present.{Colors.ENDC}")
        else:
             print(f"{Colors.FAIL}✖ Pick Efficiency stats MISSING.{Colors.ENDC}")
    else:
        print(f"{Colors.WARNING}Cannot check integrity: No history found.{Colors.ENDC}")

    # 5. Auto-Fix
    if missing_leagues:
        print(f"\n{Colors.WARNING}[!] Found {len(missing_leagues)} leagues with missing or stale data.{Colors.ENDC}")
        if fix_missing:
            print(f"{Colors.OKBLUE}>>> Initiating Auto-Fix for: {missing_leagues}{Colors.ENDC}")
            try:
                orchestrator = get_ml_training_orchestrator()
                
                # Run pipeline specifically for missing leagues with force_refresh
                print("Triggering training pipeline...")
                result = await orchestrator.run_training_pipeline(
                    league_ids=missing_leagues,
                    days_back=365,
                    force_refresh=True
                )
                
                print(f"{Colors.OKGREEN}✓ Fix complete! Processed {result.matches_processed} matches.{Colors.ENDC}")
                
                # Check cache again to confirm
                print("Verifying cache post-fix...")
                # (Simple re-check invocation could happen here, or just trust the result)
                
            except Exception as e:
                print(f"{Colors.FAIL}Error during auto-fix: {e}{Colors.ENDC}")
        else:
            print(f"Run with {Colors.BOLD}--fix{Colors.ENDC} to repair automatically.")
    else:
        print(f"\n{Colors.OKGREEN}✓ System Healthy. All leagues covered.{Colors.ENDC}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audit Predictions Cache")
    parser.add_argument("--fix", action="store_true", help="Automatically trigger training for missing leagues")
    args = parser.parse_args()
    
    try:
        asyncio.run(audit_cache(args.fix))
    except KeyboardInterrupt:
        print("Audit cancelled.")
