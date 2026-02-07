"""OVERVIEW
This file is responsible for connecting your application to the database and safely managing database sessions.
Think of it as the bridge between your Python code and PostgreSQL.
This file:
- Reads the database connection URL from .env
- Creates a database engine (connection factory)
- Uses connection pooling (important for production apps)
- Provides safe database sessions that:
    - Automatically commit changes
    - Roll back on errors
    - Always close connections properly
- Exposes a global database manager that the rest of your app can reuse
"""

from sqlalchemy import create_engine    # Creates database connection engine
from sqlalchemy.orm import sessionmaker, Session    # Creates database sessions, Type hint for DB sessions
from sqlalchemy.pool import QueuePool   # Manages a pool of DB connections
from contextlib import contextmanager   # Makes with blocks possible
import os
from dotenv import load_dotenv
from typing import Generator    # Type hint for context manager

load_dotenv()

class DatabaseManager:
    """This class is the heart of database handling.
    It provides:
    - Creates the DB engine
    - Creates sessions
    - Ensures clean commits & rollbacks
    """
    def __init__(self, database_url: str = None):
        self.database_url = database_url or os.getenv("DATABASE_URL")
        
        # Production-ready engine configuration
        self.engine = create_engine(        # Engine = the “factory” that creates DB connections.
            self.database_url,
            # Connection pooling for production
            poolclass=QueuePool,    
            pool_size=20,          # QueuePool = keeps 20 connections always ready.
            max_overflow=30,       # If more are needed, it can create 30 extra temporary ones (max_overflow).
            pool_recycle=3600,     # pool_recycle=3600 → refresh connections every hour to avoid “stale connections.”
            pool_pre_ping=True,    # pool_pre_ping=True → checks if a connection is alive before using it.
            echo=False,            # echo=False → if True, prints SQL queries to the terminal (useful for debugging)
        )

        self.SessionLocal = sessionmaker(bind=self.engine)
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Context manager for database sessions with automatic cleanup"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def get_session_direct(self) -> Session:
        """Direct session access for async operations"""
        return self.SessionLocal()
    
    

# Global database manager instance
db_manager = DatabaseManager()

