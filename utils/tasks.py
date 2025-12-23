import logging
from config.db_connection import db

logger = logging.getLogger(__name__)

async def deactivate_expired_discounts():
    """
    Deactivates discounts that have passed their end_date.
    Runs a SQL update and logs the result.
    This should be run periodically.
    """
    try:
        # Check if we have a connection pool available
        if not db.pool:
            # Depending on initialization order, this might happen on very first run if called too early,
            # but usually lifespan ensures db is ready.
            return

        query = """
            UPDATE discounts 
            SET is_active = FALSE,
                updated_at = CURRENT_TIMESTAMP
            WHERE is_active = TRUE 
            AND end_date < CURRENT_TIMESTAMP
        """
        
        result = await db.execute(query)
        
        # asyncpg execute returns a string like "UPDATE 5"
        if result and result.startswith("UPDATE"):
            try:
                count = int(result.split(" ")[1])
                if count > 0:
                    logger.info(f"Background Task: Deactivated {count} expired discounts.")
            except (IndexError, ValueError):
                pass
                
    except Exception as e:
        logger.error(f"Error execution discount cleanup task: {e}")
