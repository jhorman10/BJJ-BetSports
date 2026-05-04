import sys
import types
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.infrastructure.repositories import async_mongo_adapter as adapter


class _FakeAsyncMongoRepository:
    def __init__(self, mongo_uri: str, db_name: str) -> None:
        self.mongo_uri = mongo_uri
        self.db_name = db_name


def _reset_async_factory(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(adapter, "_async_mongo_repo", None)
    monkeypatch.setattr(adapter, "_MONGO_ASYNC_MODE", None)


def test_load_required_async_mongo_settings_requires_explicit_mongo_uri(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("MONGO_URI", raising=False)
    monkeypatch.setenv("MONGO_DB_NAME", "bjj_betsports")

    with pytest.raises(RuntimeError, match="MONGO_URI"):
        adapter._load_required_async_mongo_settings()


def test_get_async_mongo_repository_in_on_mode_uses_explicit_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _reset_async_factory(monkeypatch)
    monkeypatch.setenv("MONGO_ASYNC_MODE", "on")
    monkeypatch.setenv("MONGO_URI", "mongodb://mongo.example:27017/")
    monkeypatch.setenv("MONGO_DB_NAME", "bjj_betsports")
    monkeypatch.setitem(
        sys.modules,
        "src.infrastructure.repositories.async_mongo_repository",
        types.SimpleNamespace(AsyncMongoRepository=_FakeAsyncMongoRepository),
    )

    repository = adapter.get_async_mongo_repository()

    assert isinstance(repository, _FakeAsyncMongoRepository)
    assert repository.mongo_uri == "mongodb://mongo.example:27017/"
    assert repository.db_name == "bjj_betsports"
