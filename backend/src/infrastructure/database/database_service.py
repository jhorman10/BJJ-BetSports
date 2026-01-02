import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

logger = logging.getLogger(__name__)

Base = declarative_base()

class DatabaseService:
    """
    Service for managing database connections and sessions.
    """
    
    def __init__(self, db_url: str = None):
        # Priority: db_url param -> DATABASE_URL env -> sqlite fallback
        self.db_url = db_url or os.getenv("DATABASE_URL")
        
        if not self.db_url:
            # Fallback to local sqlite for development if no database is provided
            # Note: Render provides DATABASE_URL automatically for linked databases
            self.db_url = "sqlite:///./app_persistence.db"
            logger.warning(f"DATABASE_URL not found. Falling back to SQLite: {self.db_url}")
        
        # Adjust URL for SQLAlchemy if it starts with postgres:// (old Heroku/Render format)
        if self.db_url.startswith("postgres://"):
            self.db_url = self.db_url.replace("postgres://", "postgresql://", 1)
            
        try:
            # Create engine
            # pool_pre_ping=True helps with dropped connections (common in cloud envs)
            self.engine = create_engine(
                self.db_url, 
                pool_pre_ping=True,
                # SQLite doesn't support multiple threads by default in SQLAlchemy
                connect_args={"check_same_thread": False} if self.db_url.startswith("sqlite") else {}
            )
            
            # Create session factory
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            
            logger.info(f"DatabaseService initialized with {self.db_url.split('@')[-1] if '@' in self.db_url else 'local DB'}")
            
        except Exception as e:
            logger.error(f"Failed to initialize DatabaseService: {e}")
            raise e

    def create_tables(self):
        """Create all tables defined in Base."""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")
            raise e

    def get_session(self):
        """Get a new database session."""
        return self.SessionLocal()

# Singleton instance access
_db_instance = None

def get_database_service() -> DatabaseService:
    """Get the singleton database service instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = DatabaseService()
    return _db_instance
