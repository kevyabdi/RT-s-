"""
Database module for SVG to TGS Telegram Bot
Handles PostgreSQL operations for user management and statistics
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Optional, Tuple
import asyncpg

logger = logging.getLogger(__name__)

class Database:
    """Database handler for PostgreSQL operations"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.pool = None
    
    async def initialize(self):
        """Initialize database connection pool and create tables"""
        try:
            # Create connection pool
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=1,
                max_size=10,
                command_timeout=60
            )
            
            # Create tables
            await self.create_tables()
            logger.info("Database connection pool created successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    async def create_tables(self):
        """Create necessary database tables"""
        async with self.pool.acquire() as conn:
            # Users table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username VARCHAR(255),
                    first_name VARCHAR(255),
                    last_name VARCHAR(255),
                    is_banned BOOLEAN DEFAULT FALSE,
                    is_admin BOOLEAN DEFAULT FALSE,
                    join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    files_converted INTEGER DEFAULT 0
                )
            """)
            
            # Conversion history table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS conversions (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(user_id),
                    file_name VARCHAR(500),
                    file_size INTEGER,
                    conversion_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    success BOOLEAN DEFAULT TRUE,
                    error_message TEXT
                )
            """)
            
            # Broadcast history table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS broadcasts (
                    id SERIAL PRIMARY KEY,
                    admin_id BIGINT,
                    message TEXT,
                    sent_count INTEGER DEFAULT 0,
                    failed_count INTEGER DEFAULT 0,
                    broadcast_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
    
    async def add_user(self, user_id: int, username: str = None, 
                      first_name: str = None, last_name: str = None) -> bool:
        """Add or update user in database"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO users (user_id, username, first_name, last_name, last_active)
                    VALUES ($1, $2, $3, $4, CURRENT_TIMESTAMP)
                    ON CONFLICT (user_id) 
                    DO UPDATE SET 
                        username = EXCLUDED.username,
                        first_name = EXCLUDED.first_name,
                        last_name = EXCLUDED.last_name,
                        last_active = CURRENT_TIMESTAMP
                """, user_id, username, first_name, last_name)
            return True
        except Exception as e:
            logger.error(f"Failed to add user {user_id}: {e}")
            return False
    
    async def is_user_banned(self, user_id: int) -> bool:
        """Check if user is banned"""
        try:
            async with self.pool.acquire() as conn:
                result = await conn.fetchval(
                    "SELECT is_banned FROM users WHERE user_id = $1", user_id
                )
                return bool(result) if result is not None else False
        except Exception as e:
            logger.error(f"Failed to check ban status for user {user_id}: {e}")
            return False
    
    async def is_user_admin(self, user_id: int) -> bool:
        """Check if user is admin"""
        try:
            async with self.pool.acquire() as conn:
                result = await conn.fetchval(
                    "SELECT is_admin FROM users WHERE user_id = $1", user_id
                )
                return bool(result) if result is not None else False
        except Exception as e:
            logger.error(f"Failed to check admin status for user {user_id}: {e}")
            return False
    
    async def ban_user(self, user_id: int) -> bool:
        """Ban a user"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    "UPDATE users SET is_banned = TRUE WHERE user_id = $1", user_id
                )
            return True
        except Exception as e:
            logger.error(f"Failed to ban user {user_id}: {e}")
            return False
    
    async def unban_user(self, user_id: int) -> bool:
        """Unban a user"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    "UPDATE users SET is_banned = FALSE WHERE user_id = $1", user_id
                )
            return True
        except Exception as e:
            logger.error(f"Failed to unban user {user_id}: {e}")
            return False
    
    async def make_admin(self, user_id: int) -> bool:
        """Make user an admin"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    "UPDATE users SET is_admin = TRUE WHERE user_id = $1", user_id
                )
            return True
        except Exception as e:
            logger.error(f"Failed to make user {user_id} admin: {e}")
            return False
    
    async def remove_admin(self, user_id: int) -> bool:
        """Remove admin privileges from user"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    "UPDATE users SET is_admin = FALSE WHERE user_id = $1", user_id
                )
            return True
        except Exception as e:
            logger.error(f"Failed to remove admin from user {user_id}: {e}")
            return False
    
    async def get_user_stats(self) -> Tuple[int, int, int]:
        """Get user statistics: total users, banned users, active users"""
        try:
            async with self.pool.acquire() as conn:
                total = await conn.fetchval("SELECT COUNT(*) FROM users")
                banned = await conn.fetchval("SELECT COUNT(*) FROM users WHERE is_banned = TRUE")
                active = await conn.fetchval(
                    "SELECT COUNT(*) FROM users WHERE last_active > CURRENT_TIMESTAMP - INTERVAL '30 days'"
                )
                return total or 0, banned or 0, active or 0
        except Exception as e:
            logger.error(f"Failed to get user stats: {e}")
            return 0, 0, 0
    
    async def get_all_user_ids(self) -> List[int]:
        """Get all non-banned user IDs for broadcasting"""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    "SELECT user_id FROM users WHERE is_banned = FALSE"
                )
                return [row['user_id'] for row in rows]
        except Exception as e:
            logger.error(f"Failed to get user IDs: {e}")
            return []
    
    async def log_conversion(self, user_id: int, file_name: str, 
                           file_size: int, success: bool = True, 
                           error_message: str = None) -> bool:
        """Log a conversion attempt"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO conversions (user_id, file_name, file_size, success, error_message)
                    VALUES ($1, $2, $3, $4, $5)
                """, user_id, file_name, file_size, success, error_message)
                
                if success:
                    await conn.execute(
                        "UPDATE users SET files_converted = files_converted + 1 WHERE user_id = $1",
                        user_id
                    )
            return True
        except Exception as e:
            logger.error(f"Failed to log conversion for user {user_id}: {e}")
            return False
    
    async def log_broadcast(self, admin_id: int, message: str, 
                          sent_count: int, failed_count: int) -> bool:
        """Log a broadcast operation"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO broadcasts (admin_id, message, sent_count, failed_count)
                    VALUES ($1, $2, $3, $4)
                """, admin_id, message, sent_count, failed_count)
            return True
        except Exception as e:
            logger.error(f"Failed to log broadcast: {e}")
            return False
    
    async def close(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
