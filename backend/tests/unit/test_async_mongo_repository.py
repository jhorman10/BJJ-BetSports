import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from pymongo.errors import OperationFailure
from pytz import utc

sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.infrastructure.repositories import async_mongo_repository as async_repo
from src.utils import time_utils
from src.utils.time_utils import COLOMBIA_TZ

TTL_INDEX_KEY = [("expires_at", 1)]


class _FakeCollection:
    def __init__(self) -> None:
        self.create_index_calls: list[dict] = []
        self.drop_index_calls: list[str] = []
        self._conflict_keys: list = []

    def create_index(self, key, unique: bool = False, **kwargs):
        call = {
            "key": key,
            "unique": unique,
            "expireAfterSeconds": kwargs.get("expireAfterSeconds"),
            "partialFilterExpression": kwargs.get("partialFilterExpression"),
        }
        self.create_index_calls.append(call)
        if key in self._conflict_keys:
            raise OperationFailure("Index exists with different options", code=85)
        return call

    def drop_index(self, name: str) -> None:
        self.drop_index_calls.append(name)
        # After the drop the conflicting index no longer exists (real Mongo
        # semantics), so subsequent create_index attempts succeed.
        self._conflict_keys.clear()


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
        self.create_index_calls: list[dict] = []
        self.drop_index_calls: list[str] = []
        self.documents: dict[str, dict] = {}
        self._conflict_keys: list = []

    async def create_index(self, key, unique: bool = False, **kwargs):
        call = {
            "key": key,
            "unique": unique,
            "expireAfterSeconds": kwargs.get("expireAfterSeconds"),
            "partialFilterExpression": kwargs.get("partialFilterExpression"),
        }
        self.create_index_calls.append(call)
        if key in self._conflict_keys:
            raise OperationFailure("Index exists with different options", code=85)
        return call

    async def drop_index(self, name: str) -> None:
        self.drop_index_calls.append(name)
        # After the drop the conflicting index no longer exists (real Mongo
        # semantics), so subsequent create_index attempts succeed.
        self._conflict_keys.clear()

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


def _ttl_call(partial_filter=None):
    return {
        "key": TTL_INDEX_KEY,
        "unique": False,
        "expireAfterSeconds": 0,
        "partialFilterExpression": partial_filter,
    }


def _plain_call(key: str):
    return {
        "key": key,
        "unique": True,
        "expireAfterSeconds": None,
        "partialFilterExpression": None,
    }


def test_async_mongo_repository_creates_same_indexes_as_sync_repo(monkeypatch):
    monkeypatch.setattr(async_repo, "HAS_MOTOR", True)
    monkeypatch.setattr(async_repo, "MotorAsyncIOMotorClient", _FakeMotorClient)

    repository = async_repo.AsyncMongoRepository(
        mongo_uri="mongodb://fake", db_name="test-db"
    )

    assert repository.training_results.create_index_calls == [_plain_call("key")]
    assert repository.match_predictions.create_index_calls == [
        _plain_call("match_id"),
        _ttl_call({"labeled": {"$eq": False}}),
        {
            "expireAfterSeconds": None,
            "key": [("league_id", 1), ("expires_at", 1)],
            "partialFilterExpression": None,
            "unique": False,
        },
    ]
    assert repository.api_cache.create_index_calls == [_plain_call("key"), _ttl_call()]
    assert repository.app_state.create_index_calls == [_plain_call("key")]
    assert repository.binary_artifacts.create_index_calls == [_plain_call("key")]


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
    assert repository.training_results.create_index_calls == [_plain_call("key")]
    assert repository.match_predictions.create_index_calls == [
        _plain_call("match_id"),
        _ttl_call({"labeled": {"$eq": False}}),
        {
            "expireAfterSeconds": None,
            "key": [("league_id", 1), ("expires_at", 1)],
            "partialFilterExpression": None,
            "unique": False,
        },
    ]


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


@pytest.mark.asyncio
async def test_async_mongo_repository_ttl_indexes_created_with_expire_after_seconds_0(
    monkeypatch,
):
    monkeypatch.setattr(async_repo, "HAS_MOTOR", True)
    monkeypatch.setattr(async_repo, "MotorAsyncIOMotorClient", _FakeAsyncMotorClient)

    repository = async_repo.AsyncMongoRepository(
        mongo_uri="mongodb://fake", db_name="test-db"
    )
    await repository._ensure_ready()

    # match_predictions keeps the partial filter; api_cache stays simple.
    assert _ttl_call({"labeled": {"$eq": False}}) in (
        repository.match_predictions.create_index_calls
    )
    assert _ttl_call() in repository.api_cache.create_index_calls


@pytest.mark.asyncio
async def test_async_mongo_repo_match_preds_ttl_partial_api_cache_simple(
    monkeypatch,
):
    """C1 contract: match_predictions uses partialFilterExpression (only
    unlabeled docs purged); api_cache uses a plain TTL index."""
    monkeypatch.setattr(async_repo, "HAS_MOTOR", True)
    monkeypatch.setattr(async_repo, "MotorAsyncIOMotorClient", _FakeAsyncMotorClient)

    repository = async_repo.AsyncMongoRepository(
        mongo_uri="mongodb://fake", db_name="test-db"
    )
    await repository._ensure_ready()

    match_ttl = _ttl_call({"labeled": {"$eq": False}})
    cache_ttl = _ttl_call()

    assert match_ttl in repository.match_predictions.create_index_calls
    assert cache_ttl in repository.api_cache.create_index_calls
    # api_cache must NOT carry the partial filter (every entry is purged).
    assert cache_ttl["partialFilterExpression"] is None


@pytest.mark.asyncio
async def test_async_mongo_repository_second_init_is_noop(monkeypatch):
    monkeypatch.setattr(async_repo, "HAS_MOTOR", True)
    monkeypatch.setattr(async_repo, "MotorAsyncIOMotorClient", _FakeAsyncMotorClient)

    repository = async_repo.AsyncMongoRepository(
        mongo_uri="mongodb://fake", db_name="test-db"
    )
    await repository._ensure_ready()
    calls_before = len(repository.match_predictions.create_index_calls)

    # A second ensure (equivalent to a 2nd init) must not re-create indexes.
    await repository._ensure_indexes()
    await repository._ensure_indexes()

    assert len(repository.match_predictions.create_index_calls) == calls_before


@pytest.mark.asyncio
async def test_async_mongo_repository_ttl_collision_drops_and_recreates(monkeypatch):
    monkeypatch.setattr(async_repo, "HAS_MOTOR", True)
    monkeypatch.setattr(async_repo, "MotorAsyncIOMotorClient", _FakeAsyncMotorClient)

    repository = async_repo.AsyncMongoRepository(
        mongo_uri="mongodb://fake", db_name="test-db"
    )
    await repository._ensure_ready()

    # Simulate drift: a pre-existing index with conflicting options.
    repository.match_predictions._conflict_keys = [TTL_INDEX_KEY]
    repository.match_predictions.create_index_calls.clear()

    await repository._ensure_ttl_index(repository.match_predictions)

    assert repository.match_predictions.drop_index_calls == ["expires_at_1"]
    # First attempt raised → helper recreated after the drop.
    assert len(repository.match_predictions.create_index_calls) == 2
    assert _ttl_call() in repository.match_predictions.create_index_calls
