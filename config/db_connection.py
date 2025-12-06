"""
Database connection manager for PostgreSQL using asyncpg.
Provides connection pooling and query utilities for FastAPI.
"""

import asyncpg
from typing import Optional, List, Dict, Any
from config.config import get_config
import logging

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages PostgreSQL connection pool and provides query utilities."""
    
    _pool: Optional[asyncpg.Pool] = None
    _config = None
    
    @classmethod
    async def initialize(cls):
        """Initialize the database connection pool."""
        if cls._pool is not None:
            logger.warning("Database pool already initialized")
            return
        
        cls._config = get_config()
        
        try:
            # Create connection pool
            cls._pool = await asyncpg.create_pool(
                host=cls._config.DB_HOST,
                port=int(cls._config.DB_PORT),
                database=cls._config.DB_NAME,
                user=cls._config.DB_USER,
                password=cls._config.DB_PASSWORD,
                min_size=2,  # Minimum number of connections
                max_size=10,  # Maximum number of connections
                command_timeout=60,  # Command timeout in seconds
            )
            logger.info("Database connection pool initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database pool: {e}")
            raise
    
    @classmethod
    async def close(cls):
        """Close the database connection pool."""
        if cls._pool is not None:
            await cls._pool.close()
            cls._pool = None
            logger.info("Database connection pool closed")
    
    @classmethod
    async def get_pool(cls) -> asyncpg.Pool:
        """Get the connection pool, initializing if necessary."""
        if cls._pool is None:
            await cls.initialize()
        return cls._pool
    
    @classmethod
    async def fetch_all(cls, query: str, *args) -> List[Dict[str, Any]]:
        """
        Execute a SELECT query and return all rows as dictionaries.
        
        Args:
            query: SQL query string
            *args: Query parameters
            
        Returns:
            List of dictionaries representing rows
        """
        pool = await cls.get_pool()
        async with pool.acquire() as connection:
            rows = await connection.fetch(query, *args)
            return [dict(row) for row in rows]
    
    @classmethod
    async def fetch_one(cls, query: str, *args) -> Optional[Dict[str, Any]]:
        """
        Execute a SELECT query and return a single row as a dictionary.
        
        Args:
            query: SQL query string
            *args: Query parameters
            
        Returns:
            Dictionary representing the row, or None if not found
        """
        pool = await cls.get_pool()
        async with pool.acquire() as connection:
            row = await connection.fetchrow(query, *args)
            return dict(row) if row else None
    
    @classmethod
    async def execute(cls, query: str, *args) -> str:
        """
        Execute an INSERT, UPDATE, or DELETE query.
        
        Args:
            query: SQL query string
            *args: Query parameters
            
        Returns:
            Status message from the database
        """
        pool = await cls.get_pool()
        async with pool.acquire() as connection:
            result = await connection.execute(query, *args)
            return result
    
    @classmethod
    async def execute_many(cls, query: str, args_list: List[tuple]) -> None:
        """
        Execute a query multiple times with different parameters.
        
        Args:
            query: SQL query string
            args_list: List of tuples containing query parameters
        """
        pool = await cls.get_pool()
        async with pool.acquire() as connection:
            await connection.executemany(query, args_list)
    
    @classmethod
    async def fetch_val(cls, query: str, *args) -> Any:
        """
        Execute a query and return a single value.
        
        Args:
            query: SQL query string
            *args: Query parameters
            
        Returns:
            Single value from the query result
        """
        pool = await cls.get_pool()
        async with pool.acquire() as connection:
            return await connection.fetchval(query, *args)
    
    @classmethod
    async def transaction(cls):
        """
        Get a transaction context manager.
        
        Usage:
            async with DatabaseManager.transaction() as conn:
                await conn.execute("INSERT INTO ...")
                await conn.execute("UPDATE ...")
        """
        pool = await cls.get_pool()
        connection = await pool.acquire()
        transaction = connection.transaction()
        
        class TransactionContext:
            async def __aenter__(self):
                await transaction.start()
                return connection
            
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                if exc_type is not None:
                    await transaction.rollback()
                else:
                    await transaction.commit()
                await pool.release(connection)
        
        return TransactionContext()


# Convenience alias
db = DatabaseManager
