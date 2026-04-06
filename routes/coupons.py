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
from utils.auth import require_admin

logger = logging.getLogger(__name__)

# Prefijo aplicado en main.py, por lo que acá no es estrictamente necesario,
# pero lo dejamos vacío o con el nombre necesario.
router = APIRouter()


def _normalize_dt(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    # Keep wall-clock time from client input; DB columns are TIMESTAMP (without tz).
    return value.replace(tzinfo=None) if value.tzinfo is not None else value


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
    description: Optional[str] = None
    type_id: int
    discount_value: float
    user_id: Optional[int] = None
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    usage_limit: int = 1
    is_active: bool = True


class CouponResponse(BaseModel):
    id: int
    code: str
    description: Optional[str] = None
    type_id: int
    type_name: Optional[str] = None
    discount_type: str
    discount_value: float
    user_id: Optional[int]
    valid_from: Optional[datetime]
    valid_until: Optional[datetime]
    usage_limit: int
    used_count: int
    is_active: bool
    deactivated_at: Optional[datetime] = None


# ==========================================
# RUTAS: Tipos de Cupones (La Regla)
# ==========================================


@router.get(
    "/admin/types",
    response_model=List[CouponTypeResponse],
    dependencies=[Depends(require_admin)],
)
@router.get(
    "/admin/types/",
    response_model=List[CouponTypeResponse],
    include_in_schema=False,
    dependencies=[Depends(require_admin)],
)
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


@router.post(
    "/admin/types",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
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
            detail=f"Failed to create coupon type: {str(e)}",
        )


# ==========================================
# RUTAS: Instancias de Cupones (Los Códigos)
# ==========================================


@router.post(
    "/admin/",
    response_model=CouponResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
@router.post(
    "/admin/",
    response_model=CouponResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
    dependencies=[Depends(require_admin)],
)
async def create_coupon(coupon_data: CouponCreate):
    """
    ALTA: Genera un nuevo código de cupón asignado a un tipo
    """
    try:
        # Verificar que el tipo exista y obtener su nombre
        ctype = await db.fetch_one(
            "SELECT id, name, discount_type FROM coupon_types WHERE id = $1",
            coupon_data.type_id,
        )
        if not ctype:
            raise HTTPException(status_code=404, detail="Coupon Type not found")

        # Verificar que el código no exista ya
        existing = await db.fetch_one(
            "SELECT id FROM coupons WHERE UPPER(code) = UPPER($1)", coupon_data.code
        )
        if existing:
            raise HTTPException(status_code=400, detail="Coupon code already exists")

        query = """
            INSERT INTO coupons (
                code,
                description,
                type_id,
                discount_value,
                user_id,
                valid_from,
                valid_until,
                usage_limit,
                used_count,
                is_active,
                deactivated_at
            )
            VALUES (
                $1,
                $2,
                $3,
                $4,
                $5,
                COALESCE($6, CURRENT_TIMESTAMP),
                $7,
                $8,
                0,
                $9,
                CASE WHEN $9 = FALSE THEN CURRENT_TIMESTAMP ELSE NULL END
            )
            RETURNING id, code, description, type_id, discount_value, user_id, valid_from, valid_until, usage_limit, used_count, is_active, deactivated_at
        """
        row = await db.fetch_one(
            query,
            coupon_data.code,
            coupon_data.description,
            coupon_data.type_id,
            coupon_data.discount_value,
            coupon_data.user_id,
            _normalize_dt(coupon_data.valid_from),
            _normalize_dt(coupon_data.valid_until),
            coupon_data.usage_limit,
            coupon_data.is_active,
        )

        result = dict(row)
        result["type_name"] = ctype["name"]
        result["discount_type"] = ctype["discount_type"]
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating coupon: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error creating coupon",
        )


@router.get(
    "",
    response_model=List[CouponResponse],
    dependencies=[Depends(require_admin)],
)
@router.get(
    "/admin/",
    response_model=List[CouponResponse],
    include_in_schema=False,
    dependencies=[Depends(require_admin)],
)
async def list_coupons(offset: int = 0, limit: int = 100):
    """
    CONSULTA: Lista todos los cupones generados
    """
    try:
        query = """
            SELECT 
                c.id, c.code, c.description, c.type_id, c.discount_value, c.user_id, c.valid_from, c.valid_until, c.usage_limit, c.used_count, c.is_active, c.deactivated_at,
                t.name as type_name, t.discount_type
            FROM coupons c
            LEFT JOIN coupon_types t ON c.type_id = t.id
            WHERE c.is_active = TRUE
               OR (
                    c.is_active = FALSE
                    AND c.deactivated_at IS NOT NULL
                    AND c.deactivated_at >= (CURRENT_TIMESTAMP - INTERVAL '7 days')
               )
            ORDER BY c.id DESC
            LIMIT $1 OFFSET $2
        """
        rows = await db.fetch_all(query, limit, offset)
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Error fetching coupons: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch coupons")


@router.put("/{coupon_id}/toggle-status", dependencies=[Depends(require_admin)])
@router.put(
    "/admin/{coupon_id}/toggle-status/",
    include_in_schema=False,
    dependencies=[Depends(require_admin)],
)
async def toggle_coupon_status(coupon_id: int):
    """
    MODIFICACIÓN / BAJA LÓGICA: Activa o desactiva un cupón
    """
    try:
        coupon = await db.fetch_one(
            "SELECT id, is_active FROM coupons WHERE id = $1", coupon_id
        )
        if not coupon:
            raise HTTPException(status_code=404, detail="Coupon not found")

        # Invertimos el estado (Baja lógica si pasa a False)
        new_status = not coupon["is_active"]
        await db.execute(
            """
            UPDATE coupons
            SET
                is_active = $1,
                deactivated_at = CASE
                    WHEN $1 = FALSE THEN CURRENT_TIMESTAMP
                    ELSE NULL
                END
            WHERE id = $2
            """,
            new_status,
            coupon_id,
        )

        estado = "activated" if new_status else "deactivated"
        return {"success": True, "message": f"Coupon successfully {estado}"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling coupon status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update coupon status",
        )


@router.delete("/{coupon_id}", dependencies=[Depends(require_admin)])
@router.delete(
    "/admin/{coupon_id}/",
    include_in_schema=False,
    dependencies=[Depends(require_admin)],
)
async def delete_coupon(coupon_id: int):
    """
    BAJA FÍSICA: Elimina un cupón permanentemente (solo usar si hubo error al crearlo)
    """
    try:
        coupon = await db.fetch_one(
            "SELECT id, used_count FROM coupons WHERE id = $1", coupon_id
        )
        if not coupon:
            raise HTTPException(status_code=404, detail="Coupon not found")

        if coupon["used_count"] > 0:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete a coupon that has already been used. Please deactivate it instead.",
            )

        await db.execute("DELETE FROM coupons WHERE id = $1", coupon_id)
        return {"success": True, "message": "Coupon permanently deleted"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting coupon: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete coupon",
        )


@router.get("/{coupon_code}", response_model=CouponResponse)
@router.get("/{coupon_code}/", response_model=CouponResponse, include_in_schema=False)
async def get_coupon_by_code(coupon_code: str):
    """
    CONSULTA: Obtiene los detalles de un cupón por su código
    """
    try:
        now = datetime.utcnow()
        query = """
            SELECT 
                c.id, c.code, c.description, c.type_id, c.discount_value, c.user_id, c.valid_from, c.valid_until, c.usage_limit, c.used_count, c.is_active, c.deactivated_at,
                t.name as type_name, t.discount_type
            FROM coupons c
            LEFT JOIN coupon_types t ON c.type_id = t.id
            WHERE UPPER(c.code) = UPPER($1)
        """
        row = await db.fetch_one(query, coupon_code)
        if not row:
            raise HTTPException(status_code=404, detail="Coupon not found")

        coupon = dict(row)

        if not coupon["is_active"]:
            raise HTTPException(status_code=400, detail="Coupon is inactive")

        valid_from = coupon.get("valid_from")
        valid_until = coupon.get("valid_until")

        # Normalize timestamps for safe comparison against utcnow() if DB returns tz-aware values.
        if valid_from and valid_from.tzinfo is not None:
            valid_from = valid_from.replace(tzinfo=None)
        if valid_until and valid_until.tzinfo is not None:
            valid_until = valid_until.replace(tzinfo=None)

        if valid_from and now < valid_from:
            raise HTTPException(status_code=400, detail="Coupon is not yet valid")

        if valid_until and now > valid_until:
            await db.execute(
                """
                UPDATE coupons
                SET is_active = FALSE, deactivated_at = COALESCE(deactivated_at, CURRENT_TIMESTAMP)
                WHERE id = $1
                """,
                coupon["id"],
            )
            raise HTTPException(status_code=400, detail="Coupon has expired")

        if coupon["used_count"] >= coupon["usage_limit"]:
            await db.execute(
                """
                UPDATE coupons
                SET is_active = FALSE, deactivated_at = COALESCE(deactivated_at, CURRENT_TIMESTAMP)
                WHERE id = $1
                """,
                coupon["id"],
            )
            raise HTTPException(status_code=400, detail="Coupon usage limit reached")

        return coupon

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching coupon by code: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch coupon details")


@router.put("/{coupon_id}", response_model=CouponResponse)
@router.put("/{coupon_id}/", response_model=CouponResponse, include_in_schema=False)
async def used_cupon(coupon_id: int):
    """
    MODIFICACIÓN: Marca un cupón como usado (incrementa used_count)
    """
    try:
        coupon = await db.fetch_one(
            "SELECT id, usage_limit, used_count, is_active FROM coupons WHERE id = $1",
            coupon_id,
        )
        if not coupon:
            raise HTTPException(status_code=404, detail="Coupon not found")

        if not coupon["is_active"]:
            raise HTTPException(status_code=400, detail="Coupon is inactive")

        if coupon["used_count"] >= coupon["usage_limit"]:
            # If limit is already reached, ensure coupon is inactive.
            await db.execute(
                """
                UPDATE coupons
                SET is_active = FALSE, deactivated_at = COALESCE(deactivated_at, CURRENT_TIMESTAMP)
                WHERE id = $1
                """,
                coupon_id,
            )
            raise HTTPException(status_code=400, detail="Coupon usage limit reached")

        # Increment usage and deactivate in the same statement when limit is reached.
        updated_coupon = await db.fetch_one(
            """
            UPDATE coupons
            SET
                used_count = used_count + 1,
                is_active = CASE
                    WHEN used_count + 1 >= usage_limit THEN FALSE
                    ELSE is_active
                END,
                deactivated_at = CASE
                    WHEN used_count + 1 >= usage_limit THEN COALESCE(deactivated_at, CURRENT_TIMESTAMP)
                    ELSE deactivated_at
                END
            WHERE id = $1
            RETURNING
                id,
                code,
                description,
                type_id,
                (SELECT name FROM coupon_types WHERE id = coupons.type_id) AS type_name,
                (SELECT discount_type FROM coupon_types WHERE id = coupons.type_id) AS discount_type,
                discount_value,
                user_id,
                valid_from,
                valid_until,
                usage_limit,
                used_count,
                is_active,
                deactivated_at
            """,
            coupon_id,
        )

        return dict(updated_coupon)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking coupon as used: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update coupon usage",
        )
