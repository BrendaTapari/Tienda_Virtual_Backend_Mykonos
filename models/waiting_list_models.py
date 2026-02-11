from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class WaitingListCreate(BaseModel):
    id_producto: int
    codigo_barra_variante: Optional[str] = None
    celular_cliente: str
    nombre_cliente: Optional[str] = None
    producto_buscado: str
    sucursal_referencia: Optional[str] = None
    # ID lists for relational tables
    talle_ids: Optional[List[int]] = None
    color_ids: Optional[List[int]] = None
    # Deprecated fields (keep for backward compatibility if needed, but preferred to be null)
    talle_buscado: Optional[str] = None 
    color_buscado: Optional[str] = None

    class Config:
        populate_by_name = True

class WaitingListResponse(BaseModel):
    id: int
    id_producto: int = Field(..., validation_alias="product_id")
    codigo_barra_variante: Optional[str] = None
    producto_buscado: str
    celular_cliente: str
    nombre_cliente: Optional[str] = None
    # Detailed info lists
    talles_detalle: Optional[List[Dict[str, Any]]] = None # List of {"id": int, "name": str}
    colores_detalle: Optional[List[Dict[str, Any]]] = None # List of {"id": int, "name": str, "hex": str}
    # Legacy fields
    talle_buscado: Optional[str] = None
    color_buscado: Optional[str] = None
    sucursal_referencia: Optional[str] = None
    notificado: bool
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        populate_by_name = True

class WaitingListStats(BaseModel):
    producto_buscado: str
    count: int
