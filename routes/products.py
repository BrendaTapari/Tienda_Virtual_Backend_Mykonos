"""
Products API routes - handles all product-related endpoints.
Uses PostgreSQL database for data persistence.
"""

from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import List, Optional
from config.db_connection import db
from models.product_models import (
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    ProductSimple,
    ProductWithImages,
    OnlineStoreProduct,
    ProductImage,
    AddProductImage,
    ProductDetail,
    ProductAllResponse,
    ToggleOnlineRequest,
    ProductInfoMatrix
)
from schemas.product_schemas import (
    StockSucursalInput,
    VarianteUpdateInput,
    ProductoUpdateSchema
)
import logging
from utils.auth import require_admin
import base64
from models.imageUpload import ImageUpload
from models.imageResponse import ImageResponse
from datetime import datetime
import os
from sqlalchemy.orm import Session
import uuid
logger = logging.getLogger(__name__)

# Create the router
router = APIRouter()
IMAGES_DIR = "/home/breightend/imagenes-productos"
IMAGES_BASE_URL = "/static/productos"


@router.get("/info-matrix", response_model=List[ProductInfoMatrix], dependencies=[Depends(require_admin)])
async def get_products_info_matrix():
    """
    Get a matrix of product information: Name, Web Price, Discount, Stock, Group, Provider.
    
    Returns:
    - List of products with specific fields for the info matrix view.
    """
    try:
        query = """
            SELECT 
                p.id,
                p.product_name,
                p.precio_web,
                p.discount_percentage as discount,
                COALESCE(SUM(wv.displayed_stock), 0) as stock,
                g.group_name as group,
                e.entity_name as provider
            FROM products p
            LEFT JOIN groups g ON p.group_id = g.id
            LEFT JOIN entities e ON p.provider_id = e.id
            LEFT JOIN web_variants wv ON wv.product_id = p.id AND wv.is_active = TRUE
            GROUP BY p.id, g.group_name, e.entity_name
            ORDER BY p.id DESC
        """
        
        products = await db.fetch_all(query)
        return products
        
    except Exception as e:
        logger.error(f"Error fetching product info matrix: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener la matriz de información: {str(e)}"
        )


@router.get("/all", response_model=List[ProductAllResponse], dependencies=[Depends(require_admin)])
async def get_all_products_admin(provider_code: Optional[str] = None):
    """
    Get ALL products from the database (admin only).
    Not filtered by en_tienda_online - returns everything.
    
    Query Parameters:
    - provider_code: Optional filter by barcode/provider code
    
    Requires: Admin authentication
    """
    try:
        query = """
            SELECT 
                id,
                product_name,
                provider_code,
                sale_price,
                en_tienda_online,
                group_id,
                description
            FROM products
        """
        params = []
        
        if provider_code:
            query += " WHERE provider_code ILIKE $1"
            params.append(f"%{provider_code}%")
        
        query += " ORDER BY id DESC"
        
        products = await db.fetch_all(query, *params) if params else await db.fetch_all(query)
        
        return products
        
    except Exception as e:
        logger.error(f"Error fetching all products (admin): {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener todos los productos: {str(e)}"
        )


@router.patch("/{product_id}/toggle-online", response_model=ProductResponse, dependencies=[Depends(require_admin)])
async def toggle_product_online(product_id: int, toggle_data: ToggleOnlineRequest):
    """
    Activate or deactivate a product in the online store (admin only).
    
    Path Parameters:
    - product_id: The ID of the product to toggle
    
    Request Body:
    - en_tienda_online: true to activate, false to deactivate
    - nombre_web: Product name for web (optional, uses product_name if not provided)
    - descripcion_web: Product description for web (optional, uses description if not provided)
    - precio_web: Price for web (optional but recommended when activating)
    - slug: URL slug (optional, auto-generated from nombre_web if not provided)
    
    Validations:
    - Product must exist
    - When activating (en_tienda_online=true), nombre_web and precio_web should be set
    - Slug must be unique
    
    Requires: Admin authentication
    """
    try:
        # Check if product exists
        existing = await db.fetch_one(
            "SELECT id, product_name, description, sale_price FROM products WHERE id = $1", 
            product_id
        )
        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Producto con ID {product_id} no encontrado"
            )
        
        # Prepare update fields
        update_fields = ["en_tienda_online = $1"]
        params = [toggle_data.en_tienda_online]
        param_count = 2
        
        # If activating, ensure required fields are set
        if toggle_data.en_tienda_online:
            # Use provided nombre_web or fallback to product_name
            nombre_web = toggle_data.nombre_web or existing['product_name']
            update_fields.append(f"nombre_web = ${param_count}")
            params.append(nombre_web)
            param_count += 1
            
            # Use provided descripcion_web or fallback to description
            descripcion_web = toggle_data.descripcion_web or existing['description']
            update_fields.append(f"descripcion_web = ${param_count}")
            params.append(descripcion_web)
            param_count += 1
            
            # Use provided precio_web or fallback to sale_price
            precio_web = toggle_data.precio_web or existing['sale_price']
            update_fields.append(f"precio_web = ${param_count}")
            params.append(precio_web)
            param_count += 1
            
            # Generate or use provided slug
            if toggle_data.slug:
                slug = toggle_data.slug
            else:
                # Auto-generate slug from nombre_web
                import re
                slug = re.sub(r'[^a-z0-9]+', '-', nombre_web.lower()).strip('-')
                slug = f"{slug}-{product_id}"  # Add ID to ensure uniqueness
            
            # Check slug uniqueness
            existing_slug = await db.fetch_one(
                "SELECT id FROM products WHERE slug = $1 AND id != $2",
                slug,
                product_id
            )
            if existing_slug:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El slug '{slug}' ya está en uso por otro producto"
                )
            
            update_fields.append(f"slug = ${param_count}")
            params.append(slug)
            param_count += 1
        else:
            # When deactivating, optionally update fields if provided
            if toggle_data.nombre_web is not None:
                update_fields.append(f"nombre_web = ${param_count}")
                params.append(toggle_data.nombre_web)
                param_count += 1
            
            if toggle_data.descripcion_web is not None:
                update_fields.append(f"descripcion_web = ${param_count}")
                params.append(toggle_data.descripcion_web)
                param_count += 1
            
            if toggle_data.precio_web is not None:
                update_fields.append(f"precio_web = ${param_count}")
                params.append(toggle_data.precio_web)
                param_count += 1
            
            if toggle_data.slug is not None:
                update_fields.append(f"slug = ${param_count}")
                params.append(toggle_data.slug)
                param_count += 1
        
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
                      has_discount, comments, state, 
                      en_tienda_online, nombre_web, descripcion_web, slug, precio_web,
                      creation_date, last_modified_date
        """
        
        result = await db.fetch_one(query, *params)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling product {product_id} online status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al cambiar el estado del producto: {str(e)}"
        )


@router.patch("/{product_id}/web-price", dependencies=[Depends(require_admin)])
async def update_product_web_price(product_id: int, precio_web: float):
    """
    Quick update of product web price (admin only).
    
    Path Parameters:
    - product_id: The ID of the product
    
    Query Parameters:
    - precio_web: New web price
    
    Requires: Admin authentication
    """
    try:
        # Check if product exists
        existing = await db.fetch_one(
            "SELECT id, nombre_web FROM products WHERE id = $1",
            product_id
        )
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Producto con ID {product_id} no encontrado"
            )
        
        # Update web price
        result = await db.fetch_one(
            """
            UPDATE products
            SET precio_web = $1, last_modified_date = CURRENT_TIMESTAMP
            WHERE id = $2
            RETURNING id, nombre_web, precio_web
            """,
            precio_web,
            product_id
        )
        
        return {
            "id": result['id'],
            "nombre_web": result['nombre_web'],
            "precio_web": result['precio_web'],
            "message": "Precio actualizado exitosamente"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating product web price: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar el precio: {str(e)}"
        )


@router.patch("/{product_id}/discount", dependencies=[Depends(require_admin)])
async def apply_product_discount(
    product_id: int,
    has_discount: int,
    discount_percentage: Optional[float] = None,
    original_price: Optional[float] = None
):
    """
    Apply or remove discount on a specific product (admin only).
    
    Path Parameters:
    - product_id: The ID of the product
    
    Query Parameters:
    - has_discount: 1 to apply discount, 0 to remove
    - discount_percentage: Discount percentage (required if has_discount=1)
    - original_price: Original price (auto-calculated if not provided)
    
    Behavior:
    - When applying discount (has_discount=1):
      - Stores current sale_price as original_price if not already set
      - Calculates discount_amount and new sale_price
    - When removing discount (has_discount=0):
      - Restores original_price to sale_price
      - Clears discount fields
    
    Requires: Admin authentication
    """
    try:
        # Check if product exists
        product = await db.fetch_one(
            "SELECT id, sale_price, original_price, has_discount FROM products WHERE id = $1",
            product_id
        )
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Producto con ID {product_id} no encontrado"
            )
        
        if has_discount == 1:
            # Applying discount
            if discount_percentage is None or discount_percentage <= 0 or discount_percentage >= 100:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="El porcentaje de descuento debe estar entre 0 y 100"
                )
            
            # Determine original price
            if original_price is None:
                # Use existing original_price if product already has discount, otherwise use current sale_price
                if product['has_discount'] == 1 and product['original_price']:
                    original_price = product['original_price']
                else:
                    original_price = product['sale_price']
            
            # Calculate discount amount and new price
            # Ensure calculations are done with floats to avoid potential Decimal issues if not explicitly handled
            discount_amount = float(original_price) * (discount_percentage / 100)
            new_sale_price = float(original_price) - discount_amount
            
            # Update product
            result = await db.fetch_one(
                """
                UPDATE products
                SET has_discount = 1,
                    discount_percentage = $1,
                    original_price = $2,
                    discount_amount = $3,
                    sale_price = $4,
                    last_modified_date = CURRENT_TIMESTAMP
                WHERE id = $5
                RETURNING id, product_name, sale_price, original_price, discount_percentage, discount_amount, has_discount
                """,
                discount_percentage,
                original_price,
                discount_amount,
                new_sale_price,
                product_id
            )
            
            return {
                "id": result['id'],
                "product_name": result['product_name'],
                "original_price": result['original_price'],
                "discount_percentage": result['discount_percentage'],
                "discount_amount": result['discount_amount'],
                "sale_price": result['sale_price'],
                "has_discount": result['has_discount'],
                "message": f"Descuento del {discount_percentage}% aplicado exitosamente"
            }
        
        else:
            # Removing discount
            if not product['original_price']:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="El producto no tiene descuento aplicado"
                )
            
            # Restore original price
            result = await db.fetch_one(
                """
                UPDATE products
                SET has_discount = 0,
                    discount_percentage = 0,
                    discount_amount = 0,
                    sale_price = original_price,
                    last_modified_date = CURRENT_TIMESTAMP
                WHERE id = $1
                RETURNING id, product_name, sale_price, has_discount
                """,
                product_id
            )
            
            return {
                "id": result['id'],
                "product_name": result['product_name'],
                "sale_price": result['sale_price'],
                "has_discount": result['has_discount'],
                "message": "Descuento removido exitosamente, precio restaurado"
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error applying product discount: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al aplicar descuento: {str(e)}"
        )

from fastapi import UploadFile, File, Form
from typing import List, Optional
import os
import uuid

@router.post("/{product_id}/images", response_model=ImageResponse)
async def add_product_image(
    product_id: int,
    image: ImageUpload,
    current_user: dict = Depends(require_admin)
):
    """
    Agrega una imagen a un producto.
    
    - **product_id**: ID del producto
    - **image_data**: Imagen codificada en base64
    - **filename**: Nombre original del archivo
    
    Returns: Objeto con id e image_url
    """
    try:
        # Verificar que el producto existe
        product = await db.fetch_one(
            "SELECT id FROM products WHERE id = $1", product_id
        )
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Producto {product_id} no encontrado"
            )
        
        # Decodificar base64
        try:
            image_bytes = base64.b64decode(image.image_data)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Imagen base64 inválida"
            )
        
        # Validar tamaño (opcional, máximo 5MB)
        if len(image_bytes) > 5 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Imagen muy grande (máximo 5MB)"
            )
        
        # Generar nombre único para la imagen
        file_extension = os.path.splitext(image.filename)[1].lower()
        # Validar extensión
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.webp']
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Extensión no permitida. Use: {', '.join(allowed_extensions)}"
            )
        
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(IMAGES_DIR, unique_filename)
        
        # Crear directorio si no existe
        os.makedirs(IMAGES_DIR, exist_ok=True)
        
        # Guardar imagen
        with open(file_path, "wb") as f:
            f.write(image_bytes)
        
        # URL para el frontend
        image_url = f"{IMAGES_BASE_URL}/{unique_filename}"
        
        # Insertar en la base de datos
        # Insertar en la base de datos
        # Nota: image_data es BLOB NOT NULL en la base de datos legacy, insertamos bytes vacíos
        # ya que ahora guardamos el archivo en disco y usamos image_url.
        result = await db.fetch_one(
            """
            INSERT INTO images (image_url, product_id, image_data)
            VALUES ($1, $2, $3)
            RETURNING id, image_url
            """,
            image_url, product_id, b''  # Empty bytes for legacy BLOB column
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al subir imagen: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al guardar la imagen: {str(e)}"
        )


### Endpoint: DELETE /products/{product_id}/images/{image_id}
@router.delete("/{product_id}/images/{image_id}")
async def delete_product_image(
    product_id: int,
    image_id: int,
    current_user: dict = Depends(require_admin)
):
    """
    Elimina una imagen de un producto.
    
    - **product_id**: ID del producto
    - **image_id**: ID de la imagen a eliminar
    
    Returns: Mensaje de confirmación
    """
    try:
        # Obtener la imagen
        image = await db.fetch_one(
            """
            SELECT id, image_url FROM images 
            WHERE id = $1 AND product_id = $2
            """,
            image_id, product_id
        )
        
        if not image:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Imagen no encontrada"
            )
        
        # Extraer nombre de archivo de la URL
        filename = image["image_url"].split("/")[-1]
        file_path = os.path.join(IMAGES_DIR, filename)
        
        # Eliminar archivo físico si existe
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                logger.warning(f"No se pudo eliminar archivo físico: {e}")
        
        # Eliminar de la base de datos
        await db.execute(
            "DELETE FROM images WHERE id = $1",
            image_id
        )
        
        return {"message": "Imagen eliminada correctamente"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al eliminar imagen: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar la imagen: {str(e)}"
        )


### Endpoint: GET /products/{product_id}/images

@router.get("/{product_id}/images", response_model=list[ImageResponse])
async def get_product_images(product_id: int):
    """
    Obtiene todas las imágenes de un producto.
    
    - **product_id**: ID del producto
    
    Returns: Lista de objetos con id e image_url
    """
    try:
        images = await db.fetch_all(
            """
            SELECT id, image_url 
            FROM images 
            WHERE product_id = $1 
            ORDER BY id DESC
            """,
            product_id
        )
        return images
    except Exception as e:
        logger.error(f"Error al obtener imágenes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener imágenes: {str(e)}"
        )


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(product_id: int, payload: ProductoUpdateSchema):
    try:
        # 1. Verificar si el producto existe
        existing = await db.fetch_one("SELECT id FROM products WHERE id = $1", product_id)
        if not existing:
            raise HTTPException(status_code=404, detail=f"Producto con ID {product_id} no encontrado")

        async with await db.transaction() as conn:
            # 2. Actualizar Info General del Producto
            updated_product = dict(await conn.fetchrow(
                """
                UPDATE products 
                SET nombre_web = $1,
                    descripcion_web = $2,
                    precio_web = $3,
                    en_tienda_online = $4,
                    last_modified_date = CURRENT_TIMESTAMP
                WHERE id = $5
                RETURNING id, product_name, description, cost, sale_price, provider_code,
                          group_id, provider_id, brand_id, tax, discount,
                          original_price, discount_percentage, discount_amount,
                          has_discount, comments, state, 
                          en_tienda_online, nombre_web, descripcion_web, slug, precio_web,
                          creation_date, last_modified_date, user_id
                """,
                payload.nombre,
                payload.descripcion,
                payload.precio_web,
                payload.en_tienda_online,
                product_id
            ))

            # 3. Procesar las Variantes
            for var_input in payload.variantes:
                # 3.1. Verificar que la variante existe y pertenece al producto
                variant_exists = await conn.fetchval(
                    """
                    SELECT id FROM web_variants 
                    WHERE id = $1 AND product_id = $2
                    """,
                    var_input.id,
                    product_id
                )
                
                if not variant_exists:
                    logger.warning(f"Variante {var_input.id} no encontrada para producto {product_id}, saltando...")
                    continue
                
                # 3.2. Calcular el stock total web desde configuracion_stock
                total_stock_web = sum(
                    asignacion.cantidad_asignada 
                    for asignacion in var_input.configuracion_stock
                )
                
                # 3.3. Actualizar web_variants (stock total)
                await conn.execute(
                    """
                    UPDATE web_variants
                    SET is_active = $1,
                        displayed_stock = $2
                    WHERE id = $3 AND product_id = $4
                    """,
                    var_input.mostrar_en_web,
                    total_stock_web,
                    var_input.id,
                    product_id
                )
                
                # 3.4. NUEVO: Limpiar asignaciones anteriores de esta variante
                await conn.execute(
                    """
                    DELETE FROM web_variant_branch_assignment
                    WHERE variant_id = $1
                    """,
                    var_input.id
                )
                
                # 3.5. NUEVO: Insertar nuevas asignaciones por sucursal
                for asignacion in var_input.configuracion_stock:
                    if asignacion.cantidad_asignada > 0:
                        # Validar que la cantidad asignada no exceda el stock físico
                        stock_fisico = await conn.fetchval(
                            """
                            SELECT COALESCE(quantity, 0)
                            FROM warehouse_stock_variants wsv
                            JOIN web_variants wv ON wv.product_id = wsv.product_id 
                                AND wv.size_id = wsv.size_id 
                                AND wv.color_id = wsv.color_id
                            WHERE wv.id = $1 AND wsv.branch_id = $2
                            """,
                            var_input.id,
                            asignacion.sucursal_id
                        ) or 0
                        
                        if asignacion.cantidad_asignada > stock_fisico:
                            logger.warning(
                                f"Asignación web ({asignacion.cantidad_asignada}) excede stock físico ({stock_fisico}) "
                                f"para variante {var_input.id} en sucursal {asignacion.sucursal_id}. "
                                f"Ajustando a {stock_fisico}"
                            )
                            asignacion.cantidad_asignada = stock_fisico
                        
                        # Insertar asignación
                        await conn.execute(
                            """
                            INSERT INTO web_variant_branch_assignment 
                                (variant_id, branch_id, cantidad_asignada, updated_at)
                            VALUES ($1, $2, $3, CURRENT_TIMESTAMP)
                            """,
                            var_input.id,
                            asignacion.sucursal_id,
                            asignacion.cantidad_asignada
                        )
                
                logger.info(
                    f"Variante {var_input.id} actualizada: "
                    f"stock_web={total_stock_web}, visible={var_input.mostrar_en_web}, "
                    f"asignaciones={len(var_input.configuracion_stock)}"
                )
        
        logger.info(f"Producto {product_id} actualizado correctamente con {len(payload.variantes)} variantes")
        return updated_product

    except Exception as e:
        logger.error(f"Error actualizando producto {product_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- VIRTUAL STORE ENDPOINTS ---

@router.get("/", response_model=List[OnlineStoreProduct])
async def get_all_productos(
    branch_id: Optional[int] = Query(
        None, 
        description="ID de la sucursal para filtrar stock. Si es null, muestra el stock general de la web."
    )
):
    """
    Obtiene productos de la tienda online.
    - Si NO se envía branch_id: Usa el stock definido manualmente en WEB_VARIANTS.
    - Si SE envía branch_id: Usa el catálogo de WEB_VARIANTS pero muestra el stock real de WAREHOUSE_STOCK_VARIANTS para esa sucursal.
    """
    try:
        # 1. Definimos la consulta PRINCIPAL (Listado de productos)
        # Necesitamos calcular el "stock total" para la vista de tarjeta del producto
        
        if branch_id is None:
            # --- MODO GLOBAL (WEB) ---
            # Sumamos el stock manual configurado en WEB_VARIANTS
            query_products = """
                SELECT 
                    p.id,
                    p.nombre_web,
                    p.descripcion_web,
                    p.precio_web,
                    p.slug,
                    g.group_name,
                    COALESCE(g.group_name, 'Sin categoría') as category,
                    COALESCE(
                        ARRAY_AGG(DISTINCT i.image_url) FILTER (WHERE i.image_url IS NOT NULL),
                        ARRAY[]::TEXT[]
                    ) as images,
                    COALESCE(SUM(wv.displayed_stock), 0) as stock_disponible,
                    COALESCE(MAX(d.discount_percentage), 0) as discount_percentage
                FROM products p
                LEFT JOIN groups g ON p.group_id = g.id
                LEFT JOIN images i ON i.product_id = p.id
                LEFT JOIN web_variants wv ON wv.product_id = p.id AND wv.is_active = TRUE
                LEFT JOIN discounts d ON d.target_id = p.id AND d.discount_type = 'product' AND d.is_active = TRUE 
                    AND (d.start_date IS NULL OR d.start_date <= CURRENT_TIMESTAMP) 
                    AND (d.end_date IS NULL OR d.end_date >= CURRENT_TIMESTAMP)
                WHERE p.en_tienda_online = TRUE
                GROUP BY p.id, g.group_name
                ORDER BY p.id DESC
            """
            params_products = []
            
        else:
            # --- MODO SUCURSAL ---
            # Sumamos el stock real de WAREHOUSE_STOCK filtrado por sucursal
            # Notar que seguimos haciendo JOIN a web_variants para asegurar que solo traemos
            # productos que TIENEN variante web configurada.
            query_products = """
                SELECT 
                    p.id,
                    p.nombre_web,
                    p.descripcion_web,
                    p.precio_web,
                    p.slug,
                    COALESCE(g.group_name, 'Sin categoría') as category,
                    COALESCE(
                        ARRAY_AGG(DISTINCT i.image_url) FILTER (WHERE i.image_url IS NOT NULL),
                        ARRAY[]::TEXT[]
                    ) as images,
                    COALESCE(SUM(wsv.quantity), 0) as stock_disponible,
                    COALESCE(MAX(d.discount_percentage), 0) as discount_percentage
                FROM products p
                LEFT JOIN groups g ON p.group_id = g.id
                LEFT JOIN images i ON i.product_id = p.id
                LEFT JOIN web_variants wv ON wv.product_id = p.id AND wv.is_active = TRUE -- Usa LEFT JOIN para mostrar productos sin variantes aun
                LEFT JOIN warehouse_stock_variants wsv 
                    ON wsv.product_id = p.id 
                    AND wsv.size_id = wv.size_id 
                    AND wsv.color_id = wv.color_id
                    AND wsv.branch_id = $1 -- Filtramos por sucursal
                LEFT JOIN discounts d ON d.target_id = p.id AND d.discount_type = 'product' AND d.is_active = TRUE 
                    AND (d.start_date IS NULL OR d.start_date <= CURRENT_TIMESTAMP) 
                    AND (d.end_date IS NULL OR d.end_date >= CURRENT_TIMESTAMP)
                WHERE p.en_tienda_online = TRUE
                GROUP BY p.id, g.group_name
                ORDER BY p.id DESC
            """
            params_products = [branch_id]

        # Ejecutamos la consulta principal
        products = await db.fetch_all(query_products, *params_products)
        
        # 2. Iteramos para buscar las variantes (Detalle)
        result = []
        for product in products:
            product_dict = dict(product)
            
            if branch_id is None:
                # --- QUERY VARIANTES GLOBAL ---
                # Trae el stock manual de WEB_VARIANTS
                variants_query = """
                    SELECT 
                        wv.id as web_variant_id, -- Usamos el ID de la variante web
                        s.size_name as talle,
                        c.color_name as color,
                        c.color_hex,
                        wv.displayed_stock as stock, -- Stock manual
                        '' as barcode -- Opcional, o busca el barcode genérico
                    FROM web_variants wv
                    LEFT JOIN sizes s ON wv.size_id = s.id
                    LEFT JOIN colors c ON wv.color_id = c.id
                    WHERE wv.product_id = $1 AND wv.is_active = TRUE
                    ORDER BY s.size_name, c.color_name
                """
                variants = await db.fetch_all(variants_query, product['id'])
            
            else:
                # --- QUERY VARIANTES SUCURSAL ---
                # Cruza WEB_VARIANTS con WAREHOUSE_STOCK_VARIANTS
                variants_query = """
                    SELECT 
                        wv.id as web_variant_id,
                        s.size_name as talle,
                        c.color_name as color,
                        c.color_hex,
                        COALESCE(wsv.quantity, 0) as stock, -- Stock REAL de la sucursal
                        wsv.variant_barcode as barcode
                    FROM web_variants wv
                    LEFT JOIN sizes s ON wv.size_id = s.id
                    LEFT JOIN colors c ON wv.color_id = c.id
                    LEFT JOIN warehouse_stock_variants wsv 
                        ON wsv.product_id = wv.product_id 
                        AND wsv.size_id = wv.size_id 
                        AND wsv.color_id = wv.color_id
                        AND wsv.branch_id = $2  -- Parametro 2: ID Sucursal
                    WHERE wv.product_id = $1 AND wv.is_active = TRUE -- Parametro 1: ID Producto
                    ORDER BY s.size_name, c.color_name
                """
                variants = await db.fetch_all(variants_query, product['id'], branch_id)

            # Formateamos la respuesta de variantes
            product_dict['variantes'] = [
                {
                    "variant_id": v['web_variant_id'], # Importante: el ID ahora es el de WEB_VARIANTS
                    "talle": v['talle'],
                    "color": v['color'],
                    "color_hex": v['color_hex'],
                    "stock": v['stock'],
                    "barcode": v['barcode'] if v['barcode'] else "WEB-VAR"
                } 
                for v in variants
            ]
            
            result.append(product_dict)
        
        return result
        
    except Exception as e:
        # logger.error(f"Error fetching productos: {e}") 
        # Asegúrate de importar logger si lo usas
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener productos: {str(e)}"
        )


@router.get("/productsByGroup/{groupName}", response_model=List[OnlineStoreProduct])
async def get_productos_by_group(groupName: str):
    """
    Get products filtered by group name for the online store.
    Includes products from the specified group AND all its descendant groups (children, grandchildren, etc.).
    Only returns products where en_tienda_online = TRUE.
    
    Path Parameters:
    - groupName: The name of the group to filter by
    
    Returns:
    - List of online store products in the specified group and all descendant groups with images, stock, and variants
    
    Example:
    - If "Remeras" is selected, returns products from "Remeras", "Remeras Musculosas", "Remeras Mangas Largas", etc.
    - If "Remeras Mangas Largas" is selected, returns products from "Remeras Mangas Largas" and its children only
    """
    try:
        # First, get all descendant group IDs using recursive CTE
        descendant_groups_query = """
            WITH RECURSIVE group_tree AS (
                -- Base case: select the requested group
                SELECT id, group_name, parent_group_id
                FROM groups
                WHERE group_name = $1
                
                UNION ALL
                
                -- Recursive case: select all children
                SELECT g.id, g.group_name, g.parent_group_id
                FROM groups g
                INNER JOIN group_tree gt ON g.parent_group_id = gt.id
            )
            SELECT id FROM group_tree
        """
        
        descendant_groups = await db.fetch_all(descendant_groups_query, groupName)
        
        if not descendant_groups:
            # Group not found, return empty list
            return []
        
        # Extract group IDs
        group_ids = [g['id'] for g in descendant_groups]
        
        # Get products from all descendant groups
        # Build the query with dynamic IN clause
        placeholders = ', '.join([f'${i+1}' for i in range(len(group_ids))])
        
        query = f"""
            SELECT 
                p.id,
                p.nombre_web,
                p.descripcion_web,
                p.precio_web,
                p.slug,
                COALESCE(g.group_name, 'Sin categoría') as category,
                COALESCE(
                    ARRAY_AGG(DISTINCT i.image_url) FILTER (WHERE i.image_url IS NOT NULL),
                    ARRAY[]::TEXT[]
                ) as images,
                COALESCE(SUM(wsv.quantity), 0) as stock_disponible,
                COALESCE(MAX(d.discount_percentage), 0) as discount_percentage
            FROM products p
            LEFT JOIN groups g ON p.group_id = g.id
            LEFT JOIN images i ON i.product_id = p.id
            LEFT JOIN warehouse_stock_variants wsv ON wsv.product_id = p.id
            LEFT JOIN discounts d ON d.target_id = p.id AND d.discount_type = 'product' AND d.is_active = TRUE 
                AND (d.start_date IS NULL OR d.start_date <= CURRENT_TIMESTAMP) 
                AND (d.end_date IS NULL OR d.end_date >= CURRENT_TIMESTAMP)
            WHERE p.en_tienda_online = TRUE AND p.group_id IN ({placeholders})
            GROUP BY p.id, g.group_name
            ORDER BY p.id DESC
        """
        
        products = await db.fetch_all(query, *group_ids)
        
        # Get variants for each product
        result = []
        for product in products:
            product_dict = dict(product)
            
            # Get variants for this product
            variants_query = """
                SELECT 
                    wsv.id as variant_id,
                    s.size_name as talle,
                    c.color_name as color,
                    c.color_hex,
                    wsv.quantity as stock,
                    wsv.variant_barcode as barcode
                FROM warehouse_stock_variants wsv
                LEFT JOIN sizes s ON wsv.size_id = s.id
                LEFT JOIN colors c ON wsv.color_id = c.id
                WHERE wsv.product_id = $1 AND wsv.quantity > 0
                ORDER BY s.size_name, c.color_name
            """
            variants = await db.fetch_all(variants_query, product['id'])
            
            product_dict['variantes'] = [
                {
                    "variant_id": v['variant_id'],
                    "talle": v['talle'],
                    "color": v['color'],
                    "color_hex": v['color_hex'],
                    "stock": v['stock'],
                    "barcode": v['barcode']
                } 
                for v in variants
            ]
            
            result.append(product_dict)
        
        return result
        
    except Exception as e:
        logger.error(f"Error fetching productos by group {groupName}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener productos del grupo: {str(e)}"
        )


@router.get("/{product_id}", response_model=OnlineStoreProduct)
async def get_product(
    product_id: int,
    branch_id: Optional[int] = Query(None, description="ID de sucursal. Null = Stock Web manual.")
):
    try:
        # --- 1. DATOS PRINCIPALES DEL PRODUCTO ---
        # Usamos la misma lógica del listado: si hay sucursal, miramos stock físico global para el total, 
        # si no, miramos stock web manual.
        
        if branch_id is None:
            # Modo Web
            query_product = """
                SELECT 
                    p.id,
                    p.nombre_web,
                    p.descripcion_web,
                    p.precio_web,
                    p.slug,
                    COALESCE(g.group_name, 'Sin categoría') as category,
                    COALESCE(
                        ARRAY_AGG(DISTINCT i.image_url) FILTER (WHERE i.image_url IS NOT NULL),
                        '{}'
                    ) as images,
                    COALESCE(SUM(wv.displayed_stock), 0) as stock_disponible
                FROM products p
                LEFT JOIN groups g ON p.group_id = g.id
                LEFT JOIN images i ON i.product_id = p.id
                LEFT JOIN web_variants wv ON wv.product_id = p.id AND wv.is_active = TRUE
                WHERE p.id = $1 AND p.en_tienda_online = TRUE
                GROUP BY p.id, g.group_name
            """
            params_prod = [product_id]
        else:
            # Modo Sucursal
            query_product = """
                SELECT 
                    p.id,
                    p.nombre_web,
                    p.descripcion_web,
                    p.precio_web,
                    p.slug,
                    COALESCE(g.group_name, 'Sin categoría') as category,
                    COALESCE(
                        ARRAY_AGG(DISTINCT i.image_url) FILTER (WHERE i.image_url IS NOT NULL),
                        '{}'
                    ) as images,
                    COALESCE(SUM(wsv.quantity), 0) as stock_disponible
                FROM products p
                LEFT JOIN groups g ON p.group_id = g.id
                LEFT JOIN images i ON i.product_id = p.id
                JOIN web_variants wv ON wv.product_id = p.id AND wv.is_active = TRUE
                LEFT JOIN warehouse_stock_variants wsv 
                    ON wsv.product_id = p.id 
                    AND wsv.size_id = wv.size_id 
                    AND wsv.color_id = wv.color_id
                    AND wsv.branch_id = $2
                WHERE p.id = $1 AND p.en_tienda_online = TRUE
                GROUP BY p.id, g.group_name
            """
            params_prod = [product_id, branch_id]

        product = await db.fetch_one(query_product, *params_prod)

        if product is None:
            raise HTTPException(status_code=404, detail="Producto no encontrado")

        # --- 2. VARIANTES ---
        if branch_id is None:
            query_variants = """
                SELECT 
                    wv.id as variant_id,
                    s.size_name as talle,
                    c.color_name as color,
                    c.color_hex,
                    wv.displayed_stock as stock,
                    NULL as barcode
                FROM web_variants wv
                LEFT JOIN sizes s ON wv.size_id = s.id
                LEFT JOIN colors c ON wv.color_id = c.id
                WHERE wv.product_id = $1 AND wv.is_active = TRUE
                ORDER BY s.size_name, c.color_name
            """
            params_var = [product_id]
        else:
            query_variants = """
                SELECT 
                    wv.id as variant_id,
                    s.size_name as talle,
                    c.color_name as color,
                    c.color_hex,
                    COALESCE(wsv.quantity, 0) as stock,
                    wsv.variant_barcode as barcode
                FROM web_variants wv
                LEFT JOIN sizes s ON wv.size_id = s.id
                LEFT JOIN colors c ON wv.color_id = c.id
                LEFT JOIN warehouse_stock_variants wsv 
                    ON wsv.product_id = wv.product_id 
                    AND wsv.size_id = wv.size_id 
                    AND wsv.color_id = wv.color_id 
                    AND wsv.branch_id = $2
                WHERE wv.product_id = $1 AND wv.is_active = TRUE
                ORDER BY s.size_name, c.color_name
            """
            params_var = [product_id, branch_id]

        variants = await db.fetch_all(query_variants, *params_var)

        # Armamos respuesta usando el modelo OnlineStoreProduct
        product_dict = dict(product)
        product_dict['variantes'] = [dict(v) for v in variants]
        
        return product_dict

    except Exception as e:
        print(f"Error GET product: {e}")
        raise HTTPException(status_code=500, detail=str(e))



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
                has_discount, comments, state, 
                en_tienda_online, nombre_web, descripcion_web, slug, precio_web,
                creation_date
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, 
                    $17, $18, $19, $20, $21, CURRENT_TIMESTAMP)
            RETURNING id, product_name, description, cost, sale_price, provider_code,
                      group_id, provider_id, brand_id, tax, discount,
                      original_price, discount_percentage, discount_amount,
                      has_discount, comments, state, 
                      en_tienda_online, nombre_web, descripcion_web, slug, precio_web,
                      creation_date
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
            product.state,
            product.en_tienda_online,
            product.nombre_web,
            product.descripcion_web,
            product.slug,
            product.precio_web
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

"""
@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(product_id: int, product: ProductUpdate):
    """ """
    Update an existing product.
    
    Path Parameters:
    - product_id: The ID of the product to update
    
    Request Body:
    - ProductUpdate model with fields to update (all optional)
    """"""
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
        
        query = f""""""
            UPDATE products
            SET {', '.join(update_fields)}
            WHERE id = ${param_count}
            RETURNING id, product_name, description, cost, sale_price, provider_code,
                      group_id, provider_id, brand_id, tax, discount,
                      original_price, discount_percentage, discount_amount,
                      has_discount, comments, state, 
                      en_tienda_online, nombre_web, descripcion_web, slug, precio_web,
                      creation_date, last_modified_date
        """"""
        result = await db.fetch_one(query, *params)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating product {product_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar el producto: {str(e)}"
        ) """


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


# --- ONLINE STORE ENDPOINTS ---

@router.get("/online-store", response_model=List[OnlineStoreProduct])
async def get_online_store_products(
    category: Optional[str] = None,
    limit: Optional[int] = 50,
    offset: Optional[int] = 0
):
    """
    Get products available in the online store.
    Only returns products where en_tienda_online = TRUE and with available stock.
    
    Query Parameters:
    - category: Filter by product group name (optional)
    - limit: Maximum number of products to return (default: 50)
    - offset: Number of products to skip (default: 0)
    """
    try:
        query = """
            SELECT 
                p.id,
                p.nombre_web,
                p.descripcion_web,
                p.precio_web,
                p.slug,
                COALESCE(g.group_name, 'Sin categoría') as category,
                COALESCE(
                    ARRAY_AGG(i.image_url) FILTER (WHERE i.image_url IS NOT NULL),
                    ARRAY[]::TEXT[]
                ) as images,
                COALESCE(SUM(wsv.quantity), 0) as stock_disponible
            FROM products p
            LEFT JOIN groups g ON p.group_id = g.id
            LEFT JOIN images i ON i.product_id = p.id
            LEFT JOIN warehouse_stock_variants wsv ON wsv.product_id = p.id
            WHERE p.en_tienda_online = TRUE
        """
        params = []
        param_count = 1
        
        if category:
            query += f" AND g.group_name ILIKE ${param_count}"
            params.append(f"%{category}%")
            param_count += 1
        
        query += f"""
            GROUP BY p.id, g.group_name
            HAVING COALESCE(SUM(wsv.quantity), 0) > 0
            ORDER BY p.id DESC 
            LIMIT ${param_count} OFFSET ${param_count + 1}
        """
        params.extend([limit, offset])
        
        products = await db.fetch_all(query, *params)
        
        return products
        
    except Exception as e:
        logger.error(f"Error fetching online store products: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener productos de la tienda online: {str(e)}"
        )


@router.get("/online-store/{slug}", response_model=OnlineStoreProduct)
async def get_product_by_slug(slug: str):
    """
    Get a product by its slug for the online store.
    
    Path Parameters:
    - slug: The URL-friendly slug of the product
    """
    try:
        query = """
            SELECT 
                p.id,
                p.nombre_web,
                p.descripcion_web,
                p.precio_web,
                p.slug,
                COALESCE(g.group_name, 'Sin categoría') as category,
                COALESCE(
                    ARRAY_AGG(i.image_url) FILTER (WHERE i.image_url IS NOT NULL),
                    ARRAY[]::TEXT[]
                ) as images,
                COALESCE(SUM(wsv.quantity), 0) as stock_disponible
            FROM products p
            LEFT JOIN groups g ON p.group_id = g.id
            LEFT JOIN images i ON i.product_id = p.id
            LEFT JOIN warehouse_stock_variants wsv ON wsv.product_id = p.id
            WHERE p.slug = $1 AND p.en_tienda_online = TRUE
            GROUP BY p.id, g.group_name
        """
        
        product = await db.fetch_one(query, slug)
        
        if product is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Producto con slug '{slug}' no encontrado en la tienda online"
            )
        
        return product
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching product by slug {slug}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener el producto: {str(e)}"
        )


# --- IMAGE MANAGEMENT ENDPOINTS ---

@router.post("/{product_id}/images", response_model=ProductImage, status_code=status.HTTP_201_CREATED)
async def add_product_image(product_id: int, image_data: AddProductImage):
    """
    Add an image URL to a product.
    
    Path Parameters:
    - product_id: The ID of the product
    
    Request Body:
    - image_url: The URL of the image to add
    """
    try:
        # Check if product exists
        existing = await db.fetch_one("SELECT id FROM products WHERE id = $1", product_id)
        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Producto con ID {product_id} no encontrado"
            )
        
        # Insert the image
        query = """
            INSERT INTO images (product_id, image_url)
            VALUES ($1, $2)
            RETURNING id, image_url, product_id
        """
        
        result = await db.fetch_one(query, product_id, image_data.image_url)
        
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al agregar la imagen"
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding image to product {product_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al agregar la imagen: {str(e)}"
        )


@router.delete("/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product_image(image_id: int):
    """
    Delete an image from a product.
    
    Path Parameters:
    - image_id: The ID of the image to delete
    """
    try:
        # Check if image exists
        existing = await db.fetch_one("SELECT id FROM images WHERE id = $1", image_id)
        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Imagen con ID {image_id} no encontrada"
            )
        
        # Delete the image
        await db.execute("DELETE FROM images WHERE id = $1", image_id)
        
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting image {image_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar la imagen: {str(e)}"
        )

@router.get("/search-by-barcode/{barcode}", response_model=ProductResponse)
async def search_product_by_barcode(barcode: str):
    """
    Busca un producto por su código de barras.
    Busca primero en variant_barcode (warehouse_stock_variants) y luego en provider_code (products).
    """
    try:
        # 1. Intentar buscar por variant_barcode en warehouse_stock_variants
        query_variant = """
            SELECT product_id 
            FROM warehouse_stock_variants 
            WHERE variant_barcode = $1
            LIMIT 1
        """
        product_id = await db.fetch_val(query_variant, barcode)
        
        # 2. Si no se encuentra, intentar buscar por provider_code en products
        if not product_id:
            query_product_code = "SELECT id FROM products WHERE provider_code = $1"
            product_id = await db.fetch_val(query_product_code, barcode)
            
        if not product_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Producto con código de barras {barcode} no encontrado"
            )

        # 3. Obtener la información del producto
        query_product = """
            SELECT 
                id,
                product_name,
                description,
                cost,
                sale_price,
                provider_code,
                group_id,
                provider_id,
                brand_id,
                tax,
                discount,
                original_price,
                discount_percentage,
                discount_amount,
                has_discount,
                comments,
                state,
                en_tienda_online,
                nombre_web,
                descripcion_web,
                slug,
                precio_web,
                creation_date,
                last_modified_date,
                user_id
            FROM products
            WHERE id = $1
        """
        
        product = await db.fetch_one(query_product, product_id)
        
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Producto con ID {product_id} no encontrado"
            )
            
        return dict(product)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al buscar producto por barcode {barcode}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al buscar producto: {str(e)}"
        )

