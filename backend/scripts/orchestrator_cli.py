import argparse
import asyncio
import logging
import multiprocessing
import os
import sys
import warnings

# Load environment variables from .env file FIRST
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(env_path)

# Setup path to include backend src
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# Configure Logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
# Reduce noise from libraries
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

logger = logging.getLogger("OrchestratorCLI")

# Detectar número de CPUs disponibles
CPU_COUNT = int(os.getenv("N_JOBS", multiprocessing.cpu_count()))
logger.info(f"🚀 Running with {CPU_COUNT} CPU cores")

try:
    from tqdm import tqdm
except Exception:
    # Fallback: Simple iterator without progress bar (minimal API used)
    class Tqdm:
        def __init__(self, iterable=None, **kwargs):
            self.iterable = iterable
            self.total = kwargs.get("total", len(iterable) if iterable else 0)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def __iter__(self):
            return iter(self.iterable) if self.iterable else iter([])

        def update(self, n=1):
            pass

        def set_postfix_str(self, s):
            pass

    tqdm = Tqdm


async def cmd_train(
    days_back: int = 550,
    n_jobs: int = None,
    skip_cleanup: bool = False,
    leagues_str: str | None = None,
):
    """
    Step 1: Retrain the ML Model with parallel processing.
    """
    if n_jobs is None:
        n_jobs = CPU_COUNT

    logger.info(
        f"CMD: TRAIN. Days back: {days_back}, n_jobs: {n_jobs}, "
        f"leagues: {leagues_str or 'default'}"
    )
    from src.dependencies import get_cache_service, get_ml_training_orchestrator

    orchestrator = get_ml_training_orchestrator()
    cache = get_cache_service()

    # [FIX] Get Persistence Repo to save results to DB (source of truth for Dashboard)
    from src.dependencies import get_persistence_repository

    repo = get_persistence_repository()

    # [AUTO-CLEANUP] Limpiar DB y caché antes de entrenar para asegurar datos frescos
    if not skip_cleanup:
        logger.info("🧹 AUTO-CLEANUP: Limpiando datos anteriores...")
        try:
            db_results = repo.clear_all_data()
            logger.info(f"📊 Database cleanup: {db_results}")
            cache.clear()
            logger.info("✅ Cache limpiado - Pipeline iniciará con datos frescos.")
        except Exception as cleanup_err:
            logger.warning(f"⚠️ Cleanup parcial (no fatal): {cleanup_err}")

    if leagues_str:
        leagues = [
            league.strip() for league in leagues_str.split(",") if league.strip()
        ]
    else:
        from src.core.constants import DEFAULT_LEAGUES

        leagues = DEFAULT_LEAGUES
    logger.info(f"Targeting Leagues: {leagues}")

    try:
        if os.getenv("DISABLE_ML_TRAINING") == "true":
            logger.info("Training disabled via env var.")
            return

        # Inject git_sha for artifact metadata (ml-model-deployment spec)
        if "GIT_SHA" not in os.environ:
            try:
                import subprocess
                git_sha = subprocess.check_output(
                    ["git", "rev-parse", "--short", "HEAD"],
                    cwd=PROJECT_ROOT,
                    stderr=subprocess.DEVNULL,
                ).decode().strip()
                os.environ["GIT_SHA"] = git_sha
                logger.info(f"🔖 Injected GIT_SHA={git_sha}")
            except Exception:
                os.environ["GIT_SHA"] = "unknown"
                logger.warning("Could not determine git SHA; using 'unknown'")

        # Old orchestrator doesn't support n_jobs, removed for compatibility
        training_result = await orchestrator.run_training_pipeline(
            league_ids=leagues, days_back=days_back
        )

        # Save validation metrics to Cache/DB if needed
        logger.info(f"✅ Training Complete. Accuracy: {training_result.accuracy:.2%}")

        # Cache Result
        training_data = {
            "matches_processed": training_result.matches_processed,
            "accuracy": training_result.accuracy,
            "roi": training_result.roi,
            "global_averages": getattr(training_result, "global_averages", {}),
            "context_summary": getattr(training_result, "context_summary", {}),
        }
        cache.set("ml_training_result_data", training_data, ttl_seconds=86400)

        # [FIX] Persist to Database for Dashboard Visibility
        # IMPORTANT: Only save lightweight metrics - full model_dump() is ~69MB and
        # causes SSL timeouts
        logger.info("💾 Persisting Training Result to Database...")
        lightweight_result = {
            "matches_processed": training_result.matches_processed,
            "correct_predictions": training_result.correct_predictions,
            "accuracy": training_result.accuracy,
            "total_bets": training_result.total_bets,
            "roi": training_result.roi,
            "profit_units": training_result.profit_units,
            "market_stats": training_result.market_stats,
            "roi_evolution": training_result.roi_evolution,
            "pick_efficiency": training_result.pick_efficiency,
            "context_summary": getattr(training_result, "context_summary", {}),
            # Exclude: match_history (~60MB), team_stats (~9MB)
        }
        try:
            repo.save_training_result("latest_daily", lightweight_result)
            logger.info(
                "✅ Training Result successfully saved to DB (key: latest_daily)"
            )
        except Exception as db_err:
            logger.error(f"⚠️ Failed to persist to DB (non-fatal): {db_err}")

    except Exception as e:
        logger.error(f"❌ Training Failed: {e}", exc_info=True)
        sys.exit(1)


async def process_league_async(
    league_id: str, use_case, persistence_repository, force: bool = False
):
    """
    Helper para procesar una liga de manera asíncrona.
    """
    from src.infrastructure.data_sources.football_data_uk import LEAGUES_METADATA

    if league_id not in LEAGUES_METADATA:
        logger.warning(f"⚠️  Skipping unknown league: {league_id}")
        return None

    # Delegate to the refactored generator which is easier to test
    return await generate_predictions_for_league(
        league_id, use_case, persistence_repository, force=force
    )


def prepare_services():
    """Inicializa y devuelve el `use_case` y el `persistence_repository`.

    Las importaciones se hacen en tiempo de ejecución para evitar ciclos de importación
    y para facilitar el mocking en las pruebas unitarias.
    """
    from src.application.use_cases.use_cases import GetPredictionsUseCase
    from src.dependencies import (
        get_data_sources,
        get_match_aggregator_service,
        get_persistence_repository,
        get_prediction_service,
        get_statistics_service,
    )

    repo = get_persistence_repository()

    use_case = GetPredictionsUseCase(
        data_sources=get_data_sources(),
        prediction_service=get_prediction_service(),
        statistics_service=get_statistics_service(),
        match_aggregator=get_match_aggregator_service(),
        persistence_repository=repo,
    )

    return use_case, repo


async def generate_predictions_for_league(
    league_id: str, use_case, persistence_repository, force: bool = False
):
    """Genera predicciones para una liga y devuelve (league_id, success_bool)."""
    logger.info(f"🔄 Processing League: {league_id}")
    try:
        result = await use_case.execute(
            league_id,
            limit=50,
            force_refresh=True if "force" in locals() and force else False,
        )

        preds = getattr(result, "predictions", None)
        if preds is not None:
            logger.info(f"✅ Generated {len(preds)} predictions for {league_id}")
        else:
            logger.info(f"✅ No predictions returned for {league_id}")

        return league_id, True
    except Exception as e:
        logger.error(f"❌ Failed to process {league_id}: {e}", exc_info=True)
        return league_id, False


def map_picks_to_dtos(picks):
    """Mapea una lista de 'picks' a diccionarios listos para persistir.

    Intenta manejar objetos con `model_dump()`, `dict()` o simples `dict`.
    """
    dtos = []
    for p in picks:
        if isinstance(p, dict):
            dtos.append(p)
        elif hasattr(p, "model_dump"):
            try:
                dtos.append(p.model_dump())
            except Exception:
                try:
                    dtos.append(p.dict())
                except Exception:
                    dtos.append(vars(p))
        elif hasattr(p, "dict"):
            dtos.append(p.dict())
        else:
            try:
                dtos.append(vars(p))
            except Exception:
                dtos.append({"value": p})
    return dtos


def persist_batch(repo, batch):
    """Intenta persistir un batch usando la API conocida del repositorio.

    Devuelve True si la operación parece haber sido ejecutada (no necesariamente válida
    semánticamente), False en caso de excepción.
    """
    try:
        if hasattr(repo, "bulk_save_predictions"):
            repo.bulk_save_predictions(batch)
        elif hasattr(repo, "save_predictions"):
            repo.save_predictions(batch)
        elif hasattr(repo, "save_training_result"):
            # Fallback conservador
            repo.save_training_result("predictions_batch", batch)
        else:
            logger.warning("Repository has no known bulk save method.")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to persist batch: {e}", exc_info=True)
        return False


async def cmd_predict(leagues_str: str, parallel: bool = True, force: bool = False):
    """
    Step 2: Massive Inference for specific leagues with parallel processing.
    """
    leagues = [league.strip() for league in leagues_str.split(",") if league.strip()]
    logger.info(f"CMD: PREDICT. Target Leagues: {leagues}, Parallel: {parallel}")

    # Inicializar servicios y repositorio (se extrae a helper para facilitar tests)
    use_case, repo = prepare_services()

    if parallel and len(leagues) > 1:
        # Procesar múltiples ligas en paralelo usando helper
        results = await _process_leagues_parallel(leagues, use_case, repo, force)

        # Analizar resultados
        failed = []
        succeeded = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Exception during processing: {result}")
                failed.append("unknown")
            elif result and result[1]:
                succeeded.append(result[0])
            elif result:
                failed.append(result[0])

        logger.info(
            "📊 Results: ✅ %d succeeded, ❌ %d failed" % (len(succeeded), len(failed))
        )

        if failed:
            logger.warning(f"⚠️  Failed leagues: {failed}")
            if len(failed) == len(leagues):
                logger.error("❌ All leagues failed!")
                sys.exit(1)
    else:
        # Procesamiento secuencial con helper
        failed = await _process_leagues_sequential(leagues, use_case, repo, force)

        if failed and len(failed) == len(leagues):
            logger.error("❌ All leagues failed!")
            sys.exit(1)

        if failed:
            logger.warning(f"⚠️  Some leagues failed: {failed}")
        else:
            logger.info("✨ All leagues processed successfully.")


async def _process_leagues_parallel(leagues, use_case, repo, force: bool = False):
    """Helper: procesa ligas en paralelo y devuelve la lista de resultados."""
    logger.info(f"🔥 Processing {len(leagues)} leagues in parallel")
    tasks = [
        process_league_async(league_id, use_case, repo, force=force)
        for league_id in leagues
    ]

    # Barra de progreso para el procesamiento paralelo
    results = []
    with tqdm(total=len(leagues), desc="Leagues (parallel)", unit="league") as pbar:
        for coro in asyncio.as_completed(tasks):
            result = await coro
            pbar.update(1)
            if result:
                pbar.set_postfix_str(f"Completed {result[0]}")
            results.append(result)

    return results


async def _process_leagues_sequential(leagues, use_case, repo, force: bool = False):
    """Helper: procesa ligas de forma secuencial y devuelve la lista de fallos."""
    logger.info(f"🔄 Processing {len(leagues)} leagues sequentially")
    failed = []
    with tqdm(leagues, desc="Leagues", unit="league") as pbar:
        for league_id in pbar:
            pbar.set_postfix_str(f"Processing {league_id}")
            result = await process_league_async(league_id, use_case, repo, force=force)
            if result and not result[1]:
                failed.append(result[0])

    return failed


async def cmd_cleanup():
    """
    Step 0: Clear ALL cached data and predictions before running the pipeline.
    This ensures fresh data on every run.
    """
    logger.info("🧹 CMD: CLEANUP - Clearing ALL cached data...")
    from src.dependencies import get_cache_service, get_persistence_repository

    repo = get_persistence_repository()
    cache = get_cache_service()

    try:
        # 1. Clear Database tables (predictions, training results, API cache)
        db_results = repo.clear_all_data()
        logger.info(f"📊 Database cleanup results: {db_results}")

        # 2. Clear in-memory/Redis cache (if applicable)
        cache.clear()
        logger.info("✅ In-memory cache cleared.")

        logger.info("✅ CLEANUP COMPLETE - All cached data has been cleared.")

    except Exception as e:
        logger.error(f"❌ Cleanup Failed: {e}", exc_info=True)
        sys.exit(1)


async def cmd_top_picks(limit: int = 50, leagues_str: str = None):
    """
    Step 3: Synthesize and persist top ML picks for all or specific leagues.
    """
    if leagues_str:
        leagues = [
            league.strip() for league in leagues_str.split(",") if league.strip()
        ]
    else:
        from src.core.constants import DEFAULT_LEAGUES

        leagues = DEFAULT_LEAGUES
    logger.info(f"CMD: TOP-PICKS. Limit: {limit}, Target Leagues: {leagues}")

    from src.application.use_cases.suggested_picks_use_case import GetTopMLPicksUseCase
    from src.dependencies import get_persistence_repository

    repo = get_persistence_repository()
    use_case = GetTopMLPicksUseCase(repo)

    try:
        # 1. Generate for each league individually (Map)
        for league_id in leagues:
            logger.info(f"🏆 Generating Top Picks for {league_id}...")
            result = await use_case.execute(limit=limit, league_id=league_id)
            if result and result.picks:
                key = f"top_ml_picks_{league_id}"
                repo.save_training_result(key, result.model_dump())
                logger.info(f"✅ Saved {len(result.picks)} top picks for {league_id}")

        # 2. Generate global top picks (Reduce)
        logger.info("🌎 Generating Global Top Picks...")
        global_result = await use_case.execute(limit=limit)
        if global_result and global_result.picks:
            repo.save_training_result("top_ml_picks_all", global_result.model_dump())
            logger.info("✅ Saved global top picks (key: top_ml_picks_all)")

    except Exception as e:
        logger.error(f"❌ Top-Picks Generation Failed: {e}", exc_info=True)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="MLOps Orchestrator - Optimized for Parallel Processing"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Train
    parser_train = subparsers.add_parser("train", help="Train ML model")
    parser_train.add_argument(
        "--days",
        type=int,
        default=550,
        help="Number of days back for training data (default: 550)",
    )
    parser_train.add_argument(
        "--n-jobs",
        type=int,
        default=None,
        help="Number of parallel jobs for ML training (default: auto-detect)",
    )
    parser_train.add_argument(
        "--skip-cleanup",
        action="store_true",
        help="Skip automatic cleanup of DB/cache before training",
    )
    parser_train.add_argument(
        "--leagues",
        type=str,
        default=None,
        help="Optional comma separated league IDs for training scope",
    )

    # Predict
    parser_predict = subparsers.add_parser(
        "predict", help="Run predictions for leagues"
    )
    parser_predict.add_argument(
        "--leagues",
        type=str,
        required=True,
        help="Comma separated league IDs (e.g., 'E0,E1,E2')",
    )
    parser_predict.add_argument(
        "--parallel",
        action="store_true",
        default=True,
        help="Process leagues in parallel (default: True)",
    )
    parser_predict.add_argument(
        "--sequential",
        dest="parallel",
        action="store_false",
        help="Process leagues sequentially",
    )
    parser_predict.add_argument(
        "--force",
        action="store_true",
        help="Force regeneration of predictions (ignore cache)",
    )

    # Top-Picks
    parser_top_picks = subparsers.add_parser(
        "top-picks", help="Generate and persist top ML picks"
    )
    parser_top_picks.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Max number of picks to store (default: 50)",
    )
    parser_top_picks.add_argument(
        "--leagues",
        type=str,
        default=None,
        help="Optional comma separated league IDs filter",
    )

    # Cleanup
    subparsers.add_parser("cleanup", help="Clear ALL cached data before pipeline run")

    args = parser.parse_args()

    # =====================================================
    # DATABASE INITIALIZATION (Tables auto-creation)
    # This ensures tables exist before any DB operations.
    # =====================================================
    try:
        from src.dependencies import get_persistence_repository

        repo = get_persistence_repository()
        repo.create_tables()
        logger.info("✅ Database tables verified/created.")
    except Exception as db_init_err:
        logger.warning(
            f"⚠️ Could not initialize DB tables (may already exist): {db_init_err}"
        )

    try:
        if args.command == "train":
            asyncio.run(
                cmd_train(args.days, args.n_jobs, args.skip_cleanup, args.leagues)
            )
        elif args.command == "predict":
            asyncio.run(cmd_predict(args.leagues, args.parallel, args.force))
        elif args.command == "top-picks":
            asyncio.run(cmd_top_picks(args.limit, args.leagues))
        elif args.command == "cleanup":
            asyncio.run(cmd_cleanup())
    except KeyboardInterrupt:
        logger.info("⚠️  Interrupted by user")
        pass
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
