"""
Background task to auto-cancel expired orders.
This should be called periodically (e.g., every 5 minutes) from main.py
"""

import logging
from config.db_connection import DatabaseManager

logger = logging.getLogger(__name__)


async def cancel_expired_orders():
    """
    Find and cancel orders with expired reservations.
    
    This function:
    1. Finds orders with status 'Pendiente' and expired reservation_expires_at
    2. Updates order status to 'Cancelada'
    3. Marks stock reservations as 'expired'
    4. Creates tracking history entry
    
    Should be run every 5 minutes via background task.
    """
    try:
        pool = await DatabaseManager.get_pool()
        
        async with pool.acquire() as conn:
            # Find expired orders
            expired_orders = await conn.fetch(
                """
                SELECT id, web_user_id
                FROM sales
                WHERE status = 'Pendiente de pago'
                AND reservation_expires_at < CURRENT_TIMESTAMP
                AND reservation_expires_at IS NOT NULL
                """
            )
            
            if not expired_orders:
                logger.info("No expired orders found")
                return
            
            logger.info(f"Found {len(expired_orders)} expired orders to cancel")
            
            for order in expired_orders:
                order_id = order['id']
                
                try:
                    async with conn.transaction():
                        # Update order status
                        await conn.execute(
                            """
                            UPDATE sales
                            SET status = 'Cancelada',
                                shipping_status = 'cancelado',
                                updated_at = CURRENT_TIMESTAMP
                            WHERE id = $1
                            """,
                            order_id
                        )
                        
                        # Mark reservations as expired
                        await conn.execute(
                            """
                            UPDATE stock_reservations
                            SET status = 'expired', updated_at = CURRENT_TIMESTAMP
                            WHERE sale_id = $1 AND status = 'active'
                            """,
                            order_id
                        )
                        
                        # Create tracking entry
                        await conn.execute(
                            """
                            INSERT INTO sales_tracking_history (
                                sale_id,
                                status,
                                description,
                                location,
                                changed_by_user_id,
                                created_at
                            )
                            VALUES ($1, $2, $3, $4, NULL, CURRENT_TIMESTAMP)
                            """,
                            order_id,
                            'cancelado',
                            'Pedido cancelado automáticamente por expiración de reserva (30 minutos)',
                            'Sistema Automático'
                        )
                        
                        logger.info(f"Successfully cancelled expired order {order_id}")
                        
                except Exception as e:
                    logger.error(f"Error cancelling expired order {order_id}: {e}")
                    continue
            
            logger.info(f"Completed cancellation of {len(expired_orders)} expired orders")
            
    except Exception as e:
        logger.error(f"Error in cancel_expired_orders task: {e}")
