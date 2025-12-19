from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
from config.db_connection import db
from models.branch_models import BranchResponse, BranchWithStock
from utils.auth import require_admin
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/all", response_model=List[BranchResponse], dependencies=[Depends(require_admin)])
async def get_all_branches_admin():
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
            # 1. Obtener todas las combinaciones únicas de size/color del stock físico
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
            
            # 2. Crear web_variants si no existen
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
            
            # 3. Ahora consultar todo (ahora todas las variantes tendrán variant_id)
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
                    wv.displayed_stock as cantidad_web,
                    wv.is_active as mostrar_en_web
                FROM warehouse_stock_variants wsv
                JOIN storage s ON wsv.branch_id = s.id
                LEFT JOIN sizes sz ON wsv.size_id = sz.id
                LEFT JOIN colors c ON wsv.color_id = c.id
                JOIN web_variants wv 
                    ON wv.product_id = wsv.product_id 
                    AND wv.size_id = wsv.size_id 
                    AND wv.color_id = wsv.color_id
                WHERE wsv.product_id = $1
                ORDER BY s.id, sz.size_name, c.color_name
            """
            
            rows = await conn.fetch(query, product_id)
        
        # Group by branch
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
            
        return list(branches_dict.values())

    except Exception as e:
        logger.error(f"Error fetching products variants by branch (admin): {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener los productos variantes por sucursal: {str(e)}"
        )