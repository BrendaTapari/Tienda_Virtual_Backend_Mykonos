"""
Coupons routes
Handles CRUD (ABMC) operations for discount coupons and coupon types
"""

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import logging

from config.db_connection import db

logger = logging.getLogger(__name__)

# Prefijo aplicado en main.py, por lo que acá no es estrictamente necesario,
# pero lo dejamos vacío o con el nombre necesario.
router = APIRouter()

# ==========================================
# DTOs / Schemas (Pydantic)
# ==========================================

class CouponTypeCreate(BaseModel):
    name: str
    discount_type: str  # 'percentage', 'fixed_amount', 'free_shipping'

class CouponTypeResponse(BaseModel):
    id: int
    name: str
    discount_type: str
    created_at: Optional[datetime] = None

class CouponCreate(BaseModel):
    code: str
    type_id: int
    discount_value: float
    user_id: Optional[int] = None
    valid_until: Optional[datetime] = None
    usage_limit: int = 1

class CouponResponse(BaseModel):
    id: int
    code: str
    type_id: int
    discount_type: str
    discount_value: float
    user_id: Optional[int]
    valid_from: Optional[datetime]
    valid_until: Optional[datetime]
    usage_limit: int
    used_count: int
    is_active: bool

# ==========================================
# RUTAS: Tipos de Cupones (La Regla)
# ==========================================

@router.get("/types", response_model=List[CouponTypeResponse])
@router.get("/types/", response_model=List[CouponTypeResponse], include_in_schema=False)
async def list_coupon_types(limit: int = 100, offset: int = 0):
    """
    CONSULTA: Lista todas las reglas/tipos de cupón disponibles
    """
    try:
        query = "SELECT id, name, discount_type, created_at FROM coupon_types ORDER BY id DESC LIMIT $1 OFFSET $2"
        rows = await db.fetch_all(query, limit, offset)
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Error fetching coupon types: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch coupon types")

@router.post("/types", status_code=status.HTTP_201_CREATED)
async def create_coupon_type(type_data: CouponTypeCreate):
    """
    ALTA: Crea un nuevo TIPO de cupón (Regla de negocio)
    """
    try:
        query = """
            INSERT INTO coupon_types (name, discount_type)
            VALUES ($1, $2)
            RETURNING id
        """
        row = await db.fetch_one(query, type_data.name, type_data.discount_type)
        return {"success": True, "message": "Coupon type created", "id": row["id"]}
        
    except Exception as e:
        logger.error(f"Error creating coupon type: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create coupon type: {str(e)}"
        )

# ==========================================
# RUTAS: Instancias de Cupones (Los Códigos)
# ==========================================

@router.post("", response_model=CouponResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=CouponResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
async def create_coupon(coupon_data: CouponCreate):
    """
    ALTA: Genera un nuevo código de cupón asignado a un tipo
    """
    try:
        # Verificar que el tipo exista y obtener su nombre
        ctype = await db.fetch_one("SELECT id, discount_type FROM coupon_types WHERE id = $1", coupon_data.type_id)
        if not ctype:
            raise HTTPException(status_code=404, detail="Coupon Type not found")

        # Verificar que el código no exista ya
        existing = await db.fetch_one("SELECT id FROM coupons WHERE code = $1", coupon_data.code)
        if existing:
            raise HTTPException(status_code=400, detail="Coupon code already exists")

        query = """
            INSERT INTO coupons (code, type_id, discount_value, user_id, valid_until, usage_limit, used_count, is_active)
            VALUES ($1, $2, $3, $4, $5, $6, 0, TRUE)
            RETURNING id, code, type_id, discount_value, user_id, valid_from, valid_until, usage_limit, used_count, is_active
        """
        row = await db.fetch_one(
            query, 
            coupon_data.code, 
            coupon_data.type_id,
            coupon_data.discount_value,
            coupon_data.user_id, 
            coupon_data.valid_until.replace(tzinfo=None) if coupon_data.valid_until else None, 
            coupon_data.usage_limit
        )
        
        result = dict(row)
        result["discount_type"] = ctype["discount_type"]
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating coupon: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error creating coupon"
        )

@router.get("", response_model=List[CouponResponse])
@router.get("/", response_model=List[CouponResponse], include_in_schema=False)
async def list_coupons(offset: int = 0, limit: int = 100):
    """
    CONSULTA: Lista todos los cupones generados
    """
    try:
        query = """
            SELECT 
                c.id, c.code, c.type_id, c.discount_value, c.user_id, c.valid_from, c.valid_until, c.usage_limit, c.used_count, c.is_active,
                t.discount_type
            FROM coupons c
            LEFT JOIN coupon_types t ON c.type_id = t.id
            ORDER BY c.id DESC
            LIMIT $1 OFFSET $2
        """
        rows = await db.fetch_all(query, limit, offset)
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Error fetching coupons: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch coupons")

@router.put("/{coupon_id}/toggle-status")
@router.put("/{coupon_id}/toggle-status/", include_in_schema=False)
async def toggle_coupon_status(coupon_id: int):
    """
    MODIFICACIÓN / BAJA LÓGICA: Activa o desactiva un cupón
    """
    try:
        coupon = await db.fetch_one("SELECT id, is_active FROM coupons WHERE id = $1", coupon_id)
        if not coupon:
            raise HTTPException(status_code=404, detail="Coupon not found")

        # Invertimos el estado (Baja lógica si pasa a False)
        new_status = not coupon["is_active"]
        await db.execute("UPDATE coupons SET is_active = $1 WHERE id = $2", new_status, coupon_id)
        
        estado = "activated" if new_status else "deactivated"
        return {"success": True, "message": f"Coupon successfully {estado}"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling coupon status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update coupon status"
        )

@router.delete("/{coupon_id}")
@router.delete("/{coupon_id}/", include_in_schema=False)
async def delete_coupon(coupon_id: int):
    """
    BAJA FÍSICA: Elimina un cupón permanentemente (solo usar si hubo error al crearlo)
    """
    try:
        coupon = await db.fetch_one("SELECT id, used_count FROM coupons WHERE id = $1", coupon_id)
        if not coupon:
            raise HTTPException(status_code=404, detail="Coupon not found")

        if coupon["used_count"] > 0:
            raise HTTPException(
                status_code=400, 
                detail="Cannot delete a coupon that has already been used. Please deactivate it instead."
            )

        await db.execute("DELETE FROM coupons WHERE id = $1", coupon_id)
        return {"success": True, "message": "Coupon permanently deleted"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting coupon: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete coupon"
        )