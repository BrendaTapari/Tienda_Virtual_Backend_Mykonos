from fastapi import APIRouter, HTTPException, Depends
from schemas.barcode_schemas import ZPLRequest
from utils.zpl_service import ZPLService
from utils.auth import require_admin
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
zpl_service = ZPLService()

@router.post("/generate-zpl")
async def generate_zpl(request: ZPLRequest):
    """
    Genera código ZPL para imprimir en impresoras térmicas (Honeywell, Zebra, etc.)
    Access: Public (or add Depends(require_admin) if needed)
    """
    try:
        barcode = request.barcode
        product_info = request.product_info.dict() if request.product_info else {}
        options = request.options or {}

        if not barcode:
            raise HTTPException(status_code=400, detail="El campo 'barcode' es obligatorio")

        zpl_code = zpl_service.generate_barcode_zpl(barcode, product_info, options)
        zpl_base64 = zpl_service.generate_base64_zpl(barcode, product_info, options)

        return {
            "success": True,
            "zpl": zpl_code,
            "zpl_base64": zpl_base64,
            "barcode": barcode
        }

    except Exception as e:
        logger.error(f"Error generando ZPL: {e}")
        raise HTTPException(status_code=500, detail=f"Error generando ZPL: {str(e)}")
