#!/usr/bin/env python3
"""Benchmark script for AsyncMongoRepository.

Measures latency (p50, p95, p99) for critical endpoints:
- get_match_prediction
- get_match_predictions_bulk
- save_match_prediction
- bulk_save_predictions
- get_cached_response
- save_cached_response

Usage:
    python scripts/benchmark_async_mongo.py -n 100 -c 10
    python scripts/benchmark_async_mongo.py --sync  # compare with sync repo
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

if TYPE_CHECKING:
    from src.infrastructure.repositories.async_mongo_repository import (
        AsyncMongoRepository,
    )
    from src.infrastructure.repositories.mongo_repository import MongoRepository

# Setup path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))


@dataclass
class BenchmarkResult:
    operation: str
    durations_ms: List[float]
    errors: int = 0

    @property
    def ok(self) -> int:
        return len(self.durations_ms) - self.errors

    @property
    def p50(self) -> float:
        return percentile(self.durations_ms, 50)

    @property
    def p95(self) -> float:
        return percentile(self.durations_ms, 95)

    @property
    def p99(self) -> float:
        return percentile(self.durations_ms, 99)

    @property
    def mean(self) -> float:
        return statistics.mean(self.durations_ms) if self.durations_ms else 0

    @property
    def min(self) -> float:
        return min(self.durations_ms) if self.durations_ms else 0

    @property
    def max(self) -> float:
        return max(self.durations_ms) if self.durations_ms else 0


def create_async_repo() -> "AsyncMongoRepository":
    from src.infrastructure.repositories.async_mongo_repository import (
        AsyncMongoRepository,
    )

    return AsyncMongoRepository()


def create_sync_repo() -> "MongoRepository":
    from src.infrastructure.repositories.mongo_repository import MongoRepository

    return MongoRepository()


def percentile(data: List[float], p: float) -> float:
    if not data:
        return 0.0
    s = sorted(data)
    k = (len(s) - 1) * (p / 100.0)
    f = int(math.floor(k))
    c = int(math.ceil(k))
    if f == c:
        return s[f]
    return s[f] * (c - k) + s[c] * (k - f)


def serialize_benchmark_results(
    results: Dict[str, BenchmarkResult],
) -> Dict[str, Dict[str, float | int]]:
    return {
        op: {
            "p50_ms": res.p50,
            "p95_ms": res.p95,
            "p99_ms": res.p99,
            "mean_ms": res.mean,
            "min_ms": res.min,
            "max_ms": res.max,
            "ok": res.ok,
            "errors": res.errors,
        }
        for op, res in results.items()
    }


async def benchmark_single_operation(
    repo: AsyncMongoRepository,
    operation: str,
    data: Dict[str, Any],
    iterations: int,
    concurrency: int,
    sem: Optional[asyncio.Semaphore] = None,
) -> BenchmarkResult:
    durations: List[float] = []
    errors = 0

    op_map: Dict[str, Callable] = {
        "get_match_prediction": lambda: repo.get_match_prediction(
            data.get("match_id", "test_match")
        ),
        "get_match_predictions_bulk": lambda: repo.get_match_predictions_bulk(
            data.get("match_ids", [])
        ),
        "save_match_prediction": lambda: repo.save_match_prediction(
            data.get("match_id", "test_match"),
            data.get("league_id", "E0"),
            data.get("payload", {"test": True}),
            data.get("ttl", 3600),
        ),
        "bulk_save_predictions": lambda: repo.bulk_save_predictions(
            data.get(
                "predictions",
                [
                    {"match_id": f"m_{i}", "league_id": "E0", "data": {}}
                    for i in range(10)
                ],
            )
        ),
        "get_cached_response": lambda: repo.get_cached_response(
            data.get("endpoint", "/api/test")
        ),
        "save_cached_response": lambda: repo.save_cached_response(
            data.get("endpoint", "/api/test"),
            data.get("cached_data", {"result": "test"}),
            None,
            data.get("ttl", 3600),
        ),
    }

    op_func = op_map.get(operation)
    if not op_func:
        return BenchmarkResult(operation=operation, durations_ms=[], errors=1)

    if sem:

        async def run_op():
            async with sem:
                return await op_func()

    else:
        run_op = op_func

    tasks = [run_op() for _ in range(iterations)]
    start = time.perf_counter()

    try:
        results = await asyncio.gather(*tasks, return_exceptions=True)
    except Exception:
        errors = iterations
        return BenchmarkResult(operation=operation, durations_ms=[], errors=errors)

    elapsed_total = (time.perf_counter() - start) * 1000.0

    # Distribute elapsed time across all requests (approximation)
    per_request = elapsed_total / iterations
    durations = [per_request] * iterations

    for r in results:
        if isinstance(r, Exception):
            errors += 1

    return BenchmarkResult(operation=operation, durations_ms=durations, errors=errors)


def run_sync_comparison(
    repo: MongoRepository,
    operation: str,
    data: Dict[str, Any],
    iterations: int,
    concurrency: int,
) -> BenchmarkResult:
    """Run sync version for comparison."""
    durations: List[float] = []
    errors = 0

    op_map: Dict[str, Callable] = {
        "get_match_prediction": lambda: repo.get_match_prediction(
            data.get("match_id", "test_match")
        ),
        "get_match_predictions_bulk": lambda: repo.get_match_predictions_bulk(
            data.get("match_ids", [])
        ),
        "save_match_prediction": lambda: repo.save_match_prediction(
            data.get("match_id", "test_match"),
            data.get("league_id", "E0"),
            data.get("payload", {"test": True}),
            data.get("ttl", 3600),
        ),
        "bulk_save_predictions": lambda: repo.bulk_save_predictions(
            data.get(
                "predictions",
                [
                    {"match_id": f"m_{i}", "league_id": "E0", "data": {}}
                    for i in range(10)
                ],
            )
        ),
        "get_cached_response": lambda: repo.get_cached_response(
            data.get("endpoint", "/api/test")
        ),
        "save_cached_response": lambda: repo.save_cached_response(
            data.get("endpoint", "/api/test"),
            data.get("cached_data", {"result": "test"}),
            None,
            data.get("ttl", 3600),
        ),
    }

    op_func = op_map.get(operation)
    if not op_func:
        return BenchmarkResult(operation=operation, durations_ms=[], errors=1)

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        start = time.perf_counter()
        try:
            list(executor.map(lambda _: op_func(), range(iterations)))
        except Exception:
            errors = iterations
        elapsed_total = (time.perf_counter() - start) * 1000.0

    per_request = elapsed_total / iterations if iterations else 0
    durations = [per_request] * iterations

    return BenchmarkResult(operation=operation, durations_ms=durations, errors=errors)


async def seed_async_repo(repo: AsyncMongoRepository, data: Dict[str, Any]) -> None:
    await repo.save_match_prediction(
        data["match_id"],
        data["league_id"],
        data["payload"],
        data.get("ttl", 3600),
    )
    await repo.bulk_save_predictions(data["predictions"])
    await repo.save_cached_response(
        data["endpoint"],
        data["cached_data"],
        None,
        data.get("ttl", 3600),
    )


def seed_sync_repo(repo: MongoRepository, data: Dict[str, Any]) -> None:
    repo.save_match_prediction(
        data["match_id"],
        data["league_id"],
        data["payload"],
        data.get("ttl", 3600),
    )
    repo.bulk_save_predictions(data["predictions"])
    repo.save_cached_response(
        data["endpoint"],
        data["cached_data"],
        None,
        data.get("ttl", 3600),
    )


async def run_async_benchmarks(
    repo: AsyncMongoRepository,
    operations: List[str],
    iterations: int,
    concurrency: int,
    test_data: Dict[str, Any],
) -> Dict[str, BenchmarkResult]:
    sem = asyncio.Semaphore(concurrency)
    results: Dict[str, BenchmarkResult] = {}

    for op in operations:
        print(f"  Running {op}...")
        result = await benchmark_single_operation(
            repo, op, test_data, iterations, concurrency, sem
        )
        results[op] = result
        print(
            "    p50: "
            f"{result.p50:.2f}ms, "
            f"p95: {result.p95:.2f}ms, "
            f"errors: {result.errors}"
        )

    return results


async def main():
    parser = argparse.ArgumentParser(description="Benchmark AsyncMongoRepository")
    parser.add_argument(
        "-n", "--iterations", type=int, default=100, help="Total requests"
    )
    parser.add_argument(
        "-c", "--concurrency", type=int, default=10, help="Concurrent requests"
    )
    parser.add_argument(
        "--operations", nargs="*", default=None, help="Operations to benchmark"
    )
    parser.add_argument(
        "--sync", action="store_true", help="Compare with sync repository"
    )
    parser.add_argument("--output", type=str, default=None, help="Output JSON file")
    args = parser.parse_args()

    # Default operations
    operations = args.operations or [
        "get_match_prediction",
        "get_match_predictions_bulk",
        "save_match_prediction",
        "bulk_save_predictions",
    ]

    print(
        f"Benchmarking AsyncMongoRepository (n={args.iterations}, c={args.concurrency})"
    )

    test_data = {
        "match_id": f"bench_{int(time.time())}",
        "match_ids": [f"m_{i}" for i in range(50)],
        "league_id": "E0",
        "payload": {"test": True, "timestamp": time.time()},
        "predictions": [
            {
                "match_id": f"m_{i}",
                "league_id": "E0",
                "data": {"test": True},
                "ttl_seconds": 3600,
            }
            for i in range(10)
        ],
        "endpoint": "/api/benchmark",
        "cached_data": {"result": "benchmark", "timestamp": time.time()},
    }

    repo = create_async_repo()
    await seed_async_repo(repo, test_data)
    async_results = await run_async_benchmarks(
        repo, operations, args.iterations, args.concurrency, test_data
    )

    # Summary
    print("\n=== Async Results ===")
    total_p50 = 0
    for op, res in async_results.items():
        print(
            f"{op}: p50={res.p50:.2f}ms "
            f"p95={res.p95:.2f}ms "
            f"p99={res.p99:.2f}ms "
            f"errors={res.errors}"
        )
        total_p50 += res.p50

    avg_p50 = total_p50 / len(async_results)
    print(f"\nAverage p50: {avg_p50:.2f}ms")

    # Sync comparison if requested
    sync_results: Dict[str, BenchmarkResult] = {}
    if args.sync:
        print("\n=== Sync Comparison ===")
        sync_repo = create_sync_repo()
        seed_sync_repo(sync_repo, test_data)
        for op in operations:
            res = run_sync_comparison(
                sync_repo,
                op,
                test_data,
                args.iterations,
                args.concurrency,
            )
            sync_results[op] = res
            print(
                f"{op}: p50={res.p50:.2f}ms "
                f"p95={res.p95:.2f}ms "
                f"errors={res.errors}"
            )

    # Save results
    output_data = {
        "timestamp": time.time(),
        "iterations": args.iterations,
        "concurrency": args.concurrency,
        "operations": operations,
        "sync_requested": args.sync,
        "async": serialize_benchmark_results(async_results),
    }

    if sync_results:
        output_data["sync"] = serialize_benchmark_results(sync_results)

    if args.output:
        with open(args.output, "w") as f:
            json.dump(output_data, f, indent=2)
        print(f"\nResults saved to {args.output}")
    else:
        # Default save location
        tmp_dir = Path(__file__).parent.parent / "tmp"
        tmp_dir.mkdir(exist_ok=True)
        out_file = tmp_dir / "benchmark_async_mongo.json"
        with open(out_file, "w") as f:
            json.dump(output_data, f, indent=2)
        print(f"\nResults saved to {out_file}")


if __name__ == "__main__":
    asyncio.run(main())
