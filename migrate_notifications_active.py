
import asyncio
from config.db_connection import db
import logging

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def migrate():
    logger.info("Starting migration...")
    try:
        await db.initialize()
        
        # Check if column exists first to avoid error
        # This is a bit postgres specific
        check_query = """
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='broadcast_notifications' AND column_name='active';
        """
        
        row = await db.fetch_one(check_query)
        if row:
            logger.info("Column 'active' already exists. Skipping.")
        else:
            logger.info("Adding column 'active'...")
            await db.execute("ALTER TABLE broadcast_notifications ADD COLUMN active BOOLEAN DEFAULT TRUE")
            logger.info("Migration successful!")
            
    except Exception as e:
        logger.error(f"Migration failed: {e}")
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(migrate())
