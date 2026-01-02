"""
Orders routes for checkout and order management.
"""

from fastapi import APIRouter, HTTPException, status, Header
from typing import Optional
from config.db_connection import db
from models.cart_models import CheckoutRequest
from utils.auth import get_current_web_user
import logging

logger = logging.getLogger(__name__)

# Create the router
router = APIRouter()


@router.post("/checkout")
async def checkout(checkout_data: CheckoutRequest, authorization: Optional[str] = Header(None)):
    """
    Create an order from the user's cart.
    
    Process:
    1. Validate cart has items
    2. Verify all products still in stock
    3. Create sales record
    4. Create sales_detail records
    5. Clear cart
    
    Validations:
    - Cart must have items
    - All items must have sufficient stock
    - All products must still be online
    
    Requires: User authentication
    """
    try:
        user = await get_current_web_user(authorization)
        user_id = user['id']
        
        # Get user's cart
        cart = await db.fetch_one(
            "SELECT id FROM web_carts WHERE user_id = $1",
            user_id
        )
        
        if not cart:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No tienes un carrito activo"
            )
        
        # Get cart items with product details
        cart_items = await db.fetch_all(
            """
            SELECT 
                wci.id as cart_item_id,
                wci.product_id,
                wci.variant_id,
                wci.quantity,
                p.product_name,
                p.precio_web as unit_price,
                p.cost as cost_price,
                p.en_tienda_online,
                COALESCE(s_web.size_name, s_warehouse.size_name) as size_name,
                COALESCE(c_web.color_name, c_warehouse.color_name) as color_name,
                (wci.quantity * p.precio_web) as subtotal,
                COALESCE(
                    -- First try: variant_id is from web_variants
                    (SELECT SUM(wvba.cantidad_asignada)
                     FROM web_variant_branch_assignment wvba
                     WHERE wvba.variant_id = wci.variant_id),
                    -- Second try: variant_id is from warehouse_stock_variants
                    (SELECT SUM(wvba.cantidad_asignada)
                     FROM warehouse_stock_variants wsv
                     JOIN web_variants wv ON wv.product_id = wsv.product_id 
                         AND wv.size_id = wsv.size_id 
                         AND wv.color_id = wsv.color_id
                     JOIN web_variant_branch_assignment wvba ON wvba.variant_id = wv.id
                     WHERE wsv.id = wci.variant_id),
                    0
                ) as stock_available
            FROM web_cart_items wci
            INNER JOIN products p ON wci.product_id = p.id
            -- Try to join with web_variants
            LEFT JOIN web_variants wv ON wci.variant_id = wv.id
            LEFT JOIN sizes s_web ON wv.size_id = s_web.id
            LEFT JOIN colors c_web ON wv.color_id = c_web.id
            -- If not found, try warehouse_stock_variants
            LEFT JOIN warehouse_stock_variants wsv ON wci.variant_id = wsv.id
            LEFT JOIN sizes s_warehouse ON wsv.size_id = s_warehouse.id
            LEFT JOIN colors c_warehouse ON wsv.color_id = c_warehouse.id
            WHERE wci.cart_id = $1
            """,
            cart['id']
        )
        
        if not cart_items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tu carrito está vacío"
            )
        
        # Validate all items
        for item in cart_items:
            if not item['en_tienda_online']:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El producto '{item['product_name']}' ya no está disponible"
                )
            
            if item['stock_available'] < item['quantity']:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Stock insuficiente para '{item['product_name']}'. Disponible: {item['stock_available']}"
                )
        
        # Calculate totals
        subtotal = sum(float(item['subtotal']) for item in cart_items)
        total = subtotal  # Could add shipping cost here
        
        # Create sales record
        sale = await db.fetch_one(
            """
            INSERT INTO sales (
                web_user_id,
                cashier_user_id,
                employee_id,
                storage_id,
                sale_date,
                subtotal,
                total,
                status,
                origin,
                shipping_address,
                shipping_status,
                delivery_type,
                notes,
                created_at
            )
            VALUES ($1, 1, 1, 1, CURRENT_TIMESTAMP, $2, $3, 'Pendiente', 'web', $4, 'pendiente', 'envio', $5, CURRENT_TIMESTAMP)
            RETURNING id, sale_date, status, total
            """,
            user_id,
            subtotal,
            total,
            checkout_data.shipping_address,
            checkout_data.notes
        )
        
        # Create sales_detail records
        for item in cart_items:
            await db.execute(
                """
                INSERT INTO sales_detail (
                    sale_id,
                    product_id,
                    variant_id,
                    product_name,
                    product_code,
                    size_name,
                    color_name,
                    cost_price,
                    sale_price,
                    quantity,
                    subtotal,
                    total,
                    created_at
                )
                VALUES ($1, $2, $3, $4, '', $5, $6, $7, $8, $9, $10, $10, CURRENT_TIMESTAMP)
                """,
                sale['id'],
                item['product_id'],
                item['variant_id'],
                item['product_name'],
                item['size_name'],
                item['color_name'],
                item['cost_price'] or 0,
                item['unit_price'],
                item['quantity'],
                item['subtotal']
            )
            
            # Update web stock - decrement from web_variant_branch_assignment
            # First, check if variant_id is from web_variants or warehouse_stock_variants
            web_variant_id = await db.fetch_val(
                """
                SELECT COALESCE(
                    -- If it's already a web_variant, use it
                    (SELECT id FROM web_variants WHERE id = $1),
                    -- Otherwise, find the matching web_variant from warehouse_stock_variant
                    (SELECT wv.id 
                     FROM warehouse_stock_variants wsv
                     JOIN web_variants wv ON wv.product_id = wsv.product_id 
                         AND wv.size_id = wsv.size_id 
                         AND wv.color_id = wsv.color_id
                     WHERE wsv.id = $1
                     LIMIT 1)
                )
                """,
                item['variant_id']
            )
            
            if web_variant_id:
                # Decrement web stock proportionally from all branches
                # Get all branch assignments for this variant
                branch_assignments = await db.fetch_all(
                    """
                    SELECT id, branch_id, cantidad_asignada
                    FROM web_variant_branch_assignment
                    WHERE variant_id = $1 AND cantidad_asignada > 0
                    ORDER BY cantidad_asignada DESC
                    """,
                    web_variant_id
                )
                
                remaining_to_deduct = item['quantity']
                for assignment in branch_assignments:
                    if remaining_to_deduct <= 0:
                        break
                    
                    deduct_amount = min(assignment['cantidad_asignada'], remaining_to_deduct)
                    
                    await db.execute(
                        """
                        UPDATE web_variant_branch_assignment
                        SET cantidad_asignada = cantidad_asignada - $1,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = $2
                        """,
                        deduct_amount,
                        assignment['id']
                    )
                    
                    remaining_to_deduct -= deduct_amount
        
        # Clear cart
        await db.execute(
            "DELETE FROM web_cart_items WHERE cart_id = $1",
            cart['id']
        )
        
        # Create tracking history
        await db.execute(
            """
            INSERT INTO sales_tracking_history (sale_id, status, description, created_at)
            VALUES ($1, 'pendiente', 'Orden creada desde tienda online', CURRENT_TIMESTAMP)
            """,
            sale['id']
        )
        
        return {
            "message": "Orden creada exitosamente",
            "order": {
                "order_id": sale['id'],
                "order_number": f"ORD-{sale['sale_date'].year}-{sale['id']}",
                "total": float(sale['total']),
                "status": sale['status'],
                "created_at": sale['sale_date']
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during checkout: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al procesar la orden: {str(e)}"
        )
