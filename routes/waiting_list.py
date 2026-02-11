from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import List, Optional
from config.db_connection import db
from models.waiting_list_models import WaitingListCreate, WaitingListResponse, WaitingListStats
from utils.auth import require_admin
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/", response_model=WaitingListResponse, status_code=status.HTTP_201_CREATED)
async def create_waiting_list_request(request: WaitingListCreate):
    """
    Create a new waiting list request (Public).
    """
    try:
        # Get transaction context manager (must await the coroutine first)
        transaction_cm = await db.transaction()
        async with transaction_cm as conn:
            # 1. Insertar en la tabla principal
            query = """
                INSERT INTO lista_espera (
                    product_id, 
                    codigo_barra_variante,
                    celular_cliente, 
                    nombre_cliente, 
                    producto_buscado, 
                    sucursal_referencia, 
                    talle_buscado, 
                    color_buscado
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING id, product_id, codigo_barra_variante, celular_cliente, nombre_cliente, producto_buscado, 
                          sucursal_referencia, talle_buscado, color_buscado, notificado, created_at
            """
            
            # Use provided text or default to "Indistinto" if not provided and lists are empty
            talle_text = request.talle_buscado or "Indistinto"
            color_text = request.color_buscado or "Indistinto"
            
            # If lists are provided, we can generate a text representation for backward compatibility
            # strict=False avoids error if lists are None
            
            result = await conn.fetchrow(
                query,
                request.id_producto,
                request.codigo_barra_variante,
                request.celular_cliente,
                request.nombre_cliente,
                request.producto_buscado,
                request.sucursal_referencia,
                talle_text,
                color_text
            )
            
            waiting_list_id = result['id']
            
            # 2. Insertar talles relacionados
            if request.talle_ids:
                size_values = [(waiting_list_id, size_id) for size_id in request.talle_ids]
                await conn.executemany(
                    "INSERT INTO lista_espera_talles (waiting_list_id, size_id) VALUES ($1, $2)",
                    size_values
                )
                
            # 3. Insertar colores relacionados
            if request.color_ids:
                color_values = [(waiting_list_id, color_id) for color_id in request.color_ids]
                await conn.executemany(
                    "INSERT INTO lista_espera_colores (waiting_list_id, color_id) VALUES ($1, $2)",
                    color_values
                )
            
            # Fetch detailed response if needed, or just return the basic result + IDs
            response = dict(result)
            response['talle_ids'] = request.talle_ids
            response['color_ids'] = request.color_ids
            return response
    except Exception as e:
        logger.error(f"Error creating waiting list request: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear la solicitud: {str(e)}"
        )

@router.get("/", response_model=List[WaitingListResponse], dependencies=[Depends(require_admin)])
async def get_waiting_list(producto: Optional[str] = None):
    """
    Get all waiting list requests (Admin only).
    Optional filter by product name (partial match).
    """
    try:
        # Updated query to include relational data using JSON aggregation
        query = """
            SELECT 
                le.id, 
                le.product_id, 
                le.codigo_barra_variante,
                le.celular_cliente, 
                le.nombre_cliente, 
                le.producto_buscado, 
                le.sucursal_referencia, 
                le.talle_buscado, 
                le.color_buscado, 
                le.notificado, 
                le.created_at,
                COALESCE(
                    (
                        SELECT json_agg(json_build_object('id', s.id, 'name', s.size_name))
                        FROM lista_espera_talles let
                        JOIN sizes s ON s.id = let.size_id
                        WHERE let.waiting_list_id = le.id
                    ), '[]'
                ) as talles_detalle,
                COALESCE(
                    (
                        SELECT json_agg(json_build_object('id', c.id, 'name', c.color_name, 'hex', c.color_hex))
                        FROM lista_espera_colores lec
                        JOIN colors c ON c.id = lec.color_id
                        WHERE lec.waiting_list_id = le.id
                    ), '[]'
                ) as colores_detalle
            FROM lista_espera le
        """
        
        args = []
        if producto:
            query += " WHERE le.producto_buscado ILIKE $1"
            args.append(f"%{producto}%")
            
        query += " ORDER BY le.created_at DESC"
        
        rows = await db.fetch_all(query, *args)
        
        # Parse JSON strings if necessary (asyncpg usually returns them as strings or dicts depending on config)
        # But since we used json_agg, it likely comes as a string that Pydantic can parse if we pass it correctly.
        # However, to be safe, let's map it.
        import json
        result = []
        for row in rows:
            row_dict = dict(row)
            if isinstance(row_dict.get('talles_detalle'), str):
                 row_dict['talles_detalle'] = json.loads(row_dict['talles_detalle'])
            if isinstance(row_dict.get('colores_detalle'), str):
                 row_dict['colores_detalle'] = json.loads(row_dict['colores_detalle'])
            result.append(row_dict)
            
        return result
    except Exception as e:
        logger.error(f"Error fetching waiting list: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener la lista de espera: {str(e)}"
        )

@router.get("/stats", response_model=List[WaitingListStats], dependencies=[Depends(require_admin)])
async def get_waiting_list_stats():
    """
    Get top most requested products (Admin only).
    """
    try:
        query = """
            SELECT 
                producto_buscado, 
                COUNT(*) as count
            FROM lista_espera
            GROUP BY producto_buscado
            ORDER BY count DESC
        """
        rows = await db.fetch_all(query)
        return rows
    except Exception as e:
        logger.error(f"Error fetching waiting list stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener estadísticas: {str(e)}"
        )

@router.delete("/{request_id}", dependencies=[Depends(require_admin)])
async def delete_waiting_list_request(request_id: int):
    """
    Delete a waiting list request (Admin only).
    """
    try:
        # Check if exists
        exists = await db.fetch_val("SELECT id FROM lista_espera WHERE id = $1", request_id)
        if not exists:
            raise HTTPException(status_code=404, detail="Solicitud no encontrada")

        await db.execute("DELETE FROM lista_espera WHERE id = $1", request_id)
        return {"message": "Solicitud eliminada exitosamente"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting waiting list request: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar la solicitud: {str(e)}"
        )
