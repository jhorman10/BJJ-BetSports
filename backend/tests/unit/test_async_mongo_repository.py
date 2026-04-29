import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from pytz import utc

sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.infrastructure.repositories import async_mongo_repository as async_repo
from src.utils import time_utils
from src.utils.time_utils import COLOMBIA_TZ


class _FakeCollection:
    def __init__(self) -> None:
        self.create_index_calls: list[tuple[str, bool]] = []

    def create_index(self, key: str, unique: bool = False) -> None:
        self.create_index_calls.append((key, unique))


class _FakeDatabase:
    def __init__(self) -> None:
        self.collections: dict[str, _FakeCollection] = {}

    def __getitem__(self, name: str) -> _FakeCollection:
        if name not in self.collections:
            self.collections[name] = _FakeCollection()
        return self.collections[name]


class _FakeMotorClient:
    def __init__(self, mongo_uri: str) -> None:
        self.mongo_uri = mongo_uri
        self.databases: dict[str, _FakeDatabase] = {}

    def __getitem__(self, name: str) -> _FakeDatabase:
        if name not in self.databases:
            self.databases[name] = _FakeDatabase()
        return self.databases[name]


class _FakeDeleteResult:
    def __init__(self, deleted_count: int) -> None:
        self.deleted_count = deleted_count


class _FakeAsyncCollection:
    def __init__(self) -> None:
        self.create_index_calls: list[tuple[str, bool]] = []
        self.documents: dict[str, dict] = {}

    async def create_index(self, key: str, unique: bool = False) -> None:
        self.create_index_calls.append((key, unique))

    async def update_one(
        self, filter_query: dict, update: dict, upsert: bool = False
    ) -> None:
        _ = upsert
        document_key = next(iter(filter_query.values()))
        current = dict(self.documents.get(document_key, {}))
        current.update(filter_query)
        current.update(update.get("$set", {}))
        self.documents[document_key] = current

    async def find_one(self, filter_query: dict) -> dict | None:
        if "key" in filter_query:
            return self.documents.get(filter_query["key"])
        if "match_id" in filter_query:
            return self.documents.get(filter_query["match_id"])
        return None

    async def delete_many(self, filter_query: dict) -> _FakeDeleteResult:
        if not filter_query:
            deleted_count = len(self.documents)
            self.documents = {}
            return _FakeDeleteResult(deleted_count)

        if "league_id" in filter_query and "$in" in filter_query["league_id"]:
            allowed = set(filter_query["league_id"]["$in"])
            keys_to_delete = [
                key
                for key, value in self.documents.items()
                if value.get("league_id") in allowed
            ]
            for key in keys_to_delete:
                del self.documents[key]
            return _FakeDeleteResult(len(keys_to_delete))

        return _FakeDeleteResult(0)


class _FakeAsyncDatabase:
    def __init__(self) -> None:
        self.collections: dict[str, _FakeAsyncCollection] = {}

    def __getitem__(self, name: str) -> _FakeAsyncCollection:
        if name not in self.collections:
            self.collections[name] = _FakeAsyncCollection()
        return self.collections[name]


class _FakeAsyncMotorClient:
    def __init__(self, mongo_uri: str) -> None:
        self.mongo_uri = mongo_uri
        self.databases: dict[str, _FakeAsyncDatabase] = {}

    def __getitem__(self, name: str) -> _FakeAsyncDatabase:
        if name not in self.databases:
            self.databases[name] = _FakeAsyncDatabase()
        return self.databases[name]

    def close(self) -> None:
        return None


def test_async_mongo_repository_creates_same_indexes_as_sync_repo(monkeypatch):
    monkeypatch.setattr(async_repo, "HAS_MOTOR", True)
    monkeypatch.setattr(async_repo, "MotorAsyncIOMotorClient", _FakeMotorClient)

    repository = async_repo.AsyncMongoRepository(
        mongo_uri="mongodb://fake", db_name="test-db"
    )

    assert repository.training_results.create_index_calls == [("key", True)]
    assert repository.match_predictions.create_index_calls == [("match_id", True)]
    assert repository.api_cache.create_index_calls == [("key", True)]
    assert repository.app_state.create_index_calls == [("key", True)]
    assert repository.binary_artifacts.create_index_calls == [("key", True)]


@pytest.mark.asyncio
async def test_async_mongo_repository_waits_for_index_init_inside_event_loop(
    monkeypatch,
):
    monkeypatch.setattr(async_repo, "HAS_MOTOR", True)
    monkeypatch.setattr(async_repo, "MotorAsyncIOMotorClient", _FakeAsyncMotorClient)

    repository = async_repo.AsyncMongoRepository(
        mongo_uri="mongodb://fake", db_name="test-db"
    )

    result = await repository.get_training_result("missing")

    assert result is None
    assert repository.training_results.create_index_calls == [("key", True)]
    assert repository.match_predictions.create_index_calls == [("match_id", True)]


@pytest.mark.asyncio
async def test_async_mongo_repository_match_prediction_respects_ttl_and_metadata(
    monkeypatch,
):
    now = COLOMBIA_TZ.localize(datetime(2026, 4, 28, 12, 0, 0))
    monkeypatch.setattr(async_repo, "HAS_MOTOR", True)
    monkeypatch.setattr(async_repo, "MotorAsyncIOMotorClient", _FakeAsyncMotorClient)
    monkeypatch.setattr(async_repo, "get_current_time", lambda: now)
    monkeypatch.setattr(time_utils, "get_current_time", lambda: now)

    repository = async_repo.AsyncMongoRepository(
        mongo_uri="mongodb://fake", db_name="test-db"
    )

    await repository.save_match_prediction(
        "match-1", "E0", {"score": 1}, ttl_seconds=60
    )

    stored = repository.match_predictions.documents["match-1"]
    assert stored["league_id"] == "E0"
    assert stored["data"]["model_metadata"]["generated_by"] == "prediction-service"

    # Mongo commonly returns naive UTC datetimes on reads; simulate that round-trip.
    stored["expires_at"] = stored["expires_at"].astimezone(utc).replace(tzinfo=None)

    assert await repository.get_match_prediction("match-1") == stored["data"]

    monkeypatch.setattr(
        async_repo,
        "get_current_time",
        lambda: now + timedelta(seconds=61),
    )
    monkeypatch.setattr(
        time_utils,
        "get_current_time",
        lambda: now + timedelta(seconds=61),
    )

    assert await repository.get_match_prediction("match-1") is None
