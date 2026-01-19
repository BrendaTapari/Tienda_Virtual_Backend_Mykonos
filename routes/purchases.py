"""
Purchase/Sales routes for web users.
Handles retrieving purchase history for authenticated users.
"""

from fastapi import APIRouter, HTTPException, Header, status
from typing import Optional, List
from datetime import datetime
import os

from config.db_connection import DatabaseManager
from models.cart_models import CreateOrderRequest, TrackingUpdateRequest, PaymentConfirmationRequest, CancelOrderRequest
from utils.email import send_new_order_notification_to_business, send_order_status_email

router = APIRouter()

# Frontend URL for tracking links
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://mykonosboutique.com.ar")
RESERVATION_MINUTES = 30


async def get_user_by_token(token: str):
    """Get user by session token."""
    pool = await DatabaseManager.get_pool()
    async with pool.acquire() as conn:
        user = await conn.fetchrow(
            """
            SELECT id, username, email
            FROM web_users
            WHERE session_token = $1 AND status = 'active'
            """,
            token
        )
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
        return dict(user)


@router.get("/my-purchases")
async def get_my_purchases(authorization: Optional[str] = Header(None)):
    """
    Get purchase history for the authenticated user.
    
    Returns all purchases made by the logged-in user with details including:
    - Order information (date, total, status)
    - Product details (name, quantity, price)
    - Shipping information (if applicable)
    
    Requires Authorization header with Bearer token.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header"
        )
    
    token = authorization.replace("Bearer ", "")
    current_user = await get_user_by_token(token)
    
    pool = await DatabaseManager.get_pool()
    
    async with pool.acquire() as conn:
        # Get all sales for this web user
        sales = await conn.fetch(
            """
            SELECT 
                s.id,
                s.sale_date,
                s.subtotal,
                s.tax_amount,
                s.discount,
                s.total,
                s.status,
                s.shipping_address,
                s.shipping_status,
                s.shipping_cost,
                s.payment_reference,
                s.invoice_number,
                s.notes,
                s.origin
            FROM sales s
            WHERE s.web_user_id = $1
            ORDER BY s.sale_date DESC
            """,
            current_user['id']
        )
        
        if not sales:
            return []
        
        # For each sale, get the details (products)
        purchases = []
        for sale in sales:
            sale_dict = dict(sale)
            
            # Get sale details (products)
            details = await conn.fetch(
                """
                SELECT 
                    sd.id,
                    sd.product_name,
                    sd.product_code,
                    sd.size_name,
                    sd.color_name,
                    sd.sale_price,
                    sd.quantity,
                    sd.discount_percentage,
                    sd.discount_amount,
                    sd.subtotal,
                    sd.total,
                    p.id as product_id
                FROM sales_detail sd
                LEFT JOIN products p ON sd.product_id = p.id
                WHERE sd.sale_id = $1
                """,
                sale_dict['id']
            )
            
            # Get product images for each item
            items = []
            for detail in details:
                detail_dict = dict(detail)
                
                # Get first image of the product
                if detail_dict['product_id']:
                    image = await conn.fetchrow(
                        """
                        SELECT image_url
                        FROM images
                        WHERE product_id = $1
                        ORDER BY orden ASC
                        LIMIT 1
                        """,
                        detail_dict['product_id']
                    )
                    detail_dict['image_url'] = image['image_url'] if image else None
                else:
                    detail_dict['image_url'] = None
                
                items.append(detail_dict)
            
            sale_dict['items'] = items
            purchases.append(sale_dict)
        
        return purchases


@router.get("/my-purchases/{purchase_id}")
async def get_purchase_detail(
    purchase_id: int,
    authorization: Optional[str] = Header(None)
):
    """
    Get detailed information about a specific purchase.
    
    - **purchase_id**: ID of the purchase to retrieve
    
    Includes tracking history if available.
    
    Requires Authorization header with Bearer token.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header"
        )
    
    token = authorization.replace("Bearer ", "")
    current_user = await get_user_by_token(token)
    
    pool = await DatabaseManager.get_pool()
    
    async with pool.acquire() as conn:
        # Get sale information and verify it belongs to the user
        sale = await conn.fetchrow(
            """
            SELECT 
                s.id,
                s.sale_date,
                s.subtotal,
                s.tax_amount,
                s.discount,
                s.total,
                s.status,
                s.shipping_address,
                s.shipping_status,
                s.shipping_cost,
                s.payment_reference,
                s.invoice_number,
                s.notes,
                s.origin,
                s.delivery_type,
                s.created_at,
                s.updated_at
            FROM sales s
            WHERE s.id = $1 AND s.web_user_id = $2
            """,
            purchase_id,
            current_user['id']
        )
        
        if not sale:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Purchase not found or does not belong to you"
            )
        
        sale_dict = dict(sale)
        
        # Get sale details (products) with images
        details = await conn.fetch(
            """
            SELECT 
                sd.id,
                sd.product_name,
                sd.product_code,
                sd.size_name,
                sd.color_name,
                sd.sale_price,
                sd.quantity,
                sd.discount_percentage,
                sd.discount_amount,
                sd.tax_percentage,
                sd.tax_amount,
                sd.subtotal,
                sd.total,
                p.id as product_id,
                (
                    SELECT image_url 
                    FROM images 
                    WHERE product_id = p.id 
                    ORDER BY orden ASC 
                    LIMIT 1
                ) as image_url
            FROM sales_detail sd
            LEFT JOIN products p ON sd.product_id = p.id
            WHERE sd.sale_id = $1
            """,
            purchase_id
        )
        
        sale_dict['items'] = [dict(d) for d in details]
        
        # Get tracking history if table exists
        try:
            tracking_history = await conn.fetch(
                """
                SELECT 
                    sth.id,
                    sth.status,
                    sth.description,
                    sth.location,
                    sth.created_at,
                    u.username as changed_by
                FROM sales_tracking_history sth
                LEFT JOIN users u ON sth.changed_by_user_id = u.id
                WHERE sth.sale_id = $1
                ORDER BY sth.created_at ASC
                """,
                purchase_id
            )
            
            sale_dict['tracking_history'] = [dict(record) for record in tracking_history]
        except Exception as e:
            # Table might not exist yet, return empty history
            print(f"Warning: Could not fetch tracking history: {e}")
            sale_dict['tracking_history'] = []
        
        return sale_dict


@router.post("/create-order")
async def create_order(
    order_data: CreateOrderRequest,
    authorization: Optional[str] = Header(None)
):
    try:
        return await _create_order_impl(order_data, authorization)
    except HTTPException:
        # Re-raise standard HTTP exceptions (400, 401, etc.) unmodified
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"DEBUG ERROR: {str(e)}"
        )

async def _create_order_impl(
    order_data: CreateOrderRequest,
    authorization: Optional[str] = Header(None)
):
    """
    Create a purchase order from the user's cart with TEMPORARY stock reservation.
    
    - **shipping_address**: Complete shipping address
    - **delivery_type**: 'envio' (delivery) or 'retiro' (pickup)
    - **shipping_cost**: Shipping cost (default: 0)
    - **notes**: Optional notes for the order
    - **payment_method**: Payment method (for future use)
    
    NEW FLOW (Payment Gateway Integration):
    1. Validates user authentication
    2. Gets cart items and validates stock availability
    3. Creates sale record with 'Pendiente' status
    4. RESERVES stock temporarily (30 minutes) - does NOT deduct
    5. Sets expiration time
    6. Does NOT send emails (emails sent after payment confirmation)
    7. Clears the cart
    
    Returns order details with expiration time.
    User must complete payment within 30 minutes or order will be auto-cancelled.
    
    Requires Authorization header with Bearer token.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header"
        )
    
    token = authorization.replace("Bearer ", "")
    current_user = await get_user_by_token(token)
    
    pool = await DatabaseManager.get_pool()
    
    # Reservation expiration time (30 minutes)
    RESERVATION_MINUTES = 30
    
    async with pool.acquire() as conn:
        # Start transaction
        async with conn.transaction():
            # Get user's cart
            cart = await conn.fetchrow(
                "SELECT id FROM web_carts WHERE user_id = $1",
                current_user['id']
            )
            
            if not cart:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="El carrito está vacío. Agrega productos antes de crear un pedido."
                )
            
            # AUTO-CLEANUP: Cancel previous active reservations for this user to prevent self-blocking
            # Find recent pending sales for this user with active reservations
            await conn.execute("""
                UPDATE stock_reservations
                SET status = 'cancelled'
                WHERE status = 'active'
                AND sale_id IN (
                    SELECT id FROM sales 
                    WHERE (customer_id = $1 OR web_user_id = $1)
                    AND status = 'Pendiente de pago'
                )
            """, current_user['id'])

            # Get cart items with product details
            cart_items = await conn.fetch(
                """
                SELECT 
                    wci.id as cart_item_id,
                    wci.product_id,
                    wci.variant_id,
                    wci.quantity,
                    p.nombre_web as product_name,
                    -- Fix Price: Apply discount if active
                    CASE 
                        WHEN p.has_discount = 1 THEN 
                             CAST(p.precio_web * (1 - p.discount_percentage / 100.0) AS NUMERIC)
                        ELSE p.precio_web 
                    END as unit_price,
                    p.provider_code as product_code,
                    COALESCE(s_web.size_name, s_warehouse.size_name) as size_name,
                    COALESCE(c_web.color_name, c_warehouse.color_name) as color_name,
                    COALESCE(wsv.variant_barcode, '') as variant_barcode,
                    COALESCE((
                        SELECT SUM(wvba.cantidad_asignada)
                        FROM web_variant_branch_assignment wvba
                        WHERE wvba.variant_id = wci.variant_id
                    ), (
                        SELECT SUM(wvba.cantidad_asignada)
                        FROM warehouse_stock_variants wsv_stock
                        JOIN web_variants wv_stock ON wv_stock.product_id = wsv_stock.product_id 
                            AND wv_stock.size_id = wsv_stock.size_id 
                            AND wv_stock.color_id = wsv_stock.color_id
                        JOIN web_variant_branch_assignment wvba ON wvba.variant_id = wv_stock.id
                        WHERE wsv_stock.id = wci.variant_id
                    ), 0) as stock_available,

                     -- Resolve real Warehouse Variant ID for Sales Detail FK
                    wsv.id as warehouse_variant_id,
                    -- Get currently reserved stock for this variant
                    COALESCE((
                        SELECT SUM(sr.quantity)
                        FROM stock_reservations sr
                        WHERE sr.variant_id = wci.variant_id 
                        AND sr.status = 'active'
                        AND sr.expires_at > CURRENT_TIMESTAMP
                    ), 0) as stock_reserved
                FROM web_cart_items wci
                INNER JOIN products p ON wci.product_id = p.id
                LEFT JOIN web_variants wv ON wci.variant_id = wv.id
                LEFT JOIN sizes s_web ON wv.size_id = s_web.id
                LEFT JOIN colors c_web ON wv.color_id = c_web.id
                -- Fix Duplication: Use LEFT JOIN LATERAL to pick ONLY ONE matching warehouse variant
                LEFT JOIN LATERAL (
                    SELECT id, variant_barcode, size_id, color_id
                    FROM warehouse_stock_variants
                    WHERE product_id = wci.product_id 
                    AND size_id = wv.size_id 
                    AND color_id = wv.color_id
                    ORDER BY id ASC
                    LIMIT 1
                ) wsv ON TRUE
                LEFT JOIN sizes s_warehouse ON wsv.size_id = s_warehouse.id
                LEFT JOIN colors c_warehouse ON wsv.color_id = c_warehouse.id
                WHERE wci.cart_id = $1
                ORDER BY wci.id, wci.created_at
                """,
                cart['id']
            )
            
            if not cart_items:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="El carrito está vacío. Agrega productos antes de crear un pedido."
                )
            
            # Validate stock availability (considering active reservations)
            for item in cart_items:
                available_stock = item['stock_available'] - item['stock_reserved']
                if available_stock < item['quantity']:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Stock insuficiente para el producto '{item['product_name']}' "
                               f"(Talle: {item['size_name']}, Color: {item['color_name']}). "
                               f"Disponible: {available_stock}, Solicitado: {item['quantity']}"
                    )
            
            # Calculate totals
            # Enforce free shipping for store pickup
            final_shipping_cost = order_data.shipping_cost
            if order_data.delivery_type == 'retiro':
                final_shipping_cost = 0.0
            
            subtotal = sum(float(item['unit_price']) * item['quantity'] for item in cart_items)
            total = subtotal + final_shipping_cost
            
            # Calculate expiration time
            reservation_expires_at = await conn.fetchval(
                f"SELECT CURRENT_TIMESTAMP + INTERVAL '{RESERVATION_MINUTES} minutes'"
            )
            if hasattr(reservation_expires_at, 'tzinfo') and reservation_expires_at.tzinfo:
                reservation_expires_at = reservation_expires_at.replace(tzinfo=None)
            
            # Create sale record with reservation expiration
            sale = await conn.fetchrow(
                """
                INSERT INTO sales (
                    web_user_id,
                    employee_id,
                    cashier_user_id,
                    storage_id,
                    sale_date,
                    subtotal,
                    tax_amount,
                    discount,
                    total,
                    status,
                    origin,
                    shipping_address,
                    shipping_status,
                    shipping_cost,
                    delivery_type,
                    notes,
                    reservation_expires_at,
                    payment_method,
                    created_at,
                    updated_at
                )
                VALUES ($1, 1, 1, $2, CURRENT_TIMESTAMP, $3, 0, 0, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                RETURNING id, sale_date, subtotal, total, status, shipping_status, reservation_expires_at
                """,
                current_user['id'],
                order_data.branch_id or 1,  # Use provided branch_id or default to 1 (Main/Concordia?)
                subtotal,
                total,
                'Pendiente',  # Status pending until payment is confirmed
                'web',
                order_data.shipping_address,
                'pendiente',
                order_data.shipping_cost,
                order_data.delivery_type,
                order_data.notes,
                reservation_expires_at,
                order_data.payment_method
            )
            
            sale_id = sale['id']
            
            # Create sale details and stock reservations for each cart item
            order_items = []
            for item in cart_items:
                # Use resolved warehouse_variant_id. If missing, use None (will insert NULL)
                warehouse_variant_to_use = item['warehouse_variant_id']

                # Create sale detail
                sale_detail = await conn.fetchrow(
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
                        discount_percentage,
                        discount_amount,
                        tax_percentage,
                        tax_amount,
                        subtotal,
                        total,
                        created_at
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, 0, $8, $9, 0, 0, 0, 0, $10, $10, CURRENT_TIMESTAMP)
                    RETURNING id
                    """,
                    sale_id,
                    item['product_id'],
                    warehouse_variant_to_use,
                    item['product_name'],
                    item['product_code'],
                    item['size_name'],
                    item['color_name'],
                    item['unit_price'],
                    item['quantity'],
                    float(item['unit_price']) * item['quantity']
                )
                
                # Create stock reservation (NOT deducting stock yet)
                await conn.execute(
                    """
                    INSERT INTO stock_reservations (
                        sale_id,
                        variant_id,
                        quantity,
                        reserved_at,
                        expires_at,
                        status
                    )
                    VALUES ($1, $2, $3, CURRENT_TIMESTAMP, $4, 'active')
                    """,
                    sale_id,
                    item['variant_id'],
                    item['quantity'],
                    reservation_expires_at
                )
                
                order_items.append({
                    'product_id': item['product_id'],
                    'product_name': item['product_name'],
                    'product_code': item['product_code'],
                    'size_name': item['size_name'],
                    'color_name': item['color_name'],
                    'variant_barcode': item['variant_barcode'],
                    'quantity': item['quantity'],
                    'unit_price': float(item['unit_price']),
                    'subtotal': float(item['unit_price']) * item['quantity']
                })
            
            # Create initial tracking history entry (NO email sent)
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
                sale_id,
                'pendiente',
                'Pedido creado. Esperando confirmación de pago.',
                'Sistema Web',
            )
            
            # Clear the cart - MOVED TO PAYMENT CONFIRMATION
            # to prevent lost carts on payment failure
            # await conn.execute(
            #     "DELETE FROM web_cart_items WHERE cart_id = $1",
            #     cart['id']
            # )
            
            # Prepare tracking link
            tracking_link = f"{FRONTEND_URL}/order-tracking/{sale_id}"
            
            # Calculate minutes remaining
            minutes_to_pay = RESERVATION_MINUTES
            
            # Prepare response
            order_details = {
                'id': sale_id,
                'sale_date': sale['sale_date'].isoformat() if hasattr(sale['sale_date'], 'isoformat') else str(sale['sale_date']),
                'subtotal': float(subtotal),
                'total': float(total),
                'shipping_cost': float(order_data.shipping_cost),
                'status': sale['status'],
                'shipping_status': sale['shipping_status'],
                'shipping_address': order_data.shipping_address,
                'delivery_type': order_data.delivery_type,
                'notes': order_data.notes,
                'items': order_items
            }
            
            return {
                'message': f'Pedido creado exitosamente. Completa el pago en {minutes_to_pay} minutos.',
                'order_id': sale_id,
                'reservation_expires_at': sale['reservation_expires_at'].isoformat() if hasattr(sale['reservation_expires_at'], 'isoformat') else str(sale['reservation_expires_at']),
                'minutes_to_pay': minutes_to_pay,
                'order_details': order_details,
                'tracking_link': tracking_link
            }


@router.post("/{order_id}/confirm-payment")
async def confirm_payment(
    order_id: int,
    payment_data: PaymentConfirmationRequest,
    authorization: Optional[str] = Header(None)
):
    """
    Confirm payment for a pending order.
    
    This endpoint:
    1. Validates the order exists and is pending
    2. Checks reservation hasn't expired
    3. Updates order status to 'Completada'
    4. Deducts stock from web_variant_branch_assignment
    5. Marks reservations as 'confirmed'
    6. Creates tracking entry
    7. Sends email notifications (business + customer)
    
    Requires Authorization header with Bearer token.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header"
        )
    
    token = authorization.replace("Bearer ", "")
    current_user = await get_user_by_token(token)
    
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
                    s.shipping_address,
                    s.delivery_type,
                    s.storage_id,
                    s.web_user_id,
                    wu.username,
                    wu.email,
                    wu.fullname,
                    wu.phone
                FROM sales s
                LEFT JOIN web_users wu ON s.web_user_id = wu.id
                WHERE s.id = $1
                """,
                order_id
            )
            
            if not order:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Pedido no encontrado"
                )
            
            # ... (validation logic remains same) ...
            
            # Validate order is pending
            if order['status'] != 'Pendiente':
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El pedido ya fue procesado. Estado actual: {order['status']}"
                )
            
            # Check if reservation expired
            if order['reservation_expires_at']:
                now = await conn.fetchval("SELECT CURRENT_TIMESTAMP")
                # Ensure timezone compatibility
                if order['reservation_expires_at'].tzinfo is None and now.tzinfo is not None:
                    now = now.replace(tzinfo=None)
                elif order['reservation_expires_at'].tzinfo is not None and now.tzinfo is None:
                    # Look up how asyncpg returns it, usually aware. If order is aware, make now aware? 
                    # Simpler to just strip both or ensure now matches order.
                     now = now.replace(tzinfo=order['reservation_expires_at'].tzinfo)
                
                if now > order['reservation_expires_at']:
                    # Auto-cancel expired order
                    await conn.execute(
                        "UPDATE sales SET status = 'Cancelada', updated_at = CURRENT_TIMESTAMP WHERE id = $1",
                        order_id
                    )
                    await conn.execute(
                        "UPDATE stock_reservations SET status = 'expired' WHERE sale_id = $1",
                        order_id
                    )
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="La reserva del pedido ha expirado. Por favor, crea un nuevo pedido."
                    )
            
            # Get reservations for this order
            reservations = await conn.fetch(
                """
                SELECT 
                    sr.id,
                    sr.variant_id,
                    sr.quantity,
                    wv.product_id
                FROM stock_reservations sr
                JOIN web_variants wv ON sr.variant_id = wv.id
                WHERE sr.sale_id = $1 AND sr.status = 'active'
                """,
                order_id
            )
            
            if not reservations:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No se encontraron reservas activas para este pedido"
                )
            
            # Deduct stock from web_variant_branch_assignment
            for reservation in reservations:
                variant_id = reservation['variant_id']
                quantity_to_deduct = reservation['quantity']
                
                # Get branch assignments for this variant
                # PRIORITIZE the selected branch (storage_id)
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
                        UPDATE warehouse_stock_variants
                        SET quantity = quantity - $1,
                            last_updated = CURRENT_TIMESTAMP
                        WHERE id = $2
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
            # We need to find the cart for the user who made the order
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
                payment_data.payment_reference,
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
                f'Pago confirmado. Pedido en preparación. Método: {payment_data.payment_method}',
                'Sistema Web'
            )
            
            # Get order items count for email
            items_count = await conn.fetchval(
                "SELECT COUNT(*) FROM sales_detail WHERE sale_id = $1",
                order_id
            )
            
            # Prepare tracking link
            tracking_link = f"{FRONTEND_URL}/order-tracking/{order_id}"
            
            # Send email to business
            try:
                await send_new_order_notification_to_business(
                    order_id=order_id,
                    customer_name=order['fullname'] or order['username'],
                    customer_email=order['email'],
                    customer_phone=order.get('phone', ''),
                    total=float(order['total']),
                    items_count=items_count,
                    shipping_address=order['shipping_address'],
                    delivery_type=order['delivery_type'],
                    order_link=tracking_link
                )
            except Exception as e:
                print(f"Warning: Failed to send business notification email: {e}")
            
            # Send email to customer
            try:
                await send_order_status_email(
                    email=order['email'],
                    username=order['fullname'] or order['username'],
                    order_id=order_id,
                    status='preparando',
                    description=f'Tu pago ha sido confirmado. Estamos preparando tu pedido.',
                    base_url=FRONTEND_URL
                )
            except Exception as e:
                print(f"Warning: Failed to send customer notification email: {e}")
            
            return {
                'message': 'Pago confirmado exitosamente',
                'order_id': order_id,
                'status': 'Completada',
                'shipping_status': 'preparando',
                'tracking_link': tracking_link
            }


@router.post("/{order_id}/cancel")
async def cancel_order(
    order_id: int,
    cancel_data: CancelOrderRequest,
    authorization: Optional[str] = Header(None)
):
    """
    Cancel a pending order and release reserved stock.
    
    This endpoint:
    1. Validates the order exists
    2. Updates order status to 'Cancelada'
    3. Marks stock reservations as 'cancelled'
    4. Creates tracking entry
    5. Optionally sends email to customer
    
    Reasons: 'expired', 'user_cancelled', 'payment_failed'
    
    Requires Authorization header with Bearer token.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header"
        )
    
    token = authorization.replace("Bearer ", "")
    current_user = await get_user_by_token(token)
    
    pool = await DatabaseManager.get_pool()
    
    async with pool.acquire() as conn:
        async with conn.transaction():
            # Get order details
            order = await conn.fetchrow(
                """
                SELECT 
                    s.id,
                    s.status,
                    s.web_user_id,
                    wu.username,
                    wu.email,
                    wu.fullname
                FROM sales s
                LEFT JOIN web_users wu ON s.web_user_id = wu.id
                WHERE s.id = $1
                """,
                order_id
            )
            
            if not order:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Pedido no encontrado"
                )
            
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
            
            # Release stock reservations
            reservations_updated = await conn.execute(
                """
                UPDATE stock_reservations
                SET status = 'cancelled', updated_at = CURRENT_TIMESTAMP
                WHERE sale_id = $1 AND status = 'active'
                """,
                order_id
            )
            
            # Create tracking entry
            reason_text = {
                'expired': 'Pedido cancelado automáticamente por expiración de reserva',
                'user_cancelled': 'Pedido cancelado por el cliente',
                'payment_failed': 'Pedido cancelado por fallo en el pago'
            }.get(cancel_data.reason, 'Pedido cancelado')
            
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
                reason_text + (f'. {cancel_data.notes}' if cancel_data.notes else ''),
                'Sistema Web'
            )
            
            # Send email to customer if user cancelled
            if cancel_data.reason == 'user_cancelled' and order['email']:
                try:
                    await send_order_status_email(
                        email=order['email'],
                        username=order['fullname'] or order['username'],
                        order_id=order_id,
                        status='cancelado',
                        description='Tu pedido ha sido cancelado según tu solicitud.',
                        base_url=FRONTEND_URL
                    )
                except Exception as e:
                    print(f"Warning: Failed to send cancellation email: {e}")
            
            return {
                'message': 'Pedido cancelado exitosamente',
                'order_id': order_id,
                'status': 'Cancelada',
                'stock_released': True,
                'reason': cancel_data.reason
            }


@router.post("/{purchase_id}/tracking")
async def update_tracking_history(
    purchase_id: int,
    tracking_data: TrackingUpdateRequest,
    authorization: Optional[str] = Header(None)
):
    """
    Update the tracking history for a purchase order.
    
    - **purchase_id**: ID of the purchase to update
    - **status**: New status (preparando, despachado, en_transito, entregado, cancelado)
    - **description**: Description of the status update
    - **location**: Optional location information
    - **notify_customer**: Whether to send email notification to customer (default: true)
    
    This endpoint is typically used by admin/employee users to update order status.
    
    Requires Authorization header with Bearer token.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header"
        )
    
    token = authorization.replace("Bearer ", "")
    
    # For now, we'll use the web user token, but in production you might want
    # to validate that this is an admin/employee user
    current_user = await get_user_by_token(token)
    
    pool = await DatabaseManager.get_pool()
    
    async with pool.acquire() as conn:
        # Verify sale exists
        sale = await conn.fetchrow(
            """
            SELECT 
                s.id,
                s.web_user_id,
                wu.username,
                wu.email,
                wu.fullname
            FROM sales s
            LEFT JOIN web_users wu ON s.web_user_id = wu.id
            WHERE s.id = $1
            """,
            purchase_id
        )
        
        if not sale:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pedido no encontrado"
            )
        
        # Insert tracking history entry
        tracking_entry = await conn.fetchrow(
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
            RETURNING id, sale_id, status, description, location, created_at
            """,
            purchase_id,
            tracking_data.status,
            tracking_data.description,
            tracking_data.location
        )
        
        # Update shipping_status in sales table
        await conn.execute(
            """
            UPDATE sales
            SET shipping_status = $1, updated_at = CURRENT_TIMESTAMP
            WHERE id = $2
            """,
            tracking_data.status,
            purchase_id
        )
        
        # Send email notification to customer if requested
        email_sent = False
        if tracking_data.notify_customer and sale['email']:
            try:
                await send_order_status_email(
                    email=sale['email'],
                    username=sale['fullname'] or sale['username'],
                    order_id=purchase_id,
                    status=tracking_data.status,
                    description=tracking_data.description,
                    base_url=FRONTEND_URL
                )
                email_sent = True
            except Exception as e:
                # Log error but don't fail the tracking update
                print(f"Warning: Failed to send customer notification email: {e}")
        
        return {
            'message': 'Historial de rastreo actualizado exitosamente',
            'tracking_entry': {
                'id': tracking_entry['id'],
                'sale_id': tracking_entry['sale_id'],
                'status': tracking_entry['status'],
                'description': tracking_entry['description'],
                'location': tracking_entry['location'],
                'created_at': tracking_entry['created_at'].isoformat() if hasattr(tracking_entry['created_at'], 'isoformat') else str(tracking_entry['created_at']),
                'changed_by': 'admin'  # For now, hardcoded
            },
            'email_sent': email_sent
        }
