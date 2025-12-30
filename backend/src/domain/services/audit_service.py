import logging
import random
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from src.core.constants import DEFAULT_LEAGUES
from src.infrastructure.cache.training_cache import get_training_cache
from src.application.services.ml_training_orchestrator import MLTrainingOrchestrator

logger = logging.getLogger(__name__)

class AuditService:
    """
    Service responsible for auditing the integrity, coverage, and freshness 
    of the ML prediction cache. Can automatically trigger repairs.
    """

    def __init__(self, training_orchestrator: MLTrainingOrchestrator):
        self.orchestrator = training_orchestrator

    async def audit_and_fix(self, fix_missing: bool = True) -> Dict[str, Any]:
        """
        Run the full audit routine and optionally fix detected issues.
        
        Returns:
            Dict containing the audit report.
        """
        logger.info("AUDIT: Starting automated data integrity check...")
        report = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "missing_leagues": [],
            "integrity_issues": 0,
            "actions_taken": []
        }

        # 1. Load Cache
        cache = get_training_cache()
        if not cache.is_valid():
            logger.warning("AUDIT: Cache is invalid or empty.")
            report["status"] = "critical"
            results = {}
        else:
            results = cache.get_training_results() or {}

        match_history = results.get('match_history', [])
        
        # 2. Analyze League Coverage
        league_stats = {l: {'total': 0, 'recent': 0} for l in DEFAULT_LEAGUES}
        missing_leagues = []
        
        now = datetime.now()
        cutoff_30d = now - timedelta(days=30)
        
        for match in match_history:
            try:
                # Extract league ID from match ID (format: LEAGUE_DATE_HOME_AWAY)
                league_id = match['match_id'].split('_')[0]
                if league_id in league_stats:
                    league_stats[league_id]['total'] += 1
                    
                    # Check date
                    m_date = datetime.fromisoformat(match['match_date'].replace('Z', '+00:00')).replace(tzinfo=None)
                    if m_date >= cutoff_30d:
                        league_stats[league_id]['recent'] += 1
            except Exception:
                continue

        # 3. Detect Missing/Stale Leagues
        for league_code in DEFAULT_LEAGUES:
            stats = league_stats[league_code]
            if stats['recent'] == 0:
                logger.warning(f"AUDIT: League {league_code} is missing or stale (0 recent matches).")
                missing_leagues.append(league_code)

        report["missing_leagues"] = missing_leagues

        # 4. Data Integrity Check (Sample)
        if match_history:
            sample_size = min(30, len(match_history))
            sample = random.sample(match_history, sample_size)
            integrity_issues = 0
            
            for m in sample:
                if not m.get('picks'):
                    integrity_issues += 1
                    continue
                p = m['picks'][0]
                if not all(k in p for k in ['market_label', 'probability', 'confidence', 'result']):
                    integrity_issues += 1
            
            report["integrity_issues"] = integrity_issues
            if integrity_issues > 0:
                report["status"] = "degraded"
                logger.warning(f"AUDIT: Found {integrity_issues} integrity issues in sample.")

        # 5. Auto-Fix Logic
        if missing_leagues:
            report["status"] = "repairing"
            if fix_missing:
                logger.info(f"AUDIT: triggering auto-fix for leagues: {missing_leagues}")
                try:
                    # Run training pipeline specifically for missing leagues
                    # We run it in a way that doesn't block the main thread (orchestrator now handles threading)
                    await self.orchestrator.run_training_pipeline(
                        league_ids=missing_leagues,
                        days_back=365,
                        force_refresh=True
                    )
                    report["actions_taken"].append(f"Retrained: {missing_leagues}")
                    report["status"] = "repaired"
                    logger.info("AUDIT: Auto-fix completed successfully.")
                except Exception as e:
                    logger.error(f"AUDIT: Auto-fix failed: {e}")
                    report["status"] = "failed_repair"
            else:
                report["actions_taken"].append("Fix skipped (disabled)")

        logger.info(f"AUDIT: Check complete. Status: {report['status']}")
        return report
