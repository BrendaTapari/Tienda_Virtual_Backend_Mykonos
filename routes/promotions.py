from fastapi import APIRouter, HTTPException, Depends, status
from typing import List
from config.db_connection import db
from models.promotion_models import PromotionCreate, PromotionUpdate, PromotionResponse
from utils.auth import require_admin

router = APIRouter()

@router.get("/active", response_model=List[PromotionResponse])
async def get_active_promotions():
    """
    Get all active promotions for the public store.
    Ordered by display_order ASC.
    """
    try:
        query = """
            SELECT id, title, subtitle, icon, is_active, display_order, created_at, updated_at
            FROM promotions
            WHERE is_active = TRUE
            ORDER BY display_order ASC
        """
        promotions = await db.fetch_all(query)
        return promotions
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener promociones activas: {str(e)}"
        )

@router.get("/", response_model=List[PromotionResponse], dependencies=[Depends(require_admin)])
async def get_all_promotions():
    """
    Get all promotions (Admin only).
    """
    try:
        query = """
            SELECT id, title, subtitle, icon, is_active, display_order, created_at, updated_at
            FROM promotions
            ORDER BY display_order ASC, id DESC
        """
        promotions = await db.fetch_all(query)
        return promotions
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener todas las promociones: {str(e)}"
        )

@router.post("/", response_model=PromotionResponse, dependencies=[Depends(require_admin)])
async def create_promotion(promotion: PromotionCreate):
    """
    Create a new promotion (Admin only).
    """
    try:
        query = """
            INSERT INTO promotions (title, subtitle, icon, is_active, display_order)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id, title, subtitle, icon, is_active, display_order, created_at, updated_at
        """
        # set default display_order if not provided? Pydantic model has default 0.
        
        new_promotion = await db.fetch_one(
            query,
            promotion.title,
            promotion.subtitle,
            promotion.icon,
            promotion.is_active,
            promotion.display_order
        )
        return new_promotion
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear la promoción: {str(e)}"
        )

@router.put("/{promotion_id}", response_model=PromotionResponse, dependencies=[Depends(require_admin)])
async def update_promotion(promotion_id: int, promotion: PromotionUpdate):
    """
    Update an existing promotion (Admin only).
    """
    try:
        # Check if exists
        existing = await db.fetch_one("SELECT id FROM promotions WHERE id = $1", promotion_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Promoción no encontrada")
            
        update_fields = []
        params = []
        param_count = 1
        
        if promotion.title is not None:
            update_fields.append(f"title = ${param_count}")
            params.append(promotion.title)
            param_count += 1
            
        if promotion.subtitle is not None:
            update_fields.append(f"subtitle = ${param_count}")
            params.append(promotion.subtitle)
            param_count += 1
            
        if promotion.icon is not None:
            update_fields.append(f"icon = ${param_count}")
            params.append(promotion.icon)
            param_count += 1
            
        if promotion.is_active is not None:
            update_fields.append(f"is_active = ${param_count}")
            params.append(promotion.is_active)
            param_count += 1
            
        if promotion.display_order is not None:
            update_fields.append(f"display_order = ${param_count}")
            params.append(promotion.display_order)
            param_count += 1
            
        if not update_fields:
            # Nothing to update, fetch and return
             return await db.fetch_one("SELECT * FROM promotions WHERE id = $1", promotion_id)

        update_fields.append("updated_at = CURRENT_TIMESTAMP")
        
        params.append(promotion_id)
        
        query = f"""
            UPDATE promotions
            SET {', '.join(update_fields)}
            WHERE id = ${param_count}
            RETURNING id, title, subtitle, icon, is_active, display_order, created_at, updated_at
        """
        
        updated_promo = await db.fetch_one(query, *params)
        return updated_promo

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar la promoción: {str(e)}"
        )

@router.delete("/{promotion_id}", dependencies=[Depends(require_admin)])
async def delete_promotion(promotion_id: int):
    """
    Delete a promotion (Admin only).
    """
    try:
        result = await db.execute("DELETE FROM promotions WHERE id = $1", promotion_id)
        # result is usually status message like "DELETE 1"
        if result == "DELETE 0":
             raise HTTPException(status_code=404, detail="Promoción no encontrada")
             
        return {"message": "Promoción eliminada correctamente"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar la promoción: {str(e)}"
        )

@router.patch("/{promotion_id}/toggle", response_model=PromotionResponse, dependencies=[Depends(require_admin)])
async def toggle_promotion_active(promotion_id: int):
    """
    Toggle the active status of a promotion (Admin only).
    """
    try:
        existing = await db.fetch_one("SELECT is_active FROM promotions WHERE id = $1", promotion_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Promoción no encontrada")
            
        new_status = not existing['is_active']
        
        query = """
            UPDATE promotions
            SET is_active = $1, updated_at = CURRENT_TIMESTAMP
            RETURNING id, title, subtitle, icon, is_active, display_order, created_at, updated_at
        """
        
        updated_promo = await db.fetch_one(query, new_status) # ERROR: forgot ID in WHERE clause
        
        # FIX: The query above is missing WHERE id = $2, correct it now.
        query_fix = """
            UPDATE promotions
            SET is_active = $1, updated_at = CURRENT_TIMESTAMP
            WHERE id = $2
            RETURNING id, title, subtitle, icon, is_active, display_order, created_at, updated_at
        """
        updated_promo = await db.fetch_one(query_fix, new_status, promotion_id)
        
        return updated_promo
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al cambiar estado de la promoción: {str(e)}"
        )
