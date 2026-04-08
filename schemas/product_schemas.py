from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime

# --- SCHEMAS (Pydantic) ---

class StockSucursalInput(BaseModel):
    sucursal_id: int
    cantidad_asignada: int

class VarianteUpdateInput(BaseModel):
    id: int
    mostrar_en_web: bool
    configuracion_stock: List[StockSucursalInput]

class ProductoUpdateSchema(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None          # descripcion_web
    alt_text: Optional[str] = None             # texto alternativo de imagen (SEO)
    base_description: Optional[str] = None     # descripción larga / ficha técnica base
    technical_details: Optional[str] = None    # detalles técnicos del producto
    precio_web: Optional[float] = None
    en_tienda_online: Optional[bool] = None
    variantes: Optional[List[VarianteUpdateInput]] = []
    discount_percentage: Optional[float] = 0
    discount_start_date: Optional[datetime] = None
    discount_end_date: Optional[datetime] = None

    # Configuración V2
    model_config = ConfigDict(from_attributes=True)