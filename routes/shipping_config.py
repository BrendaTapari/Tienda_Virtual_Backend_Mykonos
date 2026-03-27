"""
Routes for managing shipping configuration.
"""

from fastapi import APIRouter, HTTPException, Depends, status, Query
from config.db_connection import db
from models.shipping_config_models import ShippingConfigUpdate, ShippingConfigResponse
from utils.auth import require_admin
from utils.paqar_servides import PaqarClient, RateRequestDTO
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=ShippingConfigResponse)
@router.get("/", response_model=ShippingConfigResponse)
async def get_shipping_config():
    """
    Get current shipping configuration (Public).
    """
    try:
        query = "SELECT policy, free_threshold, provider_name, updated_at FROM shipping_config WHERE id = 1"
        config = await db.fetch_one(query)

        if not config:
            # If the row doesn't exist for some reason, insert the default and return it
            insert_query = """
                INSERT INTO shipping_config (id, policy, free_threshold, provider_name)
                VALUES (1, 'threshold', 0, 'Correo Argentino')
                ON CONFLICT (id) DO NOTHING
                RETURNING policy, free_threshold, provider_name, updated_at
            """
            config = await db.fetch_one(insert_query)
            # if conflict triggered and returning didn't work, fetch again
            if not config:
                 config = await db.fetch_one(query)

        return config
    except Exception as e:
        logger.error(f"Error fetching shipping config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener configuración de envíos: {str(e)}"
        )


@router.put("", response_model=ShippingConfigResponse, dependencies=[Depends(require_admin)])
@router.put("/", response_model=ShippingConfigResponse, dependencies=[Depends(require_admin)])
async def update_shipping_config(config_in: ShippingConfigUpdate):
    """
    Update shipping configuration (Admin only).
    """
    try:
        query = """
            UPDATE shipping_config
            SET policy = $1,
                free_threshold = $2,
                provider_name = $3,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = 1
            RETURNING policy, free_threshold, provider_name, updated_at
        """
        updated_config = await db.fetch_one(
            query,
            config_in.policy,
            config_in.free_threshold,
            config_in.provider_name
        )

        if not updated_config:
            # In case the row didn't exist
            insert_query = """
                INSERT INTO shipping_config (id, policy, free_threshold, provider_name, updated_at)
                VALUES (1, $1, $2, $3, CURRENT_TIMESTAMP)
                RETURNING policy, free_threshold, provider_name, updated_at
            """
            updated_config = await db.fetch_one(
                insert_query,
                config_in.policy,
                config_in.free_threshold,
                config_in.provider_name
            )

        return updated_config
    except Exception as e:
        logger.error(f"Error updating shipping config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar configuración de envíos: {str(e)}"
        )


@router.post("/rates")
async def quote_shipping_rates(request_dto: RateRequestDTO):
    """
    Endpoint para cotizar envíos.
    Recibe los datos del origen, destino, dimensiones y devuelve las tarifas disponibles
    consumiendo la API MiCorreo.
    """
    try:
        async with PaqarClient() as client:
            rates = await client.get_rates(request_dto)
            return {"rates": rates}
    except Exception as e:
        logger.error(f"Error al cotizar envío: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"No se pudo cotizar el envío con MiCorreo: {str(e)}"
        )


@router.get("/agencies")
async def get_agencies(customerId: str = Query(...), provinceCode: str = Query(...)):
    """
    Obtener sucursales activas de MiCorreo filtradas por provincia.
    """
    try:
        async with PaqarClient() as client:
            agencies = await client.get_agencies(customerId, provinceCode)
            return agencies
    except Exception as e:
        logger.error(f"Error consultando agencias: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener sucursales: {str(e)}"
        )


@router.get("/tracking")
async def get_tracking(shippingId: str = Query(...)):
    """
    Obtener tracking de transporte desde MiCorreo.
    El cliente frontend pasa el shippingId por query param,
    y el backend arma el body GET que pide la API MiCorreo.
    """
    try:
        async with PaqarClient() as client:
            events = await client.get_tracking(shippingId)
            return events
    except Exception as e:
        logger.error(f"Error consultando tracking: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al consultar el seguimiento: {str(e)}"
        )

