from datetime import datetime
from fastapi import HTTPException, status
from config.db_connection import DatabaseManager
from utils.email import send_new_order_notification_to_business, send_order_status_email
import logging

logger = logging.getLogger(__name__)

async def confirm_order_payment(order_id: int, payment_reference: str, payment_proof_url: str = None, payment_method: str = "Nave"):
    """
    Core business logic to confirm payment for an order.
    Can be called by API endpoints or Webhooks.
    """
    pool = await DatabaseManager.get_pool()
    
    async with pool.acquire() as conn:
        async with conn.transaction():
            # Get order details
            order = await conn.fetchrow(
                """
                SELECT 
                    s.id,
                    s.status,
                    s.reservation_expires_at,
                    s.total,
                    s.web_user_id,
                    s.storage_id
                FROM sales s
                WHERE s.id = $1
                """,
                order_id
            )
            
            if not order:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Pedido no encontrado"
                )
            
            # If already completed, return success (idempotency)
            if order['status'] == 'Completada':
                logger.info(f"Order {order_id} already completed. Skipping processing.")
                return {"message": "Order already processed"}
            
            # Validate order is pending
            if order['status'] != 'Pendiente':
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El pedido ya fue procesado. Estado actual: {order['status']}"
                )
            
            # Check if reservation expired - Note: For webhooks, we might want to be lenient 
            # if the payment actually happened before expiration but webhook was delayed.
            # But strict enforcement is safer for stock.
            if order['reservation_expires_at']:
                now = await conn.fetchval("SELECT CURRENT_TIMESTAMP")
                # Ensure timezone compatibility
                if order['reservation_expires_at'].tzinfo is None and now.tzinfo is not None:
                    now = now.replace(tzinfo=None)
                elif order['reservation_expires_at'].tzinfo is not None and now.tzinfo is None:
                     now = now.replace(tzinfo=order['reservation_expires_at'].tzinfo)
                     
                if now > order['reservation_expires_at']:
                    # Since payment WAS received (we are confirming it), we should try to honor it 
                    # if stock is still available, OR mark it for manual review.
                    # For now, let's stick to the existing logic: cancel if expired.
                    # BUT if money was taken, we shouldn't just cancel. 
                    # Let's log it as a warning and proceed IF we can (re-check stock?).
                    # To remain consistent with original code: fail if expired.
                    
                    # Original code cancels the order here.
                    await conn.execute(
                        "UPDATE sales SET status = 'Cancelada', updated_at = CURRENT_TIMESTAMP WHERE id = $1",
                        order_id
                    )
                    await conn.execute(
                        "UPDATE stock_reservations SET status = 'expired' WHERE sale_id = $1",
                        order_id
                    )
                    logger.warning(f"Order {order_id} expired before payment confirmation.")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="La reserva del pedido ha expirado."
                    )
            
            # Get reservations for this order
            reservations = await conn.fetch(
                """
                SELECT 
                    sr.id,
                    sr.variant_id,
                    sr.quantity
                FROM stock_reservations sr
                WHERE sr.sale_id = $1 AND sr.status = 'active'
                """,
                order_id
            )
            
            if not reservations:
                 # It might be that reservations expired already?
                 raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No se encontraron reservas activas para este pedido"
                )
            
            # Deduct stock from web_variant_branch_assignment
            for reservation in reservations:
                variant_id = reservation['variant_id']
                quantity_to_deduct = reservation['quantity']
                
                # Get branch assignments for this variant
                assignments = await conn.fetch(
                    """
                    SELECT id, branch_id, cantidad_asignada
                    FROM web_variant_branch_assignment
                    WHERE variant_id = $1 AND cantidad_asignada > 0
                    ORDER BY 
                        CASE WHEN branch_id = $2 THEN 0 ELSE 1 END,
                        cantidad_asignada DESC
                    """,
                    variant_id,
                    order['storage_id'] or 0
                )
                
                remaining_to_deduct = quantity_to_deduct
                
                for assignment in assignments:
                    if remaining_to_deduct <= 0:
                        break
                    
                    deduct_from_this = min(assignment['cantidad_asignada'], remaining_to_deduct)
                    
                    # Update assignment
                    await conn.execute(
                        """
                        UPDATE web_variant_branch_assignment
                        SET cantidad_asignada = cantidad_asignada - $1,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = $2
                        """,
                        deduct_from_this,
                        assignment['id']
                    )

                    # Update PHYSICAL STOCK in warehouse_stock_variants
                    # Find the warehouse_variant corresponding to this web_assignment (same variant + branch)
                    # We need to map web_variant -> (product_id, size_id, color_id) -> warehouse_stock_variants
                    await conn.execute(
                        """
                        UPDATE warehouse_stock_variants
                        SET quantity = quantity - $1,
                            last_updated = CURRENT_TIMESTAMP
                        WHERE id = (
                            SELECT wsv.id
                            FROM warehouse_stock_variants wsv
                            JOIN web_variants wv ON wv.product_id = wsv.product_id 
                                AND wv.size_id = wsv.size_id 
                                AND wv.color_id = wsv.color_id
                            JOIN web_variant_branch_assignment wvba ON wvba.variant_id = wv.id
                            WHERE wvba.id = $2
                            AND wsv.branch_id = wvba.branch_id
                            LIMIT 1
                        )
                        """,
                        deduct_from_this,
                        assignment['id']
                    )
                    
                    remaining_to_deduct -= deduct_from_this
                
                # Update displayed_stock in web_variants
                await conn.execute(
                    """
                    UPDATE web_variants
                    SET displayed_stock = (
                        SELECT COALESCE(SUM(cantidad_asignada), 0)
                        FROM web_variant_branch_assignment
                        WHERE variant_id = $1
                    )
                    WHERE id = $1
                    """,
                    variant_id
                )
                
                # Mark reservation as confirmed
                await conn.execute(
                    """
                    UPDATE stock_reservations
                    SET status = 'confirmed'
                    WHERE id = $1
                    """,
                    reservation['id']
                )

            # Clear the cart for this user (if exists)
            cart = await conn.fetchrow(
                "SELECT id FROM web_carts WHERE user_id = $1",
                order['web_user_id']
            )
            
            if cart:
                await conn.execute(
                    "DELETE FROM web_cart_items WHERE cart_id = $1",
                    cart['id']
                )
            
            # Update order status
            await conn.execute(
                """
                UPDATE sales
                SET status = 'Completada',
                    shipping_status = 'preparando',
                    payment_reference = $1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = $2
                """,
                payment_reference,
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
                'preparando',
                f'Pago confirmado por webhook/sistema. Pedido en preparación. Método: {payment_method}',
                'Sistema Web'
            )
            
            # Get order items count for email
            items_count = await conn.fetchval(
                "SELECT COUNT(*) FROM sales_detail WHERE sale_id = $1",
                order_id
            )
            
            # Fetch full user details for email (in case not fully present in 'order' variable above, 
            # though we only fetched partial fields earlier. Let's fetch more details now or refine first query)
            # Actually, let's refine the first query to get what we need.
            # But since we are here, let's just use what we have, and maybe re-fetch if needed.
            # We need: username, email, phone, shipping_address, delivery_type, total.
            # We already fetched 'total' and 'web_user_id'. We need to JOIN web_users properly.
            
            # Re-fetch full details including user info for email
            full_order_info = await conn.fetchrow(
                 """
                SELECT 
                    s.id,
                    s.total,
                    s.shipping_address,
                    s.delivery_type,
                    COALESCE(wu.username, 'Invitado') as username,
                    wu.email,
                    wu.fullname,
                    wu.phone
                FROM sales s
                LEFT JOIN web_users wu ON s.web_user_id = wu.id
                WHERE s.id = $1
                """,
                order_id
            )
            
            FRONTEND_URL = "https://mykonosboutique.com.ar" # Or get from env
            tracking_link = f"{FRONTEND_URL}/order-tracking/{order_id}"
            
            if full_order_info:
                # Send email to business
                try:
                    await send_new_order_notification_to_business(
                        order_id=order_id,
                        customer_name=full_order_info['fullname'] or full_order_info['username'],
                        customer_email=full_order_info['email'],
                        customer_phone=full_order_info.get('phone', ''),
                        total=float(full_order_info['total']),
                        items_count=items_count,
                        shipping_address=full_order_info['shipping_address'],
                        delivery_type=full_order_info['delivery_type'],
                        order_link=tracking_link
                    )
                except Exception as e:
                    logger.warning(f"Failed to send business notification email: {e}")
                
                # Send email to customer
                try:
                    await send_order_status_email(
                        email=full_order_info['email'],
                        username=full_order_info['fullname'] or full_order_info['username'],
                        order_id=order_id,
                        status='preparando',
                        description=f'Tu pago ha sido confirmado. Estamos preparando tu pedido.',
                        base_url=FRONTEND_URL
                    )
                except Exception as e:
                    logger.warning(f"Failed to send customer notification email: {e}")
            
            logger.info(f"Payment confirmed for order {order_id}")
            return {"status": "success", "order_id": order_id}
