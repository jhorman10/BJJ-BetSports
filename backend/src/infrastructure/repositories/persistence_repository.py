import logging
import json
from datetime import datetime
from typing import List, Optional, Any
from sqlalchemy import Column, String, JSON, DateTime, Integer
from src.infrastructure.database.database_service import Base, DatabaseService, get_database_service

logger = logging.getLogger(__name__)

class TrainingResultModel(Base):
    """
    SQLAlchemy model for storing training results.
    """
    __tablename__ = "training_results"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String, unique=True, index=True, nullable=False) # e.g., "latest_daily"
    data = Column(JSON, nullable=False)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class MatchPredictionModel(Base):
    """
    SQLAlchemy model for storing pre-calculated match predictions.
    """
    __tablename__ = "match_predictions"
    
    match_id = Column(String, primary_key=True, index=True)
    league_id = Column(String, index=True)
    data = Column(JSON, nullable=False) # Prediction details and picks
    expires_at = Column(DateTime, nullable=False)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ApiCacheModel(Base):
    """
    SQLAlchemy model for caching API responses.
    """
    __tablename__ = "api_response_cache"
    
    endpoint = Column(String, primary_key=True)  # Full endpoint path e.g. /competitions/PL/matches
    params = Column(String, primary_key=True, default="") # Flattened params string
    response_json = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)

class PersistenceRepository:
    """
    Repository for persisting complex data structures to the database.
    """
    
    def __init__(self, db_service: DatabaseService = None):
        self.db_service = db_service or get_database_service()
        # Note: Tables are created in main.py lifespan to avoid redundant checks

    def create_tables(self):
        """Create all tables defined in Base."""
        self.db_service.create_tables()

    def _sanitize_json_data(self, data: Any) -> Any:
        """
        Sanitize data for JSON storage, handling datetime objects.
        This forces datetime objects to strings before SQLAlchemy passes them to PostgreSQL.
        """
        class DateTimeEncoder(json.JSONEncoder):
            def default(self, o):
                if isinstance(o, datetime):
                    return o.isoformat()
                return super().default(o)
                
        # Dump to string and reload to ensure pure JSON types (dict, list, str, int, float, bool, None)
        return json.loads(json.dumps(data, cls=DateTimeEncoder))

    def get_cached_response(self, endpoint: str, params: Optional[dict] = None) -> Optional[dict]:
        """
        Retrieve a valid cached API response.
        """
        session = self.db_service.get_session()
        try:
            # Flatten params to string key
            params_str = json.dumps(params, sort_keys=True) if params else ""
            
            now = datetime.utcnow()
            record = session.query(ApiCacheModel).filter(
                ApiCacheModel.endpoint == endpoint,
                ApiCacheModel.params == params_str,
                ApiCacheModel.expires_at > now
            ).first()
            
            return record.response_json if record else None
        except Exception as e:
            logger.error(f"Failed to retrieve cache for {endpoint}: {e}")
            return None
        finally:
            session.close()

    def save_cached_response(self, endpoint: str, data: dict, params: Optional[dict] = None, ttl_seconds: int = 3600) -> bool:
        """
        Save API response to cache.
        """
        session = self.db_service.get_session()
        try:
            from datetime import timedelta
            
            params_str = json.dumps(params, sort_keys=True) if params else ""
            expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)
            
            # Sanitize data
            sanitized_data = self._sanitize_json_data(data)
            
            # Check for existing record (upsert)
            record = session.query(ApiCacheModel).filter(
                ApiCacheModel.endpoint == endpoint,
                ApiCacheModel.params == params_str
            ).first()
            
            if record:
                record.response_json = sanitized_data
                record.expires_at = expires_at
                record.created_at = datetime.utcnow()
            else:
                record = ApiCacheModel(
                    endpoint=endpoint,
                    params=params_str,
                    response_json=sanitized_data,
                    expires_at=expires_at
                )
                session.add(record)
            
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to save cache for {endpoint}: {e}")
            return False
        finally:
            session.close()

    def save_training_result(self, key: str, data: dict) -> bool:
        """
        Save or update a training result by key.
        """
        session = self.db_service.get_session()
        try:
            # Sanitize data to remove non-JSON serializable objects (like datetime)
            sanitized_data = self._sanitize_json_data(data)
            
            # Check if exists
            record = session.query(TrainingResultModel).filter(TrainingResultModel.key == key).first()
            
            if record:
                record.data = sanitized_data
                record.last_updated = datetime.utcnow()
            else:
                record = TrainingResultModel(key=key, data=sanitized_data)
                session.add(record)
            
            session.commit()
            logger.info(f"Training result saved with key: {key}")
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to save training result: {e}")
            return False
        finally:
            session.close()

    def get_training_result(self, key: str) -> dict:
        """
        Retrieve a training result by key.
        """
        session = self.db_service.get_session()
        try:
            record = session.query(TrainingResultModel).filter(TrainingResultModel.key == key).first()
            if record:
                return record.data
            return None
        except Exception as e:
            logger.error(f"Failed to retrieve training result: {e}")
            return None
        finally:
            session.close()

    def get_last_updated(self, key: str) -> datetime:
        """
        Get the last updated timestamp for a result.
        """
        session = self.db_service.get_session()
        try:
            record = session.query(TrainingResultModel).filter(TrainingResultModel.key == key).first()
            if record:
                return record.last_updated
            return None
        except Exception as e:
            logger.error(f"Failed to get last updated timestamp: {e}")
            return None
        finally:
            session.close()

    def save_match_prediction(self, match_id: str, league_id: str, data: dict, ttl_seconds: int = 86400) -> bool:
        """
        Save or update a match prediction with an expiration time.
        """
        from datetime import timedelta
        session = self.db_service.get_session()
        try:
            expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)
            
            # Sanitize data
            sanitized_data = self._sanitize_json_data(data)
            
            record = session.query(MatchPredictionModel).filter(MatchPredictionModel.match_id == match_id).first()
            if record:
                record.league_id = league_id
                record.data = sanitized_data
                record.expires_at = expires_at
                record.last_updated = datetime.utcnow()
            else:
                record = MatchPredictionModel(
                    match_id=match_id,
                    league_id=league_id,
                    data=sanitized_data,
                    expires_at=expires_at
                )
                session.add(record)
            
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to save match prediction {match_id}: {e}")
            return False
        finally:
            session.close()

    def get_match_prediction(self, match_id: str) -> Optional[dict]:
        """
        Retrieve a valid (non-expired) match prediction.
        """
        session = self.db_service.get_session()
        try:
            now = datetime.utcnow()
            record = session.query(MatchPredictionModel).filter(
                MatchPredictionModel.match_id == match_id,
                MatchPredictionModel.expires_at > now
            ).first()
            
            return record.data if record else None
        except Exception as e:
            logger.error(f"Failed to retrieve match prediction {match_id}: {e}")
            return None
        finally:
            session.close()

    def get_league_predictions(self, league_id: str) -> list[dict]:
        """
        Retrieve all valid predictions for a specific league.
        """
        session = self.db_service.get_session()
        try:
            now = datetime.utcnow()
            records = session.query(MatchPredictionModel).filter(
                MatchPredictionModel.league_id == league_id,
                MatchPredictionModel.expires_at > now
            ).all()
            
            return [r.data for r in records]
        except Exception as e:
            logger.error(f"Failed to retrieve league predictions {league_id}: {e}")
            return []
        finally:
            session.close()

    def get_all_active_predictions(self) -> list[dict]:
        """
        Retrieve all valid predictions across all leagues.
        Useful for generating cross-league top picks.
        """
        session = self.db_service.get_session()
        try:
            now = datetime.utcnow()
            records = session.query(MatchPredictionModel).filter(
                MatchPredictionModel.expires_at > now
            ).all()
            
            return [r.data for r in records]
        except Exception as e:
            logger.error(f"Failed to retrieve all active predictions: {e}")
            return []
        finally:
            session.close()

    def bulk_save_predictions(self, predictions_batch: list[dict]) -> bool:
        """
        Save multiple predictions in a single transaction for better performance.
        Each dict in 'predictions_batch' should have: match_id, league_id, data, and optionally ttl_seconds.
        """
        from datetime import timedelta
        session = self.db_service.get_session()
        try:
            now = datetime.utcnow()
            for p in predictions_batch:
                match_id = p['match_id']
                league_id = p['league_id']
                data = p['data']
                ttl = p.get('ttl_seconds', 86400 * 7)
                
                expires_at = now + timedelta(seconds=ttl)
                
                # Sanitize data
                sanitized_data = self._sanitize_json_data(data)
                
                record = session.query(MatchPredictionModel).filter(MatchPredictionModel.match_id == match_id).first()
                if record:
                    record.league_id = league_id
                    record.data = sanitized_data
                    record.expires_at = expires_at
                    record.last_updated = now
                else:
                    record = MatchPredictionModel(
                        match_id=match_id,
                        league_id=league_id,
                        data=sanitized_data,
                        expires_at=expires_at,
                        last_updated=now
                    )
                    session.add(record)
            
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to bulk save predictions: {e}")
            return False
        finally:
            session.close()

# Factory function for dependency injection
def get_persistence_repository() -> PersistenceRepository:
    """Get the persistence repository instance."""
    return PersistenceRepository()
