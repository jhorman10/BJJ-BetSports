import asyncio
import logging
import random
from datetime import datetime, timedelta
from typing import Any, Dict, List

from src.application.services.ml_training_orchestrator import MLTrainingOrchestrator
from src.core.constants import DEFAULT_LEAGUES

logger = logging.getLogger(__name__)

# Minimum fields a pick must expose to be considered structurally sound.
# Adapted from the original audit's (`market_label`, `probability`,
# `confidence`, `result`): the real SuggestedPickDTO shape has no `result`
# field — confidence is exposed as `confidence_level` / `ml_confidence`.
_PICK_REQUIRED_KEYS = ("market_label", "probability")
_PICK_CONFIDENCE_KEYS = ("confidence_level", "ml_confidence", "confidence")


def _extract_picks(doc: Dict[str, Any]) -> List[Any]:
    """Extract the picks list from an active prediction doc.

    ``match_predictions.data`` is a ``MatchPredictionDTO.model_dump()`` whose
    pick lists live in ``top_ml_picks`` (preferred) or
    ``prediction.suggested_picks`` (use_cases.py:860 persists exactly this
    shape). Defensive: any unexpected payload shape yields an empty list.
    """
    data = doc.get("prediction") or {}
    if not isinstance(data, dict):
        return []

    top_ml_picks = data.get("top_ml_picks") or []
    if top_ml_picks:
        return top_ml_picks

    prediction = data.get("prediction") or {}
    if isinstance(prediction, dict):
        return prediction.get("suggested_picks") or []
    return []


class AuditService:
    """
    Service responsible for auditing the integrity, coverage, and freshness
    of the ML prediction data. Can automatically trigger repairs.
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
        report: Dict[str, Any] = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "missing_leagues": [],
            "integrity_issues": 0,
            "actions_taken": [],
        }

        # 1. Load active predictions from Mongo (D1: the training cache no
        # longer holds match_history — coverage/integrity re-source from the
        # persistence repository's active predictions, which carry a 7d TTL).
        try:
            repo = getattr(self.orchestrator, "persistence_repo", None)
            if repo:
                # pymongo is synchronous: run the scan off the event loop so
                # it never blocks other coroutines (W2).
                predictions = await asyncio.to_thread(repo.get_all_active_predictions)
            else:
                predictions = []
        except Exception as exc:
            logger.warning("AUDIT: failed to load active predictions: %s", exc)
            predictions = []

        if not predictions:
            logger.warning("AUDIT: No active predictions in MongoDB.")
            report["status"] = "critical"

        # 2. Analyze League Coverage
        league_stats = {
            league_code: {"total": 0, "recent": 0} for league_code in DEFAULT_LEAGUES
        }
        missing_leagues = []

        now = datetime.now()
        cutoff_30d = now - timedelta(days=30)

        for prediction in predictions:
            try:
                data = prediction.get("prediction") or {}
                match = data.get("match") if isinstance(data, dict) else None
                match = match or {}

                league_id = prediction.get("league_id")
                if not league_id and isinstance(match, dict):
                    league_id = (match.get("league") or {}).get("id")
                # Fallback: match IDs follow LEAGUE_DATE_HOME_AWAY format.
                if not league_id:
                    league_id = prediction["match_id"].split("_")[0]

                if league_id in league_stats:
                    league_stats[league_id]["total"] += 1

                    raw_date = (
                        match.get("match_date") if isinstance(match, dict) else None
                    )
                    if isinstance(raw_date, str):
                        m_date = datetime.fromisoformat(
                            raw_date.replace("Z", "+00:00")
                        ).replace(tzinfo=None)
                    elif isinstance(raw_date, datetime):
                        m_date = raw_date.replace(tzinfo=None)
                    else:
                        m_date = None

                    if m_date is not None and m_date >= cutoff_30d:
                        league_stats[league_id]["recent"] += 1
            except Exception as e:
                logger.debug(f"Error processing prediction in audit: {e}")
                continue

        # 3. Detect Missing/Stale Leagues
        for league_code in DEFAULT_LEAGUES:
            stats = league_stats[league_code]
            if stats["recent"] == 0:
                logger.warning(
                    "AUDIT: League %s is missing or stale (0 recent matches).",
                    league_code,
                )
                missing_leagues.append(league_code)

        report["missing_leagues"] = missing_leagues

        # 4. Data Integrity Check (Sample)
        if predictions:
            sample_size = min(30, len(predictions))
            sample = random.sample(predictions, sample_size)
            integrity_issues = 0

            for p in sample:
                picks = _extract_picks(p)
                if not picks:
                    integrity_issues += 1
                    continue
                for pick in picks:
                    if not isinstance(pick, dict):
                        integrity_issues += 1
                        continue
                    if not all(k in pick for k in _PICK_REQUIRED_KEYS):
                        integrity_issues += 1
                        continue
                    if not any(k in pick for k in _PICK_CONFIDENCE_KEYS):
                        integrity_issues += 1

            report["integrity_issues"] = integrity_issues
            if integrity_issues > 0:
                report["status"] = "degraded"
                logger.warning(
                    "AUDIT: Found %s integrity issues in sample.",
                    integrity_issues,
                )

        # 5. Auto-Fix Logic
        if missing_leagues:
            report["status"] = "repairing"
            if fix_missing:
                logger.info(
                    f"AUDIT: triggering auto-fix for leagues: {missing_leagues}"
                )
                try:
                    # Run training pipeline specifically for missing leagues
                    # We run it in a way that doesn't block the main thread
                    # (orchestrator now handles threading)
                    await self.orchestrator.run_training_pipeline(
                        league_ids=missing_leagues, days_back=550, force_refresh=True
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
