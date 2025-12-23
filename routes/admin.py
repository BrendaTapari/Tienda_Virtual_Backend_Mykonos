"""
Admin routes for managing users, orders, and products.
All endpoints require admin authentication.
"""

from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import List, Optional
from config.db_connection import db
from models.user_models import UserListResponse, UpdateUserRole, UpdateUserStatus
from models.order_models import (
    OrderListResponse,
    OrderDetailResponse,
    UpdateOrderStatus,
    OrderCustomer,
    OrderItem,
    TrackingHistoryItem
)
from utils.auth import require_admin
import logging

logger = logging.getLogger(__name__)

# Create the router
router = APIRouter()


# --- USER MANAGEMENT ENDPOINTS ---

@router.get("/users", response_model=List[UserListResponse], dependencies=[Depends(require_admin)])
async def get_all_users(
    role: Optional[str] = Query(None, description="Filter by role (admin/customer)"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of users to return"),
    offset: int = Query(0, ge=0, description="Number of users to skip")
):
    """
    Get all users in the system (admin only).
    
    Query Parameters:
    - role: Filter by role (optional)
    - limit: Maximum number of results (default: 50)
    - offset: Pagination offset (default: 0)
    
    Requires: Admin authentication
    """
    try:
        # Build query
        query = """
            SELECT 
                u.id,
                u.username,
                u.fullname,
                u.email,
                u.role,
                u.status,
                u.email_verified,
                u.created_at,
                COALESCE(COUNT(s.id), 0) as total_purchases
            FROM web_users u
            LEFT JOIN sales s ON s.web_user_id = u.id
        """
        
        params = []
        param_count = 1
        
        if role:
            query += f" WHERE u.role = ${param_count}"
            params.append(role)
            param_count += 1
        
        query += f"""
            GROUP BY u.id, u.username, u.fullname, u.email, u.role, u.status, u.email_verified, u.created_at
            ORDER BY u.created_at DESC
            LIMIT ${param_count} OFFSET ${param_count + 1}
        """
        params.extend([limit, offset])
        
        users = await db.fetch_all(query, *params)
        
        return users
        
    except Exception as e:
        logger.error(f"Error fetching users (admin): {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener usuarios: {str(e)}"
        )


@router.patch("/users/{user_id}/role", dependencies=[Depends(require_admin)])
async def update_user_role(user_id: int, role_data: UpdateUserRole, authorization: Optional[str] = None):
    """
    Update a user's role (admin only).
    
    Path Parameters:
    - user_id: The ID of the user to update
    
    Request Body:
    - role: New role ("admin" or "customer")
    
    Validations:
    - Role must be "admin" or "customer"
    - Cannot remove the last admin
    - Cannot change own role
    
    Requires: Admin authentication
    """
    try:
        # Validate role
        if role_data.role not in ["admin", "customer"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El rol debe ser 'admin' o 'customer'"
            )
        
        # Check if user exists
        user = await db.fetch_one("SELECT id, role FROM web_users WHERE id = $1", user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Usuario con ID {user_id} no encontrado"
            )
        
        # If removing admin role, check there's at least one other admin
        if user['role'] == 'admin' and role_data.role != 'admin':
            admin_count = await db.fetch_val("SELECT COUNT(*) FROM web_users WHERE role = 'admin'")
            if admin_count <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No se puede quitar el rol de admin al último administrador del sistema"
                )
        
        # Get current admin user to prevent self-demotion
        if authorization:
            token = authorization.replace("Bearer ", "")
            current_user = await db.fetch_one(
                "SELECT id FROM web_users WHERE session_token = $1",
                token
            )
            if current_user and current_user['id'] == user_id and role_data.role != 'admin':
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No puedes quitarte el rol de admin a ti mismo"
                )
        
        # Update role
        await db.execute(
            "UPDATE web_users SET role = $1 WHERE id = $2",
            role_data.role,
            user_id
        )
        
        return {"message": f"Rol actualizado a '{role_data.role}' exitosamente", "user_id": user_id, "new_role": role_data.role}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user role: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar el rol: {str(e)}"
        )


@router.patch("/users/{user_id}/status", dependencies=[Depends(require_admin)])
async def update_user_status(user_id: int, status_data: UpdateUserStatus):
    """
    Update a user's status (admin only).
    
    Path Parameters:
    - user_id: The ID of the user to update
    
    Request Body:
    - status: New status ("active" or "inactive")
    
    Requires: Admin authentication
    """
    try:
        # Validate status
        if status_data.status not in ["active", "inactive"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El estado debe ser 'active' o 'inactive'"
            )
        
        # Check if user exists
        user = await db.fetch_one("SELECT id FROM web_users WHERE id = $1", user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Usuario con ID {user_id} no encontrado"
            )
        
        # Update status
        await db.execute(
            "UPDATE web_users SET status = $1 WHERE id = $2",
            status_data.status,
            user_id
        )
        
        return {"message": f"Estado actualizado a '{status_data.status}' exitosamente", "user_id": user_id, "new_status": status_data.status}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar el estado: {str(e)}"
        )


# --- ORDER MANAGEMENT ENDPOINTS ---

@router.get("/orders", response_model=List[OrderListResponse], dependencies=[Depends(require_admin)])
async def get_all_orders(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of orders to return"),
    offset: int = Query(0, ge=0, description="Number of orders to skip")
):
    """
    Get all orders in the system (admin only).
    
    Query Parameters:
    - status: Filter by order status (optional)
    - limit: Maximum number of results (default: 50)
    - offset: Pagination offset (default: 0)
    
    Requires: Admin authentication
    """
    try:
        query = """
            SELECT 
                s.id as order_id,
                s.sale_date as order_date,
                s.status,
                s.shipping_status,
                s.total,
                s.shipping_address,
                s.origin,
                COALESCE(COUNT(sd.id), 0) as items_count,
                wu.id as customer_id,
                wu.username as customer_username,
                wu.email as customer_email
            FROM sales s
            LEFT JOIN web_users wu ON s.web_user_id = wu.id
            LEFT JOIN sales_detail sd ON sd.sale_id = s.id
        """
        
        params = []
        param_count = 1
        
        if status_filter:
            query += f" WHERE s.status = ${param_count}"
            params.append(status_filter)
            param_count += 1
        
        query += f"""
            GROUP BY s.id, s.sale_date, s.status, s.shipping_status, s.total, s.shipping_address, s.origin,
                     wu.id, wu.username, wu.email
            ORDER BY s.sale_date DESC
            LIMIT ${param_count} OFFSET ${param_count + 1}
        """
        params.extend([limit, offset])
        
        orders = await db.fetch_all(query, *params)
        
        # Format response
        result = []
        for order in orders:
            order_dict = dict(order)
            
            # Build customer object if exists
            customer = None
            if order_dict.get('customer_id'):
                customer = {
                    "id": order_dict['customer_id'],
                    "username": order_dict['customer_username'],
                    "email": order_dict['customer_email']
                }
            
            result.append({
                "order_id": order_dict['order_id'],
                "customer": customer,
                "order_date": order_dict['order_date'],
                "status": order_dict['status'],
                "shipping_status": order_dict['shipping_status'],
                "total": order_dict['total'],
                "items_count": order_dict['items_count'],
                "shipping_address": order_dict['shipping_address'],
                "origin": order_dict['origin']
            })
        
        return result
        
    except Exception as e:
        logger.error(f"Error fetching orders (admin): {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener órdenes: {str(e)}"
        )


@router.get("/orders/{order_id}", response_model=OrderDetailResponse, dependencies=[Depends(require_admin)])
async def get_order_details(order_id: int):
    """
    Get complete details of a specific order (admin only).
    
    Path Parameters:
    - order_id: The ID of the order
    
    Requires: Admin authentication
    """
    try:
        # Get order info
        order = await db.fetch_one(
            """
            SELECT 
                s.id as order_id,
                s.sale_date as order_date,
                s.status,
                s.shipping_status,
                s.origin,
                s.delivery_type,
                s.subtotal,
                s.shipping_cost,
                s.discount,
                s.total,
                s.shipping_address,
                s.external_payment_id,
                s.notes,
                wu.id as customer_id,
                wu.username as customer_username,
                wu.email as customer_email
            FROM sales s
            LEFT JOIN web_users wu ON s.web_user_id = wu.id
            WHERE s.id = $1
            """,
            order_id
        )
        
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Orden con ID {order_id} no encontrada"
            )
        
        # Get order items
        items = await db.fetch_all(
            """
            SELECT 
                sd.product_id,
                sd.product_name,
                sd.size_name,
                sd.color_name,
                sd.quantity,
                sd.sale_price as unit_price,
                sd.subtotal
            FROM sales_detail sd
            WHERE sd.sale_id = $1
            """,
            order_id
        )
        
        # Get tracking history
        tracking = await db.fetch_all(
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
            ORDER BY sth.created_at DESC
            """,
            order_id
        )
        
        # Build response
        order_dict = dict(order)
        
        customer = None
        if order_dict.get('customer_id'):
            customer = {
                "id": order_dict['customer_id'],
                "username": order_dict['customer_username'],
                "email": order_dict['customer_email']
            }
        
        return {
            "order_id": order_dict['order_id'],
            "customer": customer,
            "order_date": order_dict['order_date'],
            "status": order_dict['status'],
            "shipping_status": order_dict['shipping_status'],
            "origin": order_dict['origin'],
            "delivery_type": order_dict['delivery_type'],
            "items": [dict(item) for item in items],
            "subtotal": order_dict['subtotal'],
            "shipping_cost": order_dict['shipping_cost'] or 0,
            "discount": order_dict['discount'] or 0,
            "total": order_dict['total'],
            "shipping_address": order_dict['shipping_address'],
            "external_payment_id": order_dict['external_payment_id'],
            "tracking_history": [dict(t) for t in tracking],
            "notes": order_dict['notes']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching order details: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener detalles de la orden: {str(e)}"
        )


@router.patch("/orders/{order_id}/status", dependencies=[Depends(require_admin)])
async def update_order_status(order_id: int, status_data: UpdateOrderStatus):
    """
    Update an order's shipping status (admin only).
    
    Path Parameters:
    - order_id: The ID of the order
    
    Request Body:
    - status: New shipping status
    - tracking_number: Optional tracking number
    - notes: Optional notes
    
    Requires: Admin authentication
    """
    try:
        # Check if order exists
        order = await db.fetch_one("SELECT id FROM sales WHERE id = $1", order_id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Orden con ID {order_id} no encontrada"
            )
        
        # Update shipping status
        await db.execute(
            "UPDATE sales SET shipping_status = $1, updated_at = CURRENT_TIMESTAMP WHERE id = $2",
            status_data.status,
            order_id
        )
        
        # Add to tracking history
        description = status_data.notes or f"Estado cambiado a: {status_data.status}"
        if status_data.tracking_number:
            description += f" | Tracking: {status_data.tracking_number}"
        
        await db.execute(
            """
            INSERT INTO sales_tracking_history (sale_id, status, description, created_at)
            VALUES ($1, $2, $3, CURRENT_TIMESTAMP)
            """,
            order_id,
            status_data.status,
            description
        )
        
        return {
            "message": "Estado de la orden actualizado exitosamente",
            "order_id": order_id,
            "new_status": status_data.status,
            "tracking_number": status_data.tracking_number
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating order status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar el estado de la orden: {str(e)}"
        )


# --- DASHBOARD STATISTICS ---

@router.get("/stats", dependencies=[Depends(require_admin)])
async def get_dashboard_stats():
    """
    Get dashboard statistics (admin only).
    
    Returns:
    - Total users (by role)
    - Total products (total and online)
    - Total orders (total, pending, this month)
    - Revenue (this month, total)
    
    Requires: Admin authentication
    """
    try:
        # User statistics
        total_users = await db.fetch_val("SELECT COUNT(*) FROM web_users")
        total_customers = await db.fetch_val("SELECT COUNT(*) FROM web_users WHERE role = 'customer'")
        total_admins = await db.fetch_val("SELECT COUNT(*) FROM web_users WHERE role = 'admin'")
        
        # Product statistics
        total_products = await db.fetch_val("SELECT COUNT(*) FROM products")
        products_online = await db.fetch_val("SELECT COUNT(*) FROM products WHERE en_tienda_online = TRUE")
        
        # Order statistics
        total_orders = await db.fetch_val("SELECT COUNT(*) FROM sales")
        orders_pending = await db.fetch_val(
            "SELECT COUNT(*) FROM sales WHERE status = 'Pendiente' OR shipping_status = 'pendiente'"
        )
        
        # Orders this month
        orders_this_month = await db.fetch_val(
            """
            SELECT COUNT(*) FROM sales 
            WHERE DATE_TRUNC('month', sale_date) = DATE_TRUNC('month', CURRENT_DATE)
            """
        )
        
        # Revenue statistics
        revenue_this_month = await db.fetch_val(
            """
            SELECT COALESCE(SUM(total), 0) FROM sales 
            WHERE DATE_TRUNC('month', sale_date) = DATE_TRUNC('month', CURRENT_DATE)
            """
        )
        
        revenue_total = await db.fetch_val("SELECT COALESCE(SUM(total), 0) FROM sales")
        
        return {
            "total_users": total_users or 0,
            "total_customers": total_customers or 0,
            "total_admins": total_admins or 0,
            "total_products": total_products or 0,
            "products_online": products_online or 0,
            "total_orders": total_orders or 0,
            "orders_pending": orders_pending or 0,
            "orders_this_month": orders_this_month or 0,
            "revenue_this_month": float(revenue_this_month or 0),
            "revenue_total": float(revenue_total or 0)
        }
        
    except Exception as e:
        logger.error(f"Error fetching dashboard stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener estadísticas: {str(e)}"
        )


# --- DISCOUNT MANAGEMENT ---

from models.discount_models import CreateGroupDiscount, DiscountResponse, UpdateDiscount

@router.post("/discounts/group", dependencies=[Depends(require_admin)])
async def create_group_discount(discount_data: CreateGroupDiscount):
    """
    Apply discount to a group of products (admin only).
    
    Request Body:
    - group_id: Group to apply discount to
    - discount_percentage: Discount percentage (0-100)
    - start_date: Optional start date
    - end_date: Optional end date
    - apply_to_children: Apply to subgroups as well
    
    Returns:
    - discount_id: ID of created discount
    - affected_products: Number of products affected
    
    Requires: Admin authentication
    """
    try:
        # Check if group exists
        group = await db.fetch_one("SELECT id, group_name FROM groups WHERE id = $1", discount_data.group_id)
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Grupo con ID {discount_data.group_id} no encontrado"
            )
        
        # Create discount record
        discount = await db.fetch_one(
            """
            INSERT INTO discounts (discount_type, target_id, target_name, discount_percentage, 
                                   start_date, end_date, apply_to_children, is_active)
            VALUES ('group', $1, $2, $3, $4, $5, $6, TRUE)
            RETURNING id
            """,
            discount_data.group_id,
            group['group_name'],
            discount_data.discount_percentage,
            discount_data.start_date,
            discount_data.end_date,
            discount_data.apply_to_children
        )
        
        # Find all products in the group (with recursive query if apply_to_children)
        if discount_data.apply_to_children:
            # Recursive query to get all child groups
            products_query = """
                WITH RECURSIVE group_tree AS (
                    SELECT id FROM groups WHERE id = $1
                    UNION ALL
                    SELECT g.id FROM groups g
                    INNER JOIN group_tree gt ON g.parent_group_id = gt.id
                )
                SELECT id, sale_price FROM products 
                WHERE group_id IN (SELECT id FROM group_tree)
            """
        else:
            products_query = "SELECT id, sale_price FROM products WHERE group_id = $1"
        
        products = await db.fetch_all(products_query, discount_data.group_id)
        
        # Apply discount to each product
        affected_count = 0
        for product in products:
            discount_amount = float(product['sale_price']) * (discount_data.discount_percentage / 100)
            new_price = float(product['sale_price']) - discount_amount
            
            await db.execute(
                """
                UPDATE products
                SET has_discount = 1,
                    discount_percentage = $1,
                    original_price = CASE WHEN has_discount = 0 THEN sale_price ELSE original_price END,
                    discount_amount = $2,
                    sale_price = $3,
                    last_modified_date = CURRENT_TIMESTAMP
                WHERE id = $4
                """,
                discount_data.discount_percentage,
                discount_amount,
                new_price,
                product['id']
            )
            affected_count += 1
        
        return {
            "message": "Descuento aplicado exitosamente",
            "discount_id": discount['id'],
            "affected_products": affected_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating group discount: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear descuento: {str(e)}"
        )


@router.get("/discounts", response_model=List[DiscountResponse], dependencies=[Depends(require_admin)])
async def get_all_discounts():
    """
    Get all discounts (admin only).
    
    Returns list of all discounts with affected product counts.
    
    Requires: Admin authentication
    """
    try:
        discounts = await db.fetch_all(
            """
            SELECT 
                d.id as discount_id,
                d.discount_type as type,
                d.target_id,
                COALESCE(d.target_name, p_name.product_name, 'Sin nombre') as target_name,
                d.discount_percentage,
                d.start_date,
                d.end_date,
                d.is_active,
                d.created_at,
                CASE 
                    WHEN d.discount_type = 'product' THEN 1
                    ELSE COUNT(DISTINCT p.id)
                END as affected_products
            FROM discounts d
            LEFT JOIN products p_name ON d.discount_type = 'product' AND d.target_id = p_name.id
            LEFT JOIN products p ON (
                d.discount_type = 'group' AND p.group_id = d.target_id
            )
            GROUP BY d.id, d.discount_type, d.target_id, d.target_name, p_name.product_name, d.discount_percentage,
                     d.start_date, d.end_date, d.is_active, d.created_at
            ORDER BY d.created_at DESC
            """
        )
        
        return discounts
        
    except Exception as e:
        logger.error(f"Error fetching discounts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener descuentos: {str(e)}"
        )


@router.patch("/discounts/{discount_id}", dependencies=[Depends(require_admin)])
async def update_discount(discount_id: int, update_data: UpdateDiscount):
    """
    Update a discount (admin only).
    
    Path Parameters:
    - discount_id: ID of the discount to update
    
    Request Body:
    - discount_percentage: New percentage (optional)
    - end_date: New end date (optional)
    - is_active: Activate/pause discount (optional)
    
    Requires: Admin authentication
    """
    try:
        # Check if discount exists
        discount = await db.fetch_one("SELECT id, target_id, discount_type FROM discounts WHERE id = $1", discount_id)
        if not discount:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Descuento con ID {discount_id} no encontrado"
            )
        
        # Build update query
        update_fields = []
        params = []
        param_count = 1
        
        if update_data.discount_percentage is not None:
            update_fields.append(f"discount_percentage = ${param_count}")
            params.append(update_data.discount_percentage)
            param_count += 1
        
        if update_data.end_date is not None:
            update_fields.append(f"end_date = ${param_count}")
            params.append(update_data.end_date)
            param_count += 1
        
        if update_data.is_active is not None:
            update_fields.append(f"is_active = ${param_count}")
            params.append(update_data.is_active)
            param_count += 1
        
        if not update_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No hay campos para actualizar"
            )
        
        update_fields.append("updated_at = CURRENT_TIMESTAMP")
        params.append(discount_id)
        
        await db.execute(
            f"UPDATE discounts SET {', '.join(update_fields)} WHERE id = ${param_count}",
            *params
        )
        
        # If percentage changed, recalculate affected products
        if update_data.discount_percentage is not None:
            # Get affected products
            if discount['discount_type'] == 'group':
                products = await db.fetch_all(
                    "SELECT id, original_price FROM products WHERE group_id = $1 AND has_discount = 1",
                    discount['target_id']
                )
            else:
                products = await db.fetch_all(
                    "SELECT id, original_price FROM products WHERE id = $1 AND has_discount = 1",
                    discount['target_id']
                )
            
            # Recalculate prices
            for product in products:
                discount_amount = float(product['original_price']) * (update_data.discount_percentage / 100)
                new_price = float(product['original_price']) - discount_amount
                
                await db.execute(
                    """
                    UPDATE products
                    SET discount_percentage = $1,
                        discount_amount = $2,
                        sale_price = $3,
                        last_modified_date = CURRENT_TIMESTAMP
                    WHERE id = $4
                    """,
                    update_data.discount_percentage,
                    discount_amount,
                    new_price,
                    product['id']
                )
        
        return {"message": "Descuento actualizado exitosamente", "discount_id": discount_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating discount: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar descuento: {str(e)}"
        )


@router.delete("/discounts/{discount_id}", dependencies=[Depends(require_admin)])
async def delete_discount(discount_id: int):
    """
    Delete a discount and restore original prices (admin only).
    
    Path Parameters:
    - discount_id: ID of the discount to delete
    
    Requires: Admin authentication
    """
    try:
        # Check if discount exists
        discount = await db.fetch_one(
            "SELECT id, target_id, discount_type FROM discounts WHERE id = $1",
            discount_id
        )
        if not discount:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Descuento con ID {discount_id} no encontrado"
            )
        
        # Get affected products
        if discount['discount_type'] == 'group':
            products = await db.fetch_all(
                "SELECT id FROM products WHERE group_id = $1 AND has_discount = 1",
                discount['target_id']
            )
        else:
            products = await db.fetch_all(
                "SELECT id FROM products WHERE id = $1 AND has_discount = 1",
                discount['target_id']
            )
        
        # Restore original prices
        for product in products:
            await db.execute(
                """
                UPDATE products
                SET has_discount = 0,
                    discount_percentage = 0,
                    discount_amount = 0,
                    sale_price = original_price,
                    last_modified_date = CURRENT_TIMESTAMP
                WHERE id = $1
                """,
                product['id']
            )
        
        # Delete discount record
        await db.execute("DELETE FROM discounts WHERE id = $1", discount_id)
        
        return {
            "message": "Descuento eliminado y precios restaurados exitosamente",
            "discount_id": discount_id,
            "products_restored": len(products)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting discount: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar descuento: {str(e)}"
        )
