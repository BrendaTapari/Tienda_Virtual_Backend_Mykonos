"""
Products API routes - handles all product-related endpoints.
Uses PostgreSQL database for data persistence.
"""

from fastapi import APIRouter, HTTPException, status
from typing import List, Optional
from config.db_connection import db
from models.product_models import (
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    ProductSimple
)
import logging

logger = logging.getLogger(__name__)

# Create the router
router = APIRouter()


# --- ROUTES ---

@router.get("/", response_model=List[ProductSimple])
async def get_products(
    category: Optional[str] = None,
    state: Optional[str] = None,
    limit: Optional[int] = 100,
    offset: Optional[int] = 0
):
    """
    Get all products from the database.
    
    Query Parameters:
    - category: Filter by product group name (optional)
    - state: Filter by product state (optional)
    - limit: Maximum number of products to return (default: 100)
    - offset: Number of products to skip (default: 0)
    """
    try:
        # Build the query dynamically based on filters
        query = """
            SELECT 
                p.id,
                p.product_name as name,
                p.sale_price as price,
                p.description,
                COALESCE(p.comments, '') as image,
                COALESCE(g.group_name, 'Sin categoría') as category
            FROM products p
            LEFT JOIN groups g ON p.group_id = g.id
            WHERE 1=1
        """
        params = []
        param_count = 1
        
        if state:
            query += f" AND p.state = ${param_count}"
            params.append(state)
            param_count += 1
        
        if category:
            query += f" AND g.group_name ILIKE ${param_count}"
            params.append(f"%{category}%")
            param_count += 1
        
        query += f" ORDER BY p.id DESC LIMIT ${param_count} OFFSET ${param_count + 1}"
        params.extend([limit, offset])
        
        products = await db.fetch_all(query, *params)
        
        return products
        
    except Exception as e:
        logger.error(f"Error fetching products: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener productos: {str(e)}"
        )


@router.get("/{product_id}", response_model=ProductSimple)
async def get_product(product_id: int):
    """
    Get a specific product by ID.
    
    Path Parameters:
    - product_id: The ID of the product to retrieve
    """
    try:
        query = """
            SELECT 
                p.id,
                p.product_name as name,
                p.sale_price as price,
                p.description,
                COALESCE(p.comments, '') as image,
                COALESCE(g.group_name, 'Sin categoría') as category
            FROM products p
            LEFT JOIN groups g ON p.group_id = g.id
            WHERE p.id = $1
        """
        
        product = await db.fetch_one(query, product_id)
        
        if product is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Producto con ID {product_id} no encontrado"
            )
        
        return product
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching product {product_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener el producto: {str(e)}"
        )


@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(product: ProductCreate):
    """
    Create a new product in the database.
    
    Request Body:
    - ProductCreate model with all product details
    """
    try:
        query = """
            INSERT INTO products (
                product_name, description, cost, sale_price, provider_code,
                group_id, provider_id, brand_id, tax, discount,
                original_price, discount_percentage, discount_amount,
                has_discount, comments, state, creation_date
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, CURRENT_TIMESTAMP)
            RETURNING id, product_name, description, cost, sale_price, provider_code,
                      group_id, provider_id, brand_id, tax, discount,
                      original_price, discount_percentage, discount_amount,
                      has_discount, comments, state, creation_date
        """
        
        result = await db.fetch_one(
            query,
            product.product_name,
            product.description,
            product.cost,
            product.sale_price,
            product.provider_code,
            product.group_id,
            product.provider_id,
            product.brand_id,
            product.tax,
            product.discount,
            product.original_price,
            product.discount_percentage,
            product.discount_amount,
            product.has_discount,
            product.comments,
            product.state
        )
        
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al crear el producto"
            )
        
        return result
        
    except Exception as e:
        logger.error(f"Error creating product: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear el producto: {str(e)}"
        )


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(product_id: int, product: ProductUpdate):
    """
    Update an existing product.
    
    Path Parameters:
    - product_id: The ID of the product to update
    
    Request Body:
    - ProductUpdate model with fields to update (all optional)
    """
    try:
        # First, check if product exists
        existing = await db.fetch_one("SELECT id FROM products WHERE id = $1", product_id)
        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Producto con ID {product_id} no encontrado"
            )
        
        # Build dynamic update query based on provided fields
        update_fields = []
        params = []
        param_count = 1
        
        for field, value in product.dict(exclude_unset=True).items():
            update_fields.append(f"{field} = ${param_count}")
            params.append(value)
            param_count += 1
        
        if not update_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se proporcionaron campos para actualizar"
            )
        
        # Add last_modified_date
        update_fields.append(f"last_modified_date = CURRENT_TIMESTAMP")
        
        # Add product_id as the last parameter
        params.append(product_id)
        
        query = f"""
            UPDATE products
            SET {', '.join(update_fields)}
            WHERE id = ${param_count}
            RETURNING id, product_name, description, cost, sale_price, provider_code,
                      group_id, provider_id, brand_id, tax, discount,
                      original_price, discount_percentage, discount_amount,
                      has_discount, comments, state, creation_date, last_modified_date
        """
        
        result = await db.fetch_one(query, *params)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating product {product_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar el producto: {str(e)}"
        )


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(product_id: int):
    """
    Delete a product from the database.
    
    Path Parameters:
    - product_id: The ID of the product to delete
    """
    try:
        # Check if product exists
        existing = await db.fetch_one("SELECT id FROM products WHERE id = $1", product_id)
        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Producto con ID {product_id} no encontrado"
            )
        
        # Delete the product
        await db.execute("DELETE FROM products WHERE id = $1", product_id)
        
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting product {product_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar el producto: {str(e)}"
        )