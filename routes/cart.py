"""
Shopping cart routes for managing user carts and checkout.
"""

from fastapi import APIRouter, HTTPException, status, Depends, Header
from typing import Optional
from config.db_connection import db
from models.cart_models import (
    CartResponse,
    CartItemResponse,
    AddToCartRequest,
    UpdateCartItemRequest,
    CheckoutRequest
)
from utils.auth import get_current_web_user
import logging

logger = logging.getLogger(__name__)

# Create the router
router = APIRouter()


@router.get("/", response_model=CartResponse)
async def get_cart(authorization: Optional[str] = Header(None)):
    """
    Get current user's shopping cart.
    
    Creates a new cart if user doesn't have one.
    Returns cart with all items, including product details and stock availability.
    
    Requires: User authentication
    """
    try:
        user = await get_current_web_user(authorization)
        user_id = user['id']
        
        # Get or create cart
        cart = await db.fetch_one(
            "SELECT id, user_id, created_at FROM web_carts WHERE user_id = $1",
            user_id
        )
        
        if not cart:
            # Create new cart
            cart = await db.fetch_one(
                """
                INSERT INTO web_carts (user_id, created_at)
                VALUES ($1, CURRENT_TIMESTAMP)
                RETURNING id, user_id, created_at
                """,
                user_id
            )
        
        # Get cart items with product details
        items = await db.fetch_all(
            """
            SELECT 
                wci.id as cart_item_id,
                wci.product_id,
                p.nombre_web as product_name,
                i.image_url as product_image,
                wci.variant_id,
                s.size_name,
                c.color_name,
                wci.quantity,
                p.precio_web as unit_price,
                (wci.quantity * p.precio_web) as subtotal,
                COALESCE(wsv.quantity, 0) as stock_available
            FROM web_cart_items wci
            INNER JOIN products p ON wci.product_id = p.id
            LEFT JOIN warehouse_stock_variants wsv ON wci.variant_id = wsv.id
            LEFT JOIN sizes s ON wsv.size_id = s.id
            LEFT JOIN colors c ON wsv.color_id = c.id
            LEFT JOIN LATERAL (
                SELECT image_url FROM images WHERE product_id = p.id LIMIT 1
            ) i ON TRUE
            WHERE wci.cart_id = $1
            ORDER BY wci.created_at DESC
            """,
            cart['id']
        )
        
        # Calculate totals
        total_items = sum(item['quantity'] for item in items)
        subtotal = sum(item['subtotal'] for item in items)
        
        return {
            "cart_id": cart['id'],
            "user_id": cart['user_id'],
            "items": [dict(item) for item in items],
            "total_items": total_items,
            "subtotal": float(subtotal),
            "created_at": cart['created_at'],
            "updated_at": None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting cart: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener el carrito: {str(e)}"
        )


@router.post("/items")
async def add_to_cart(item_data: AddToCartRequest, authorization: Optional[str] = Header(None)):
    """
    Add a product to the cart.
    
    Validations:
    - Product must exist and be online (en_tienda_online = TRUE)
    - Variant must exist
    - Sufficient stock must be available
    - If item already exists, quantity is updated
    
    Requires: User authentication
    """
    try:
        user = await get_current_web_user(authorization)
        user_id = user['id']
        
        # Validate product exists and is online
        product = await db.fetch_one(
            """
            SELECT id, nombre_web, precio_web, en_tienda_online
            FROM products
            WHERE id = $1
            """,
            item_data.product_id
        )
        
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Producto no encontrado"
            )
        
        if not product['en_tienda_online']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Este producto no está disponible en la tienda online"
            )
        
        # Validate variant exists and has stock
        variant = await db.fetch_one(
            """
            SELECT id, quantity as stock_available
            FROM warehouse_stock_variants
            WHERE id = $1 AND product_id = $2
            """,
            item_data.variant_id,
            item_data.product_id
        )
        
        if not variant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Variante de producto no encontrada"
            )
        
        if variant['stock_available'] < item_data.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Stock insuficiente. Disponible: {variant['stock_available']}"
            )
        
        # Get or create cart
        cart = await db.fetch_one(
            "SELECT id FROM web_carts WHERE user_id = $1",
            user_id
        )
        
        if not cart:
            cart = await db.fetch_one(
                """
                INSERT INTO web_carts (user_id, created_at)
                VALUES ($1, CURRENT_TIMESTAMP)
                RETURNING id
                """,
                user_id
            )
        
        # Check if item already exists in cart
        existing_item = await db.fetch_one(
            """
            SELECT id, quantity
            FROM web_cart_items
            WHERE cart_id = $1 AND product_id = $2 AND variant_id = $3
            """,
            cart['id'],
            item_data.product_id,
            item_data.variant_id
        )
        
        if existing_item:
            # Update quantity
            new_quantity = existing_item['quantity'] + item_data.quantity
            
            if variant['stock_available'] < new_quantity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Stock insuficiente. Ya tienes {existing_item['quantity']} en el carrito. Disponible: {variant['stock_available']}"
                )
            
            cart_item = await db.fetch_one(
                """
                UPDATE web_cart_items
                SET quantity = $1
                WHERE id = $2
                RETURNING id, product_id, variant_id, quantity
                """,
                new_quantity,
                existing_item['id']
            )
        else:
            # Add new item
            cart_item = await db.fetch_one(
                """
                INSERT INTO web_cart_items (cart_id, product_id, variant_id, quantity, created_at)
                VALUES ($1, $2, $3, $4, CURRENT_TIMESTAMP)
                RETURNING id, product_id, variant_id, quantity
                """,
                cart['id'],
                item_data.product_id,
                item_data.variant_id,
                item_data.quantity
            )
        
        return {
            "message": "Producto agregado al carrito",
            "cart_item": {
                "cart_item_id": cart_item['id'],
                "product_id": cart_item['product_id'],
                "variant_id": cart_item['variant_id'],
                "quantity": cart_item['quantity'],
                "unit_price": float(product['precio_web'])
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding to cart: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al agregar al carrito: {str(e)}"
        )


@router.patch("/items/{cart_item_id}")
async def update_cart_item(
    cart_item_id: int,
    update_data: UpdateCartItemRequest,
    authorization: Optional[str] = Header(None)
):
    """
    Update the quantity of a cart item.
    
    Validations:
    - Item must belong to user's cart
    - Sufficient stock must be available
    
    Requires: User authentication
    """
    try:
        user = await get_current_web_user(authorization)
        user_id = user['id']
        
        # Verify item belongs to user's cart
        item = await db.fetch_one(
            """
            SELECT wci.id, wci.variant_id, wci.product_id, p.precio_web
            FROM web_cart_items wci
            INNER JOIN web_carts wc ON wci.cart_id = wc.id
            INNER JOIN products p ON wci.product_id = p.id
            WHERE wci.id = $1 AND wc.user_id = $2
            """,
            cart_item_id,
            user_id
        )
        
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item no encontrado en tu carrito"
            )
        
        # Check stock
        variant = await db.fetch_one(
            "SELECT quantity as stock_available FROM warehouse_stock_variants WHERE id = $1",
            item['variant_id']
        )
        
        if not variant or variant['stock_available'] < update_data.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Stock insuficiente. Disponible: {variant['stock_available'] if variant else 0}"
            )
        
        # Update quantity
        updated_item = await db.fetch_one(
            """
            UPDATE web_cart_items
            SET quantity = $1
            WHERE id = $2
            RETURNING id, quantity
            """,
            update_data.quantity,
            cart_item_id
        )
        
        subtotal = update_data.quantity * float(item['precio_web'])
        
        return {
            "message": "Cantidad actualizada",
            "cart_item": {
                "cart_item_id": updated_item['id'],
                "quantity": updated_item['quantity'],
                "subtotal": subtotal
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating cart item: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar el item: {str(e)}"
        )


@router.delete("/items/{cart_item_id}")
async def remove_cart_item(cart_item_id: int, authorization: Optional[str] = Header(None)):
    """
    Remove an item from the cart.
    
    Requires: User authentication
    """
    try:
        user = await get_current_web_user(authorization)
        user_id = user['id']
        
        # Verify item belongs to user's cart and delete
        result = await db.execute(
            """
            DELETE FROM web_cart_items
            WHERE id = $1 AND cart_id IN (
                SELECT id FROM web_carts WHERE user_id = $2
            )
            """,
            cart_item_id,
            user_id
        )
        
        if result == "DELETE 0":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item no encontrado en tu carrito"
            )
        
        return {"message": "Producto eliminado del carrito"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing cart item: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar el item: {str(e)}"
        )


@router.delete("/")
async def clear_cart(authorization: Optional[str] = Header(None)):
    """
    Clear all items from the cart.
    
    Requires: User authentication
    """
    try:
        user = await get_current_web_user(authorization)
        user_id = user['id']
        
        # Delete all items from user's cart
        await db.execute(
            """
            DELETE FROM web_cart_items
            WHERE cart_id IN (
                SELECT id FROM web_carts WHERE user_id = $1
            )
            """,
            user_id
        )
        
        return {"message": "Carrito vaciado exitosamente"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clearing cart: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al vaciar el carrito: {str(e)}"
        )
