from datetime import datetime, timedelta

from src.api.services.data_loader import DataLoader


class FakeColl:
    def __init__(self, docs):
        self._docs = docs

    def find(self, query):
        return self._docs


class PredictionRepo:
    def __init__(self, docs):
        self.match_predictions = FakeColl(docs)


def test_data_loader_filters_out_of_range_predictions():
    # Create a prediction with a match date far in the future (365 days)
    future_date = (datetime.utcnow() + timedelta(days=365)).isoformat() + "Z"
    doc = {
        "match_id": "m_future",
        "league_id": "E0",
        "data": {
            "match": {
                "id": "m_future",
                "match_date": future_date,
                "home_team": {"id": "t1", "name": "Future Home"},
                "away_team": {"id": "t2", "name": "Future Away"},
                "status": "NS",
            },
            "prediction": {
                "home_win_probability": 0.5,
                "draw_probability": 0.3,
                "away_win_probability": 0.2,
            },
        },
    }

    loader = DataLoader(repository=PredictionRepo([doc]))
    results = loader.load_predictions_for_league("E0")
    # The out-of-range prediction should be filtered out
    assert len(results) == 0


class FakeCollection:
    def __init__(self, docs):
        self._docs = docs

    def find(self, query=None):
        return iter(self._docs)

    def find_one(self, query):
        for d in self._docs:
            if d.get("match_id") == query.get("match_id"):
                return d
        return None


class PredictionRepoWithTraining:
    def __init__(self, docs, training=None, updated_at=None):
        self.match_predictions = FakeCollection(docs)
        self._training = training
        self._updated_at = updated_at

    def get_training_result_with_timestamp(self, key):
        return self._training, self._updated_at


def test_data_loader_loads_predictions_and_training_result():
    upcoming_match_date = (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z"

    doc = {
        "league_id": "E0",
        "match_id": "m1",
        "prediction": {
            "match": {
                "id": "m1",
                "match_date": upcoming_match_date,
                "home_team": {"id": "h1", "name": "A"},
                "away_team": {"id": "a1", "name": "B"},
                "status": "scheduled",
            },
            "prediction": {"match_id": "m1", "home_win_probability": 0.5},
        },
    }

    training = {"version": "v1"}
    updated_at = datetime(2026, 3, 31)
    repo = PredictionRepoWithTraining([doc], training=training, updated_at=updated_at)
    loader = DataLoader(repository=repo)

    preds = loader.load_predictions_for_league("E0")
    assert isinstance(preds, list)
    assert len(preds) == 1

    result, ts = loader.get_latest_training_result()
    assert result == training
    assert ts is not None
