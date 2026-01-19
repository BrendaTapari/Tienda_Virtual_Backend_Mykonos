from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
from config.db_connection import db
from models.branch_models import BranchResponse, BranchWithStock
from utils.auth import require_admin
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/all", response_model=List[BranchResponse])
async def get_all_branches():
    try:
        # The table name is 'storage' as per TABLES.STORAGE definition in database.py
        branches = await db.fetch_all("SELECT * FROM storage")
        return branches
    except Exception as e:
        logger.error(f"Error fetching all branches (admin): {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener todas las sucursales: {str(e)}"
        )
    

@router.get("/productsVariantsByBranch/{product_id}", response_model=List[BranchWithStock], dependencies=[Depends(require_admin)])
async def get_products_variants_by_branch(product_id: int):
    try:
        async with await db.transaction() as conn:
            
            unique_variants = await conn.fetch(
                """
                SELECT DISTINCT 
                    wsv.product_id,
                    wsv.size_id,
                    wsv.color_id
                FROM warehouse_stock_variants wsv
                WHERE wsv.product_id = $1
                """,
                product_id
            )
            
            
            for variant in unique_variants:
                await conn.execute(
                    """
                    INSERT INTO web_variants (product_id, size_id, color_id, displayed_stock, is_active)
                    VALUES ($1, $2, $3, 0, TRUE)
                    ON CONFLICT (product_id, size_id, color_id) DO NOTHING
                    """,
                    variant['product_id'],
                    variant['size_id'],
                    variant['color_id']
                )
            
            
            query = """
                SELECT 
                    s.id as branch_id,
                    s.name as branch_name,
                    wv.id as variant_id,
                    sz.size_name as size,
                    c.color_name as color,
                    c.color_hex as color_hex,
                    wsv.quantity,
                    wsv.variant_barcode as barcode,
                    COALESCE(wvba.cantidad_asignada, 0) as cantidad_web,
                    wv.is_active as mostrar_en_web
                FROM warehouse_stock_variants wsv
                JOIN storage s ON wsv.branch_id = s.id
                LEFT JOIN sizes sz ON wsv.size_id = sz.id
                LEFT JOIN colors c ON wsv.color_id = c.id
                JOIN web_variants wv 
                    ON wv.product_id = wsv.product_id 
                    AND wv.size_id = wsv.size_id 
                    AND wv.color_id = wsv.color_id
                LEFT JOIN web_variant_branch_assignment wvba
                    ON wvba.variant_id = wv.id AND wvba.branch_id = s.id
                WHERE wsv.product_id = $1
                ORDER BY s.id, sz.size_name, c.color_name
            """
            
            
            rows = await conn.fetch(query, product_id)

            # Fetch active discount with dates
            discount_info = await conn.fetchrow("""
                SELECT 
                    discount_percentage,
                    start_date,
                    end_date
                FROM discounts 
                WHERE discount_type='product' AND target_id=$1 AND is_active = TRUE
                AND (start_date IS NULL OR start_date <= CURRENT_TIMESTAMP) 
                AND (end_date IS NULL OR end_date >= CURRENT_TIMESTAMP)
                ORDER BY discount_percentage DESC
                LIMIT 1
            """, product_id)

            # Fetch group name
            group_name = await conn.fetchval("""
                SELECT g.group_name 
                FROM products p
                LEFT JOIN groups g ON p.group_id = g.id
                WHERE p.id = $1
            """, product_id)

            # Fetch provider name
            provider_name = await conn.fetchval("""
                SELECT e.entity_name 
                FROM products p
                LEFT JOIN entities e ON p.provider_id = e.id
                WHERE p.id = $1
            """, product_id)
        
        
        branches_dict = {}
        for row in rows:
            b_id = row['branch_id']
            if b_id not in branches_dict:
                branches_dict[b_id] = {
                    "branch_id": b_id,
                    "branch_name": row['branch_name'],
                    "variants": []
                }
            
            branches_dict[b_id]["variants"].append({
                "variant_id": row['variant_id'],
                "size": row['size'],
                "color": row['color'],
                "color_hex": row['color_hex'],
                "quantity": row['quantity'],
                "barcode": row['barcode'],
                "cantidad_web": row['cantidad_web'],
                "mostrar_en_web": row['mostrar_en_web']
            })
            
        # Assign discount to all branches
        result_list = list(branches_dict.values())
        
        disc_perc = 0
        disc_start = None
        disc_end = None
        
        if discount_info:
            disc_perc = discount_info['discount_percentage']
            disc_start = discount_info['start_date']
            disc_end = discount_info['end_date']
            
        for branch_data in result_list:
            branch_data["discount_percentage"] = disc_perc
            branch_data["discount_start_date"] = disc_start
            branch_data["discount_end_date"] = disc_end
            branch_data["group_name"] = group_name or "Sin categoría"
            branch_data["provider_name"] = provider_name or "Sin proveedor"
            
        return result_list

    except Exception as e:
        logger.error(f"Error fetching products variants by branch (admin): {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener los productos variantes por sucursal: {str(e)}"
        )

@router.get("/webProductsVariantsByBranch/{product_id}/{branch_id}", response_model=List[BranchWithStock])
async def get_web_products_variants_by_branch(product_id: int, branch_id: int):
    #Obtiene los productos variantes por sucursal y producto que tienen un stock web mayor a 0
    try:
        async with await db.transaction() as conn:
            # Check if branch exists
            branch_name = await conn.fetchval("SELECT name FROM storage WHERE id = $1", branch_id)
            if not branch_name:
                 raise HTTPException(status_code=404, detail="Sucursal no encontrada")

            query = """
                SELECT 
                    wv.id as variant_id,
                    sz.size_name as size,
                    c.color_name as color,
                    c.color_hex as color_hex,
                    COALESCE(wvba.cantidad_asignada, 0) as quantity,
                    wv.displayed_stock as cantidad_web,
                    wv.is_active as mostrar_en_web
                FROM web_variants wv
                LEFT JOIN web_variant_branch_assignment wvba 
                    ON wv.id = wvba.variant_id AND wvba.branch_id = $2
                LEFT JOIN sizes sz ON wv.size_id = sz.id
                LEFT JOIN colors c ON wv.color_id = c.id
                WHERE wv.product_id = $1
                ORDER BY sz.size_name, c.color_name
            """
            
            rows = await conn.fetch(query, product_id, branch_id)
            
            variants = []
            for row in rows:
                variants.append({
                    "variant_id": row['variant_id'],
                    "size": row['size'],
                    "color": row['color'],
                    "color_hex": row['color_hex'],
                    "quantity": row['quantity'], # This is the assigned stock for this branch
                    "barcode": None, # Not in web_variants
                    "cantidad_web": row['cantidad_web'],
                    "mostrar_en_web": row['mostrar_en_web']
                })
            
            return [{
                "branch_id": branch_id,
                "branch_name": branch_name,
                "variants": variants
            }]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching web products variants by branch: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener los productos variantes web por sucursal: {str(e)}"
        )