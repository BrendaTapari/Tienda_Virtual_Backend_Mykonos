import logging
from datetime import datetime, timedelta
from config.db_connection import db
from database.database import TABLES

logger = logging.getLogger(__name__)

async def cleanup_old_notifications_task():
    """
    Background task to delete notifications and broadcasts older than 6 months.
    """
    try:
        # Check if DB is ready (might be called during startup/shutdown)
        if not db._pool:
            return

        cutoff_date = datetime.now() - timedelta(days=180)
        
        # Eliminar notificaciones personales antiguas
        query_personal = f"DELETE FROM {TABLES.NOTIFICATIONS.value} WHERE created_at < $1"
        result_personal = await db.execute(query_personal, cutoff_date)
        
        # Eliminar user_broadcasts asociados
        query_user_broadcasts = f"""
            DELETE FROM {TABLES.USER_BROADCASTS.value} 
            WHERE broadcast_id IN (
                SELECT id FROM {TABLES.BROADCAST_NOTIFICATIONS.value} 
                WHERE created_at < $1
            )
        """
        result_ub = await db.execute(query_user_broadcasts, cutoff_date)
        
        # Eliminar broadcasts antiguos
        query_broadcasts = f"DELETE FROM {TABLES.BROADCAST_NOTIFICATIONS.value} WHERE created_at < $1"
        result_broadcasts = await db.execute(query_broadcasts, cutoff_date)
        
        logger.info(f"Weekly Cleanup: Removed notifications older than {cutoff_date}. Results: Personal={result_personal}, UserBroadcasts={result_ub}, Broadcasts={result_broadcasts}")
        
    except Exception as e:
        logger.error(f"Error in notification cleanup task: {e}")
