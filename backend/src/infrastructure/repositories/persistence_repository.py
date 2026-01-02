import logging
import json
from datetime import datetime
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

class PersistenceRepository:
    """
    Repository for persisting complex data structures to the database.
    """
    
    def __init__(self, db_service: DatabaseService = None):
        self.db_service = db_service or get_database_service()
        # Note: Tables are created in main.py lifespan to avoid redundant checks

    def save_training_result(self, key: str, data: dict) -> bool:
        """
        Save or update a training result by key.
        """
        session = self.db_service.get_session()
        try:
            # Check if exists
            record = session.query(TrainingResultModel).filter(TrainingResultModel.key == key).first()
            
            if record:
                record.data = data
                record.last_updated = datetime.utcnow()
            else:
                record = TrainingResultModel(key=key, data=data)
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

# Factory function for dependency injection
def get_persistence_repository() -> PersistenceRepository:
    """Get the persistence repository instance."""
    return PersistenceRepository()
